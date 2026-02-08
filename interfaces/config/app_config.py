from __future__ import annotations

from dataclasses import dataclass
from config.assessment_paths_config import AssessmentPathsConfig

@dataclass(frozen=True)
class AppConfigShape:
    assessmentPaths: AssessmentPathsConfig