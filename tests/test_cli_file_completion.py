from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cli.file_completion import (
    ActiveAtToken,
    find_active_at_token,
    find_matching_files,
    normalize_selected_path,
    replace_active_at_token,
)


class CliFileCompletionTests(unittest.TestCase):
    def test_find_active_token_for_at_path(self) -> None:
        text = "/topic-sentence @Asses"
        token = find_active_at_token(text, len(text))
        self.assertIsNotNone(token)
        assert token is not None
        self.assertEqual(token.query, "Asses")

    def test_find_active_token_returns_none_without_at(self) -> None:
        token = find_active_at_token("/topic-sentence foo", len("/topic-sentence foo"))
        self.assertIsNone(token)

    def test_replace_active_token_preserves_at_and_quotes_spaces(self) -> None:
        original = '/topic-sentence @"Asse'
        token = ActiveAtToken(start=16, end=len(original), query="Asse")
        updated = replace_active_at_token(original, token, "/tmp/Assessment/in/my essay.docx")
        self.assertEqual(updated, '/topic-sentence @"/tmp/Assessment/in/my essay.docx"')

    def test_active_token_end_covers_full_token_beyond_cursor(self) -> None:
        text = "/topic-sentence @Assessment/in/sample.docx trailing"
        cursor = text.index("@Assessment") + len("@Assess")
        token = find_active_at_token(text, cursor)
        self.assertIsNotNone(token)
        assert token is not None
        self.assertEqual(text[token.start:token.end], "@Assessment/in/sample.docx")

    def test_find_matching_files_ranking_and_ignore(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "folder").mkdir()
            (root / "folder" / "essay_alpha.docx").write_text("x", encoding="utf-8")
            (root / "folder" / "my_essay_beta.docx").write_text("x", encoding="utf-8")
            (root / "ignoreme").mkdir()
            (root / "ignoreme" / "essay_hidden.docx").write_text("x", encoding="utf-8")

            matches = find_matching_files(
                "essa",
                root=root,
                ignore_dirs={"ignoreme"},
                max_results=10,
            )

            self.assertTrue(matches)
            expected_a = str((root / "folder" / "essay_alpha.docx").resolve())
            expected_b = str((root / "folder" / "my_essay_beta.docx").resolve())
            hidden = str((root / "ignoreme" / "essay_hidden.docx").resolve())
            self.assertIn(expected_a, matches)
            self.assertIn(expected_b, matches)
            self.assertNotIn(hidden, matches)
            self.assertEqual(matches[0], expected_a)

    def test_normalize_selected_path_converts_relative_to_absolute(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            rel = "Assessment/in/student/file.docx"
            normalized = normalize_selected_path(rel, root=root)
            self.assertEqual(normalized, str((root / rel).resolve()))


if __name__ == "__main__":
    unittest.main()
