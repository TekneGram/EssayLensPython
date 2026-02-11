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
        discovered_inputs.pdf_paths

        # Then process the paths with images
        discovered_inputs.image_paths
        

    # Return all the files
    def _discover_inputs(self) -> DiscoveredInputs:
        inputs = self.input_discovery_service.discover()
        return inputs

    
