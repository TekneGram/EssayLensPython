from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from services.input_discovery_service import InputDiscoveryService


class InputDiscoveryServiceRuntimeTests(unittest.TestCase):
    def test_discover_raises_for_missing_input_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing = Path(tmpdir) / "does-not-exist"
            service = InputDiscoveryService(
                input_root=missing,
                output_root=Path(tmpdir) / "out",
                explainability_root=Path(tmpdir) / "explained",
            )
            with self.assertRaises(FileNotFoundError):
                service.discover()

    def test_discover_raises_for_non_directory_input_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.txt"
            input_file.write_text("x", encoding="utf-8")
            service = InputDiscoveryService(
                input_root=input_file,
                output_root=Path(tmpdir) / "out",
                explainability_root=Path(tmpdir) / "explained",
            )
            with self.assertRaises(ValueError):
                service.discover()

    def test_discover_classifies_submission_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            output_root = root / "checked"
            explain_root = root / "explained"

            sub1 = root / "student_01"
            sub2 = root / "student_02"
            sub3 = root / "student_03"
            sub1.mkdir()
            sub2.mkdir()
            sub3.mkdir()

            docx = sub1 / "essay.docx"
            pdf = sub2 / "essay.pdf"
            image = sub3 / "scan.HEIC"
            unsupported = sub3 / "notes.txt"

            docx.write_text("docx", encoding="utf-8")
            pdf.write_text("pdf", encoding="utf-8")
            image.write_text("image", encoding="utf-8")
            unsupported.write_text("text", encoding="utf-8")

            service = InputDiscoveryService(
                input_root=root,
                output_root=output_root,
                explainability_root=explain_root,
            )
            discovered = service.discover()

            self.assertEqual(len(discovered.docx_paths), 1)
            self.assertEqual(discovered.docx_paths[0].in_path, docx)
            self.assertEqual(
                discovered.docx_paths[0].out_path,
                output_root / "student_01" / "essay_checked.docx",
            )
            self.assertEqual(
                discovered.docx_paths[0].explained_path,
                explain_root / "student_01" / "essay_explained.txt",
            )

            self.assertEqual(len(discovered.pdf_paths), 1)
            self.assertEqual(discovered.pdf_paths[0].in_path, pdf)
            self.assertEqual(
                discovered.pdf_paths[0].out_path,
                output_root / "student_02" / "essay_checked.docx",
            )
            self.assertEqual(
                discovered.pdf_paths[0].explained_path,
                explain_root / "student_02" / "essay_explained.txt",
            )

            self.assertEqual(len(discovered.image_paths), 1)
            self.assertEqual(discovered.image_paths[0].in_path, image)
            self.assertEqual(
                discovered.image_paths[0].out_path,
                output_root / "student_03" / "scan_checked.docx",
            )
            self.assertEqual(
                discovered.image_paths[0].explained_path,
                explain_root / "student_03" / "scan_explained.txt",
            )

            self.assertEqual(len(discovered.unsupported_paths), 1)
            self.assertEqual(discovered.unsupported_paths[0].in_path, unsupported)
            self.assertEqual(
                discovered.unsupported_paths[0].out_path,
                output_root / "student_03" / "notes_checked.docx",
            )
            self.assertEqual(
                discovered.unsupported_paths[0].explained_path,
                explain_root / "student_03" / "notes_explained.txt",
            )


if __name__ == "__main__":
    unittest.main()
