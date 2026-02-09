from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError

from nlp.ged.ged_types import GedSentenceResult


class GedTypesRuntimeTests(unittest.TestCase):
    def test_sentence_result_fields_and_defaults(self) -> None:
        result = GedSentenceResult(sentence="A sentence.", has_error=True)
        self.assertEqual(result.sentence, "A sentence.")
        self.assertTrue(result.has_error)
        self.assertIsNone(result.score)
        self.assertEqual(result.error_tokens, [])

    def test_sentence_result_custom_fields(self) -> None:
        result = GedSentenceResult(
            sentence="A sentence.",
            has_error=False,
            score=0.25,
            error_tokens=["bad", "token"],
        )
        self.assertEqual(result.score, 0.25)
        self.assertEqual(result.error_tokens, ["bad", "token"])

    def test_sentence_result_is_frozen(self) -> None:
        result = GedSentenceResult(sentence="A sentence.", has_error=True)
        with self.assertRaises(FrozenInstanceError):
            result.has_error = False  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
