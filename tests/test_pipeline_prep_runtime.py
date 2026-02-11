from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock

from app.pipeline_prep import PrepPipeline
from services.input_discovery_service import DiscoveredInputs, DiscoveredPathTriplet


class PrepPipelineRuntimeTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
