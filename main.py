from utils.terminal_ui import Color, type_print, stage

from app.settings import build_settings
from app.select_model import select_model_and_update_config
from app.bootstrap_llm import bootstrap_llm
from app.container import build_container
from app.pipeline import TestPipeline

def main():
    # Handle environment variables for production vs dev later
    type_print("Building settings", color=Color.BLUE)
    app_cfg = build_settings()

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
    llm_service = deps.get("llm_service")
    if llm_service is None:
        raise RuntimeError("llm_service is not available. Ensure llama backend is set to server.")

    type_print("Running parallel KV-cache test", color=Color.BLUE)
    pipeline = TestPipeline(llm=llm_service)
    result = pipeline.run_test(app_cfg)

    type_print(
        f"Parallel test complete: tasks={result['task_count']}, "
        f"elapsed={result['elapsed_s']:.2f}s, "
        f"chars/s={result['chars_per_second']:.2f}\n",
        color=Color.BLUE,
    )
    for idx, output in enumerate(result["outputs"], start=1):
        type_print(f"[Task {idx}] {output}\n")

if __name__ == "__main__":
    main()
