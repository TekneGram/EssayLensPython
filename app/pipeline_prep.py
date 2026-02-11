from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.llm_service import LlmService
    from services.ocr_service import OcrService
    from services.docx_output_service import DocxOutputService
    from services.input_discovery_service import InputDiscoveryService
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

    # Return all the files
    
