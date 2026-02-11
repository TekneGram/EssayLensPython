from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.runtime_lifecycle import RuntimeLifecycle
from utils.terminal_ui import Color, type_print

if TYPE_CHECKING:
    from interfaces.config.app_config import AppConfigShape
    from nlp.llm.llm_server_process import LlmServerProcess
    from services.document_input_service import DocumentInputService
    from services.docx_output_service import DocxOutputService
    from services.input_discovery_service import DiscoveredInputs, DiscoveredPathTriplet
    from services.llm_task_service import LlmTaskService


@dataclass
class SummarizeFBPipeline:
    """
    Summarize and personalize feedback pipeline.

    Reads each `fb.docx`, summarizes/personalizes in batches of 4 files, and
    appends the final feedback to the student's checked document (`out_path`).
    """

    app_cfg: "AppConfigShape"
    discovered_inputs: "DiscoveredInputs"
    document_input_service: "DocumentInputService"
    docx_out_service: "DocxOutputService"
    llm_task_service: "LlmTaskService"
    llm_server_proc: "LlmServerProcess | None" = None
    runtime_lifecycle: RuntimeLifecycle = field(default_factory=RuntimeLifecycle)

    def run_pipeline(self) -> dict[str, Any]:
        triplets = self._triplets()
        if not triplets:
            return {
                "document_count": 0,
                "task_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "batch_size": 4,
                "items": [],
            }

        def _run_all_batches() -> dict[str, Any]:
            tasks, items = self._prepare_tasks(triplets)
            items_by_out_path: dict[str, dict[str, Any]] = {
                item["out_path"]: item for item in items
            }

            if not tasks:
                return {
                    "document_count": len(triplets),
                    "task_count": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "batch_size": 4,
                    "items": items,
                }

            type_print("Summarizing fb.docx feedback in batches of 4.", color=Color.BLUE)
            task_count = 0
            success_count = 0
            failure_count = 0

            for idx in range(0, len(tasks), 4):
                batch_tasks = tasks[idx : idx + 4]
                type_print(
                    f"Summarize feedback batch: {idx + 1} to {idx + len(batch_tasks)}",
                    color=Color.GREEN,
                )
                batch_inputs = [task["feedback_text"] for task in batch_tasks]
                batch_result = self.llm_task_service.summarize_personalize_parallel(
                    app_cfg=self.app_cfg,
                    text_tasks=batch_inputs,
                    max_concurrency=self.app_cfg.llm_server.llama_n_parallel,
                )
                task_count += batch_result["task_count"]
                success_count += batch_result["success_count"]
                failure_count += batch_result["failure_count"]

                for task, output in zip(batch_tasks, batch_result["outputs"]):
                    triplet = task["triplet"]
                    item = items_by_out_path[str(triplet.out_path)]
                    if isinstance(output, Exception):
                        item["errors"].append(f"summarize_personalize failed: {output}")
                        continue

                    summary = (getattr(output, "content", "") or "").strip()
                    if not summary:
                        item["errors"].append("summarize_personalize returned empty content")
                        continue

                    self.docx_out_service.append_paragraphs(
                        output_path=triplet.out_path,
                        paragraphs=["", "Final Feedback", summary],
                    )
                    item["appended_to_out"] = True
                    item["append_count"] = int(item.get("append_count", 0)) + 1

            result = {
                "document_count": len(triplets),
                "task_count": task_count,
                "success_count": success_count,
                "failure_count": failure_count,
                "batch_size": 4,
                "items": list(items_by_out_path.values()),
            }
            self._print_run_summary(result)
            return result

        if self.llm_server_proc is None:
            result = _run_all_batches()
            return result

        self.runtime_lifecycle.register_process(self.llm_server_proc)
        self.llm_server_proc.start()
        try:
            result = _run_all_batches()
            return result
        finally:
            self.llm_server_proc.stop()

    def _prepare_tasks(
        self,
        triplets: list["DiscoveredPathTriplet"],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        tasks: list[dict[str, Any]] = []
        items: list[dict[str, Any]] = []

        type_print("Loading fb.docx files for summarize/personalize stage.", color=Color.BLUE)

        for triplet in triplets:
            item: dict[str, Any] = {
                "out_path": str(triplet.out_path),
                "explained_path": str(triplet.explained_path),
                "errors": [],
            }

            fb_path = triplet.out_path.parent / "fb.docx"
            if not fb_path.exists():
                item["errors"].append(f"Missing source file: {fb_path}")
                items.append(item)
                continue

            loaded = self.document_input_service.load(fb_path)
            feedback_text = "\n".join(block for block in loaded.blocks if (block or "").strip()).strip()
            if not feedback_text:
                item["errors"].append(f"No feedback text found in: {fb_path}")
                items.append(item)
                continue

            tasks.append(
                {
                    "triplet": triplet,
                    "feedback_text": feedback_text,
                }
            )
            items.append(item)

        return tasks, items

    def _triplets(self) -> list["DiscoveredPathTriplet"]:
        return (
            self.discovered_inputs.docx_paths
            + self.discovered_inputs.pdf_paths
            + self.discovered_inputs.image_paths
        )

    @staticmethod
    def _print_run_summary(result: dict[str, Any]) -> None:
        items = result.get("items", [])
        appended_count = len([i for i in items if i.get("appended_to_out")])
        skipped_or_failed = len(items) - appended_count
        type_print(
            (
                "[SummarizeFB] "
                f"docs={result.get('document_count', 0)}, "
                f"tasks={result.get('task_count', 0)}, "
                f"llm_success={result.get('success_count', 0)}, "
                f"llm_failure={result.get('failure_count', 0)}, "
                f"appended={appended_count}, "
                f"skipped_or_failed={skipped_or_failed}"
            ),
            color=Color.BLUE,
        )
