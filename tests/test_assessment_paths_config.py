from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from config.assessment_paths_config import AssessmentPathsConfig


class AssessmentPathsConfigTests(unittest.TestCase):
    def test_from_strings_normalizes_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cfg = AssessmentPathsConfig.from_strings(
                input_folder=root / "in",
                output_folder=root / "out",
                explained_folder=root / "explained",
            )

            self.assertEqual(cfg.input_folder, (root / "in").resolve())
            self.assertEqual(cfg.output_folder, (root / "out").resolve())
            self.assertEqual(cfg.explained_folder, (root / "explained").resolve())

    def test_ensure_output_dirs_creates_missing_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cfg = AssessmentPathsConfig.from_strings(
                input_folder=root / "in",
                output_folder=root / "out",
                explained_folder=root / "explained",
            )

            cfg.ensure_output_dirs()

            self.assertTrue(cfg.output_folder.exists())
            self.assertTrue(cfg.output_folder.is_dir())
            self.assertTrue(cfg.explained_folder.exists())
            self.assertTrue(cfg.explained_folder.is_dir())

    def test_validate_creates_missing_input_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cfg = AssessmentPathsConfig.from_strings(
                input_folder=root / "in",
                output_folder=root / "out",
                explained_folder=root / "explained",
            )

            self.assertFalse(cfg.input_folder.exists())
            cfg.validate()
            self.assertTrue(cfg.input_folder.exists())
            self.assertTrue(cfg.input_folder.is_dir())

    def test_validate_raises_when_input_path_is_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_file = root / "in"
            input_file.write_text("not-a-dir", encoding="utf-8")
            cfg = AssessmentPathsConfig.from_strings(
                input_folder=input_file,
                output_folder=root / "out",
                explained_folder=root / "explained",
            )

            with self.assertRaises(ValueError):
                cfg.validate()

    def test_validate_raises_when_output_path_is_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "in").mkdir()
            output_file = root / "out"
            output_file.write_text("not-a-dir", encoding="utf-8")
            cfg = AssessmentPathsConfig.from_strings(
                input_folder=root / "in",
                output_folder=output_file,
                explained_folder=root / "explained",
            )

            with self.assertRaises(ValueError):
                cfg.validate()

    def test_validate_raises_when_explained_path_is_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "in").mkdir()
            explained_file = root / "explained"
            explained_file.write_text("not-a-dir", encoding="utf-8")
            cfg = AssessmentPathsConfig.from_strings(
                input_folder=root / "in",
                output_folder=root / "out",
                explained_folder=explained_file,
            )

            with self.assertRaises(ValueError):
                cfg.validate()

    def test_list_inputs_returns_nested_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_folder = root / "in"
            nested = input_folder / "a" / "b"
            nested.mkdir(parents=True)
            first = input_folder / "root.txt"
            second = nested / "nested.txt"
            first.write_text("x", encoding="utf-8")
            second.write_text("y", encoding="utf-8")
            cfg = AssessmentPathsConfig.from_strings(
                input_folder=input_folder,
                output_folder=root / "out",
                explained_folder=root / "explained",
            )

            files = sorted(cfg.list_inputs())
            self.assertEqual(files, sorted([first.resolve(), second.resolve()]))


if __name__ == "__main__":
    unittest.main()
