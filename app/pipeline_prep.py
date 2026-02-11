from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.llm_service import LlmService
    from services.ocr_service import OcrService
    from services.docx_output_service import DocxOutputService

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
    docx_out: "DocxOutputService"
