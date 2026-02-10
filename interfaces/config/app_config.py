from __future__ import annotations

from dataclasses import dataclass
from config.llm_request_config import LlmRequestConfig
from config.llm_server_config import LlmServerConfig
from config.assessment_paths_config import AssessmentPathsConfig
from config.llm_config import LlmConfig
from config.run_config import RunConfig
from config.ged_config import GedConfig
from config.ocr_config import OcrConfig

@dataclass(frozen=True)
class AppConfigShape:
    assessment_paths: AssessmentPathsConfig
    llm_config: LlmConfig
    ocr_config: OcrConfig
    llm_server: LlmServerConfig
    llm_request: LlmRequestConfig
    run_config: RunConfig
    ged_config: GedConfig
