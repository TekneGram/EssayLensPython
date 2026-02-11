from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from app.pipeline_summarize_fb import SummarizeFBPipeline
from services.input_discovery_service import DiscoveredInputs, DiscoveredPathTriplet


class SummarizeFBPipelineRuntimeTests(unittest.TestCase):
    def _make_cfg(self, *, llama_n_parallel: int = 3):
        return SimpleNamespace(llm_server=SimpleNamespace(llama_n_parallel=llama_n_parallel))

    def test_run_pipeline_batches_fb_documents_and_appends_to_out_docx(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            triplets: list[DiscoveredPathTriplet] = []
            fb_by_parent: dict[Path, str] = {}

            for idx in range(1, 6):
                out_parent = root / "out" / f"doc{idx}"
                out_parent.mkdir(parents=True, exist_ok=True)
                out_path = out_parent / f"doc{idx}_checked.docx"
                explained_path = root / "explained" / f"doc{idx}_explained.txt"
                fb_path = out_parent / "fb.docx"
                fb_path.write_bytes(b"")

                triplets.append(
                    DiscoveredPathTriplet(
                        in_path=root / "in" / f"doc{idx}.docx",
                        out_path=out_path,
                        explained_path=explained_path,
                    )
                )
                fb_by_parent[out_parent] = f"Feedback text for student {idx}."

            discovered_inputs = DiscoveredInputs(
                docx_paths=triplets,
                pdf_paths=[],
                image_paths=[],
                unsupported_paths=[],
            )

            document_input_service = Mock()

            def _load_side_effect(path: Path):
                p = Path(path)
                if p.name == "fb.docx":
                    return Mock(blocks=[fb_by_parent[p.parent]])
                raise AssertionError(f"Unexpected load path: {p}")

            document_input_service.load.side_effect = _load_side_effect

            summarize_batches: list[list[str]] = []
            llm_task_service = Mock()

            def _summarize_side_effect(*, app_cfg, text_tasks, max_concurrency):
                _ = (app_cfg, max_concurrency)
                summarize_batches.append(list(text_tasks))
                return {
                    "task_count": len(text_tasks),
                    "success_count": len(text_tasks),
                    "failure_count": 0,
                    "outputs": [Mock(content=f"Summary {i}") for i, _ in enumerate(text_tasks, start=1)],
                }

            llm_task_service.summarize_personalize_parallel.side_effect = _summarize_side_effect
            docx_out_service = Mock()

            pipeline = SummarizeFBPipeline(
                app_cfg=self._make_cfg(llama_n_parallel=3),
                discovered_inputs=discovered_inputs,
                document_input_service=document_input_service,
                docx_out_service=docx_out_service,
                llm_task_service=llm_task_service,
            )

            result = pipeline.run_pipeline()

            self.assertEqual(len(summarize_batches), 2)
            self.assertEqual(len(summarize_batches[0]), 4)
            self.assertEqual(len(summarize_batches[1]), 1)
            self.assertEqual(result["document_count"], 5)
            self.assertEqual(result["task_count"], 5)
            self.assertEqual(result["success_count"], 5)
            self.assertEqual(result["failure_count"], 0)
            self.assertEqual(result["batch_size"], 4)
            self.assertEqual(docx_out_service.append_paragraphs.call_count, 5)

            first_call = docx_out_service.append_paragraphs.call_args_list[0]
            self.assertEqual(first_call.kwargs["paragraphs"][1], "Final Feedback")
            self.assertEqual(Path(first_call.kwargs["output_path"]).name, "doc1_checked.docx")

    def test_run_pipeline_handles_missing_fb_docx(self) -> None:
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

            pipeline = SummarizeFBPipeline(
                app_cfg=self._make_cfg(),
                discovered_inputs=discovered_inputs,
                document_input_service=Mock(),
                docx_out_service=Mock(),
                llm_task_service=Mock(),
            )

            result = pipeline.run_pipeline()

            self.assertEqual(result["document_count"], 1)
            self.assertEqual(result["task_count"], 0)
            self.assertEqual(result["success_count"], 0)
            self.assertEqual(result["failure_count"], 0)
            self.assertIn("Missing source file", result["items"][0]["errors"][0])


if __name__ == "__main__":
    unittest.main()
