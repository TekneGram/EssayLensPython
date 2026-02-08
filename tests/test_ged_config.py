from __future__ import annotations

import unittest

from config.ged_config import GedConfig


class GedConfigTests(unittest.TestCase):
    def test_from_strings_parses_batch_size(self) -> None:
        cfg = GedConfig.from_strings(
            model_name="gotutiyan/token-ged-bert-large-cased-bin",
            batch_size="8",
        )
        self.assertEqual(cfg.model_name, "gotutiyan/token-ged-bert-large-cased-bin")
        self.assertEqual(cfg.batch_size, 8)

    def test_validate_rejects_empty_model_name(self) -> None:
        with self.assertRaises(ValueError):
            GedConfig.from_strings(model_name="   ")

    def test_validate_rejects_non_positive_batch_size(self) -> None:
        with self.assertRaises(ValueError):
            GedConfig.from_strings(model_name="m", batch_size=0)

    def test_validate_rejects_unusually_large_batch_size(self) -> None:
        with self.assertRaises(ValueError):
            GedConfig.from_strings(model_name="m", batch_size=257)

    def test_validate_rejects_non_integer_batch_size(self) -> None:
        with self.assertRaises(ValueError):
            GedConfig.from_strings(model_name="m", batch_size="abc")


if __name__ == "__main__":
    unittest.main()
