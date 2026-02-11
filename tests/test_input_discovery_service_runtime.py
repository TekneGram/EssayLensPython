from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from services.input_discovery_service import InputDiscoveryService


class InputDiscoveryServiceRuntimeTests(unittest.TestCase):
    def test_discover_raises_for_missing_input_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing = Path(tmpdir) / "does-not-exist"
            service = InputDiscoveryService(input_root=missing)
            with self.assertRaises(FileNotFoundError):
                service.discover()

    def test_discover_raises_for_non_directory_input_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.txt"
            input_file.write_text("x", encoding="utf-8")
            service = InputDiscoveryService(input_root=input_file)
            with self.assertRaises(ValueError):
                service.discover()

    def test_discover_classifies_submission_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

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

            service = InputDiscoveryService(input_root=root)
            discovered = service.discover()

            self.assertEqual(discovered.docx_paths, [docx])
            self.assertEqual(discovered.pdf_paths, [pdf])
            self.assertEqual(discovered.image_paths, [image])
            self.assertEqual(discovered.unsupported_paths, [unsupported])


if __name__ == "__main__":
    unittest.main()
