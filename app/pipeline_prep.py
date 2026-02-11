from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from services.llm_service import LlmService
    from services.ocr_service import OcrService
    from services.docx_output_service import DocxOutputService
    from services.input_discovery_service import InputDiscoveryService, DiscoveredInputs
    from services.document_input_service import DocumentInputService

from nlp.llm.llm_types import ChatRequest, ChatResponse

# Interfaces
from interfaces.config.app_config import AppConfigShape
from interfaces.inout import DocxLoader

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

    def run_pipeline(self):
        discovered_inputs: DiscoveredInputs = self._discover_inputs()
        
        # Process the paths with docx first
        for triplet in discovered_inputs.docx_paths:
            loaded = self.document_input_service.load(triplet.in_path)
            self.docx_out_service.write_plain_copy(
                output_path=triplet.out_path,
                paragraphs=loaded.blocks,
            )

        # Then process the paths with pdfs
        for triplet in discovered_inputs.pdf_paths:
            loaded = self.document_input_service.load(triplet.in_path)
            self.docx_out_service.write_plain_copy(
                output_path=triplet.out_path,
                paragraphs=self._format_pdf_blocks_for_docx(loaded.blocks),
            )

        # Then process the paths with images
        discovered_inputs.image_paths
        

    # Return all the files
    def _discover_inputs(self) -> DiscoveredInputs:
        inputs = self.input_discovery_service.discover()
        return inputs

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

    
