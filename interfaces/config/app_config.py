from __future__ import annotations

from dataclasses import dataclass
from config.LlmRequestConfig import LlmRequestConfig
from config.LlmServerConfig import LlmServerConfig
from config.assessment_paths_config import AssessmentPathsConfig

@dataclass(frozen=True)
class AppConfigShape:
    assessmentPaths: AssessmentPathsConfig
    llmServer: LlmServerConfig
    llmRequest: LlmRequestConfig
