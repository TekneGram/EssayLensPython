from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from app.bootstrap_llm import bootstrap_llm
from app.container import build_container
from app.runtime_lifecycle import RuntimeLifecycle
from app.settings import AppConfig, build_settings
from cli.model_manager import (
    get_selected_llm_key,
    llm_statuses,
    ocr_statuses,
    select_llm_and_update_config,
    select_ocr_and_update_config,
)
from cli.output import print_model_rows
from docx_tools.sentence_splitter import split_sentences


@dataclass
class CliSession:
    runtime_lifecycle: RuntimeLifecycle = field(default_factory=RuntimeLifecycle)
    app_cfg: AppConfig | None = None
    deps: dict[str, Any] | None = None

    def _build_cfg(self, llm_key: str | None = None, ocr_key: str | None = None) -> AppConfig:
        cfg = build_settings()
        cfg = select_llm_and_update_config(cfg, model_key=llm_key)
        cfg = select_ocr_and_update_config(cfg, model_key=ocr_key)
        return cfg

    def configure_llm_selection(self, model_key: str | None = None) -> dict[str, Any]:
        cfg = self._build_cfg(llm_key=model_key)
        self.app_cfg = cfg
        self.deps = None
        selected_key = cfg.llm_config.llama_model_key
        statuses = llm_statuses()
        selected_row = next((s for s in statuses if s.key == selected_key), None)
        return {
            "selected_llm_key": selected_key,
            "selected_display_name": selected_row.display_name if selected_row else selected_key,
            "installed": bool(selected_row and selected_row.installed),
            "message": "Selection persisted. Model server will start lazily on first LLM task.",
        }

    def configure_ocr_selection(self, model_key: str | None = None) -> dict[str, Any]:
        cfg = self._build_cfg(ocr_key=model_key)
        self.app_cfg = cfg
        self.deps = None
        selected_key = cfg.ocr_config.ocr_model_key
        statuses = ocr_statuses()
        selected_row = next((s for s in statuses if s.key == selected_key), None)
        return {
            "selected_ocr_key": selected_key,
            "selected_display_name": selected_row.display_name if selected_row else selected_key,
            "installed": bool(selected_row and selected_row.installed),
            "message": "Selection persisted.",
        }

    def list_models(self) -> dict[str, Any]:
        llm_rows = [
            {
                "key": row.key,
                "display_name": row.display_name,
                "installed": row.installed,
                "recommended": row.recommended,
                "selected": row.selected,
            }
            for row in llm_statuses()
        ]
        ocr_rows = [
            {
                "key": row.key,
                "display_name": row.display_name,
                "installed": row.installed,
                "selected": row.selected,
            }
            for row in ocr_statuses()
        ]
        return {
            "llm": llm_rows,
            "ocr": ocr_rows,
        }

    def print_model_list(self) -> None:
        rows = self.list_models()
        print_model_rows("LLM models", rows["llm"])
        print_model_rows("OCR models", rows["ocr"])

    def status(self) -> dict[str, Any]:
        server_proc = self._server_proc()
        running = bool(server_proc and server_proc.is_running())
        endpoint = None
        if self.app_cfg is not None:
            endpoint = self.app_cfg.llm_server.llama_server_url
        return {
            "selected_llm_key": get_selected_llm_key(),
            "running": running,
            "endpoint": endpoint,
        }

    def ensure_runtime_for_llm_task(self) -> None:
        if self.deps is None or self.app_cfg is None:
            cfg = self._build_cfg()
            cfg = bootstrap_llm(cfg)
            deps = build_container(cfg)
            self.app_cfg = cfg
            self.deps = deps

        proc = self._server_proc()
        if proc is None:
            raise RuntimeError("LLM server process is not available in container.")
        if not proc.is_running():
            self.runtime_lifecycle.register_process(proc)
            proc.start()

    def stop_llm(self) -> bool:
        proc = self._server_proc()
        if proc is None:
            return False
        if not proc.is_running():
            return False
        proc.stop()
        return True

    def switch_llm(self, model_key: str) -> dict[str, Any]:
        was_running = self.stop_llm()
        selection = self.configure_llm_selection(model_key)
        return {
            **selection,
            "was_running": was_running,
            "message": "Switched model selection. Server will start lazily on next LLM task.",
        }

    def run_topic_sentence(
        self,
        file_path: str | Path,
        *,
        max_concurrency: int | None = None,
        json_out: str | Path | None = None,
    ) -> dict[str, Any]:
        src_path = Path(file_path).expanduser().resolve()
        if not src_path.exists():
            raise FileNotFoundError(f"File not found: {src_path}")
        if src_path.suffix.lower() not in {".docx", ".pdf"}:
            raise ValueError(f"Unsupported file type: {src_path.suffix} (supported: .docx, .pdf)")

        self.ensure_runtime_for_llm_task()
        assert self.app_cfg is not None
        assert self.deps is not None

        doc_input = self.deps["document_input_service"]
        llm_task_service = self.deps["llm_task_service"]
        if llm_task_service is None:
            raise RuntimeError("LLM task service is unavailable.")

        loaded = doc_input.load(src_path)
        learner_text = "\n".join(block for block in loaded.blocks if (block or "").strip()).strip()
        if not learner_text:
            raise ValueError(f"No text found in: {src_path}")

        sentences = split_sentences(learner_text)
        if not sentences:
            raise ValueError("Could not split document text into sentences.")
        learner_topic_sentence = sentences[0].strip()
        remainder_text = " ".join(s.strip() for s in sentences[1:] if s.strip())
        if not remainder_text:
            raise ValueError("Text needs at least two sentences to analyze topic sentence quality.")

        constructor_result = llm_task_service.construct_topic_sentence_parallel(
            app_cfg=self.app_cfg,
            text_tasks=[remainder_text],
            max_concurrency=max_concurrency,
        )
        constructor_output = constructor_result["outputs"][0]
        if isinstance(constructor_output, Exception):
            raise RuntimeError(f"Topic sentence construction failed: {constructor_output}")
        suggested = (getattr(constructor_output, "content", "") or "").strip()
        if not suggested:
            raise RuntimeError("Topic sentence construction returned empty content.")

        analysis_input = json.dumps(
            {
                "learner_text": learner_text,
                "learner_topic_sentence": learner_topic_sentence,
                "good_topic_sentence": suggested,
            },
            ensure_ascii=True,
        )

        analysis_result = llm_task_service.analyze_topic_sentence_parallel(
            app_cfg=self.app_cfg,
            text_tasks=[analysis_input],
            max_concurrency=max_concurrency,
        )
        analysis_output = analysis_result["outputs"][0]
        if isinstance(analysis_output, Exception):
            raise RuntimeError(f"Topic sentence analysis failed: {analysis_output}")
        feedback = (getattr(analysis_output, "content", "") or "").strip()
        if not feedback:
            raise RuntimeError("Topic sentence analysis returned empty content.")

        if json_out is None:
            json_path = self.app_cfg.assessment_paths.explained_folder / "cli" / f"{src_path.stem}.topic_sentence.json"
        else:
            json_path = Path(json_out).expanduser().resolve()

        result = {
            "file": str(src_path),
            "learner_topic_sentence": learner_topic_sentence,
            "suggested_topic_sentence": suggested,
            "feedback": feedback,
            "json_out": str(json_path),
        }
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8")
        return result

    def _server_proc(self) -> Any:
        if self.deps is None:
            return None
        return self.deps.get("server_proc")
