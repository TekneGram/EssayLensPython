from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from pathlib import Path
from app.runtime_lifecycle import RuntimeLifecycle
from utils.terminal_ui import type_print, Color

if TYPE_CHECKING:
    from services.llm_service import LlmService
    from services.docx_output_service import DocxOutputService
    from services.input_discovery_service import DiscoveredInputs
    from services.explainability import ExplainabilityRecorder
    from inout.explainability_writer import ExplainabilityWriter
    from nlp.llm.llm_server_process import LlmServerProcess

from nlp.llm.llm_types import ChatRequest, ChatResponse