from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from app.pipeline_fb import FBPipeline
from services.input_discovery_service import DiscoveredInputs, DiscoveredPathTriplet


class FBPipelineRuntimeTests(unittest.TestCase):
    def _make_cfg(self, *, max_llm_corrections: int = 4, llama_n_parallel: int = 3):
        return SimpleNamespace(
            run_config=SimpleNamespace(max_llm_corrections=max_llm_corrections),
            llm_server=SimpleNamespace(llama_n_parallel=llama_n_parallel),
        )

    def test_run_pipeline_batches_documents_and_writes_ts_and_fb_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            triplets: list[DiscoveredPathTriplet] = []
            conc_by_parent: dict[Path, str] = {}
            ts_from_file_by_parent: dict[Path, str] = {}

            for idx in range(1, 6):
                out_parent = root / "out" / f"doc{idx}"
                out_parent.mkdir(parents=True, exist_ok=True)
                out_path = out_parent / f"doc{idx}_checked.docx"
                explained_path = root / "explained" / f"doc{idx}_explained.txt"
                conc_path = out_parent / "conc_para.docx"
                conc_path.write_bytes(b"")

                triplet = DiscoveredPathTriplet(
                    in_path=root / "in" / f"doc{idx}.docx",
                    out_path=out_path,
                    explained_path=explained_path,
                )
                triplets.append(triplet)

                conc_by_parent[out_parent] = (
                    f"Learner topic {idx}. Supporting detail {idx}a. Supporting detail {idx}b."
                )
                ts_from_file_by_parent[out_parent] = f"TS file topic {idx}."

            discovered_inputs = DiscoveredInputs(
                docx_paths=triplets,
                pdf_paths=[],
                image_paths=[],
                unsupported_paths=[],
            )

            document_input_service = Mock()

            def _load_side_effect(path: Path):
                p = Path(path)
                if p.name == "conc_para.docx":
                    return Mock(blocks=[conc_by_parent[p.parent]])
                if p.name == "ts.docx":
                    return Mock(blocks=[ts_from_file_by_parent[p.parent]])
                raise AssertionError(f"Unexpected load path: {p}")

            document_input_service.load.side_effect = _load_side_effect

            constructor_calls: list[list[str]] = []
            analyzer_calls: list[list[str]] = []

            llm_task_service = Mock()

            def _construct_side_effect(*, app_cfg, text_tasks, max_concurrency):
                _ = (app_cfg, max_concurrency)
                constructor_calls.append(list(text_tasks))
                outputs = [Mock(content=f"Constructed topic {i}.") for i, _ in enumerate(text_tasks, start=1)]
                return {
                    "task_count": len(text_tasks),
                    "success_count": len(text_tasks),
                    "failure_count": 0,
                    "outputs": outputs,
                }

            def _analyze_side_effect(*, app_cfg, text_tasks, max_concurrency):
                _ = (app_cfg, max_concurrency)
                analyzer_calls.append(list(text_tasks))
                outputs = [Mock(content=f"Feedback {i}") for i, _ in enumerate(text_tasks, start=1)]
                return {
                    "task_count": len(text_tasks),
                    "success_count": len(text_tasks),
                    "failure_count": 0,
                    "outputs": outputs,
                }

            llm_task_service.construct_topic_sentence_parallel.side_effect = _construct_side_effect
            llm_task_service.analyze_topic_sentence_parallel.side_effect = _analyze_side_effect

            docx_out_service = Mock()

            pipeline = FBPipeline(
                app_cfg=self._make_cfg(max_llm_corrections=4, llama_n_parallel=3),
                discovered_inputs=discovered_inputs,
                document_input_service=document_input_service,
                docx_out_service=docx_out_service,
                llm_task_service=llm_task_service,
            )

            result = pipeline.run_pipeline()

            self.assertEqual(len(constructor_calls), 2)
            self.assertEqual(len(constructor_calls[0]), 4)
            self.assertEqual(len(constructor_calls[1]), 1)
            self.assertEqual(len(analyzer_calls), 2)
            self.assertEqual(len(analyzer_calls[0]), 4)
            self.assertEqual(len(analyzer_calls[1]), 1)

            first_analyzer_payload = json.loads(analyzer_calls[0][0])
            self.assertEqual(first_analyzer_payload["learner_topic_sentence"], "Learner topic 1.")
            self.assertEqual(
                first_analyzer_payload["good_topic_sentence"],
                "TS file topic 1.",
                "Analyzer should use ts.docx content as good_topic_sentence.",
            )

            self.assertEqual(result["document_count"], 5)
            self.assertEqual(result["constructor_task_count"], 5)
            self.assertEqual(result["analysis_task_count"], 5)
            self.assertEqual(result["batch_size"], 4)
            self.assertEqual(docx_out_service.write_plain_copy.call_count, 10)

    def test_run_pipeline_marks_missing_conc_para(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out_path = root / "out" / "doc" / "doc_checked.docx"
            triplet = DiscoveredPathTriplet(
                in_path=root / "in" / "doc.docx",
                out_path=out_path,
                explained_path=root / "explained" / "doc_explained.txt",
            )
            discovered_inputs = DiscoveredInputs(
                docx_paths=[triplet],
                pdf_paths=[],
                image_paths=[],
                unsupported_paths=[],
            )

            pipeline = FBPipeline(
                app_cfg=self._make_cfg(max_llm_corrections=4, llama_n_parallel=3),
                discovered_inputs=discovered_inputs,
                document_input_service=Mock(),
                docx_out_service=Mock(),
                llm_task_service=Mock(),
            )

            result = pipeline.run_pipeline()

            self.assertEqual(result["document_count"], 1)
            self.assertEqual(result["constructor_task_count"], 0)
            self.assertEqual(result["analysis_task_count"], 0)
            self.assertIn("Missing source file", result["items"][0]["error"])


if __name__ == "__main__":
    unittest.main()
