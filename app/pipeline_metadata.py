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

@dataclass
class MetadataPipeline():
    """
    This pipeline loops through all the extracted files.
    It runs them through the LLM to extract metadata such as
    student name, student number, and the title of the essay
    """

    discovered_inputs: DiscoveredInputs
    runtime_lifecycle: RuntimeLifecycle = field(default_factory=RuntimeLifecycle)
    llm_server_proc: "LlmServerProcess"
    llm_service: "LlmService"
    explainability: "ExplainabilityRecorder"
    explain_file_writer: "ExplainabilityWriter"
    docx_out_service: "DocxOutputService"

    def run_pipeline(self):
        # Load up the server

        # Loop through all the "out" files for docx, pdf and image

        # For each file, extract the text

        # Create batches of four files each and send the text to the LLM.

        # The LLM will have a system prompt already prepared to do parallel inference.

        # The returned text should be appended to the same document from which
        # it came, with "EDITED TEXT" as a header, using the metadata.
        return