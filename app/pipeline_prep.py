from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from app.runtime_lifecycle import RuntimeLifecycle
from utils.terminal_ui import type_print, Color

if TYPE_CHECKING:
    from services.ocr_service import OcrService
    from services.docx_output_service import DocxOutputService
    from services.input_discovery_service import (
        InputDiscoveryService,
        DiscoveredInputs,
        DiscoveredPathTriplet,
    )
    from services.document_input_service import DocumentInputService
    from services.explainability import ExplainabilityRecorder
    from inout.explainability_writer import ExplainabilityWriter
    from nlp.ocr.ocr_server_process import OcrServerProcess


@dataclass
class PrepPipeline():
    """
    This pipeline establishes the files input
    and creates a new set of files.
    It loads text data in from word, pdf and image documents
    """
    app_root: str
    input_discovery_service: "InputDiscoveryService"
    document_input_service: "DocumentInputService"
    docx_out_service: "DocxOutputService"
    explainability: "ExplainabilityRecorder | None" = None
    explain_file_writer: "ExplainabilityWriter | None" = None
    ocr_server_proc: "OcrServerProcess | None" = None
    ocr_service: "OcrService | None" = None
    runtime_lifecycle: RuntimeLifecycle = field(default_factory=RuntimeLifecycle)

    def run_pipeline(self):
        discovered_inputs: DiscoveredInputs = self._discover_inputs()
        self._initialize_explainability_files(discovered_inputs)
        
        # Process the paths with docx first
        type_print("Loading docx files.", color=Color.GREEN)
        for triplet in discovered_inputs.docx_paths:
            loaded = self.document_input_service.load(triplet.in_path)
            self.docx_out_service.write_plain_copy(
                output_path=triplet.out_path,
                paragraphs=loaded.blocks,
            )

        # Then process the paths with pdfs
        type_print("Loading pdf files.", color=Color.GREEN)
        for triplet in discovered_inputs.pdf_paths:
            loaded = self.document_input_service.load(triplet.in_path)
            self.docx_out_service.write_plain_copy(
                output_path=triplet.out_path,
                paragraphs=self._format_pdf_blocks_for_docx(loaded.blocks),
            )
            self._append_prep_stage_line(
                triplet=triplet,
                line="[PREP STAGE] Extracted text from pdf.",
            )

        # Then process the paths with images
        if discovered_inputs.image_paths:
            type_print("Extracting text from image files.", color=Color.GREEN)
            if self.ocr_server_proc is None or self.ocr_service is None:
                return discovered_inputs
            self.runtime_lifecycle.register_process(self.ocr_server_proc)
            self.ocr_server_proc.start()
            try:
                for triplet in discovered_inputs.image_paths:
                    image_bytes = triplet.in_path.read_bytes()
                    extracted_text = self.ocr_service.extract_text(image_bytes=image_bytes)
                    self.docx_out_service.write_plain_copy(
                        output_path=triplet.out_path,
                        paragraphs=self._normalize_ocr_text(extracted_text),
                    )
                    self._append_prep_stage_line(
                        triplet=triplet,
                        line="[PREP STAGE] Extracted text from image.",
                    )
            finally:
                self.ocr_server_proc.stop()
        return discovered_inputs
        

    # Return all the files
    def _discover_inputs(self) -> DiscoveredInputs:
        inputs = self.input_discovery_service.discover()
        return inputs

    def _initialize_explainability_files(self, discovered_inputs: DiscoveredInputs) -> None:
        if self.explainability is None or self.explain_file_writer is None:
            return

        all_triplets = (
            discovered_inputs.docx_paths
            + discovered_inputs.pdf_paths
            + discovered_inputs.image_paths
            + discovered_inputs.unsupported_paths
        )
        for triplet in all_triplets:
            self.explainability.reset()
            self.explainability.start_doc(
                docx_path=triplet.out_path,
                include_edited_text=True,
            )
            lines = self.explainability.finish_doc()
            self.explain_file_writer.write_to_path(
                explained_path=triplet.explained_path,
                lines=lines,
            )

    def _append_prep_stage_line(
        self,
        triplet: "DiscoveredPathTriplet",
        line: str,
    ) -> None:
        if self.explainability is None or self.explain_file_writer is None:
            return
        triplet.explained_path.parent.mkdir(parents=True, exist_ok=True)
        with triplet.explained_path.open("a", encoding="utf-8") as explained_file:
            explained_file.write(f"{line}\n")

    def _format_pdf_blocks_for_docx(self, page_blocks: list[str]) -> list[str]:
        paragraphs: list[str] = []
        for idx, page_text in enumerate(page_blocks, start=1):
            paragraphs.append(f"--- Page {idx} ---")
            normalized = self._normalize_pdf_page_text(page_text)
            if normalized:
                paragraphs.extend(normalized)
            else:
                paragraphs.append("")
        return paragraphs

    def _normalize_pdf_page_text(self, page_text: str) -> list[str]:
        raw_lines = [line.strip() for line in page_text.splitlines()]
        if not raw_lines:
            return []

        paragraphs: list[str] = []
        current: str = ""
        non_empty_seen = 0

        for line in raw_lines:
            if not line:
                if current:
                    paragraphs.append(current)
                    current = ""
                continue

            non_empty_seen += 1
            if self._is_likely_heading(line, non_empty_seen):
                if current:
                    paragraphs.append(current)
                    current = ""
                paragraphs.append(line)
                continue

            if not current:
                current = line
            else:
                current = f"{current} {line}"

        if current:
            paragraphs.append(current)

        return paragraphs

    @staticmethod
    def _is_likely_heading(line: str, non_empty_seen: int) -> bool:
        if non_empty_seen != 1:
            return False
        if len(line) > 140:
            return False
        return not line.endswith((".", "!", "?", ";", ":"))

    @staticmethod
    def _normalize_ocr_text(text: str) -> list[str]:
        lines = [line.rstrip() for line in text.splitlines()]
        if not lines:
            return [""]
        normalized = [line for line in lines if line.strip()]
        return normalized or [""]

    
