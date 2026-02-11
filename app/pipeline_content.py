from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
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
class ContentPipeline:
    """
    Content pipeline.

    Stage 1: analyze `conc_para.docx` paragraphs and write results to
    `comp_para.docx` in the same output folder.
    Stage 2: filter `comp_para.docx` paragraphs and append results to `fb.docx`.

    Both stages process paragraph tasks in batches of 4, and stage 2 starts
    only after stage 1 completes for all files.
    """

    app_cfg: "AppConfigShape"
    discovered_inputs: "DiscoveredInputs"
    document_input_service: "DocumentInputService"
    docx_out_service: "DocxOutputService"
    llm_task_service: "LlmTaskService"
    llm_server_proc: "LlmServerProcess | None" = None
    runtime_lifecycle: RuntimeLifecycle = field(default_factory=RuntimeLifecycle)

    def run_pipeline(self) -> dict[str, Any]:
        triplets = self._content_triplets()
        if not triplets:
            return {
                "document_count": 0,
                "batch_size": 4,
                "content_analysis": {
                    "task_count": 0,
                    "success_count": 0,
                    "failure_count": 0,
                },
                "content_filter": {
                    "task_count": 0,
                    "success_count": 0,
                    "failure_count": 0,
                },
                "items": [],
            }

        def _run_all_batches() -> dict[str, Any]:
            analysis_tasks, items = self._prepare_conc_tasks(triplets)
            items_by_out_path: dict[str, dict[str, Any]] = {
                item["out_path"]: item for item in items
            }

            analysis_counts = {
                "task_count": 0,
                "success_count": 0,
                "failure_count": 0,
            }

            type_print("Running content analysis on conc_para.docx in batches of 4.", color=Color.BLUE)
            comp_by_out_parent: dict[Path, list[str]] = {}

            for idx in range(0, len(analysis_tasks), 4):
                batch_tasks = analysis_tasks[idx : idx + 4]
                type_print(
                    f"Content analysis batch: {idx + 1} to {idx + len(batch_tasks)}",
                    color=Color.GREEN,
                )
                batch_inputs = [task["paragraph"] for task in batch_tasks]
                batch_result = self.llm_task_service.analyze_content_parallel(
                    app_cfg=self.app_cfg,
                    text_tasks=batch_inputs,
                    max_concurrency=self.app_cfg.llm_server.llama_n_parallel,
                )
                analysis_counts["task_count"] += batch_result["task_count"]
                analysis_counts["success_count"] += batch_result["success_count"]
                analysis_counts["failure_count"] += batch_result["failure_count"]

                for task, output in zip(batch_tasks, batch_result["outputs"]):
                    triplet = task["triplet"]
                    item = items_by_out_path[str(triplet.out_path)]
                    if isinstance(output, Exception):
                        item["errors"].append(
                            f"content_analysis, paragraph {task['paragraph_idx']}: {output}"
                        )
                        continue

                    content = (getattr(output, "content", "") or "").strip()
                    if not content:
                        item["errors"].append(
                            f"content_analysis, paragraph {task['paragraph_idx']}: empty content"
                        )
                        continue

                    out_parent = triplet.out_path.parent
                    comp_by_out_parent.setdefault(out_parent, []).append(content)

            for triplet in triplets:
                out_parent = triplet.out_path.parent
                comp_path = out_parent / "comp_para.docx"
                comp_paragraphs = comp_by_out_parent.get(out_parent, [])
                if not comp_paragraphs:
                    continue
                self.docx_out_service.write_plain_copy(
                    output_path=comp_path,
                    paragraphs=comp_paragraphs,
                )
                item = items_by_out_path[str(triplet.out_path)]
                item["comp_path"] = str(comp_path)
                item["comp_paragraph_count"] = len(comp_paragraphs)

            filter_tasks = self._prepare_comp_tasks(triplets, items_by_out_path)
            filter_counts = {
                "task_count": 0,
                "success_count": 0,
                "failure_count": 0,
            }

            type_print("Running content filter on comp_para.docx in batches of 4.", color=Color.BLUE)
            for idx in range(0, len(filter_tasks), 4):
                batch_tasks = filter_tasks[idx : idx + 4]
                type_print(
                    f"Content filter batch: {idx + 1} to {idx + len(batch_tasks)}",
                    color=Color.GREEN,
                )
                batch_inputs = [task["paragraph"] for task in batch_tasks]
                batch_result = self.llm_task_service.filter_content_parallel(
                    app_cfg=self.app_cfg,
                    text_tasks=batch_inputs,
                    max_concurrency=self.app_cfg.llm_server.llama_n_parallel,
                )
                filter_counts["task_count"] += batch_result["task_count"]
                filter_counts["success_count"] += batch_result["success_count"]
                filter_counts["failure_count"] += batch_result["failure_count"]

                for task, output in zip(batch_tasks, batch_result["outputs"]):
                    triplet = task["triplet"]
                    item = items_by_out_path[str(triplet.out_path)]

                    if isinstance(output, Exception):
                        item["errors"].append(
                            f"content_filter, paragraph {task['paragraph_idx']}: {output}"
                        )
                        continue

                    content = (getattr(output, "content", "") or "").strip()
                    if not content:
                        item["errors"].append(
                            f"content_filter, paragraph {task['paragraph_idx']}: empty content"
                        )
                        continue

                    fb_path = triplet.out_path.parent / "fb.docx"
                    self.docx_out_service.append_paragraphs(
                        output_path=fb_path,
                        paragraphs=[content],
                    )
                    item["fb_path"] = str(fb_path)
                    item["fb_count"] = int(item.get("fb_count", 0)) + 1

            return {
                "document_count": len(triplets),
                "batch_size": 4,
                "content_analysis": analysis_counts,
                "content_filter": filter_counts,
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

    def _prepare_conc_tasks(
        self,
        triplets: list["DiscoveredPathTriplet"],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        tasks: list[dict[str, Any]] = []
        items: list[dict[str, Any]] = []

        type_print("Loading conc_para.docx files for content analysis.", color=Color.BLUE)

        for triplet in triplets:
            item: dict[str, Any] = {
                "out_path": str(triplet.out_path),
                "explained_path": str(triplet.explained_path),
                "errors": [],
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
                        "paragraph_idx": paragraph_idx,
                        "paragraph": paragraph,
                    }
                )

            items.append(item)

        return tasks, items

    def _prepare_comp_tasks(
        self,
        triplets: list["DiscoveredPathTriplet"],
        items_by_out_path: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        tasks: list[dict[str, Any]] = []
        type_print("Loading comp_para.docx files for content filter.", color=Color.BLUE)

        for triplet in triplets:
            item = items_by_out_path[str(triplet.out_path)]
            comp_path = triplet.out_path.parent / "comp_para.docx"
            if not comp_path.exists():
                item["errors"].append(f"Missing source file: {comp_path}")
                continue

            loaded = self.document_input_service.load(comp_path)
            paragraphs = [p.strip() for p in loaded.blocks if (p or "").strip()]
            if not paragraphs:
                item["errors"].append(f"No paragraphs found in: {comp_path}")
                continue

            for paragraph_idx, paragraph in enumerate(paragraphs, start=1):
                tasks.append(
                    {
                        "triplet": triplet,
                        "paragraph_idx": paragraph_idx,
                        "paragraph": paragraph,
                    }
                )

        return tasks

    def _content_triplets(self) -> list["DiscoveredPathTriplet"]:
        return (
            self.discovered_inputs.docx_paths
            + self.discovered_inputs.pdf_paths
            + self.discovered_inputs.image_paths
        )
