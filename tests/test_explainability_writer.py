from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from inout.explainability_writer import ExplainabilityWriter


class ExplainabilityWriterTests(unittest.TestCase):
    def test_write_creates_output_dir_and_writes_text_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "explained"
            writer = ExplainabilityWriter(output_dir=output_dir)

            out_path = writer.write(Path("essay.docx"), ["line1", "line2"])

            self.assertEqual(out_path, output_dir / "essay.txt")
            self.assertTrue(out_path.exists())
            self.assertEqual(out_path.read_text(encoding="utf-8"), "line1\nline2\n")


if __name__ == "__main__":
    unittest.main()
