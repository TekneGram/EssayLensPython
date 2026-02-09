from __future__ import annotations

# Standard library imports
from dataclasses import dataclass
from pathlib import Path
import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.llm_service import LlmService

# Interfaces and protocols
from interfaces.config.app_config import AppConfigShape

@dataclass
class TestPipeline():
    """
    End to end pipeline to run a quick sanity check test.
    Responsibilities
    - Apply LLM chat
    """

    # Injected dependencies
    llm: "LlmService"

    def run_test(self, app_cfg:AppConfigShape):
        return asyncio.run(self.llm.run_parallel_kv_cache_test(app_cfg))