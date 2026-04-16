from __future__ import annotations

import torch


class KVCache:
    """Lightweight per-layer KV cache for incremental decoding.

    Stores a list of ``(key, value)`` tensor pairs, one per layer.
    Supports appending new KV slices, truncation, and sliding-window eviction.
    """

    def __init__(self, max_length: int | None = None) -> None:
        self.max_length = max_length
        self._cache: list[tuple[torch.Tensor, torch.Tensor]] = []

    @property
    def seq_len(self) -> int:
        if not self._cache:
            return 0
        return self._cache[0][0].shape[2]

    @property
    def num_layers(self) -> int:
        return len(self._cache)

    def update(
        self,
        layer_idx: int,
        key: torch.Tensor,
        value: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Append new key/value slices for *layer_idx* and return the full KV."""
        while len(self._cache) <= layer_idx:
            self._cache.append(
                (
                    torch.empty(0, device=key.device),
                    torch.empty(0, device=value.device),
                )
            )

        prev_k, prev_v = self._cache[layer_idx]
        if prev_k.numel() == 0:
            new_k, new_v = key, value
        else:
            new_k = torch.cat([prev_k, key], dim=2)
            new_v = torch.cat([prev_v, value], dim=2)

        if self.max_length is not None and new_k.shape[2] > self.max_length:
            trim = new_k.shape[2] - self.max_length
            new_k = new_k[:, :, trim:, :]
            new_v = new_v[:, :, trim:, :]

        self._cache[layer_idx] = (new_k, new_v)
        return new_k, new_v

    def truncate(self, length: int) -> None:
        """Keep only the first *length* positions in every layer."""
        for i, (k, v) in enumerate(self._cache):
            if k.numel() > 0 and k.shape[2] > length:
                self._cache[i] = (k[:, :, :length, :], v[:, :, :length, :])

    def clear(self) -> None:
        self._cache.clear()

    def to_legacy_tuple(self) -> tuple[tuple[torch.Tensor, torch.Tensor], ...] | None:
        """Return cache in the HF ``past_key_values`` format."""
        if not self._cache or self._cache[0][0].numel() == 0:
            return None
        return tuple(self._cache)
