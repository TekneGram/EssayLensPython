from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from docx_tools.sentence_splitter import split_sentences
from utils.terminal_ui import type_print, Color

from app.runtime_lifecycle import RuntimeLifecycle

if TYPE_CHECKING:
    from interfaces.config.app_config import AppConfigShape
    from nlp.ged.ged_types import GedSentenceResult
    from nlp.llm.llm_server_process import LlmServerProcess
    from services.document_input_service import DocumentInputService
    from services.explainability import ExplainabilityRecorder
    from services.docx_output_service import DocxOutputService
    from services.input_discovery_service import DiscoveredInputs, DiscoveredPathTriplet
    from services.ged_service import GedService
    from services.llm_task_service import LlmTaskService


@dataclass
class FBPipeline:
    """
    Grammar Error Detection and Correction Pipeline

    Loops through all the individual paragraphs and finds grammar errors
    using the GED BERT.
    Uses LLM to correct sentences with errors.
    """
    app_cfg: "AppConfigShape"
    discovered_inputs: "DiscoveredInputs"
    document_input_service: "DocumentInputService"
    docx_out_service: "DocxOutputService"
    ged_service: "GedService"
    llm_task_service: "LlmTaskService"
    explainability: "ExplainabilityRecorder | None" = None
    llm_server_proc: "LlmServerProcess | None" = None
    rng: random.Random = field(default_factory=random.Random)
    runtime_lifecycle: RuntimeLifecycle = field(default_factory=RuntimeLifecycle)

    def run_pipeline(self) -> dict[str, Any]:

        return