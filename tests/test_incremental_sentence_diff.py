from __future__ import annotations

import unittest

from docx_tools.incremental_sentence_diff import align_sentences, diff_words, split_sentences


class IncrementalSentenceDiffTests(unittest.TestCase):
    def test_split_sentences_handles_empty_and_basic_text(self) -> None:
        self.assertEqual(split_sentences(""), [])
        self.assertEqual(split_sentences("One. Two? Three!"), ["One.", "Two?", "Three!"])

    def test_diff_words_reports_replace_and_insert(self) -> None:
        ops = diff_words("I like apples", "I really like oranges")
        tags = [op.tag for op in ops]
        self.assertIn("insert", tags)
        self.assertIn("replace", tags)

    def test_align_sentences_handles_equal_replace_and_insert(self) -> None:
        aligned = align_sentences(
            "Keep this. Replace this.",
            "Keep this. Replace that. Add this.",
        )
        tags = [tag for tag, _, _ in aligned]
        self.assertIn("equal", tags)
        self.assertIn("replace", tags)
        self.assertIn("insert", tags)


if __name__ == "__main__":
    unittest.main()
