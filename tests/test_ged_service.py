from __future__ import annotations

import unittest

from nlp.ged.ged_types import GedSentenceResult
from services.ged_service import GedService


class _FakeDetector:
    def score_sentences(self, sentences: list[str], batch_size: int = 8) -> list[GedSentenceResult]:
        _ = batch_size
        return [
            GedSentenceResult(sentence=s, has_error=("bad" in s), error_tokens=(["bad"] if "bad" in s else []))
            for s in sentences
        ]


class _ExplainCapture:
    def __init__(self) -> None:
        self.logs: list[tuple[str, str]] = []

    def log(self, section: str, message: str) -> None:
        self.logs.append((section, message))


class GedServiceTests(unittest.TestCase):
    def test_score_empty_sentences_logs_and_returns_empty(self) -> None:
        service = GedService(detector=_FakeDetector())
        explain = _ExplainCapture()

        result = service.score([], batch_size=4, explain=explain)

        self.assertEqual(result, [])
        self.assertEqual(explain.logs[0], ("GED", "No sentences to score"))

    def test_flag_and_count_helpers(self) -> None:
        service = GedService(detector=_FakeDetector())
        sentences = ["good sentence", "bad sentence"]

        flags = service.flag_sentences(sentences, batch_size=2)
        count = service.count_flagged(sentences, batch_size=2)

        self.assertEqual(flags, [False, True])
        self.assertEqual(count, 1)

    def test_score_logs_summary_and_sentence_details(self) -> None:
        service = GedService(detector=_FakeDetector())
        explain = _ExplainCapture()

        _ = service.score(["good sentence", "bad sentence"], batch_size=2, explain=explain)
        messages = [m for _, m in explain.logs]

        self.assertTrue(any("Scoring 2 sentences" in m for m in messages))
        self.assertTrue(any("Flagged 1 sentences" in m for m in messages))
        self.assertTrue(any("Sentence 2: has_error=True" in m for m in messages))


if __name__ == "__main__":
    unittest.main()
