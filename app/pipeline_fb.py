from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from docx_tools.sentence_splitter import split_sentences
from utils.terminal_ui import Color, type_print

from app.runtime_lifecycle import RuntimeLifecycle

if TYPE_CHECKING:
    from interfaces.config.app_config import AppConfigShape
    from nlp.llm.llm_server_process import LlmServerProcess
    from services.document_input_service import DocumentInputService
    from services.docx_output_service import DocxOutputService
    from services.input_discovery_service import DiscoveredInputs, DiscoveredPathTriplet
    from services.llm_task_service import LlmTaskService


@dataclass
class FBPipeline:
    """
    Topic sentence feedback pipeline.

    For each discovered document, reads `conc_para.docx`, removes the learner's
    first sentence, asks the LLM to construct a stronger topic sentence, then
    asks the LLM to analyze the learner sentence against that suggestion.
    """

    app_cfg: "AppConfigShape"
    discovered_inputs: "DiscoveredInputs"
    document_input_service: "DocumentInputService"
    docx_out_service: "DocxOutputService"
    llm_task_service: "LlmTaskService"
    llm_server_proc: "LlmServerProcess | None" = None
    runtime_lifecycle: RuntimeLifecycle = field(default_factory=RuntimeLifecycle)

    def run_pipeline(self) -> dict[str, Any]:
        triplets = self._fb_triplets()
        if not triplets:
            return {
                "document_count": 0,
                "constructor_task_count": 0,
                "constructor_success_count": 0,
                "constructor_failure_count": 0,
                "analysis_task_count": 0,
                "analysis_success_count": 0,
                "analysis_failure_count": 0,
                "items": [],
            }

        batch_size = self._batch_size()
        if batch_size <= 0:
            type_print(
                "Skipping topic sentence pipeline because run_config.max_llm_corrections is 0.",
                color=Color.YELLOW,
            )
            return {
                "document_count": len(triplets),
                "constructor_task_count": 0,
                "constructor_success_count": 0,
                "constructor_failure_count": 0,
                "analysis_task_count": 0,
                "analysis_success_count": 0,
                "analysis_failure_count": 0,
                "items": [
                    {
                        "out_path": str(t.out_path),
                        "explained_path": str(t.explained_path),
                        "error": "max_llm_corrections is 0",
                    }
                    for t in triplets
                ],
            }

        def _run_all_batches() -> dict[str, Any]:
            prepared_docs, initial_items = self._prepare_documents(triplets)
            items_by_out_path: dict[str, dict[str, Any]] = {
                item["out_path"]: item for item in initial_items
            }

            constructor_task_count = 0
            constructor_success_count = 0
            constructor_failure_count = 0
            analysis_task_count = 0
            analysis_success_count = 0
            analysis_failure_count = 0

            if prepared_docs:
                type_print(
                    f"Constructing topic sentences in document batches of {batch_size}.",
                    color=Color.BLUE,
                )
                for idx in range(0, len(prepared_docs), batch_size):
                    batch_docs = prepared_docs[idx : idx + batch_size]
                    type_print(
                        f"Topic sentence constructor batch: {idx + 1} to {idx + len(batch_docs)}",
                        color=Color.GREEN,
                    )
                    batch_inputs = [doc["remainder_text"] for doc in batch_docs]
                    batch_result = self.llm_task_service.construct_topic_sentence_parallel(
                        app_cfg=self.app_cfg,
                        text_tasks=batch_inputs,
                        max_concurrency=self.app_cfg.llm_server.llama_n_parallel,
                    )
                    constructor_task_count += batch_result["task_count"]
                    constructor_success_count += batch_result["success_count"]
                    constructor_failure_count += batch_result["failure_count"]

                    for doc, output in zip(batch_docs, batch_result["outputs"]):
                        item = items_by_out_path[str(doc["triplet"].out_path)]
                        if isinstance(output, Exception):
                            item["error"] = f"topic sentence construction failed: {output}"
                            continue

                        suggested_topic = (getattr(output, "content", "") or "").strip()
                        if not suggested_topic:
                            item["error"] = "topic sentence construction returned empty content"
                            continue

                        ts_path = doc["triplet"].out_path.parent / "ts.docx"
                        self.docx_out_service.write_plain_copy(
                            output_path=ts_path,
                            paragraphs=[suggested_topic],
                        )
                        doc["ts_path"] = ts_path
                        item["ts_path"] = str(ts_path)

                analyzable_docs = [
                    d for d in prepared_docs if isinstance(d.get("ts_path"), Path)
                ]

                if analyzable_docs:
                    type_print(
                        f"Analyzing topic sentences in document batches of {batch_size}.",
                        color=Color.BLUE,
                    )
                    for idx in range(0, len(analyzable_docs), batch_size):
                        batch_docs = analyzable_docs[idx : idx + batch_size]
                        type_print(
                            f"Topic sentence analyzer batch: {idx + 1} to {idx + len(batch_docs)}",
                            color=Color.GREEN,
                        )
                        batch_inputs: list[str] = []
                        filtered_docs: list[dict[str, Any]] = []
                        for doc in batch_docs:
                            item = items_by_out_path[str(doc["triplet"].out_path)]
                            ts_path = doc.get("ts_path")
                            if not isinstance(ts_path, Path):
                                item["error"] = "ts.docx path missing before topic sentence analysis"
                                continue
                            good_topic_sentence = self._load_topic_sentence_from_ts(ts_path)
                            if not good_topic_sentence:
                                item["error"] = f"No topic sentence found in: {ts_path}"
                                continue
                            batch_inputs.append(
                                json.dumps(
                                    {
                                        "learner_text": doc["learner_text"],
                                        "learner_topic_sentence": doc["learner_topic_sentence"],
                                        "good_topic_sentence": good_topic_sentence,
                                    },
                                    ensure_ascii=True,
                                )
                            )
                            filtered_docs.append(doc)

                        if not filtered_docs:
                            continue

                        batch_result = self.llm_task_service.analyze_topic_sentence_parallel(
                            app_cfg=self.app_cfg,
                            text_tasks=batch_inputs,
                            max_concurrency=self.app_cfg.llm_server.llama_n_parallel,
                        )
                        analysis_task_count += batch_result["task_count"]
                        analysis_success_count += batch_result["success_count"]
                        analysis_failure_count += batch_result["failure_count"]

                        for doc, output in zip(filtered_docs, batch_result["outputs"]):
                            item = items_by_out_path[str(doc["triplet"].out_path)]
                            if isinstance(output, Exception):
                                item["error"] = f"topic sentence analysis failed: {output}"
                                continue

                            feedback = (getattr(output, "content", "") or "").strip()
                            if not feedback:
                                item["error"] = "topic sentence analysis returned empty content"
                                continue

                            fb_path = doc["triplet"].out_path.parent / "fb.docx"
                            self.docx_out_service.write_plain_copy(
                                output_path=fb_path,
                                paragraphs=[feedback],
                            )
                            item["fb_path"] = str(fb_path)

            return {
                "document_count": len(triplets),
                "constructor_task_count": constructor_task_count,
                "constructor_success_count": constructor_success_count,
                "constructor_failure_count": constructor_failure_count,
                "analysis_task_count": analysis_task_count,
                "analysis_success_count": analysis_success_count,
                "analysis_failure_count": analysis_failure_count,
                "batch_size": batch_size,
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

    def _prepare_documents(
        self,
        triplets: list["DiscoveredPathTriplet"],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        prepared_docs: list[dict[str, Any]] = []
        items: list[dict[str, Any]] = []

        type_print("Loading conc_para.docx files for topic sentence analysis.", color=Color.BLUE)

        for triplet in triplets:
            item: dict[str, Any] = {
                "out_path": str(triplet.out_path),
                "explained_path": str(triplet.explained_path),
            }

            conc_para_path = triplet.out_path.parent / "conc_para.docx"
            if not conc_para_path.exists():
                item["error"] = f"Missing source file: {conc_para_path}"
                items.append(item)
                continue

            loaded = self.document_input_service.load(conc_para_path)
            learner_text = "\n".join(block for block in loaded.blocks if (block or "").strip()).strip()
            if not learner_text:
                item["error"] = f"No learner text found in: {conc_para_path}"
                items.append(item)
                continue

            sentences = split_sentences(learner_text)
            if not sentences:
                item["error"] = f"Could not split learner text into sentences: {conc_para_path}"
                items.append(item)
                continue

            learner_topic_sentence = sentences[0].strip()
            remainder_text = " ".join(s.strip() for s in sentences[1:] if s.strip())
            if not remainder_text:
                item["error"] = (
                    "Learner text has no remainder after removing first sentence; "
                    "cannot construct replacement topic sentence."
                )
                items.append(item)
                continue

            prepared_docs.append(
                {
                    "triplet": triplet,
                    "learner_text": learner_text,
                    "learner_topic_sentence": learner_topic_sentence,
                    "remainder_text": remainder_text,
                }
            )
            items.append(item)

        return prepared_docs, items

    def _fb_triplets(self) -> list["DiscoveredPathTriplet"]:
        return (
            self.discovered_inputs.docx_paths
            + self.discovered_inputs.pdf_paths
            + self.discovered_inputs.image_paths
        )

    def _batch_size(self) -> int:
        configured = self.app_cfg.run_config.max_llm_corrections
        if isinstance(configured, int):
            return configured
        return 0

    def _load_topic_sentence_from_ts(self, ts_path: Path) -> str:
        loaded = self.document_input_service.load(ts_path)
        blocks = [block.strip() for block in loaded.blocks if (block or "").strip()]
        if not blocks:
            return ""
        return blocks[0]
