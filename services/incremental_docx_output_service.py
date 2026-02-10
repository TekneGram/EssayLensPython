from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from docx_tools.incremental_track_changes_editor import IncrementalTrackChangesEditor
from services.incremental_docx_state_store import IncrementalDocxStateStore, StateStoreError


@dataclass
class IncrementalDocxOutputService:
    author: str
    llm_service: object | None = None

    def __post_init__(self) -> None:
        self._editor = IncrementalTrackChangesEditor(author=self.author)

    def start_original_section(self, *, output_path: Path, original_paragraphs: list[str]) -> Path:
        state_store = IncrementalDocxStateStore(output_path=output_path)
        state = state_store.load()

        doc = self._editor.create_or_load_document(output_path)
        self._editor.enable_track_revisions(doc)
        self._editor.append_original_section(doc, original_paragraphs)
        self._editor.save(doc, output_path)

        state_store.ensure_section(state, "original")
        state_store.save(state)
        return output_path

    def append_header_and_edited_section(
        self,
        *,
        output_path: Path,
        header_lines: list[str],
        edited_text: str,
        include_page_break: bool = True,
    ) -> Path:
        state_store = IncrementalDocxStateStore(output_path=output_path)
        state = state_store.load()

        doc = self._editor.create_or_load_document(output_path)
        self._editor.enable_track_revisions(doc)
        self._editor.append_header_and_edited_section(
            doc,
            header_lines=header_lines,
            edited_text=edited_text,
            include_page_break=include_page_break,
        )
        self._editor.save(doc, output_path)

        state_store.ensure_section(state, "header_edited")
        state_store.record_edited_hash(state, edited_text)
        state_store.save(state)
        return output_path

    def append_corrected_section(
        self,
        *,
        output_path: Path,
        edited_text: str,
        corrected_text: str,
    ) -> Path:
        state_store = IncrementalDocxStateStore(output_path=output_path)
        state = state_store.load()
        state_store.validate_edited_hash(state, edited_text)

        doc = self._editor.create_or_load_document(output_path)
        self._editor.enable_track_revisions(doc)
        self._editor.append_corrected_diff_section(
            doc,
            edited_text=edited_text,
            corrected_text=corrected_text,
        )
        self._editor.save(doc, output_path)

        state_store.ensure_section(state, "corrected")
        state_store.save(state)
        return output_path

    def append_feedback_section(
        self,
        *,
        output_path: Path,
        feedback_paragraphs: list[str],
        heading: str = "Language Feedback",
        feedback_target_path: Path | None = None,
    ) -> Path:
        target_path = feedback_target_path or output_path
        state_store = IncrementalDocxStateStore(output_path=target_path)
        state = state_store.load()

        doc = self._editor.create_or_load_document(target_path)
        self._editor.enable_track_revisions(doc)
        feedback_id = self._editor.append_feedback_section(
            doc,
            feedback_paragraphs=feedback_paragraphs,
            heading=heading,
        )
        self._editor.save(doc, target_path)

        state_store.ensure_section(state, "feedback")
        state_store.add_feedback_entry(
            state,
            feedback_id=feedback_id,
            marker_start=f"ELP_FEEDBACK_BLOCK_START::{feedback_id}",
            marker_end=f"ELP_FEEDBACK_BLOCK_END::{feedback_id}",
            target_path=str(target_path),
        )
        state_store.save(state)
        return target_path

    def append_feedback_summary(
        self,
        *,
        output_path: Path,
        mode: str = "append_summary",
        heading: str = "Feedback Summary",
        feedback_target_path: Path | None = None,
    ) -> Path:
        target_path = feedback_target_path or output_path
        state_store = IncrementalDocxStateStore(output_path=target_path)
        state = state_store.load()

        doc = self._editor.create_or_load_document(target_path)
        feedback_blocks = self._editor.collect_feedback_blocks(doc)
        if not feedback_blocks:
            raise StateStoreError("Cannot generate feedback summary: no feedback blocks found.")

        summary = self._summarize_feedback(feedback_blocks)

        if mode == "replace_with_summary":
            self._editor.remove_feedback_sections(doc)
        elif mode != "append_summary":
            raise ValueError("mode must be 'append_summary' or 'replace_with_summary'.")

        self._editor.append_feedback_summary_section(doc, summary, heading=heading)
        self._editor.save(doc, target_path)

        state_store.record_feedback_summary(
            state,
            summary_text=summary,
            source_count=len(feedback_blocks),
        )
        state_store.save(state)
        return target_path

    def _summarize_feedback(self, feedback_blocks: list[str]) -> str:
        if self.llm_service is None:
            return self._fallback_summary(feedback_blocks)

        combined = "\n\n".join(feedback_blocks)
        response = self.llm_service.chat(
            system=(
                "You summarize writing feedback for students. Keep summary concise, structured, and actionable."
            ),
            user=(
                "Summarize the following language feedback into a short section with:\n"
                "1) strengths\n2) key issues\n3) next revision priorities.\n\n"
                f"Feedback:\n{combined}"
            ),
            max_tokens=300,
            temperature=0.2,
        )
        content = getattr(response, "content", "")
        return content.strip() or self._fallback_summary(feedback_blocks)

    @staticmethod
    def _fallback_summary(feedback_blocks: list[str]) -> str:
        if not feedback_blocks:
            return "No feedback available."
        lines = [
            "Summary generated without LLM.",
            f"Feedback blocks analyzed: {len(feedback_blocks)}.",
            "Review each block for detailed revision instructions.",
        ]
        return "\n".join(lines)
