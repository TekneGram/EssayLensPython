from __future__ import annotations

import unittest

from config.run_config import RunConfig


class RunConfigTests(unittest.TestCase):
    def test_from_strings_parses_boolean_strings(self) -> None:
        cfg = RunConfig.from_strings(
            author="Daniel",
            single_paragraph_mode="true",
            max_llm_corrections="3",
            include_edited_text_section_policy="no",
        )
        self.assertEqual(cfg.author, "Daniel")
        self.assertTrue(cfg.single_paragraph_mode)
        self.assertEqual(cfg.max_llm_corrections, 3)
        self.assertFalse(cfg.include_edited_text_section_policy)

    def test_validate_rejects_empty_author(self) -> None:
        with self.assertRaises(ValueError):
            RunConfig.from_strings(author="   ")

    def test_validate_rejects_negative_max_corrections(self) -> None:
        with self.assertRaises(ValueError):
            RunConfig.from_strings(author="Daniel", max_llm_corrections="-1")

    def test_validate_rejects_non_integer_max_corrections(self) -> None:
        with self.assertRaises(ValueError):
            RunConfig.from_strings(author="Daniel", max_llm_corrections="abc")

    def test_validate_rejects_invalid_bool_string(self) -> None:
        with self.assertRaises(ValueError):
            RunConfig.from_strings(author="Daniel", single_paragraph_mode="maybe")


if __name__ == "__main__":
    unittest.main()
