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
        fake_prep_pipeline.run_pipeline.return_value = object()
        fake_metadata_pipeline = Mock()
        fake_fb_pipeline = Mock()
        fake_conclusion_pipeline = Mock()
        fake_body_pipeline = Mock()
        fake_content_pipeline = Mock()
        fake_summarize_fb_pipeline = Mock()
        fake_summarize_fb_pipeline.run_pipeline.return_value = {
            "document_count": 0,
            "task_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "items": [],
        }
        fake_ged_pipeline = Mock()
        fake_lifecycle = object()
        fake_ocr_server_proc = object()
        fake_ocr_service = object()
        fake_llm_service = object()
        fake_llm_task_service = object()

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
                "ocr_server_proc": fake_ocr_server_proc,
                "ocr_service": fake_ocr_service,
                "server_proc": object(),
                "llm_service": fake_llm_service,
                "llm_task_service": fake_llm_task_service,
                "ged": object(),
                "explain": None,
            },
        ), patch(
            "main.RuntimeLifecycle", return_value=fake_lifecycle
        ), patch(
            "main.PrepPipeline", return_value=fake_prep_pipeline
        ) as prep_pipeline_cls, patch(
            "main.MetadataPipeline", return_value=fake_metadata_pipeline
        ) as metadata_pipeline_cls, patch(
            "main.FBPipeline", return_value=fake_fb_pipeline
        ) as fb_pipeline_cls, patch(
            "main.ConclusionPipeline", return_value=fake_conclusion_pipeline
        ) as conclusion_pipeline_cls, patch(
            "main.BodyPipeline", return_value=fake_body_pipeline
        ) as body_pipeline_cls, patch(
            "main.ContentPipeline", return_value=fake_content_pipeline
        ) as content_pipeline_cls, patch(
            "main.SummarizeFBPipeline", return_value=fake_summarize_fb_pipeline
        ) as summarize_fb_pipeline_cls, patch(
            "main.GEDPipeline", return_value=fake_ged_pipeline
        ) as ged_pipeline_cls:
            main.main()

        self.assertEqual(
            order,
            ["build_settings", "select_model", "select_ocr", "bootstrap", "container"],
        )
        prep_pipeline_cls.assert_called_once_with(
            app_root="/tmp/project",
            input_discovery_service=unittest.mock.ANY,
            document_input_service=unittest.mock.ANY,
            docx_out_service=unittest.mock.ANY,
            explainability=None,
            explain_file_writer=None,
            ocr_server_proc=fake_ocr_server_proc,
            ocr_service=fake_ocr_service,
            runtime_lifecycle=fake_lifecycle,
        )
        fake_prep_pipeline.run_pipeline.assert_called_once()
        metadata_pipeline_cls.assert_called_once_with(
            app_cfg=cfg,
            discovered_inputs=fake_prep_pipeline.run_pipeline.return_value,
            document_input_service=unittest.mock.ANY,
            docx_out_service=unittest.mock.ANY,
            llm_server_proc=unittest.mock.ANY,
            llm_task_service=fake_llm_task_service,
            runtime_lifecycle=fake_lifecycle,
        )
        fb_pipeline_cls.assert_called_once_with(
            app_cfg=cfg,
            discovered_inputs=fake_prep_pipeline.run_pipeline.return_value,
            document_input_service=unittest.mock.ANY,
            docx_out_service=unittest.mock.ANY,
            llm_task_service=fake_llm_task_service,
            llm_server_proc=unittest.mock.ANY,
            runtime_lifecycle=fake_lifecycle,
        )
        conclusion_pipeline_cls.assert_called_once_with(
            app_cfg=cfg,
            discovered_inputs=fake_prep_pipeline.run_pipeline.return_value,
            document_input_service=unittest.mock.ANY,
            docx_out_service=unittest.mock.ANY,
            llm_task_service=fake_llm_task_service,
            llm_server_proc=unittest.mock.ANY,
            runtime_lifecycle=fake_lifecycle,
        )
        body_pipeline_cls.assert_called_once_with(
            app_cfg=cfg,
            discovered_inputs=fake_prep_pipeline.run_pipeline.return_value,
            document_input_service=unittest.mock.ANY,
            docx_out_service=unittest.mock.ANY,
            llm_task_service=fake_llm_task_service,
            llm_server_proc=unittest.mock.ANY,
            runtime_lifecycle=fake_lifecycle,
        )
        content_pipeline_cls.assert_called_once_with(
            app_cfg=cfg,
            discovered_inputs=fake_prep_pipeline.run_pipeline.return_value,
            document_input_service=unittest.mock.ANY,
            docx_out_service=unittest.mock.ANY,
            llm_task_service=fake_llm_task_service,
            llm_server_proc=unittest.mock.ANY,
            runtime_lifecycle=fake_lifecycle,
        )
        summarize_fb_pipeline_cls.assert_called_once_with(
            app_cfg=cfg,
            discovered_inputs=fake_prep_pipeline.run_pipeline.return_value,
            document_input_service=unittest.mock.ANY,
            docx_out_service=unittest.mock.ANY,
            llm_task_service=fake_llm_task_service,
            llm_server_proc=unittest.mock.ANY,
            runtime_lifecycle=fake_lifecycle,
        )
        ged_pipeline_cls.assert_called_once_with(
            app_cfg=cfg,
            discovered_inputs=fake_prep_pipeline.run_pipeline.return_value,
            document_input_service=unittest.mock.ANY,
            docx_out_service=unittest.mock.ANY,
            ged_service=unittest.mock.ANY,
            llm_task_service=fake_llm_task_service,
            explainability=None,
            llm_server_proc=unittest.mock.ANY,
            runtime_lifecycle=fake_lifecycle,
        )
        fake_metadata_pipeline.run_pipeline.assert_called_once()
        fake_fb_pipeline.run_pipeline.assert_called_once()
        fake_conclusion_pipeline.run_pipeline.assert_called_once()
        fake_body_pipeline.run_pipeline.assert_called_once()
        fake_content_pipeline.run_pipeline.assert_called_once()
        fake_summarize_fb_pipeline.run_pipeline.assert_called_once()
        fake_ged_pipeline.run_pipeline.assert_called_once()


if __name__ == "__main__":
    unittest.main()
