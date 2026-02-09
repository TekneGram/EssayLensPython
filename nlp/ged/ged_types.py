from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass(frozen=True)
class GedSentenceResultBase:
    sentence: str
    has_error: bool
    score: Optional[float] = None


@dataclass(frozen=True)
class GedSentenceResult(GedSentenceResultBase):
    error_tokens: List[str] = field(default_factory=list)

@dataclass(frozen=True)
class GedDetector:
    def score_sentences(self, sentences: list[str], batch_size: int = 8) -> list[GedSentenceResult]:
        ...