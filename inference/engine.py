from __future__ import annotations

import gc
import logging
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol, runtime_checkable

import torch
from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer, AutoProcessor

from .attention import AttentionCapture
from .chat import ChatRenderer
from .sampler import Sampler, SamplingParams

QuantizationMode = str | None  # "4bit", "8bit", or None

log = logging.getLogger(__name__)


@runtime_checkable
class InferenceEngine(Protocol):
    """Protocol that any backend must satisfy."""

    def load(
        self,
        model_path: str,
        *,
        dtype: torch.dtype = torch.bfloat16,
        device: str = "cuda",
        quantization: QuantizationMode = None,
    ) -> None: ...

    def generate(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        *,
        max_new_tokens: int = 4096,
        temperature: float = 0.6,
        top_p: float = 0.95,
        stream: bool = True,
        token_importance: bool = False,
        token_importance_interval: int = 8,
    ) -> Iterator[str]: ...

    def get_attention_weights(self) -> list[tuple[int, torch.Tensor]] | None: ...


def _cuda_cleanup() -> None:
    """Release stale GPU memory back to the CUDA allocator."""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _cuda_mem_mb() -> tuple[float, float]:
    """Return (allocated_MiB, reserved_MiB) on device 0, or (0,0) if no CUDA."""
    if not torch.cuda.is_available():
        return 0.0, 0.0
    return (
        torch.cuda.memory_allocated(0) / (1024 * 1024),
        torch.cuda.memory_reserved(0) / (1024 * 1024),
    )


def _accumulate_attention_importance(
    scores: torch.Tensor,
    attentions,
    *,
    key_count: int,
) -> int:
    """Add attention received by prior KV entries from the current future query.

    The score estimates how much each token's KV entry is used to predict later
    tokens. Deeper layers get slightly more weight because their attention is
    closer to the logits, and low-entropy heads get slightly more weight because
    focused routing is usually a stronger attribution signal than diffuse mass.
    """
    if not attentions:
        return 0

    device = scores.device
    total = torch.zeros(key_count, dtype=torch.float32, device=device)
    total_weight = 0.0
    layer_count = len(attentions)

    for layer_idx, attn in enumerate(attentions):
        if not isinstance(attn, torch.Tensor) or attn.numel() == 0:
            continue
        # Expected shape: (batch, heads, query_len, key_len). Use only the
        # newest-query slice. Slicing before conversion avoids materializing a
        # full fp32 copy of every layer's attention tensor on the GPU.
        if attn.ndim != 4:
            continue
        vec = attn.detach()[0, :, -1, :key_count].to(device=device, dtype=torch.float32)
        if vec.numel() == 0:
            continue

        eps = 1e-8
        head_entropy = -(vec.clamp_min(eps) * vec.clamp_min(eps).log()).sum(dim=-1)
        max_entropy = max(1.0, float(torch.log(torch.tensor(vec.shape[-1], dtype=torch.float32)).item()))
        focus = (1.0 - head_entropy / max_entropy).clamp(0.15, 1.0)
        head_mean = (vec * focus[:, None]).sum(dim=0) / focus.sum().clamp_min(eps)
        layer_weight = 0.65 + 0.35 * ((layer_idx + 1) / max(1, layer_count))
        total += head_mean.to(device) * layer_weight
        total_weight += layer_weight

    if total_weight <= 0:
        return 0

    scores[:key_count] += total / total_weight
    return 1


def _normalize_importance(raw_scores: torch.Tensor) -> list[float]:
    if raw_scores.numel() == 0:
        return []
    scores = raw_scores.float().clamp_min(0)
    positive = scores[scores > 0]
    if positive.numel() == 0:
        return [0.0 for _ in range(scores.numel())]
    high = torch.quantile(positive, 0.95).clamp_min(1e-8)
    normalized = (scores / high).clamp(0, 1)
    return [round(float(x), 4) for x in normalized.tolist()]


def _build_token_importance_payload(
    *,
    token_ids: list[int],
    prompt_len: int,
    raw_scores: torch.Tensor,
    renderer: ChatRenderer,
    observations: int,
) -> dict:
    normalized = _normalize_importance(raw_scores)
    raw = [round(float(x), 6) for x in raw_scores.tolist()]
    tokens = []
    for i, token_id in enumerate(token_ids):
        tokens.append(
            {
                "id": i,
                "token_id": int(token_id),
                "text": renderer.decode([int(token_id)], skip_special=False),
                "score": normalized[i] if i < len(normalized) else 0.0,
                "raw_score": raw[i] if i < len(raw) else 0.0,
                "source": "prompt" if i < prompt_len else "generated",
            }
        )
    return {
        "label": "Future attention importance",
        "method": "attention_received_by_future_decode_queries",
        "observations": observations,
        "prompt_tokens": prompt_len,
        "generated_tokens": max(0, len(token_ids) - prompt_len),
        "tokens": tokens,
    }


