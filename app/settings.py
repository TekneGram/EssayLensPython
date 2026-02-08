from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from config.assessment_paths_config import AssessmentPathsConfig


@dataclass(frozen=True, slots=True)
class AppConfig:
    assessment_paths: AssessmentPathsConfig

def build_settings() -> AppConfig:

    assessment_paths = AssessmentPathsConfig.from_strings(
        input_folder="Assessment/in",
        output_folder="Assessment/checked",
        explained_folder="Assessment/explained"
    )
    assessment_paths.validate()
    assessment_paths.ensure_output_dirs()

    return AppConfig(assessment_paths=assessment_paths)