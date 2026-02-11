from __future__ import annotations

import random
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from app.pipeline_ged import GEDPipeline
from nlp.ged.ged_types import GedSentenceResult
from services.input_discovery_service import DiscoveredInputs, DiscoveredPathTriplet


class GEDPipelineRuntimeTests(unittest.TestCase):
    def _make_triplet(self, root: Path) -> DiscoveredPathTriplet:
        out_path = root / "out" / "student_checked.docx"
        explained_path = root / "explained" / "student_explained.txt"
        conc_para_path = out_path.parent / "conc_para.docx"
        conc_para_path.parent.mkdir(parents=True, exist_ok=True)
        conc_para_path.write_bytes(b"")
        return DiscoveredPathTriplet(
            in_path=root / "input" / "student.docx",
            out_path=out_path,
            explained_path=explained_path,
        )

    def _make_cfg(self, *, max_llm_corrections: int = 5, llama_n_parallel: int = 3):
        return SimpleNamespace(
            run_config=SimpleNamespace(max_llm_corrections=max_llm_corrections),
            ged_config=SimpleNamespace(batch_size=8),
            llm_server=SimpleNamespace(llama_n_parallel=llama_n_parallel),
        )

    def test_run_pipeline_skips_llm_when_no_grammar_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            triplet = self._make_triplet(Path(tmpdir))
            discovered_inputs = DiscoveredInputs(
                docx_paths=[triplet],
                pdf_paths=[],
                image_paths=[],
                unsupported_paths=[],
            )

            document_input_service = Mock()
            document_input_service.load.return_value = Mock(blocks=["Clean sentence."])
            docx_out_service = Mock()
            ged_service = Mock()
            ged_service.score.return_value = [
                GedSentenceResult(
                    sentence="Clean sentence.",
                    has_error=False,
                    error_tokens=[],
                )
            ]
            llm_task_service = Mock()

            pipeline = GEDPipeline(
                app_cfg=self._make_cfg(),
                discovered_inputs=discovered_inputs,
                document_input_service=document_input_service,
                docx_out_service=docx_out_service,
                ged_service=ged_service,
                llm_task_service=llm_task_service,
            )

            result = pipeline.run_pipeline()

            llm_task_service.correct_grammar_parallel.assert_not_called()
            docx_out_service.append_corrected_paragraph.assert_called_once_with(
                output_path=triplet.out_path,
                original_paragraph="Clean sentence.",
                corrected_paragraph="Clean sentence.",
            )
            self.assertEqual(result["paragraph_count"], 1)
            self.assertEqual(result["corrected_paragraph_count"], 0)
            self.assertEqual(result["llm_task_count"], 0)

    def test_run_pipeline_caps_and_samples_flagged_sentences(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            triplet = self._make_triplet(Path(tmpdir))
            discovered_inputs = DiscoveredInputs(
                docx_paths=[triplet],
                pdf_paths=[],
                image_paths=[],
                unsupported_paths=[],
            )

            document_input_service = Mock()
            document_input_service.load.return_value = Mock(
                blocks=["Bad one. Bad two. Bad three. Fine."]
            )
            docx_out_service = Mock()
            ged_service = Mock()
            ged_service.score.return_value = [
                GedSentenceResult(sentence="Bad one.", has_error=True, error_tokens=["Bad"]),
                GedSentenceResult(sentence="Bad two.", has_error=True, error_tokens=["Bad"]),
                GedSentenceResult(sentence="Bad three.", has_error=True, error_tokens=["Bad"]),
                GedSentenceResult(sentence="Fine.", has_error=False, error_tokens=[]),
            ]
            llm_task_service = Mock()
            llm_task_service.correct_grammar_parallel.return_value = {
                "outputs": [Mock(content="Good two."), Mock(content="Good three.")],
                "task_count": 2,
                "success_count": 2,
                "failure_count": 0,
            }

            pipeline = GEDPipeline(
                app_cfg=self._make_cfg(max_llm_corrections=2, llama_n_parallel=5),
                discovered_inputs=discovered_inputs,
                document_input_service=document_input_service,
                docx_out_service=docx_out_service,
                ged_service=ged_service,
                llm_task_service=llm_task_service,
                rng=random.Random(0),
            )

            result = pipeline.run_pipeline()

            llm_task_service.correct_grammar_parallel.assert_called_once_with(
                app_cfg=pipeline.app_cfg,
                text_tasks=["Bad two.", "Bad three."],
                max_concurrency=5,
            )
            docx_out_service.append_corrected_paragraph.assert_called_once_with(
                output_path=triplet.out_path,
                original_paragraph="Bad one. Bad two. Bad three. Fine.",
                corrected_paragraph="Bad one. Good two. Good three. Fine.",
            )
            explained_text = triplet.explained_path.read_text(encoding="utf-8")
            self.assertIn("sampled=2", explained_text)
            self.assertEqual(result["llm_task_count"], 2)
            self.assertEqual(result["llm_success_count"], 2)
            self.assertEqual(result["corrected_paragraph_count"], 1)


if __name__ == "__main__":
    unittest.main()
