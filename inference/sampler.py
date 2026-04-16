from __future__ import annotations

from dataclasses import dataclass, field

import torch


@dataclass
class SamplingParams:
    temperature: float = 0.6
    top_p: float = 0.95
    top_k: int = 50
    min_p: float = 0.0
    repetition_penalty: float = 1.0
    repetition_window: int = 64


class Sampler:
    """Pure-torch token sampler with temperature, top-k, top-p, min-p, and
    repetition penalty.  Stateless -- call :meth:`sample` each step."""

    def __init__(self, params: SamplingParams | None = None) -> None:
        self.params = params or SamplingParams()

    # --------------------------------------------------------------------- #
    def sample(
        self,
        logits: torch.Tensor,
        generated_ids: list[int] | None = None,
    ) -> int:
        """Return a single token id from *logits* ``(vocab_size,)``."""
        logits = logits.float()

        if self.params.repetition_penalty != 1.0 and generated_ids:
            logits = self._apply_repetition_penalty(logits, generated_ids)

        if self.params.temperature <= 0:
            return int(logits.argmax().item())

        logits = logits / self.params.temperature

        if self.params.top_k > 0:
            logits = self._top_k(logits)

        if self.params.min_p > 0:
            logits = self._min_p(logits)

        if self.params.top_p < 1.0:
            logits = self._top_p(logits)

        probs = torch.softmax(logits, dim=-1)
        return int(torch.multinomial(probs, num_samples=1).item())

    # --------------------------------------------------------------------- #
    # Filtering helpers
    # --------------------------------------------------------------------- #
    def _apply_repetition_penalty(
        self, logits: torch.Tensor, generated_ids: list[int]
    ) -> torch.Tensor:
        window = generated_ids[-self.params.repetition_window :]
        unique = torch.tensor(list(set(window)), device=logits.device, dtype=torch.long)
        selected = logits[unique]
        selected = torch.where(
            selected > 0,
            selected / self.params.repetition_penalty,
            selected * self.params.repetition_penalty,
        )
        logits[unique] = selected
        return logits

    @staticmethod
    def _top_k(logits: torch.Tensor, k: int | None = None) -> torch.Tensor:
        k = k or 50
        top_k = min(k, logits.size(-1))
        indices_to_remove = logits < torch.topk(logits, top_k).values[..., -1, None]
        logits[indices_to_remove] = float("-inf")
        return logits

    def _top_p(self, logits: torch.Tensor) -> torch.Tensor:
        sorted_logits, sorted_idx = torch.sort(logits, descending=True)
        cumulative = torch.softmax(sorted_logits, dim=-1).cumsum(dim=-1)
        mask = cumulative - torch.softmax(sorted_logits, dim=-1) > self.params.top_p
        sorted_logits[mask] = float("-inf")
        logits.scatter_(0, sorted_idx, sorted_logits)
        return logits

    def _min_p(self, logits: torch.Tensor) -> torch.Tensor:
        probs = torch.softmax(logits, dim=-1)
        top_prob = probs.max()
        logits[probs < self.params.min_p * top_prob] = float("-inf")
        return logits
