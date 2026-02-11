import asyncio
import json

from utils.terminal_ui import Color, type_print, stage

from app.settings import build_settings
from app.select_model import select_model_and_update_config
from app.select_ocr_model import select_ocr_model_and_update_config
from app.bootstrap_llm import bootstrap_llm
from app.container import build_container
from app.pipeline_prep import PrepPipeline

from app.pipeline import TestPipeline
from nlp.llm.llm_client import ChatResponse, JsonSchemaChatRequest
from nlp.llm.tasks.test_sequential import run_sequential_stream_demo

def main():
    # Handle environment variables for production vs dev later
    type_print("Building settings", color=Color.BLUE)
    app_cfg = build_settings()

    # Set up the OCR model
    type_print("Selecting the OCR model", color=Color.BLUE)
    app_cfg = select_ocr_model_and_update_config(app_cfg)

    # Run all OCR things here

    # Set up the LLM
    type_print("Selecting the best model for your system", color=Color.BLUE)
    app_cfg = select_model_and_update_config(app_cfg)

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

    # Preparation stage (involves using OCR)
    prep_pipeline = PrepPipeline(deps)

    # Run all the LLM work next.

    llm_service = deps.get("llm_service")
    if llm_service is None:
        raise RuntimeError("llm_service is not available. Ensure llama backend is set to server.")

    type_print("Running parallel KV-cache test", color=Color.BLUE)
    pipeline = TestPipeline(llm=llm_service)
    result = pipeline.run_test_again(app_cfg)
    print(result)

    # type_print(
    #     f"Parallel test complete: tasks={result['task_count']}, "
    #     f"elapsed={result['elapsed_s']:.2f}s, "
    #     f"chars/s={result['chars_per_second']:.2f}\n",
    #     color=Color.BLUE,
    # )
    for idx, output in enumerate(result["outputs"], start=1):
        if isinstance(output, Exception):
            type_print(f"[Task {idx}] ERROR: {output}\n")
            continue
        if isinstance(output, ChatResponse):
            type_print(f"[Task {idx}] {output.content}\n")
            type_print(f"[Task {idx}] {output.reasoning_content}")
            type_print(f"[Task {idx}] {output.finish_reason}")
            type_print(f"[Task {idx}] {output.usage}")
            continue
        type_print(f"[Task {idx}] {output}\n")

    # type_print("Running live streaming demo", color=Color.BLUE)
    # llm_stream = llm_service.with_mode("no_think")
    # stream_system = "You are a concise writing coach."
    # stream_user = (
    #     "Give 3 short bullet tips to improve sentence variety in a student paragraph. "
    #     "Keep each tip under 12 words."
    # )
    # try:
    #     stream_response = llm_stream.chat_stream_to_terminal(
    #         system=stream_system,
    #         user=stream_user,
    #     )
    #     type_print(f"Streaming complete. finish_reason={stream_response.finish_reason}", color=Color.BLUE)
    #     type_print(f"Streaming usage: {stream_response.usage}", color=Color.BLUE)
    #     if stream_response.reasoning_content:
    #         preview = stream_response.reasoning_content[:120]
    #         type_print(f"Reasoning preview: {preview}", color=Color.BLUE)
    #     else:
    #         type_print("Reasoning preview: <none>", color=Color.BLUE)
    # except Exception as e:
    #     type_print(f"Streaming demo failed: {e}", color=Color.RED)

    # type_print("Running sequential streaming demo (think mode)", color=Color.BLUE)
    # llm_stream_think = llm_service.with_mode("think")
    # try:
    #     sequential_result = run_sequential_stream_demo(llm_stream_think)
    #     type_print(
    #         f"Sequential streaming complete: tasks={sequential_result['task_count']}, "
    #         f"success={sequential_result['success_count']}, "
    #         f"failure={sequential_result['failure_count']}, "
    #         f"elapsed={sequential_result['elapsed_s']:.2f}s, "
    #         f"reasoning={sequential_result['reasoning_count']}",
    #         color=Color.BLUE,
    #     )
    #     for idx, output in enumerate(sequential_result["outputs"], start=1):
    #         if isinstance(output, Exception):
    #             type_print(f"[Sequential Task {idx}] ERROR: {output}", color=Color.RED)
    #             continue
    #         type_print(f"[Sequential Task {idx}] finish_reason={output.finish_reason}", color=Color.BLUE)
    # except Exception as e:
    #     type_print(f"Sequential streaming demo failed: {e}", color=Color.RED)

    # type_print("Running parallel JSON-schema demo", color=Color.BLUE)
    # json_schema = {
    #     "type": "json_schema",
    #     "json_schema": {
    #         "name": "quick_feedback",
    #         "schema": {
    #             "type": "object",
    #             "properties": {
    #                 "tone": {"type": "string"},
    #                 "score": {"type": "integer"},
    #                 "tip": {"type": "string"},
    #             },
    #             "required": ["tone", "score", "tip"],
    #             "additionalProperties": False,
    #         },
    #     },
    # }
    # json_requests = [
    #     JsonSchemaChatRequest(
    #         system="Return valid JSON only.",
    #         user="Assess writing quality quickly and provide one tip.",
    #         schema=json_schema,
    #         max_tokens=150,
    #     ),
    #     JsonSchemaChatRequest(
    #         system="Return valid JSON only.",
    #         user="Assess grammar briefly and provide one practical tip.",
    #         schema=json_schema,
    #         max_tokens=150,
    #     ),
    #     JsonSchemaChatRequest(
    #         system="Return valid JSON only.",
    #         user="Assess coherence briefly and provide one practical tip.",
    #         schema=json_schema,
    #         max_tokens=150,
    #     ),
    # ]
    # try:
    #     json_outputs = asyncio.run(
    #         llm_stream.json_schema_chat_many(
    #             json_requests,
    #             max_concurrency=app_cfg.llm_server.llama_n_parallel,
    #         )
    #     )
    #     for idx, output in enumerate(json_outputs, start=1):
    #         if isinstance(output, Exception):
    #             type_print(f"[JSON Task {idx}] ERROR: {output}", color=Color.RED)
    #             continue
    #         type_print(f"[JSON Task {idx}] {json.dumps(output, ensure_ascii=True)}", color=Color.BLUE)
    # except Exception as e:
    #     type_print(f"Parallel JSON-schema demo failed: {e}", color=Color.RED)

if __name__ == "__main__":
    main()
