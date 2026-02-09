from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from nlp.ged.ged_types import GedSentenceResult, GedDetector

if TYPE_CHECKING:
    from services.explainability import ExplainabilityRecorder

@dataclass(frozen=True, slots=True)
class GedService:
    """
    App-facing wrapper around GedBertDetector

    Keeps the detector (heavy model) alive and provides simple outputs
    that the pipeline needs (flags, counts, etc).
    """
    detector: GedDetector

    def score(self, sentences: list[str], batch_size: int, explain: "ExplainabilityRecorder | None" = None) -> list[GedSentenceResult]:
        """
        Return full results (sentence + has_error).
        Useful for explainability.
        """
        if not sentences:
            if explain is not None:
                explain.log("GED", "No sentences to score")
            return []
        
        if explain is not None:
            explain.log("GED", f"Scoring {len(sentences)} sentences (batch_size={batch_size})")
        results = self.detector.score_sentences(sentences, batch_size=batch_size)
        if explain is not None:
            flagged = sum(1 for r in results if r.has_error)
            explain.log("GED", f"Flagged {flagged} sentences")
            for idx, r in enumerate(results, start=1):
                error_tokens = getattr(r, "error_tokens", None) or []
                tokens = ", ".join(error_tokens) if error_tokens else "none"
                explain.log(
                    "GED",
                    f"Sentence {idx}: has_error={r.has_error}; error_tokens={tokens}; text={r.sentence}"
                )
        return results
    
    def flag_sentences(self, sentences: list[str], batch_size: int, explain: "ExplainabilityRecorder | None" = None) -> list[bool]:
        """
        Return only the boolean flags in the same order as input
        """
        return [r.has_error for r in self.score(sentences, batch_size=batch_size, explain=explain)]
    
    def count_flagged(self, sentences: list[str], batch_size: int, explain: "ExplainabilityRecorder | None" = None) -> int:
        """
        Convenience helper
        """
        return sum(self.flag_sentences(sentences, batch_size=batch_size, explain=explain))
