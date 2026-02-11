from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from utils.terminal_ui import type_print, Color

from app.runtime_lifecycle import RuntimeLifecycle
from nlp.llm.tasks.extract_metadata import run_parallel_metadata_extraction

if TYPE_CHECKING:
    from interfaces.config.app_config import AppConfigShape
    from nlp.llm.llm_server_process import LlmServerProcess
    from services.document_input_service import DocumentInputService
    from services.docx_output_service import DocxOutputService
    from services.input_discovery_service import DiscoveredInputs, DiscoveredPathTriplet
    from services.llm_service import LlmService


@dataclass
class MetadataPipeline:
    """
    Metadata extraction pipeline.

    Reads prepared docx outputs and sends each document text as one parallel
    metadata extraction request using JSON schema mode.
    """

    app_cfg: "AppConfigShape"
    discovered_inputs: "DiscoveredInputs"
    document_input_service: "DocumentInputService"
    docx_out_service: "DocxOutputService"
    llm_service: "LlmService"
    llm_server_proc: "LlmServerProcess | None" = None
    runtime_lifecycle: RuntimeLifecycle = field(default_factory=RuntimeLifecycle)

    def run_pipeline(self) -> dict[str, Any]:
        triplets = self._metadata_triplets()
        if not triplets:
            return {
                "task_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "items": [],
                "outputs": [],
            }

        batch_size = self._batch_size()
        type_print("Establishing server in no_think mode - this will need updating later for instruct only llms", color=Color.YELLOW)
        llm_no_think = self.llm_service.with_mode("no_think")
        items: list[dict[str, Any]] = []

        def _run_all_batches() -> dict[str, Any]:
            outputs: list[dict[str, Any] | Exception] = []
            success_count = 0
            failure_count = 0
            elapsed_s = 0.0

            for idx in range(0, len(triplets), batch_size):
                batch_triplets = triplets[idx : idx + batch_size]
                text_tasks = [self._load_prepared_text(t) for t in batch_triplets]
                type_print("Extracting metadata on a batch...", color=Color.BLUE)
                batch_result = asyncio.run(
                    run_parallel_metadata_extraction(
                        llm_service=llm_no_think,
                        app_cfg=self.app_cfg,
                        text_tasks=text_tasks,
                    )
                )
                outputs.extend(batch_result["outputs"])
                success_count += batch_result["success_count"]
                failure_count += batch_result["failure_count"]
                elapsed_s += batch_result["elapsed_s"]
                type_print("Writing metadata outputs...", color=Color.BLUE)
                self._persist_batch_outputs(
                    batch_triplets=batch_triplets,
                    batch_outputs=batch_result["outputs"],
                    items=items,
                )

            return {
                "mode": "parallel_json_schema_batched",
                "task_count": len(triplets),
                "success_count": success_count,
                "failure_count": failure_count,
                "max_concurrency": self.app_cfg.llm_server.llama_n_parallel,
                "batch_size": batch_size,
                "elapsed_s": elapsed_s,
                "outputs": outputs,
            }

        if self.llm_server_proc is None:
            results = _run_all_batches()
        else:
            self.runtime_lifecycle.register_process(self.llm_server_proc)
            self.llm_server_proc.start()
            try:
                results = _run_all_batches()
            finally:
                self.llm_server_proc.stop()
        return {
            **results,
            "items": items,
        }

    def _metadata_triplets(self) -> list["DiscoveredPathTriplet"]:
        return (
            self.discovered_inputs.docx_paths
            + self.discovered_inputs.pdf_paths
            + self.discovered_inputs.image_paths
        )

    def _load_prepared_text(self, triplet: "DiscoveredPathTriplet") -> str:
        loaded = self.document_input_service.load(triplet.out_path)
        return "\n".join(block for block in loaded.blocks if block).strip()

    def _write_metadata_docx_outputs(
        self,
        *,
        triplet: "DiscoveredPathTriplet",
        metadata: dict[str, Any],
    ) -> None:
        student_name = str(metadata.get("student_name", "") or "")
        student_number = str(metadata.get("student_number", "") or "")
        essay_title = str(metadata.get("essay_title", "") or "")
        essay_raw = str(metadata.get("essay", "") or "")
        essay = self._to_single_paragraph(essay_raw)

        self.docx_out_service.append_paragraphs(
            output_path=triplet.out_path,
            paragraphs=[
                "",
                "Edited Text",
                f"Student Name: {student_name}",
                f"Student Number: {student_number}",
                f"Essay Title: {essay_title}",
                essay,
            ],
        )

        conc_para_path = triplet.out_path.parent / "conc_para.docx"
        self.docx_out_service.write_plain_copy(
            output_path=conc_para_path,
            paragraphs=[essay],
        )

    def _persist_batch_outputs(
        self,
        *,
        batch_triplets: list["DiscoveredPathTriplet"],
        batch_outputs: list[dict[str, Any] | Exception],
        items: list[dict[str, Any]],
    ) -> None:
        for triplet, output in zip(batch_triplets, batch_outputs):
            if isinstance(output, Exception):
                items.append(
                    {
                        "out_path": str(triplet.out_path),
                        "explained_path": str(triplet.explained_path),
                        "error": str(output),
                    }
                )
                continue

            self._write_metadata_docx_outputs(
                triplet=triplet,
                metadata=output,
            )
            items.append(
                {
                    "out_path": str(triplet.out_path),
                    "explained_path": str(triplet.explained_path),
                    "metadata": output,
                }
            )

    def _batch_size(self) -> int:
        configured = self.app_cfg.llm_server.llama_n_parallel
        if isinstance(configured, int) and configured > 0:
            return configured
        return 1

    @staticmethod
    def _to_single_paragraph(text: str) -> str:
        return " ".join(text.split())
