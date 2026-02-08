from __future__ import annotations

from dataclasses import dataclass

from config.llm_request_config import LlmRequestConfig
from config.llm_server_config import LlmServerConfig
from config.assessment_paths_config import AssessmentPathsConfig
from config.llm_config import LlmConfig
from config.ged_config import GedConfig
from config.run_config import RunConfig


@dataclass(frozen=True, slots=True)
class AppConfig:
    assessment_paths: AssessmentPathsConfig
    llm_config: LlmConfig
    llm_server: LlmServerConfig
    llm_request: LlmRequestConfig
    ged_config: GedConfig
    run_config: RunConfig

def build_settings() -> AppConfig:

    assessment_paths = AssessmentPathsConfig.from_strings(
        input_folder="Assessment/in",
        output_folder="Assessment/checked",
        explained_folder="Assessment/explained"
    )
    assessment_paths.validate()
    assessment_paths.ensure_output_dirs()

    llm_config = LlmConfig.from_strings(
        hf_repo_id=None,
        hf_filename=None,
        hf_revision=None,
        hf_mmproj_filename=None,
        llama_gguf_path="",  # empty until bootstrap
        llama_mmproj_path="", # bootstrap can update it if mmproj_path also downloaded
        llama_server_model="llama",
        llama_model_key="default",
        llama_model_display_name="Default Model",
        llama_model_alias="Default Model",
        llama_model_family="instruct",
    )
    llm_config.validate(allow_unresolved_model_paths=True)

    llm_server = LlmServerConfig.from_strings(
        llama_backend="server",
        llama_server_path=".appdata/build/llama.cpp/bin/llama-server",
        llama_server_url="http://127.0.0.1:8080/v1/chat/completions",
        llama_n_ctx=4096,
        llama_host="127.0.0.1",
        llama_port=8080,
        llama_n_threads=None,
        llama_n_gpu_layers=99,
        llama_n_batch=None,
        llama_n_parallel=8,
        llama_seed=None,
        llama_rope_freq_base=None,
        llama_rope_freq_scale=None,
        llama_use_jinja=True,
        llama_cache_prompt=True,
        llama_flash_attn=True,
    )
    llm_server.validate()

    llm_request = LlmRequestConfig.from_values(
        default_max_tokens=1024,
        default_temperature=0.2,
        default_top_p=0.95,
        default_top_k=40,
        default_repeat_penalty=1.1,
        default_seed=None,
        default_stop=None,
        default_response_format=None,
        default_stream=False,
    )
    llm_request.validate()

    ged_config = GedConfig.from_strings(
        model_name="gotutiyan/token-ged-bert-large-cased-bin",
        batch_size=8,
    )
    ged_config.validate()

    run_config = RunConfig.from_strings(
        author="Daniel Parsons",
        single_paragraph_mode = True,
        max_llm_corrections=5,
        include_edited_text_section_policy=True
    )
    run_config.validate()

    return AppConfig(
        assessment_paths=assessment_paths,
        llm_config=llm_config,
        llm_server=llm_server,
        llm_request=llm_request,
        ged_config=ged_config,
        run_config=run_config
    )
