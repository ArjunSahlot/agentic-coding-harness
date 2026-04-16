from __future__ import annotations

import platform
import sys
import time
from typing import Any

try:
    import torch

    _HAS_TORCH = True
except ImportError:
    _HAS_TORCH = False

try:
    import numpy as np

    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False


def json_safe(value: Any) -> Any:
    """Recursively convert values to JSON-serializable forms (torch.dtype, numpy, etc.)."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if _HAS_TORCH:
        if isinstance(value, torch.dtype):
            return str(value)
        if isinstance(value, torch.Tensor):
            n = value.numel()
            if n <= 256:
                return value.detach().cpu().tolist()
            return {"_tensor": True, "shape": list(value.shape), "dtype": str(value.dtype)}
    if _HAS_NUMPY:
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, np.ndarray):
            return value.tolist()
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(v) for v in value]
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


_CONFIG_KEYS = (
    "model_type",
    "architectures",
    "vocab_size",
    "hidden_size",
    "intermediate_size",
    "num_hidden_layers",
    "num_attention_heads",
    "num_key_value_heads",
    "max_position_embeddings",
    "torch_dtype",
    "tie_word_embeddings",
    "use_cache",
    "bos_token_id",
    "eos_token_id",
    "pad_token_id",
)


def build_runtime_payload(app_state) -> dict[str, Any]:
    out: dict[str, Any] = {
        "python_version": sys.version.split()[0],
        "python_full": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "processor": platform.processor() or "",
        "hostname": platform.node(),
        "uptime_seconds": round(time.time() - app_state.started_at, 3),
        "models_dir": app_state.models_dir,
        "conversation_count": len(app_state.conversations),
    }

    try:
        import torch

        out["torch_version"] = torch.__version__
        out["cuda_available"] = torch.cuda.is_available()
        out["cuda_version"] = getattr(torch.version, "cuda", None)
        if torch.cuda.is_available():
            out["cuda_device_count"] = torch.cuda.device_count()
            out["cuda_devices"] = [
                {
                    "index": i,
                    "name": torch.cuda.get_device_name(i),
                    "capability": list(torch.cuda.get_device_capability(i)),
                }
                for i in range(torch.cuda.device_count())
            ]
            free, total = torch.cuda.mem_get_info(0)
            out["cuda_mem_free_bytes"] = free
            out["cuda_mem_total_bytes"] = total
            out["cuda_mem_used_bytes"] = total - free
            out["cuda_allocated_bytes"] = torch.cuda.memory_allocated(0)
            out["cuda_reserved_bytes"] = torch.cuda.memory_reserved(0)
    except Exception as exc:
        out["torch_error"] = str(exc)

    try:
        import psutil

        p = psutil.Process()
        mi = p.memory_info()
        out["process_rss_bytes"] = mi.rss
        out["process_vms_bytes"] = getattr(mi, "vms", 0)
        out["process_threads"] = p.num_threads()
        out["process_cpu_percent"] = p.cpu_percent(interval=None)
        vm = psutil.virtual_memory()
        out["host_mem_total_bytes"] = vm.total
        out["host_mem_available_bytes"] = vm.available
        out["host_mem_percent"] = vm.percent
        if hasattr(psutil, "cpu_freq") and psutil.cpu_freq():
            cf = psutil.cpu_freq()
            out["cpu_freq_mhz_current"] = cf.current
    except Exception:
        pass

    return out


def build_model_payload(app_state) -> dict[str, Any]:
    eng = app_state.engine
    if not eng.loaded or eng.model is None:
        return {"loaded": False, "message": "No model loaded"}

    model = eng.model
    cfg = model.config
    tok = eng.tokenizer

    try:
        full_cfg = cfg.to_dict()
    except Exception:
        full_cfg = {}

    summary = {k: full_cfg.get(k) for k in _CONFIG_KEYS if k in full_cfg}
    for k in _CONFIG_KEYS:
        if k not in summary and hasattr(cfg, k):
            try:
                summary[k] = getattr(cfg, k)
            except Exception:
                pass

    n_params = sum(p.numel() for p in model.parameters())
    n_trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)

    tok_info: dict[str, Any] = {
        "vocab_size": getattr(tok, "vocab_size", None),
        "model_max_length": getattr(tok, "model_max_length", None),
    }
    for name in ("bos_token_id", "eos_token_id", "pad_token_id", "unk_token_id"):
        tok_info[name] = getattr(tok, name, None)

    hf_map = getattr(model, "hf_device_map", None)
    device_map_summary = hf_map if isinstance(hf_map, dict) else None

    payload = {
        "loaded": True,
        "model_path": eng._model_path,
        "device": eng.device,
        "dtype": str(eng.dtype),
        "parameters_total": n_params,
        "parameters_trainable": n_trainable,
        "config_summary": json_safe(summary),
        "tokenizer": json_safe(tok_info),
        "hf_device_map": json_safe(device_map_summary) if device_map_summary else None,
        "model_class": model.__class__.__name__,
    }
    return json_safe(payload)


def build_tokenizer_sample(app_state, text: str, max_tokens: int = 512) -> dict[str, Any]:
    """Encode sample text for debugging (optional query helper)."""
    eng = app_state.engine
    if not eng.loaded or eng.tokenizer is None:
        return {"error": "No tokenizer"}
    tok = eng.tokenizer
    enc = tok.encode(text, add_special_tokens=False)
    enc = enc[:max_tokens]
    preview = enc[:64]
    if hasattr(tok, "convert_ids_to_tokens"):
        pieces = tok.convert_ids_to_tokens(preview)
    else:
        pieces = [tok.decode([i]) for i in preview]

    return {
        "input_chars": len(text),
        "token_count": len(enc),
        "token_ids": enc,
        "tokens_preview": pieces,
    }
