from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from app.pipeline_metadata import MetadataPipeline
from services.input_discovery_service import DiscoveredInputs, DiscoveredPathTriplet


class MetadataPipelineRuntimeTests(unittest.TestCase):
    def test_run_pipeline_loads_out_paths_and_maps_parallel_results(self) -> None:
        triplet_a = DiscoveredPathTriplet(
            in_path=Path("/tmp/in/a.pdf"),
            out_path=Path("/tmp/out/a_checked.docx"),
            explained_path=Path("/tmp/explained/a_explained.txt"),
        )
        triplet_b = DiscoveredPathTriplet(
            in_path=Path("/tmp/in/b.png"),
            out_path=Path("/tmp/out/b_checked.docx"),
            explained_path=Path("/tmp/explained/b_explained.txt"),
        )

        discovered_inputs = DiscoveredInputs(
            docx_paths=[],
            pdf_paths=[triplet_a],
            image_paths=[triplet_b],
            unsupported_paths=[],
        )
        app_cfg = SimpleNamespace(llm_server=SimpleNamespace(llama_n_parallel=2))

        document_input_service = Mock()
        document_input_service.load.side_effect = [
            Mock(blocks=["name: student A", "essay body A"]),
            Mock(blocks=["name: student B", "essay body B"]),
        ]

        llm_no_think = Mock()
        llm_no_think.json_schema_chat_many = AsyncMock(
            return_value=[
                {
                    "student_name": "A",
                    "student_number": "",
                    "essay_title": "",
                    "essay": "essay body A",
                    "extraneous": "",
                },
                RuntimeError("parse failed"),
            ]
        )
        llm_service = Mock()
        llm_service.with_mode.return_value = llm_no_think
        docx_out_service = Mock()

        pipeline = MetadataPipeline(
            app_cfg=app_cfg,
            discovered_inputs=discovered_inputs,
            document_input_service=document_input_service,
            docx_out_service=docx_out_service,
            llm_service=llm_service,
        )

        result = pipeline.run_pipeline()

        llm_service.with_mode.assert_called_once_with("no_think")
        document_input_service.load.assert_any_call(triplet_a.out_path)
        document_input_service.load.assert_any_call(triplet_b.out_path)
        self.assertEqual(result["task_count"], 2)
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["failure_count"], 1)
        self.assertEqual(result["items"][0]["metadata"]["student_name"], "A")
        self.assertEqual(result["items"][1]["error"], "parse failed")
        docx_out_service.append_paragraphs.assert_called_once_with(
            output_path=triplet_a.out_path,
            paragraphs=[
                "",
                "Edited Text",
                "Student Name: A",
                "Student Number: ",
                "Essay Title: ",
                "essay body A",
            ],
        )
        docx_out_service.write_plain_copy.assert_called_once_with(
            output_path=triplet_a.out_path.parent / "conc_para.docx",
            paragraphs=["essay body A"],
        )

    def test_run_pipeline_batches_by_llama_n_parallel(self) -> None:
        triplets = [
            DiscoveredPathTriplet(
                in_path=Path(f"/tmp/in/{i}.pdf"),
                out_path=Path(f"/tmp/out/{i}_checked.docx"),
                explained_path=Path(f"/tmp/explained/{i}_explained.txt"),
            )
            for i in range(5)
        ]
        discovered_inputs = DiscoveredInputs(
            docx_paths=[],
            pdf_paths=triplets,
            image_paths=[],
            unsupported_paths=[],
        )
        app_cfg = SimpleNamespace(llm_server=SimpleNamespace(llama_n_parallel=2))

        document_input_service = Mock()
        document_input_service.load.side_effect = [Mock(blocks=[f"essay {i}"]) for i in range(5)]

        llm_no_think = Mock()
        llm_no_think.json_schema_chat_many = AsyncMock(
            side_effect=[
                [
                    {
                        "student_name": "A",
                        "student_number": "",
                        "essay_title": "",
                        "essay": "essay 0",
                        "extraneous": "",
                    },
                    {
                        "student_name": "B",
                        "student_number": "",
                        "essay_title": "",
                        "essay": "essay 1",
                        "extraneous": "",
                    },
                ],
                [
                    {
                        "student_name": "C",
                        "student_number": "",
                        "essay_title": "",
                        "essay": "essay 2",
                        "extraneous": "",
                    },
                    RuntimeError("fail-d"),
                ],
                [
                    {
                        "student_name": "E",
                        "student_number": "",
                        "essay_title": "",
                        "essay": "essay 4",
                        "extraneous": "",
                    }
                ],
            ]
        )
        llm_service = Mock()
        llm_service.with_mode.return_value = llm_no_think
        docx_out_service = Mock()

        pipeline = MetadataPipeline(
            app_cfg=app_cfg,
            discovered_inputs=discovered_inputs,
            document_input_service=document_input_service,
            docx_out_service=docx_out_service,
            llm_service=llm_service,
        )

        result = pipeline.run_pipeline()

        self.assertEqual(llm_no_think.json_schema_chat_many.await_count, 3)
        first_batch = llm_no_think.json_schema_chat_many.await_args_list[0].args[0]
        second_batch = llm_no_think.json_schema_chat_many.await_args_list[1].args[0]
        third_batch = llm_no_think.json_schema_chat_many.await_args_list[2].args[0]
        self.assertEqual(len(first_batch), 2)
        self.assertEqual(len(second_batch), 2)
        self.assertEqual(len(third_batch), 1)

        self.assertEqual(result["batch_size"], 2)
        self.assertEqual(result["task_count"], 5)
        self.assertEqual(result["success_count"], 4)
        self.assertEqual(result["failure_count"], 1)
        self.assertEqual(result["items"][0]["metadata"]["student_name"], "A")
        self.assertEqual(result["items"][3]["error"], "fail-d")
        self.assertEqual(result["items"][4]["metadata"]["student_name"], "E")
        self.assertEqual(docx_out_service.append_paragraphs.call_count, 4)
        self.assertEqual(docx_out_service.write_plain_copy.call_count, 4)

    def test_run_pipeline_normalizes_essay_to_single_paragraph(self) -> None:
        triplet = DiscoveredPathTriplet(
            in_path=Path("/tmp/in/a.pdf"),
            out_path=Path("/tmp/out/a_checked.docx"),
            explained_path=Path("/tmp/explained/a_explained.txt"),
        )
        discovered_inputs = DiscoveredInputs(
            docx_paths=[],
            pdf_paths=[triplet],
            image_paths=[],
            unsupported_paths=[],
        )
        app_cfg = SimpleNamespace(llm_server=SimpleNamespace(llama_n_parallel=1))

        document_input_service = Mock()
        document_input_service.load.return_value = Mock(blocks=["raw input"])

        llm_no_think = Mock()
        llm_no_think.json_schema_chat_many = AsyncMock(
            return_value=[
                {
                    "student_name": "A",
                    "student_number": "123",
                    "essay_title": "Title",
                    "essay": "Line one.\n\nLine two.\n   Line three.",
                    "extraneous": "",
                }
            ]
        )
        llm_service = Mock()
        llm_service.with_mode.return_value = llm_no_think
        docx_out_service = Mock()

        pipeline = MetadataPipeline(
            app_cfg=app_cfg,
            discovered_inputs=discovered_inputs,
            document_input_service=document_input_service,
            docx_out_service=docx_out_service,
            llm_service=llm_service,
        )

        pipeline.run_pipeline()

        docx_out_service.append_paragraphs.assert_called_once_with(
            output_path=triplet.out_path,
            paragraphs=[
                "",
                "Edited Text",
                "Student Name: A",
                "Student Number: 123",
                "Essay Title: Title",
                "Line one. Line two. Line three.",
            ],
        )
        docx_out_service.write_plain_copy.assert_called_once_with(
            output_path=triplet.out_path.parent / "conc_para.docx",
            paragraphs=["Line one. Line two. Line three."],
        )

    def test_run_pipeline_writes_batch_before_next_batch_runs(self) -> None:
        triplets = [
            DiscoveredPathTriplet(
                in_path=Path(f"/tmp/in/{i}.pdf"),
                out_path=Path(f"/tmp/out/{i}_checked.docx"),
                explained_path=Path(f"/tmp/explained/{i}_explained.txt"),
            )
            for i in range(4)
        ]
        discovered_inputs = DiscoveredInputs(
            docx_paths=[],
            pdf_paths=triplets,
            image_paths=[],
            unsupported_paths=[],
        )
        app_cfg = SimpleNamespace(llm_server=SimpleNamespace(llama_n_parallel=2))

        document_input_service = Mock()
        document_input_service.load.side_effect = [Mock(blocks=[f"essay {i}"]) for i in range(4)]

        batch_calls = {"count": 0}
        docx_out_service = Mock()

        async def _json_many_side_effect(*args, **kwargs):
            _ = (args, kwargs)
            batch_calls["count"] += 1
            if batch_calls["count"] == 1:
                return [
                    {
                        "student_name": "A",
                        "student_number": "",
                        "essay_title": "",
                        "essay": "essay 0",
                        "extraneous": "",
                    },
                    {
                        "student_name": "B",
                        "student_number": "",
                        "essay_title": "",
                        "essay": "essay 1",
                        "extraneous": "",
                    },
                ]
            self.assertEqual(
                docx_out_service.append_paragraphs.call_count,
                2,
                "Second batch started before first batch writes were flushed.",
            )
            return [
                {
                    "student_name": "C",
                    "student_number": "",
                    "essay_title": "",
                    "essay": "essay 2",
                    "extraneous": "",
                },
                {
                    "student_name": "D",
                    "student_number": "",
                    "essay_title": "",
                    "essay": "essay 3",
                    "extraneous": "",
                },
            ]

        llm_no_think = Mock()
        llm_no_think.json_schema_chat_many = AsyncMock(side_effect=_json_many_side_effect)
        llm_service = Mock()
        llm_service.with_mode.return_value = llm_no_think

        pipeline = MetadataPipeline(
            app_cfg=app_cfg,
            discovered_inputs=discovered_inputs,
            document_input_service=document_input_service,
            docx_out_service=docx_out_service,
            llm_service=llm_service,
        )

        result = pipeline.run_pipeline()

        self.assertEqual(result["success_count"], 4)
        self.assertEqual(docx_out_service.append_paragraphs.call_count, 4)


if __name__ == "__main__":
    unittest.main()
