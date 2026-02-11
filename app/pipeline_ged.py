from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from docx_tools.sentence_splitter import split_sentences
from utils.terminal_ui import type_print, Color

from app.runtime_lifecycle import RuntimeLifecycle

if TYPE_CHECKING:
    from interfaces.config.app_config import AppConfigShape
    from nlp.ged.ged_types import GedSentenceResult
    from nlp.llm.llm_server_process import LlmServerProcess
    from services.document_input_service import DocumentInputService
    from services.explainability import ExplainabilityRecorder
    from services.docx_output_service import DocxOutputService
    from services.input_discovery_service import DiscoveredInputs, DiscoveredPathTriplet
    from services.ged_service import GedService
    from services.llm_task_service import LlmTaskService


@dataclass
class GEDPipeline:
    """
    Grammar Error Detection and Correction Pipeline

    Loops through all the individual paragraphs and finds grammar errors
    using the GED BERT.
    Uses LLM to correct sentences with errors.
    """
    app_cfg: "AppConfigShape"
    discovered_inputs: "DiscoveredInputs"
    document_input_service: "DocumentInputService"
    docx_out_service: "DocxOutputService"
    ged_service: "GedService"
    llm_task_service: "LlmTaskService"
    explainability: "ExplainabilityRecorder | None" = None
    llm_server_proc: "LlmServerProcess | None" = None
    rng: random.Random = field(default_factory=random.Random)
    runtime_lifecycle: RuntimeLifecycle = field(default_factory=RuntimeLifecycle)

    def run_pipeline(self) -> dict[str, Any]:
        triplets = self._ged_triplets()
        if not triplets:
            return {
                "document_count": 0,
                "paragraph_count": 0,
                "corrected_paragraph_count": 0,
                "llm_task_count": 0,
                "llm_success_count": 0,
                "llm_failure_count": 0,
                "items": [],
            }

        def _run_all() -> dict[str, Any]:
            paragraph_count = 0
            corrected_paragraph_count = 0
            llm_task_count = 0
            llm_success_count = 0
            llm_failure_count = 0
            items: list[dict[str, Any]] = []

            for triplet in triplets:
                conc_para_path = triplet.out_path.parent / "conc_para.docx"
                if not conc_para_path.exists():
                    self._append_explain_lines(
                        explained_path=triplet.explained_path,
                        lines=[
                            f"[GED] Missing source file for GED stage: {conc_para_path}",
                        ],
                    )
                    items.append(
                        {
                            "out_path": str(triplet.out_path),
                            "explained_path": str(triplet.explained_path),
                            "paragraph_count": 0,
                            "error": f"Missing source file: {conc_para_path}",
                        }
                    )
                    continue

                loaded = self.document_input_service.load(conc_para_path)
                source_paragraphs = [p for p in loaded.blocks if (p or "").strip()]

                item_paragraph_count = 0
                item_corrected_count = 0

                for paragraph_idx, paragraph in enumerate(source_paragraphs, start=1):
                    item_paragraph_count += 1
                    paragraph_count += 1
                    type_print("Detecting grammar errors...", color=Color.GREEN)
                    paragraph_result = self._process_paragraph(
                        paragraph=paragraph,
                        paragraph_idx=paragraph_idx,
                        triplet=triplet,
                    )

                    llm_task_count += paragraph_result["llm_task_count"]
                    llm_success_count += paragraph_result["llm_success_count"]
                    llm_failure_count += paragraph_result["llm_failure_count"]
                    if paragraph_result["was_corrected"]:
                        corrected_paragraph_count += 1
                        item_corrected_count += 1

                items.append(
                    {
                        "out_path": str(triplet.out_path),
                        "explained_path": str(triplet.explained_path),
                        "paragraph_count": item_paragraph_count,
                        "corrected_paragraph_count": item_corrected_count,
                    }
                )

            return {
                "document_count": len(triplets),
                "paragraph_count": paragraph_count,
                "corrected_paragraph_count": corrected_paragraph_count,
                "llm_task_count": llm_task_count,
                "llm_success_count": llm_success_count,
                "llm_failure_count": llm_failure_count,
                "items": items,
            }

        if self.llm_server_proc is None:
            return _run_all()

        self.runtime_lifecycle.register_process(self.llm_server_proc)
        self.llm_server_proc.start()
        try:
            return _run_all()
        finally:
            self.llm_server_proc.stop()

    def _process_paragraph(
        self,
        *,
        paragraph: str,
        paragraph_idx: int,
        triplet: "DiscoveredPathTriplet",
    ) -> dict[str, Any]:
        sentences = split_sentences(paragraph)
        if not sentences:
            self.docx_out_service.append_corrected_paragraph(
                output_path=triplet.out_path,
                original_paragraph=paragraph,
                corrected_paragraph=paragraph,
            )
            self._append_explain_lines(
                explained_path=triplet.explained_path,
                lines=[f"[GED] Paragraph {paragraph_idx}: no sentence content found."],
            )
            return {
                "was_corrected": False,
                "llm_task_count": 0,
                "llm_success_count": 0,
                "llm_failure_count": 0,
            }

        ged_results = self._score_sentences_with_explainability(
            sentences=sentences,
            paragraph_idx=paragraph_idx,
            triplet=triplet,
        )
        flagged_indexes = [idx for idx, result in enumerate(ged_results) if result.has_error]

        if not flagged_indexes or self.app_cfg.run_config.max_llm_corrections == 0:
            self.docx_out_service.append_corrected_paragraph(
                output_path=triplet.out_path,
                original_paragraph=paragraph,
                corrected_paragraph=paragraph,
            )
            return {
                "was_corrected": False,
                "llm_task_count": 0,
                "llm_success_count": 0,
                "llm_failure_count": 0,
            }

        max_llm_corrections = self.app_cfg.run_config.max_llm_corrections
        selected_indexes = list(flagged_indexes)
        if len(flagged_indexes) > max_llm_corrections:
            selected_indexes = self.rng.sample(flagged_indexes, max_llm_corrections)
            selected_indexes.sort()
            self._append_explain_lines(
                explained_path=triplet.explained_path,
                lines=[
                    (
                        f"[GED] Paragraph {paragraph_idx}: flagged={len(flagged_indexes)} "
                        f"sentences, sampled={len(selected_indexes)} for LLM correction."
                    )
                ],
            )

        type_print("Correcting grammar errors...", color=Color.BLUE)
        selected_sentences = [sentences[idx] for idx in selected_indexes]
        llm_result = self.llm_task_service.correct_grammar_parallel(
            app_cfg=self.app_cfg,
            text_tasks=selected_sentences,
            max_concurrency=self.app_cfg.llm_server.llama_n_parallel,
        )

        corrected_sentences = list(sentences)
        for sentence_idx, output in zip(selected_indexes, llm_result["outputs"]):
            if isinstance(output, Exception):
                self._append_explain_lines(
                    explained_path=triplet.explained_path,
                    lines=[
                        (
                            f"[GED] Paragraph {paragraph_idx}, sentence {sentence_idx + 1}: "
                            f"LLM correction failed: {output}"
                        )
                    ],
                )
                continue

            corrected = (getattr(output, "content", "") or "").strip()
            if corrected:
                corrected_sentences[sentence_idx] = corrected

        corrected_paragraph = " ".join(s.strip() for s in corrected_sentences if s.strip())
        self.docx_out_service.append_corrected_paragraph(
            output_path=triplet.out_path,
            original_paragraph=paragraph,
            corrected_paragraph=corrected_paragraph,
        )

        return {
            "was_corrected": corrected_paragraph.strip() != paragraph.strip(),
            "llm_task_count": llm_result["task_count"],
            "llm_success_count": llm_result["success_count"],
            "llm_failure_count": llm_result["failure_count"],
        }

    def _score_sentences_with_explainability(
        self,
        *,
        sentences: list[str],
        paragraph_idx: int,
        triplet: "DiscoveredPathTriplet",
    ) -> list["GedSentenceResult"]:
        explain = self.explainability
        if explain is None:
            return self.ged_service.score(
                sentences,
                batch_size=self.app_cfg.ged_config.batch_size,
                explain=None,
            )

        explain.reset()
        explain.log("GED", f"Document: {triplet.out_path.name}")
        explain.log("GED", f"Paragraph index: {paragraph_idx}")
        scored = self.ged_service.score(
            sentences,
            batch_size=self.app_cfg.ged_config.batch_size,
            explain=explain,
        )
        self._append_explain_lines(
            explained_path=triplet.explained_path,
            lines=explain.finish_doc(),
        )
        return scored

    def _ged_triplets(self) -> list["DiscoveredPathTriplet"]:
        return (
            self.discovered_inputs.docx_paths
            + self.discovered_inputs.pdf_paths
            + self.discovered_inputs.image_paths
        )

    @staticmethod
    def _append_explain_lines(*, explained_path: Path, lines: list[str]) -> None:
        explained_path.parent.mkdir(parents=True, exist_ok=True)
        with explained_path.open("a", encoding="utf-8") as explained_file:
            for line in lines:
                explained_file.write(f"{line}\n")
