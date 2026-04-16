from __future__ import annotations

from typing import Any

import torch
import torch.nn as nn


class AttentionCapture:
    """Register forward hooks on attention layers to capture weights.

    Usage::

        cap = AttentionCapture(model)
        cap.enable()          # start capturing
        model(input_ids)
        weights = cap.get()   # list of (layer_idx, attn_weight) tensors
        cap.disable()         # remove hooks
    """

    def __init__(self, model: nn.Module, pattern: str = "attn") -> None:
        self._model = model
        self._pattern = pattern
        self._hooks: list[torch.utils.hooks.RemovableHook] = []
        self._weights: list[tuple[int, torch.Tensor]] = []

    def enable(self) -> None:
        self.disable()
        self._weights.clear()
        idx = 0
        for name, module in self._model.named_modules():
            if self._pattern in name and not any(
                skip in name for skip in ("proj", "norm", "dropout")
            ):
                self._hooks.append(
                    module.register_forward_hook(self._make_hook(idx))
                )
                idx += 1

    def disable(self) -> None:
        for h in self._hooks:
            h.remove()
        self._hooks.clear()

    def clear(self) -> None:
        self._weights.clear()

    def get(self) -> list[tuple[int, torch.Tensor]]:
        return list(self._weights)

    def _make_hook(self, layer_idx: int):
        def hook(
            _module: nn.Module,
            _input: Any,
            output: Any,
        ) -> None:
            attn = None
            if isinstance(output, tuple) and len(output) >= 2:
                attn = output[1]
            if attn is not None and isinstance(attn, torch.Tensor):
                self._weights.append((layer_idx, attn.detach().cpu()))

        return hook
