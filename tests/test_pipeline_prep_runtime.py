from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from app.pipeline_prep import PrepPipeline
from config.ged_config import GedConfig
from config.llm_config import LlmConfig
from config.ocr_config import OcrConfig
from config.run_config import RunConfig
from inout.explainability_writer import ExplainabilityWriter
from services.input_discovery_service import DiscoveredInputs, DiscoveredPathTriplet
from services.explainability import ExplainabilityRecorder


class PrepPipelineRuntimeTests(unittest.TestCase):
    def test_run_pipeline_initializes_explainability_files_after_discovery(self) -> None:
        docx_triplet = DiscoveredPathTriplet(
            in_path=Path("/tmp/a.docx"),
            out_path=Path("/tmp/out/a_checked.docx"),
            explained_path=Path("/tmp/explained/a_explained.txt"),
        )
        pdf_triplet = DiscoveredPathTriplet(
            in_path=Path("/tmp/b.pdf"),
            out_path=Path("/tmp/out/b_checked.docx"),
            explained_path=Path("/tmp/explained/b_explained.txt"),
        )

        discovery = Mock()
        discovery.discover.return_value = DiscoveredInputs(
            docx_paths=[docx_triplet],
            pdf_paths=[pdf_triplet],
            image_paths=[],
            unsupported_paths=[],
        )
        document_input = Mock()
        document_input.load.side_effect = [
            Mock(blocks=["docx"]),
            Mock(blocks=["pdf page"]),
        ]
        docx_out = Mock()

        explainability = Mock()
        explainability.finish_doc.return_value = ["header"]
        explain_writer = Mock()

        pipeline = PrepPipeline(
            app_root="/tmp",
            input_discovery_service=discovery,
            document_input_service=document_input,
            docx_out_service=docx_out,
            explainability=explainability,
            explain_file_writer=explain_writer,
        )

        pipeline.run_pipeline()

        self.assertEqual(explainability.reset.call_count, 2)
        explainability.start_doc.assert_any_call(
            docx_path=docx_triplet.out_path,
            include_edited_text=True,
        )
        explainability.start_doc.assert_any_call(
            docx_path=pdf_triplet.out_path,
            include_edited_text=True,
        )
        explain_writer.write_to_path.assert_any_call(
            explained_path=docx_triplet.explained_path,
            lines=["header"],
        )
        explain_writer.write_to_path.assert_any_call(
            explained_path=pdf_triplet.explained_path,
            lines=["header"],
        )
        self.assertEqual(explain_writer.write_to_path.call_count, 2)

    def test_run_pipeline_processes_docx_and_pdf_paths(self) -> None:
        docx_triplet_1 = DiscoveredPathTriplet(
            in_path=Path("/tmp/a.docx"),
            out_path=Path("/tmp/out/a_checked.docx"),
            explained_path=Path("/tmp/explained/a_explained.txt"),
        )
        docx_triplet_2 = DiscoveredPathTriplet(
            in_path=Path("/tmp/b.docx"),
            out_path=Path("/tmp/out/b_checked.docx"),
            explained_path=Path("/tmp/explained/b_explained.txt"),
        )
        pdf_triplet = DiscoveredPathTriplet(
            in_path=Path("/tmp/c.pdf"),
            out_path=Path("/tmp/out/c_checked.docx"),
            explained_path=Path("/tmp/explained/c_explained.txt"),
        )

        discovery = Mock()
        discovery.discover.return_value = DiscoveredInputs(
            docx_paths=[docx_triplet_1, docx_triplet_2],
            pdf_paths=[pdf_triplet],
            image_paths=[],
            unsupported_paths=[],
        )

        document_input = Mock()
        document_input.load.side_effect = [
            Mock(blocks=["a1", "a2"]),
            Mock(blocks=["b1"]),
            Mock(
                blocks=[
                    "The question of Should tourists in japan stay in hotels or in traditional ryokans\n\n"
                    "When visiting Japan, tourists often wonder whether they should stay in modern hotels or in\n"
                    "traditional ryokans. Hotels are usually cheaper and more convenient, but they offer less cultural\n"
                    "depth than ryokans.",
                    "",
                ]
            ),
        ]

        docx_out = Mock()

        pipeline = PrepPipeline(
            app_root="/tmp",
            input_discovery_service=discovery,
            document_input_service=document_input,
            docx_out_service=docx_out,
        )

        pipeline.run_pipeline()

        discovery.discover.assert_called_once_with()
        self.assertEqual(document_input.load.call_count, 3)
        document_input.load.assert_any_call(docx_triplet_1.in_path)
        document_input.load.assert_any_call(docx_triplet_2.in_path)
        document_input.load.assert_any_call(pdf_triplet.in_path)
        docx_out.write_plain_copy.assert_any_call(
            output_path=docx_triplet_1.out_path,
            paragraphs=["a1", "a2"],
        )
        docx_out.write_plain_copy.assert_any_call(
            output_path=docx_triplet_2.out_path,
            paragraphs=["b1"],
        )
        docx_out.write_plain_copy.assert_any_call(
            output_path=pdf_triplet.out_path,
            paragraphs=[
                "--- Page 1 ---",
                "The question of Should tourists in japan stay in hotels or in traditional ryokans",
                "When visiting Japan, tourists often wonder whether they should stay in modern hotels or in traditional ryokans. Hotels are usually cheaper and more convenient, but they offer less cultural depth than ryokans.",
                "--- Page 2 ---",
                "",
            ],
        )
        self.assertEqual(docx_out.write_plain_copy.call_count, 3)

    def test_normalize_pdf_page_text_keeps_title_and_merges_wrapped_lines(self) -> None:
        pipeline = PrepPipeline(
            app_root="/tmp",
            input_discovery_service=Mock(),
            document_input_service=Mock(),
            docx_out_service=Mock(),
        )

        normalized = pipeline._normalize_pdf_page_text(
            "My Title Line\n\n"
            "This sentence is wrapped\n"
            "across two visual lines.\n"
            "Another sentence starts\n"
            "and continues."
        )

        self.assertEqual(
            normalized,
            [
                "My Title Line",
                "This sentence is wrapped across two visual lines. Another sentence starts and continues.",
            ],
        )

    def test_run_pipeline_starts_and_stops_ocr_for_image_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "scan.png"
            image_path.write_bytes(b"image-bytes")

            image_triplet = DiscoveredPathTriplet(
                in_path=image_path,
                out_path=Path(tmpdir) / "out" / "scan_checked.docx",
                explained_path=Path(tmpdir) / "explained" / "scan_explained.txt",
            )

            discovery = Mock()
            discovery.discover.return_value = DiscoveredInputs(
                docx_paths=[],
                pdf_paths=[],
                image_paths=[image_triplet],
                unsupported_paths=[],
            )

            ocr_server_proc = Mock()
            ocr_service = Mock()
            ocr_service.extract_text.return_value = "line one\nline two"
            docx_out = Mock()
            lifecycle = Mock()

            pipeline = PrepPipeline(
                app_root=tmpdir,
                input_discovery_service=discovery,
                document_input_service=Mock(),
                docx_out_service=docx_out,
                ocr_server_proc=ocr_server_proc,
                ocr_service=ocr_service,
                runtime_lifecycle=lifecycle,
            )

            pipeline.run_pipeline()

            lifecycle.register_process.assert_called_once_with(ocr_server_proc)
            ocr_server_proc.start.assert_called_once_with()
            ocr_service.extract_text.assert_called_once_with(image_bytes=b"image-bytes")
            docx_out.write_plain_copy.assert_called_once_with(
                output_path=image_triplet.out_path,
                paragraphs=["line one", "line two"],
            )
            ocr_server_proc.stop.assert_called_once_with()

    def test_run_pipeline_appends_prep_stage_line_for_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_triplet = DiscoveredPathTriplet(
                in_path=Path(tmpdir) / "essay.pdf",
                out_path=Path(tmpdir) / "out" / "essay_checked.docx",
                explained_path=Path(tmpdir) / "explained" / "essay_explained.txt",
            )
            pdf_triplet.in_path.write_text("placeholder", encoding="utf-8")

            discovery = Mock()
            discovery.discover.return_value = DiscoveredInputs(
                docx_paths=[],
                pdf_paths=[pdf_triplet],
                image_paths=[],
                unsupported_paths=[],
            )
            document_input = Mock()
            document_input.load.return_value = Mock(blocks=["Page one"])
            docx_out = Mock()

            explainability = ExplainabilityRecorder.new(
                run_cfg=RunConfig.from_strings(author="tester"),
                ged_cfg=GedConfig.from_strings(model_name="ged-model"),
                llm_config=LlmConfig.from_strings(
                    llama_server_model="demo",
                    llama_model_key="demo",
                    llama_model_display_name="Demo",
                    llama_model_alias="demo",
                    llama_model_family="instruct",
                ),
                ocr_config=OcrConfig.from_strings(
                    ocr_server_model="ocr",
                    ocr_model_key="ocr",
                    ocr_model_display_name="OCR",
                    ocr_model_alias="ocr",
                    ocr_model_family="vision",
                ),
            )
            explain_writer = ExplainabilityWriter(output_dir=Path(tmpdir) / "unused")

            pipeline = PrepPipeline(
                app_root=tmpdir,
                input_discovery_service=discovery,
                document_input_service=document_input,
                docx_out_service=docx_out,
                explainability=explainability,
                explain_file_writer=explain_writer,
            )

            pipeline.run_pipeline()

            explained_text = pdf_triplet.explained_path.read_text(encoding="utf-8")
            self.assertIn("[PREP STAGE] Extracted text from pdf.\n", explained_text)

    def test_run_pipeline_appends_prep_stage_line_for_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "scan.png"
            image_path.write_bytes(b"image-bytes")

            image_triplet = DiscoveredPathTriplet(
                in_path=image_path,
                out_path=Path(tmpdir) / "out" / "scan_checked.docx",
                explained_path=Path(tmpdir) / "explained" / "scan_explained.txt",
            )

            discovery = Mock()
            discovery.discover.return_value = DiscoveredInputs(
                docx_paths=[],
                pdf_paths=[],
                image_paths=[image_triplet],
                unsupported_paths=[],
            )

            ocr_server_proc = Mock()
            ocr_service = Mock()
            ocr_service.extract_text.return_value = "line one\nline two"
            docx_out = Mock()
            lifecycle = Mock()

            explainability = ExplainabilityRecorder.new(
                run_cfg=RunConfig.from_strings(author="tester"),
                ged_cfg=GedConfig.from_strings(model_name="ged-model"),
                llm_config=LlmConfig.from_strings(
                    llama_server_model="demo",
                    llama_model_key="demo",
                    llama_model_display_name="Demo",
                    llama_model_alias="demo",
                    llama_model_family="instruct",
                ),
                ocr_config=OcrConfig.from_strings(
                    ocr_server_model="ocr",
                    ocr_model_key="ocr",
                    ocr_model_display_name="OCR",
                    ocr_model_alias="ocr",
                    ocr_model_family="vision",
                ),
            )
            explain_writer = ExplainabilityWriter(output_dir=Path(tmpdir) / "unused")

            pipeline = PrepPipeline(
                app_root=tmpdir,
                input_discovery_service=discovery,
                document_input_service=Mock(),
                docx_out_service=docx_out,
                explainability=explainability,
                explain_file_writer=explain_writer,
                ocr_server_proc=ocr_server_proc,
                ocr_service=ocr_service,
                runtime_lifecycle=lifecycle,
            )

            pipeline.run_pipeline()

            explained_text = image_triplet.explained_path.read_text(encoding="utf-8")
            self.assertIn("[PREP STAGE] Extracted text from image.\n", explained_text)


if __name__ == "__main__":
    unittest.main()
