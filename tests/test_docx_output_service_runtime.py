from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from services.docx_output_service import DocxOutputService


class DocxOutputServiceRuntimeTests(unittest.TestCase):
    def test_post_init_constructs_editor_with_author(self) -> None:
        with patch("services.docx_output_service.TrackChangesEditor") as editor_cls:
            svc = DocxOutputService(author="Alice")
        editor_cls.assert_called_once_with(author="Alice")
        self.assertIsNotNone(svc)

    def test_build_report_with_header_and_body_forwards_arguments(self) -> None:
        with patch("services.docx_output_service.TrackChangesEditor") as editor_cls:
            editor = MagicMock()
            editor_cls.return_value = editor
            svc = DocxOutputService(author="Alice")

            svc.build_report_with_header_and_body(
                output_path=Path("out.docx"),
                original_paragraphs=["p1", "p2"],
                edited_text="edited full",
                header_lines=["Name: Dan", "Course: X"],
                edited_body_text="edited body",
                corrected_body_text="corrected body",
                feedback_paragraphs=["Good", "## Next"],
                include_edited_text=False,
            )

            editor.build_report_with_header_and_body.assert_called_once_with(
                output_path="out.docx",
                original_paragraphs=["p1", "p2"],
                edited_text="edited full",
                header_lines=["Name: Dan", "Course: X"],
                edited_body_text="edited body",
                corrected_body_text="corrected body",
                feedback_heading="Language Feedback",
                feedback_paragraphs=["Good", "## Next"],
                feedback_as_tracked_insertion=False,
                add_page_break_before_feedback=True,
                include_edited_text_section=False,
            )


if __name__ == "__main__":
    unittest.main()
