from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from app.pipeline_content import ContentPipeline
from services.input_discovery_service import DiscoveredInputs, DiscoveredPathTriplet


class ContentPipelineRuntimeTests(unittest.TestCase):
    def _make_cfg(self, *, llama_n_parallel: int = 3):
        return SimpleNamespace(llm_server=SimpleNamespace(llama_n_parallel=llama_n_parallel))

    def test_run_pipeline_uses_two_stage_order_with_batches_of_4(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            triplets: list[DiscoveredPathTriplet] = []
            conc_by_parent: dict[Path, list[str]] = {}
            comp_by_parent: dict[Path, list[str]] = {}

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
                conc_by_parent[out_parent] = [
                    f"Conc paragraph {idx}.{p}" for p in range(1, para_count + 1)
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
                    return Mock(blocks=conc_by_parent[p.parent])
                if p.name == "comp_para.docx":
                    return Mock(blocks=comp_by_parent.get(p.parent, []))
                raise AssertionError(f"Unexpected load path: {p}")

            document_input_service.load.side_effect = _load_side_effect

            stage_calls: list[str] = []
            llm_task_service = Mock()

            def _content_side_effect(*, app_cfg, text_tasks, max_concurrency):
                _ = (app_cfg, max_concurrency)
                stage_calls.append(f"analysis:{len(text_tasks)}")
                return {
                    "task_count": len(text_tasks),
                    "success_count": len(text_tasks),
                    "failure_count": 0,
                    "outputs": [Mock(content=f"Comp paragraph {i}") for i, _ in enumerate(text_tasks, start=1)],
                }

            def _filter_side_effect(*, app_cfg, text_tasks, max_concurrency):
                _ = (app_cfg, max_concurrency)
                stage_calls.append(f"filter:{len(text_tasks)}")
                return {
                    "task_count": len(text_tasks),
                    "success_count": len(text_tasks),
                    "failure_count": 0,
                    "outputs": [Mock(content=f"Filtered paragraph {i}") for i, _ in enumerate(text_tasks, start=1)],
                }

            llm_task_service.analyze_content_parallel.side_effect = _content_side_effect
            llm_task_service.filter_content_parallel.side_effect = _filter_side_effect

            docx_out_service = Mock()

            def _write_plain_copy_side_effect(*, output_path: Path, paragraphs: list[str]):
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                Path(output_path).write_bytes(b"")
                comp_by_parent[Path(output_path).parent] = list(paragraphs)
                return output_path

            docx_out_service.write_plain_copy.side_effect = _write_plain_copy_side_effect

            pipeline = ContentPipeline(
                app_cfg=self._make_cfg(llama_n_parallel=3),
                discovered_inputs=discovered_inputs,
                document_input_service=document_input_service,
                docx_out_service=docx_out_service,
                llm_task_service=llm_task_service,
            )

            result = pipeline.run_pipeline()

            self.assertEqual(
                stage_calls,
                ["analysis:4", "analysis:2", "filter:4", "filter:2"],
            )
            self.assertEqual(result["document_count"], 5)
            self.assertEqual(result["batch_size"], 4)
            self.assertEqual(result["content_analysis"]["task_count"], 6)
            self.assertEqual(result["content_filter"]["task_count"], 6)

            self.assertEqual(docx_out_service.write_plain_copy.call_count, 5)
            self.assertEqual(docx_out_service.append_paragraphs.call_count, 6)
            first_fb_call = docx_out_service.append_paragraphs.call_args_list[0]
            self.assertEqual(Path(first_fb_call.kwargs["output_path"]).name, "fb.docx")

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

            pipeline = ContentPipeline(
                app_cfg=self._make_cfg(),
                discovered_inputs=discovered_inputs,
                document_input_service=Mock(),
                docx_out_service=Mock(),
                llm_task_service=Mock(),
            )

            result = pipeline.run_pipeline()

            self.assertEqual(result["document_count"], 1)
            self.assertEqual(result["content_analysis"]["task_count"], 0)
            self.assertEqual(result["content_filter"]["task_count"], 0)
            self.assertIn("Missing source file", result["items"][0]["errors"][0])


if __name__ == "__main__":
    unittest.main()
