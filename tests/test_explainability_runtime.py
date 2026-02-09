from __future__ import annotations

import re
import unittest
from pathlib import Path

from config.ged_config import GedConfig
from config.llm_config import LlmConfig
from config.run_config import RunConfig
from services.explainability import ExplainabilityRecorder


class ExplainabilityRuntimeTests(unittest.TestCase):
    def _make_recorder(self) -> ExplainabilityRecorder:
        run_cfg = RunConfig.from_strings(author="tester")
        ged_cfg = GedConfig.from_strings(model_name="ged-demo", batch_size=8)
        llm_cfg = LlmConfig.from_strings(
            llama_server_model="demo",
            llama_model_key="demo",
            llama_model_display_name="Demo",
            llama_model_alias="demo",
            llama_model_family="instruct",
        )
        return ExplainabilityRecorder.new(run_cfg=run_cfg, ged_cfg=ged_cfg, llm_config=llm_cfg)

    def test_new_builds_utc_run_id(self) -> None:
        recorder = self._make_recorder()
        self.assertRegex(recorder.run_id, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_start_doc_writes_expected_metadata(self) -> None:
        recorder = self._make_recorder()
        recorder.start_doc(Path("essay.docx"), include_edited_text=True)
        lines = recorder.finish_doc()

        self.assertIn("Explainability Report: essay.docx", lines)
        self.assertTrue(any("GED_MODEL: ged-demo" in line for line in lines))
        self.assertTrue(any("GED_BATCH_SIZE: 8" in line for line in lines))
        self.assertTrue(any("LLAMA_MODEL: Demo" in line for line in lines))
        self.assertTrue(any("INCLUDE_EDITED_TEXT_SECTION: True" in line for line in lines))

    def test_log_and_log_kv(self) -> None:
        recorder = self._make_recorder()
        recorder.log("GED", "scored")
        recorder.log_kv("LLM", {"model": "demo", "tokens": 42})

        lines = recorder.finish_doc()
        self.assertIn("[GED] scored", lines)
        self.assertIn("[LLM] model: demo", lines)
        self.assertIn("[LLM] tokens: 42", lines)

    def test_finish_doc_returns_copy_like_snapshot(self) -> None:
        recorder = self._make_recorder()
        recorder.log("X", "one")
        lines = recorder.finish_doc()
        lines.append("mutated")
        self.assertNotIn("mutated", recorder.finish_doc())

    def test_reset_clears_lines(self) -> None:
        recorder = self._make_recorder()
        recorder.log("GED", "x")
        recorder.reset()
        self.assertEqual(recorder.finish_doc(), [])


if __name__ == "__main__":
    unittest.main()
