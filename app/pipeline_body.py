from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

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
class BodyPipeline:
    """
    Body language feedback pipeline.

    Runs three analysis stages over all paragraphs from each `conc_para.docx`:
    hedging, cause/effect, and compare/contrast.
    Each stage processes all paragraphs in batches of 4 to preserve KV-cache
    locality before moving to the next stage.
    """

    app_cfg: "AppConfigShape"
    discovered_inputs: "DiscoveredInputs"
    document_input_service: "DocumentInputService"
    docx_out_service: "DocxOutputService"
    llm_task_service: "LlmTaskService"
    llm_server_proc: "LlmServerProcess | None" = None
    runtime_lifecycle: RuntimeLifecycle = field(default_factory=RuntimeLifecycle)

    def run_pipeline(self) -> dict[str, Any]:
        triplets = self._body_triplets()
        if not triplets:
            return {
                "document_count": 0,
                "batch_size": 4,
                "stages": {},
                "items": [],
            }

        def _run_all_batches() -> dict[str, Any]:
            tasks, items = self._prepare_tasks(triplets)
            if not tasks:
                return {
                    "document_count": len(triplets),
                    "batch_size": 4,
                    "stages": {},
                    "items": items,
                }

            items_by_out_path: dict[str, dict[str, Any]] = {
                item["out_path"]: item for item in items
            }

            stages: list[tuple[str, str, Callable[..., dict[str, Any]]]] = [
                ("hedging", "Hedging", self.llm_task_service.analyze_hedging_parallel),
                (
                    "cause_effect",
                    "Cause and Effect",
                    self.llm_task_service.prompt_tester_parallel,
                ),
                (
                    "compare_contrast",
                    "Compare and Contrast",
                    self.llm_task_service.analyze_compare_contrast_parallel,
                ),
            ]

            stage_results: dict[str, dict[str, int]] = {}

            for stage_key, stage_title, stage_fn in stages:
                type_print(
                    f"Running {stage_title} analysis in batches of 4.",
                    color=Color.BLUE,
                )
                task_count = 0
                success_count = 0
                failure_count = 0

                for idx in range(0, len(tasks), 4):
                    batch_tasks = tasks[idx : idx + 4]
                    type_print(
                        f"{stage_title} batch: {idx + 1} to {idx + len(batch_tasks)}",
                        color=Color.GREEN,
                    )
                    batch_inputs = [task["paragraph"] for task in batch_tasks]
                    batch_result = stage_fn(
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
                            item["errors"].append(
                                f"{stage_title}, paragraph {task['paragraph_idx']}: {output}"
                            )
                            continue

                        feedback = (getattr(output, "content", "") or "").strip()
                        if not feedback:
                            item["errors"].append(
                                f"{stage_title}, paragraph {task['paragraph_idx']}: empty feedback"
                            )
                            continue

                        fb_path = triplet.out_path.parent / "fb.docx"
                        self.docx_out_service.append_paragraphs(
                            output_path=fb_path,
                            paragraphs=[
                                f"Body Feedback - Paragraph {task['paragraph_idx']}",
                                f"{stage_title}: {feedback}",
                            ],
                        )
                        item["fb_path"] = str(fb_path)
                        item["feedback_count"] = int(item.get("feedback_count", 0)) + 1

                stage_results[stage_key] = {
                    "task_count": task_count,
                    "success_count": success_count,
                    "failure_count": failure_count,
                }

            return {
                "document_count": len(triplets),
                "batch_size": 4,
                "stages": stage_results,
                "items": list(items_by_out_path.values()),
            }

        if self.llm_server_proc is None:
            return _run_all_batches()

        self.runtime_lifecycle.register_process(self.llm_server_proc)
        self.llm_server_proc.start()
        try:
            return _run_all_batches()
        finally:
            self.llm_server_proc.stop()

    def _prepare_tasks(
        self,
        triplets: list["DiscoveredPathTriplet"],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        tasks: list[dict[str, Any]] = []
        items: list[dict[str, Any]] = []

        type_print("Loading conc_para.docx files for body analysis.", color=Color.BLUE)

        for triplet in triplets:
            item: dict[str, Any] = {
                "out_path": str(triplet.out_path),
                "explained_path": str(triplet.explained_path),
                "errors": [],
                "feedback_count": 0,
            }

            conc_para_path = triplet.out_path.parent / "conc_para.docx"
            if not conc_para_path.exists():
                item["errors"].append(f"Missing source file: {conc_para_path}")
                items.append(item)
                continue

            loaded = self.document_input_service.load(conc_para_path)
            paragraphs = [p.strip() for p in loaded.blocks if (p or "").strip()]
            if not paragraphs:
                item["errors"].append(f"No paragraphs found in: {conc_para_path}")
                items.append(item)
                continue

            for paragraph_idx, paragraph in enumerate(paragraphs, start=1):
                tasks.append(
                    {
                        "triplet": triplet,
                        "paragraph": paragraph,
                        "paragraph_idx": paragraph_idx,
                    }
                )
            items.append(item)

        return tasks, items

    def _body_triplets(self) -> list["DiscoveredPathTriplet"]:
        return (
            self.discovered_inputs.docx_paths
            + self.discovered_inputs.pdf_paths
            + self.discovered_inputs.image_paths
        )
