from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from cli.runner import CliSession, RuntimeStageError


class CliRunnerRuntimeTests(unittest.TestCase):
    def test_configure_llm_selection_persists_without_starting_server(self) -> None:
        session = CliSession()
        fake_cfg = SimpleNamespace(llm_config=SimpleNamespace(llama_model_key="qwen3_4b_q8"))

        with patch.object(session, "_build_cfg", return_value=fake_cfg), patch(
            "cli.runner.llm_statuses",
            return_value=[SimpleNamespace(key="qwen3_4b_q8", display_name="Qwen", installed=True)],
        ):
            result = session.configure_llm_selection("qwen3_4b_q8")

        self.assertEqual(result["selected_llm_key"], "qwen3_4b_q8")
        self.assertTrue(result["installed"])
        self.assertIn("lazily", result["message"].lower())

    def test_switch_llm_stops_server_and_updates_selection(self) -> None:
        session = CliSession()
        with patch.object(session, "stop_llm", return_value=True), patch.object(
            session,
            "configure_llm_selection",
            return_value={"selected_llm_key": "qwen3_8b_q8", "message": "ok"},
        ):
            result = session.switch_llm("qwen3_8b_q8")

        self.assertTrue(result["was_running"])
        self.assertEqual(result["selected_llm_key"], "qwen3_8b_q8")

    def test_topic_sentence_runs_with_lazy_server_start(self) -> None:
        session = CliSession()

        with tempfile.TemporaryDirectory() as tmpdir:
            doc_path = Path(tmpdir) / "essay.docx"
            doc_path.write_text("placeholder", encoding="utf-8")
            out_root = Path(tmpdir) / "explained"

            server_proc = Mock()
            server_proc.is_running.return_value = False

            llm_task_service = Mock()
            llm_task_service.construct_topic_sentence_parallel.return_value = {
                "outputs": [SimpleNamespace(content="A tighter topic sentence.")]
            }
            llm_task_service.analyze_topic_sentence_parallel.return_value = {
                "outputs": [SimpleNamespace(content="The original sentence is too broad.")]
            }

            document_input_service = Mock()
            document_input_service.load.return_value = SimpleNamespace(
                blocks=["This is sentence one. This is sentence two."]
            )

            session.app_cfg = SimpleNamespace(
                assessment_paths=SimpleNamespace(explained_folder=out_root)
            )
            session.deps = {
                "server_proc": server_proc,
                "llm_task_service": llm_task_service,
                "document_input_service": document_input_service,
            }

            result = session.run_topic_sentence(doc_path)

            server_proc.start.assert_called_once()
            self.assertIn("tighter", result["suggested_topic_sentence"].lower())
            self.assertTrue(Path(result["json_out"]).exists())

    def test_ensure_runtime_raises_stage_error_with_context(self) -> None:
        session = CliSession()
        with patch.object(session, "_build_cfg", side_effect=RuntimeError("boom cfg")):
            with self.assertRaises(RuntimeStageError) as ctx:
                session.ensure_runtime_for_llm_task()
        self.assertEqual(ctx.exception.stage, "build_cfg")
        self.assertIn("boom cfg", ctx.exception.detail)

    def test_diagnostics_hook_receives_stage_details(self) -> None:
        captured: list[tuple[str, str]] = []

        def hook(stage: str, detail: str, _tb: str) -> None:
            captured.append((stage, detail))

        session = CliSession(diagnostics_hook=hook)
        with patch.object(session, "_build_cfg", side_effect=RuntimeError("cfg error")):
            with self.assertRaises(RuntimeStageError):
                session.ensure_runtime_for_llm_task()

        self.assertTrue(captured)
        self.assertEqual(captured[0][0], "build_cfg")
        self.assertIn("cfg error", captured[0][1])

    def test_run_metadata_success_writes_json_output(self) -> None:
        session = CliSession()

        with tempfile.TemporaryDirectory() as tmpdir:
            doc_path = Path(tmpdir) / "essay.docx"
            doc_path.write_text("placeholder", encoding="utf-8")
            out_root = Path(tmpdir) / "explained"

            llm_task_service = Mock()
            llm_task_service.extract_metadata_parallel.return_value = {
                "outputs": [
                    {
                        "student_name": "Ada",
                        "student_number": "123",
                        "essay_title": "On Engines",
                        "essay": "Body",
                        "extraneous": "",
                    }
                ],
                "task_count": 1,
                "success_count": 1,
                "failure_count": 0,
            }
            document_input_service = Mock()
            document_input_service.load.return_value = SimpleNamespace(blocks=["name", "essay body"])
            server_proc = Mock()
            server_proc.is_running.return_value = True

            session.app_cfg = SimpleNamespace(
                assessment_paths=SimpleNamespace(explained_folder=out_root)
            )
            session.deps = {
                "server_proc": server_proc,
                "llm_task_service": llm_task_service,
                "document_input_service": document_input_service,
            }

            result = session.run_metadata(doc_path)

            self.assertEqual(result["metadata"]["student_name"], "Ada")
            self.assertTrue(Path(result["json_out"]).exists())
            llm_task_service.extract_metadata_parallel.assert_called_once()

    def test_run_metadata_rejects_unsupported_file_type(self) -> None:
        session = CliSession()
        with tempfile.TemporaryDirectory() as tmpdir:
            txt_path = Path(tmpdir) / "essay.txt"
            txt_path.write_text("x", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Unsupported file type"):
                session.run_metadata(txt_path)

    def test_run_metadata_rejects_empty_text(self) -> None:
        session = CliSession()
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_path = Path(tmpdir) / "essay.docx"
            doc_path.write_text("placeholder", encoding="utf-8")

            llm_task_service = Mock()
            document_input_service = Mock()
            document_input_service.load.return_value = SimpleNamespace(blocks=[" ", ""])
            server_proc = Mock()
            server_proc.is_running.return_value = True

            session.app_cfg = SimpleNamespace(
                assessment_paths=SimpleNamespace(explained_folder=Path(tmpdir) / "explained")
            )
            session.deps = {
                "server_proc": server_proc,
                "llm_task_service": llm_task_service,
                "document_input_service": document_input_service,
            }

            with self.assertRaisesRegex(ValueError, "No text found"):
                session.run_metadata(doc_path)

    def test_run_metadata_raises_when_task_returns_exception(self) -> None:
        session = CliSession()
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "essay.pdf"
            pdf_path.write_text("placeholder", encoding="utf-8")

            llm_task_service = Mock()
            llm_task_service.extract_metadata_parallel.return_value = {
                "outputs": [RuntimeError("bad parse")],
                "task_count": 1,
                "success_count": 0,
                "failure_count": 1,
            }
            document_input_service = Mock()
            document_input_service.load.return_value = SimpleNamespace(blocks=["content"])
            server_proc = Mock()
            server_proc.is_running.return_value = True

            session.app_cfg = SimpleNamespace(
                assessment_paths=SimpleNamespace(explained_folder=Path(tmpdir) / "explained")
            )
            session.deps = {
                "server_proc": server_proc,
                "llm_task_service": llm_task_service,
                "document_input_service": document_input_service,
            }

            with self.assertRaisesRegex(RuntimeError, "Metadata extraction failed"):
                session.run_metadata(pdf_path)

    def test_run_prompt_test_success_writes_json_output(self) -> None:
        session = CliSession()
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_path = Path(tmpdir) / "essay.docx"
            doc_path.write_text("placeholder", encoding="utf-8")
            out_root = Path(tmpdir) / "explained"

            llm_task_service = Mock()
            llm_task_service.prompt_tester_parallel.return_value = {
                "outputs": [SimpleNamespace(content="Use clearer cause/effect links.")],
                "task_count": 1,
                "success_count": 1,
                "failure_count": 0,
            }
            document_input_service = Mock()
            document_input_service.load.return_value = SimpleNamespace(blocks=["essay body"])
            server_proc = Mock()
            server_proc.is_running.return_value = True

            session.app_cfg = SimpleNamespace(
                assessment_paths=SimpleNamespace(explained_folder=out_root)
            )
            session.deps = {
                "server_proc": server_proc,
                "llm_task_service": llm_task_service,
                "document_input_service": document_input_service,
            }

            result = session.run_prompt_test(doc_path)

            self.assertIn("cause/effect", result["feedback"])
            self.assertTrue(Path(result["json_out"]).exists())
            llm_task_service.prompt_tester_parallel.assert_called_once()

    def test_run_prompt_test_raises_when_task_returns_exception(self) -> None:
        session = CliSession()
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "essay.pdf"
            pdf_path.write_text("placeholder", encoding="utf-8")

            llm_task_service = Mock()
            llm_task_service.prompt_tester_parallel.return_value = {
                "outputs": [RuntimeError("prompt failed")],
                "task_count": 1,
                "success_count": 0,
                "failure_count": 1,
            }
            document_input_service = Mock()
            document_input_service.load.return_value = SimpleNamespace(blocks=["content"])
            server_proc = Mock()
            server_proc.is_running.return_value = True

            session.app_cfg = SimpleNamespace(
                assessment_paths=SimpleNamespace(explained_folder=Path(tmpdir) / "explained")
            )
            session.deps = {
                "server_proc": server_proc,
                "llm_task_service": llm_task_service,
                "document_input_service": document_input_service,
            }

            with self.assertRaisesRegex(RuntimeError, "Prompt test failed"):
                session.run_prompt_test(pdf_path)


if __name__ == "__main__":
    unittest.main()
