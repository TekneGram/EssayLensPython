from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import torch

from nlp.ged.ged_bert import GedBertDetector


class _FakeTokenizer:
    all_special_ids = [101, 102, 0]

    def __call__(self, batch, return_tensors=None, padding=True, truncation=True):
        _ = (return_tensors, padding, truncation)
        # shape: [batch, 4]
        input_ids = torch.tensor([
            [101, 11, 12, 0],
            [101, 21, 22, 0],
        ], dtype=torch.long)
        attention_mask = torch.tensor([
            [1, 1, 1, 0],
            [1, 1, 1, 0],
        ], dtype=torch.long)
        return {"input_ids": input_ids[: len(batch)], "attention_mask": attention_mask[: len(batch)]}

    def convert_ids_to_tokens(self, ids):
        return [f"tok_{ids[0]}"]


class _FakeModel:
    def to(self, device):
        self._device = device

    def eval(self):
        return None

    def __call__(self, **enc):
        input_ids = enc["input_ids"]
        bsz, seq_len = input_ids.shape
        logits = torch.zeros((bsz, seq_len, 2), dtype=torch.float32)
        # Mark token position 2 (non-special) as ERROR for each row.
        logits[:, 2, 1] = 5.0
        return SimpleNamespace(logits=logits)


class GedBertRuntimeTests(unittest.TestCase):
    def _build_detector(self, cuda_available: bool = False, device: str | None = None) -> GedBertDetector:
        with patch("nlp.ged.ged_bert.torch.cuda.is_available", return_value=cuda_available):
            with patch("nlp.ged.ged_bert.AutoTokenizer.from_pretrained", return_value=_FakeTokenizer()):
                with patch("nlp.ged.ged_bert.AutoModelForTokenClassification.from_pretrained", return_value=_FakeModel()):
                    return GedBertDetector(model_name="demo-ged", device=device)

    def test_constructor_selects_cpu_when_cuda_unavailable(self) -> None:
        detector = self._build_detector(cuda_available=False)
        self.assertEqual(str(detector.device), "cpu")

    def test_constructor_uses_explicit_device(self) -> None:
        detector = self._build_detector(cuda_available=False, device="cpu")
        self.assertEqual(str(detector.device), "cpu")

    def test_score_sentences_returns_empty_for_empty_input(self) -> None:
        detector = self._build_detector()
        self.assertEqual(detector.score_sentences([], batch_size=2), [])

    def test_score_sentences_flags_error_tokens_ignoring_special_and_padding(self) -> None:
        detector = self._build_detector()
        results = detector.score_sentences(["a", "b"], batch_size=2)

        self.assertEqual(len(results), 2)
        self.assertTrue(all(r.has_error for r in results))
        self.assertEqual(results[0].error_tokens, ["tok_12"])
        self.assertEqual(results[1].error_tokens, ["tok_22"])

    def test_score_sentences_batches_across_chunks(self) -> None:
        detector = self._build_detector()
        results = detector.score_sentences(["s1", "s2", "s3"], batch_size=2)
        self.assertEqual(len(results), 3)
        self.assertTrue(all(hasattr(r, "sentence") and hasattr(r, "has_error") for r in results))


if __name__ == "__main__":
    unittest.main()
