from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from docx import Document
from docx_tools.track_changes_editor import TrackChangesEditor

@dataclass
class DocxOutputService():
    author: str

    def __post_init__(self) -> None:
        self._editor = TrackChangesEditor(author=self.author)

    # def build_report(
    #     self,
    #     *,
    #     input_path: Path,
    #     output_path: Path,
    #     original_paragraphs: List[str],
    #     edited_text: str,
    #     corrected_text: str,
    #     feedback_paragraphs: Optional[List[str]] = None,
    #     include_edited_text: bool = True,
    # ) -> Path:
    #     self._editor.build_single_paragraph_report(
    #         output_path=str(output_path),
    #         original_paragraphs=original_paragraphs,
    #         edited_text=edited_text,
    #         corrected_text=corrected_text,
    #         feedback_heading="Language Feedback",
    #         feedback_paragraphs=feedback_paragraphs,
    #         feedback_as_tracked_insertion=False,
    #         add_page_break_before_feedback=True,
    #         include_edited_text_section=include_edited_text,
    #     )
    #     return output_path

    def build_report_with_header_and_body(
        self,
        *,
        output_path: Path,
        original_paragraphs: List[str],
        edited_text: str,
        header_lines: List[str],
        edited_body_text: str,
        corrected_body_text: str,
        feedback_paragraphs: Optional[List[str]] = None,
        include_edited_text: bool = True,
    ) -> None:
        self._editor.build_report_with_header_and_body(
            output_path=str(output_path),
            original_paragraphs=original_paragraphs,
            edited_text=edited_text,
            header_lines=header_lines,
            edited_body_text=edited_body_text,
            corrected_body_text=corrected_body_text,
            feedback_heading="Language Feedback",
            feedback_paragraphs=feedback_paragraphs,
            feedback_as_tracked_insertion=False,
            add_page_break_before_feedback=True,
            include_edited_text_section=include_edited_text,
        )

    def write_plain_copy(self, *, output_path: Path, paragraphs: List[str]) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc = Document()
        for p in paragraphs:
            doc.add_paragraph(p or "")
        doc.save(str(output_path))
        return output_path
