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

    @property
    def loaded(self) -> bool:
        return self.model is not None

    @property
    def last_generation_stats(self) -> dict | None:
        return self._last_generation_stats

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
    ) -> Iterator[str]:
        assert self.model is not None and self.renderer is not None
        assert self.tokenizer is not None

        _cuda_cleanup()
        alloc_before, _ = _cuda_mem_mb()

        input_ids = self.renderer.render(messages, tools=tools)
        prompt_len = len(input_ids)
        input_tensor = torch.tensor([input_ids], device=self.device, dtype=torch.long)

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
                outputs = self.model(input_ids=input_tensor, use_cache=True)
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
                    outputs = self.model(
                        input_ids=next_input,
                        past_key_values=past,
                        use_cache=True,
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
        }

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
