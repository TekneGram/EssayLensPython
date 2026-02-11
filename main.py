import asyncio
import json

from utils.terminal_ui import Color, type_print, stage

from app.settings import build_settings
from app.select_model import select_model_and_update_config
from app.select_ocr_model import select_ocr_model_and_update_config
from app.bootstrap_llm import bootstrap_llm
from app.container import build_container
from app.pipeline_prep import PrepPipeline
from app.pipeline_metadata import MetadataPipeline
from app.pipeline_fb import FBPipeline
from app.pipeline_conclusion import ConclusionPipeline
from app.pipeline_body import BodyPipeline
from app.pipeline_content import ContentPipeline
from app.pipeline_summarize_fb import SummarizeFBPipeline
from app.pipeline_ged import GEDPipeline
from app.runtime_lifecycle import RuntimeLifecycle

from nlp.llm.llm_client import ChatResponse, JsonSchemaChatRequest

def main():
    # Handle environment variables for production vs dev later
    type_print("Building settings", color=Color.BLUE)
    app_cfg = build_settings()

    # Set up the LLM
    type_print("Selecting the best model for your system", color=Color.BLUE)
    app_cfg = select_model_and_update_config(app_cfg)

    # Set up the OCR model
    type_print("Setting up the OCR model", color=Color.BLUE)
    app_cfg = select_ocr_model_and_update_config(app_cfg)

    type_print("Bootstrapping a large language model", color=Color.BLUE)
    app_cfg = bootstrap_llm(app_cfg)

    type_print("Configuration complete:\n------------------")
    type_print(f"Language Model: {app_cfg.llm_config.llama_model_display_name}\n", color=Color.BLUE)
    type_print(f"Language Model Family: {app_cfg.llm_config.llama_model_family}\n", color=Color.BLUE)
    type_print(f"Server url: {app_cfg.llm_server.llama_server_url} (Set in llm_server)\n", color=Color.BLUE)
    type_print(f"Multi-modal projected used: {app_cfg.llm_config.hf_mmproj_filename}\n", color=Color.BLUE)
    type_print(f"Grammer Error Detection: {app_cfg.ged_config.model_name}, batch size: {app_cfg.ged_config.batch_size}\n", color=Color.BLUE)
    type_print(f"Maximum LLM GED corrections: {app_cfg.run_config.max_llm_corrections}\n", color=Color.BLUE)
    type_print(f"Your grading input folder: {app_cfg.assessment_paths.input_folder}\n", color=Color.BLUE)
    type_print(f"Your grading completed folder: {app_cfg.assessment_paths.output_folder}\n", color=Color.BLUE)
    type_print(f"Your grading explained folder: {app_cfg.assessment_paths.explained_folder}\n", color=Color.BLUE)
    type_print(f"Mode: {'Single Paragraph' if app_cfg.run_config.single_paragraph_mode else 'Essay'} (Set in run config)\n", color=Color.BLUE)
    type_print(f"Word document author name: {app_cfg.run_config.author} (Set in run config) \n", color=Color.BLUE)

    deps = build_container(app_cfg)
    # Start the runtime lifecycle manager
    runtime_lifecycle = RuntimeLifecycle()

    # ----- PREPARATION STAGE -----
    # Preparation stage (involves using OCR)
    # Prepare the texts and return the file paths where they are located
    prep_pipeline = PrepPipeline(
        app_root=str(deps["project_root"]),
        input_discovery_service=deps["input_discovery_service"],
        document_input_service=deps["document_input_service"],
        docx_out_service=deps["docx_out_service"],
        explainability=deps.get("explain"),
        explain_file_writer=deps.get("explain_file_writer"),
        ocr_server_proc=deps.get("ocr_server_proc"),
        ocr_service=deps.get("ocr_service"),
        runtime_lifecycle=runtime_lifecycle,
    )
    discovered_inputs = prep_pipeline.run_pipeline()

    # ----- METADATA EXTRACTION STAGE -----
    # Run the metadata extraction
    llm_task_service = deps.get("llm_task_service")
    if llm_task_service is None:
        raise RuntimeError("llm_task_service is not available. Ensure llama backend is set to server.")

    metadata_pipeline = MetadataPipeline(
        app_cfg=app_cfg,
        discovered_inputs=discovered_inputs,
        document_input_service=deps["document_input_service"],
        docx_out_service=deps["docx_out_service"],
        llm_server_proc=deps.get("server_proc"),
        llm_task_service=llm_task_service,
        runtime_lifecycle=runtime_lifecycle,
    )
    metadata_pipeline.run_pipeline()

    ged_pipeline = GEDPipeline(
        app_cfg=app_cfg,
        discovered_inputs=discovered_inputs,
        document_input_service=deps["document_input_service"],
        docx_out_service=deps["docx_out_service"],
        ged_service=deps["ged"],
        llm_task_service=llm_task_service,
        explainability=deps.get("explain"),
        llm_server_proc=deps.get("server_proc"),
        runtime_lifecycle=runtime_lifecycle,
    )
    ged_pipeline.run_pipeline()

    fb_pipeline = FBPipeline(
        app_cfg=app_cfg,
        discovered_inputs=discovered_inputs,
        document_input_service=deps["document_input_service"],
        docx_out_service=deps["docx_out_service"],
        llm_task_service=llm_task_service,
        llm_server_proc=deps.get("server_proc"),
        runtime_lifecycle=runtime_lifecycle,
    )
    fb_pipeline.run_pipeline()

    conclusion_pipeline = ConclusionPipeline(
        app_cfg=app_cfg,
        discovered_inputs=discovered_inputs,
        document_input_service=deps["document_input_service"],
        docx_out_service=deps["docx_out_service"],
        llm_task_service=llm_task_service,
        llm_server_proc=deps.get("server_proc"),
        runtime_lifecycle=runtime_lifecycle,
    )
    conclusion_pipeline.run_pipeline()

    body_pipeline = BodyPipeline(
        app_cfg=app_cfg,
        discovered_inputs=discovered_inputs,
        document_input_service=deps["document_input_service"],
        docx_out_service=deps["docx_out_service"],
        llm_task_service=llm_task_service,
        llm_server_proc=deps.get("server_proc"),
        runtime_lifecycle=runtime_lifecycle,
    )
    body_pipeline.run_pipeline()

    content_pipeline = ContentPipeline(
        app_cfg=app_cfg,
        discovered_inputs=discovered_inputs,
        document_input_service=deps["document_input_service"],
        docx_out_service=deps["docx_out_service"],
        llm_task_service=llm_task_service,
        llm_server_proc=deps.get("server_proc"),
        runtime_lifecycle=runtime_lifecycle,
    )
    content_pipeline.run_pipeline()

    summarize_fb_pipeline = SummarizeFBPipeline(
        app_cfg=app_cfg,
        discovered_inputs=discovered_inputs,
        document_input_service=deps["document_input_service"],
        docx_out_service=deps["docx_out_service"],
        llm_task_service=llm_task_service,
        llm_server_proc=deps.get("server_proc"),
        runtime_lifecycle=runtime_lifecycle,
    )
    summarize_result = summarize_fb_pipeline.run_pipeline()
    type_print(
        (
            "[Main] SummarizeFB complete: "
            f"docs={summarize_result.get('document_count', 0)}, "
            f"tasks={summarize_result.get('task_count', 0)}, "
            f"llm_success={summarize_result.get('success_count', 0)}, "
            f"llm_failure={summarize_result.get('failure_count', 0)}"
        ),
        color=Color.BLUE,
    )
    for item in summarize_result.get("items", []):
        errors = item.get("errors", [])
        if not errors:
            continue
        doc_name = str(item.get("out_path", "unknown"))
        for err in errors:
            type_print(f"[Main] SummarizeFB note for {doc_name}: {err}", color=Color.YELLOW)


if __name__ == "__main__":
    main()
