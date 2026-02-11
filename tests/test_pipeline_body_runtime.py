from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from app.pipeline_body import BodyPipeline
from services.input_discovery_service import DiscoveredInputs, DiscoveredPathTriplet


class BodyPipelineRuntimeTests(unittest.TestCase):
    def _make_cfg(self, *, llama_n_parallel: int = 3):
        return SimpleNamespace(llm_server=SimpleNamespace(llama_n_parallel=llama_n_parallel))

    def test_run_pipeline_processes_full_stage_passes_in_batches_of_4(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            triplets: list[DiscoveredPathTriplet] = []
            paragraphs_by_parent: dict[Path, list[str]] = {}

            paragraph_counts = [2, 1, 1, 1, 1]  # total paragraphs = 6
            for idx, para_count in enumerate(paragraph_counts, start=1):
                out_parent = root / "out" / f"doc{idx}"
                out_parent.mkdir(parents=True, exist_ok=True)
                out_path = out_parent / f"doc{idx}_checked.docx"
                explained_path = root / "explained" / f"doc{idx}_explained.txt"
                conc_path = out_parent / "conc_para.docx"
                conc_path.write_bytes(b"")

                triplets.append(
                    DiscoveredPathTriplet(
                        in_path=root / "in" / f"doc{idx}.docx",
                        out_path=out_path,
                        explained_path=explained_path,
                    )
                )
                paragraphs_by_parent[out_parent] = [
                    f"Paragraph {idx}.{p}" for p in range(1, para_count + 1)
                ]

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
                    return Mock(blocks=paragraphs_by_parent[p.parent])
                raise AssertionError(f"Unexpected load path: {p}")

            document_input_service.load.side_effect = _load_side_effect

            stage_calls: list[str] = []
            llm_task_service = Mock()

            def _hedging_side_effect(*, app_cfg, text_tasks, max_concurrency):
                _ = (app_cfg, max_concurrency)
                stage_calls.append(f"hedging:{len(text_tasks)}")
                return {
                    "task_count": len(text_tasks),
                    "success_count": len(text_tasks),
                    "failure_count": 0,
                    "outputs": [Mock(content=f"Hedging {i}") for i, _ in enumerate(text_tasks, start=1)],
                }

            def _cause_effect_side_effect(*, app_cfg, text_tasks, max_concurrency):
                _ = (app_cfg, max_concurrency)
                stage_calls.append(f"cause_effect:{len(text_tasks)}")
                return {
                    "task_count": len(text_tasks),
                    "success_count": len(text_tasks),
                    "failure_count": 0,
                    "outputs": [Mock(content=f"CauseEffect {i}") for i, _ in enumerate(text_tasks, start=1)],
                }

            def _compare_contrast_side_effect(*, app_cfg, text_tasks, max_concurrency):
                _ = (app_cfg, max_concurrency)
                stage_calls.append(f"compare_contrast:{len(text_tasks)}")
                return {
                    "task_count": len(text_tasks),
                    "success_count": len(text_tasks),
                    "failure_count": 0,
                    "outputs": [Mock(content=f"CompareContrast {i}") for i, _ in enumerate(text_tasks, start=1)],
                }

            llm_task_service.analyze_hedging_parallel.side_effect = _hedging_side_effect
            llm_task_service.analyze_cause_effect_parallel.side_effect = _cause_effect_side_effect
            llm_task_service.analyze_compare_contrast_parallel.side_effect = _compare_contrast_side_effect

            docx_out_service = Mock()

            pipeline = BodyPipeline(
                app_cfg=self._make_cfg(llama_n_parallel=3),
                discovered_inputs=discovered_inputs,
                document_input_service=document_input_service,
                docx_out_service=docx_out_service,
                llm_task_service=llm_task_service,
            )

            result = pipeline.run_pipeline()

            self.assertEqual(
                stage_calls,
                [
                    "hedging:4",
                    "hedging:2",
                    "cause_effect:4",
                    "cause_effect:2",
                    "compare_contrast:4",
                    "compare_contrast:2",
                ],
            )
            self.assertEqual(result["document_count"], 5)
            self.assertEqual(result["batch_size"], 4)
            self.assertEqual(result["stages"]["hedging"]["task_count"], 6)
            self.assertEqual(result["stages"]["cause_effect"]["task_count"], 6)
            self.assertEqual(result["stages"]["compare_contrast"]["task_count"], 6)

            self.assertEqual(docx_out_service.append_paragraphs.call_count, 18)
            first_call = docx_out_service.append_paragraphs.call_args_list[0]
            self.assertEqual(Path(first_call.kwargs["output_path"]).name, "fb.docx")
            self.assertIn("Body Feedback - Paragraph", first_call.kwargs["paragraphs"][0])
            self.assertTrue(first_call.kwargs["paragraphs"][1].startswith("Hedging:"))

    def test_run_pipeline_handles_missing_conc_para(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            triplet = DiscoveredPathTriplet(
                in_path=root / "in" / "doc.docx",
                out_path=root / "out" / "doc" / "doc_checked.docx",
                explained_path=root / "explained" / "doc_explained.txt",
            )

            discovered_inputs = DiscoveredInputs(
                docx_paths=[triplet],
                pdf_paths=[],
                image_paths=[],
                unsupported_paths=[],
            )

            pipeline = BodyPipeline(
                app_cfg=self._make_cfg(),
                discovered_inputs=discovered_inputs,
                document_input_service=Mock(),
                docx_out_service=Mock(),
                llm_task_service=Mock(),
            )

            result = pipeline.run_pipeline()

            self.assertEqual(result["document_count"], 1)
            self.assertEqual(result["stages"], {})
            self.assertIn("Missing source file", result["items"][0]["errors"][0])


if __name__ == "__main__":
    unittest.main()