class LocalEngine:
    """Load any HuggingFace-compatible model and generate token-by-token.

    Provides direct access to attention layers for research purposes.
    """

    def __init__(self) -> None:
        self.model: torch.nn.Module | None = None
        self.tokenizer: AutoTokenizer | None = None
        self.renderer: ChatRenderer | None = None
        self.attention: AttentionCapture | None = None
        self.device: str = "cuda"
        self.dtype: torch.dtype = torch.bfloat16
        self._model_path: str | None = None
        self._quantization: QuantizationMode = None
        self._last_generation_stats: dict | None = None
        self._last_token_importance: dict | None = None

    @property
    def loaded(self) -> bool:
        return self.model is not None

    @property
    def last_generation_stats(self) -> dict | None:
        return self._last_generation_stats

    @property
    def last_token_importance(self) -> dict | None:
        return self._last_token_importance

    def load(
        self,
        model_path: str,
        *,
        dtype: torch.dtype = torch.bfloat16,
        device: str = "cuda",
        quantization: QuantizationMode = None,
    ) -> None:
        log.info(
            "Loading model from %s (dtype=%s, device=%s, quantization=%s)",
            model_path, dtype, device, quantization or "none",
        )

        if self.model is not None:
            log.info("Unloading previous model before loading new one")
            self.model = None
            self.attention = None
            _cuda_cleanup()

        self.device = device
        self.dtype = dtype
        self._model_path = model_path
        self._quantization = quantization

        config = AutoConfig.from_pretrained(model_path, trust_remote_code=True)
        # Token-importance capture requires attention tensors. Transformers'
        # SDPA path refuses output_attentions=True, so load with eager attention.
        if hasattr(config, "attn_implementation"):
            config.attn_implementation = "eager"
        if hasattr(config, "_attn_implementation"):
            config._attn_implementation = "eager"

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_path, trust_remote_code=True
            )
        except Exception:
            processor = AutoProcessor.from_pretrained(
                model_path, trust_remote_code=True
            )
            self.tokenizer = processor.tokenizer

        self.renderer = ChatRenderer(self.tokenizer)

        model_cls = self._resolve_model_class(config)
        quant_config = self._build_quant_config(quantization)

        load_kwargs: dict = {
            "config": config,
            "torch_dtype": dtype,
            "trust_remote_code": True,
            "attn_implementation": "eager",
        }

        if quant_config is not None:
            load_kwargs["quantization_config"] = quant_config
            load_kwargs["device_map"] = "auto"
        else:
            load_kwargs["device_map"] = device if device != "cpu" else None

        self.model = model_cls.from_pretrained(model_path, **load_kwargs)

        if quant_config is None:
            if device == "cpu" or (device == "cuda" and not hasattr(self.model, "hf_device_map")):
                self.model = self.model.to(device)

        self.model.eval()
        self.attention = AttentionCapture(self.model)

        param_count = sum(p.numel() for p in self.model.parameters())
        log.info("Model loaded: %s parameters", f"{param_count:,}")
        if quantization:
            trainable = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
            log.info("Quantization: %s  (trainable params: %s)", quantization, f"{trainable:,}")

    def generate(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        *,
        max_new_tokens: int = 4096,
        temperature: float = 0.6,
        top_p: float = 0.95,
        stream: bool = True,
        token_importance: bool = False,
        token_importance_interval: int = 8,
    ) -> Iterator[str]:
        assert self.model is not None and self.renderer is not None
        assert self.tokenizer is not None

        _cuda_cleanup()
        alloc_before, _ = _cuda_mem_mb()

        input_ids = self.renderer.render(messages, tools=tools)
        prompt_len = len(input_ids)
        input_tensor = torch.tensor([input_ids], device=self.device, dtype=torch.long)
        self._last_token_importance = None
        importance_scores: torch.Tensor | None = (
            torch.zeros(prompt_len + max_new_tokens, dtype=torch.float32)
            if token_importance
            else None
        )
        importance_observations = 0

        sampler = Sampler(SamplingParams(temperature=temperature, top_p=top_p))
        eos_ids = self._get_eos_ids()
        vocab_size = int(self.model.config.vocab_size) if hasattr(self.model.config, "vocab_size") else None

        generated: list[int] = []
        forward_passes = 0
        stop_reason = "max_tokens"
        t_start = time.perf_counter()
        past = None

        try:
            with torch.no_grad():
                # -- Prefill: process the entire prompt, get first token --
                forward_passes += 1
                outputs = self.model(
                    input_ids=input_tensor,
                    use_cache=True,
                    output_attentions=False,
                )
                logits = outputs.logits[:, -1, :]
                past = outputs.past_key_values

                del outputs, input_tensor
                # logits is a small (1, vocab) slice -- keep it for sampling

                token_id = sampler.sample(logits[0], generated)
                del logits
                generated.append(token_id)

                text = self.renderer.decode([token_id], skip_special=False)
                if stream:
                    yield text

                # -- Decode: one token at a time, reusing KV cache --
                for _ in range(max_new_tokens - 1):
                    next_input = torch.tensor([[token_id]], device=self.device, dtype=torch.long)
                    forward_passes += 1
                    capture_importance = (
                        importance_scores is not None
                        and token_importance_interval > 0
                        and len(generated) % token_importance_interval == 0
                    )
                    outputs = self.model(
                        input_ids=next_input,
                        past_key_values=past,
                        use_cache=True,
                        output_attentions=capture_importance,
                    )
                    if capture_importance:
                        importance_observations += _accumulate_attention_importance(
                            importance_scores,
                            outputs.attentions,
                            key_count=prompt_len + len(generated),
                        )
                    logits = outputs.logits[:, -1, :]
                    past = outputs.past_key_values
                    del outputs

                    token_id = sampler.sample(logits[0], generated)
                    del logits

                    if token_id in eos_ids:
                        stop_reason = "eos"
                        break

                    generated.append(token_id)
                    text = self.renderer.decode([token_id], skip_special=False)
                    if stream:
                        yield text

            if not stream:
                yield self.renderer.decode(generated)

        finally:
            # Deterministic cleanup: drop the KV cache immediately
            del past
            _cuda_cleanup()

        t_elapsed = time.perf_counter() - t_start
        alloc_after, _ = _cuda_mem_mb()
        completion_tokens = len(generated)
        n = completion_tokens
        head_n, tail_n = 32, 16
        tok_per_sec = completion_tokens / t_elapsed if t_elapsed > 0 else 0

        self._last_generation_stats = {
            "prompt_tokens": prompt_len,
            "completion_tokens": completion_tokens,
            "total_new_tokens": completion_tokens,
            "sequence_length_after": prompt_len + completion_tokens,
            "forward_passes": forward_passes,
            "max_new_tokens_requested": max_new_tokens,
            "stop_reason": stop_reason,
            "temperature": temperature,
            "top_p": top_p,
            "vocab_size": vocab_size,
            "device": self.device,
            "dtype": str(self.dtype),
            "decode_utf8_chars": len(self.renderer.decode(generated, skip_special=False)),
            "generated_token_ids_count": n,
            "generated_token_ids_head": generated[:head_n],
            "generated_token_ids_tail": generated[-tail_n:] if n > tail_n else [],
            "elapsed_seconds": round(t_elapsed, 3),
            "tokens_per_second": round(tok_per_sec, 1),
            "vram_allocated_before_mb": round(alloc_before, 1),
            "vram_allocated_after_mb": round(alloc_after, 1),
            "token_importance_enabled": token_importance,
            "token_importance_interval": token_importance_interval,
            "token_importance_observations": importance_observations,
        }

        if importance_scores is not None and importance_observations > 0:
            all_ids = input_ids + generated
            raw_scores = importance_scores[: len(all_ids)]
            self._last_token_importance = _build_token_importance_payload(
                token_ids=all_ids,
                prompt_len=prompt_len,
                raw_scores=raw_scores,
                renderer=self.renderer,
                observations=importance_observations,
            )

    def get_attention_weights(self) -> list[tuple[int, torch.Tensor]] | None:
        if self.attention is None:
            return None
        return self.attention.get()

    def _get_eos_ids(self) -> set[int]:
        tok = self.tokenizer
        ids: set[int] = set()
        eos = getattr(tok, "eos_token_id", None)
        if isinstance(eos, int):
            ids.add(eos)
        elif isinstance(eos, list):
            ids.update(eos)
        additional = getattr(tok, "additional_special_tokens_ids", []) or []
        for tid in additional:
            if isinstance(tid, int):
                ids.add(tid)
        if not ids:
            ids.add(2)
        return ids

    @staticmethod
    def _build_quant_config(quantization: QuantizationMode):
        """Return a BitsAndBytesConfig or None."""
        if not quantization:
            return None
        try:
            from transformers import BitsAndBytesConfig
        except ImportError:
            raise RuntimeError(
                "bitsandbytes is required for quantization. "
                "Install it with: pip install bitsandbytes"
            )

        if quantization == "4bit":
            return BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
        elif quantization == "8bit":
            return BitsAndBytesConfig(load_in_8bit=True)
        else:
            raise ValueError(f"Unknown quantization mode: {quantization!r}  (expected '4bit' or '8bit')")

    @staticmethod
    def _resolve_model_class(config: AutoConfig):
        arch = getattr(config, "architectures", None)
        if arch:
            try:
                from transformers import AutoModelForVision2Seq
                if "conditional" in arch[0].lower() or "vision" in arch[0].lower():
                    return AutoModelForVision2Seq
            except ImportError:
                pass
        return AutoModelForCausalLM
