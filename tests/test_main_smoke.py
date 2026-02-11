from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import main


def _fake_cfg() -> SimpleNamespace:
    llm_config = SimpleNamespace(
        llama_model_display_name="Demo",
        llama_model_family="instruct",
        hf_mmproj_filename=None,
    )
    ged_config = SimpleNamespace(model_name="ged", batch_size=8)
    run_config = SimpleNamespace(
        max_llm_corrections=5,
        single_paragraph_mode=True,
        author="tester",
    )
    assessment_paths = SimpleNamespace(
        input_folder="Assessment/in",
        output_folder="Assessment/out",
        explained_folder="Assessment/explained",
    )
    llm_server = SimpleNamespace(llama_server_url="http://127.0.0.1:8080/v1/chat/completions")
    return SimpleNamespace(
        llm_config=llm_config,
        ged_config=ged_config,
        run_config=run_config,
        assessment_paths=assessment_paths,
        llm_server=llm_server,
    )


class MainSmokeTests(unittest.TestCase):
    def test_main_executes_expected_wiring_order(self) -> None:
        order: list[str] = []
        cfg = _fake_cfg()
        fake_prep_pipeline = Mock()

        with patch("main.type_print"), patch("builtins.print"), patch(
            "main.build_settings", side_effect=lambda: order.append("build_settings") or cfg
        ), patch(
            "main.select_model_and_update_config",
            side_effect=lambda c: order.append("select_model") or c,
        ), patch(
            "main.select_ocr_model_and_update_config",
            side_effect=lambda c: order.append("select_ocr") or c,
        ), patch(
            "main.bootstrap_llm",
            side_effect=lambda c: order.append("bootstrap") or c,
        ), patch(
            "main.build_container",
            side_effect=lambda c: order.append("container") or {
                "project_root": "/tmp/project",
                "input_discovery_service": object(),
                "document_input_service": object(),
                "docx_out_service": object(),
            },
        ), patch(
            "main.PrepPipeline", return_value=fake_prep_pipeline
        ) as prep_pipeline_cls:
            main.main()

        self.assertEqual(
            order,
            ["build_settings", "select_model", "select_ocr", "bootstrap", "container"],
        )
        prep_pipeline_cls.assert_called_once()
        fake_prep_pipeline.run_pipeline.assert_called_once()


if __name__ == "__main__":
    unittest.main()
