# Import services and processes
from nlp.llm.llm_server_process import LlmServerProcess
from nlp.llm.llm_client import OpenAICompatChatClient
from services.llm_service import LlmService
from services.explainability import ExplainabilityRecorder
from inout.explainability_writer import ExplainabilityWriter
from services.ged_service import GedService
from nlp.ged.ged_bert import GedBertDetector
from inout.docx_loader import DocxLoader
from services.docx_output_service import DocxOutputService


# Standard utilities
from pathlib import Path
import atexit
from app.settings import AppConfig

def _resolve_path(p: str | Path, project_root: Path) -> Path:
    """
    Resolve a path string to an absolute path
    - Expands ~
    - If relative, resolve it against the project root.
    """
    pp = Path(p).expanduser()
    return pp if pp.is_absolute() else (project_root / pp).resolve()

def build_container(app_cfg: AppConfig):
    """
    Dependency container builder
    Responsibility
    - Takes a fully loaded config object
    - Constructs all the shared services exactly once
    - Wires dependencies together
    - Returns a dictionary of ready-to-use services
    """

    # Determine the project root (used for resolving relative paths)
    project_root = Path(__file__).resolve().parents[1]

    # ----- OCR config (kept independent from LLM config) -----
    ocr_model_path = None
    if app_cfg.ocr_config.ocr_gguf_path is not None:
        ocr_model_path = Path(app_cfg.ocr_config.ocr_gguf_path).expanduser().resolve()
    ocr_mmproj_path = None
    if app_cfg.ocr_config.ocr_mmproj_path is not None:
        ocr_mmproj_path = Path(app_cfg.ocr_config.ocr_mmproj_path).expanduser().resolve()

    # ----- Input layer -----
    loader = DocxLoader(
        strip_whitespace=True,
        keep_empty_paragraphs=False
    )

    docx_out = DocxOutputService(
        author=app_cfg.run_config.author
    )

    # ----- GED BERT -----
    # Load the GED BERT model and wrap the grammar detector in a service abstraction
    ged_detector = GedBertDetector(model_name=app_cfg.ged_config.model_name)
    ged_service = GedService(detector=ged_detector)
    

    # ----- LLM Wiring (server mode) -----
    server_proc = None
    server_bin: Path | None = None
    client: OpenAICompatChatClient | None = None
    llm_service: LlmService | None = None
    if app_cfg.llm_server.llama_backend == "server":

        # Resolve llm-server binary path
        server_bin = _resolve_path(
            app_cfg.llm_server.llama_server_path,
            project_root
        )
        
        # Resolve llm gguf path
        model_path = None
        if app_cfg.llm_config.llama_gguf_path is not None:
            model_path = Path(
                app_cfg.llm_config.llama_gguf_path
            ).expanduser().resolve()

        # Resolve optional multimodel projection file
        mmproj_path = None
        if app_cfg.llm_config.llama_mmproj_path:
            mmproj_path = Path(
                app_cfg.llm_config.llama_mmproj_path
            ).expanduser().resolve()

        # Create the llm-server process wrapper
        server_proc = LlmServerProcess(
            server_cfg=app_cfg.llm_server,
            llm_cfg=app_cfg.llm_config,
        )

        # Start the llm server
        server_proc.start()

        # Ensure the server is stopped cleanly on program exit
        atexit.register(server_proc.stop)

        # ----- LLM Client -----
        client = OpenAICompatChatClient(
            server_url=app_cfg.llm_server.llama_server_url,
            model_name=app_cfg.llm_config.llama_model_alias,
            model_family=app_cfg.llm_config.llama_model_family,
            request_cfg=app_cfg.llm_request,
        )
        llm_service = LlmService(
            client=client,
            max_parallel=app_cfg.llm_server.llama_n_parallel,
        )

    # ----- Explainability Recorder -----
    explainability = ExplainabilityRecorder.new(
        run_cfg=app_cfg.run_config,
        ged_cfg=app_cfg.ged_config,
        llm_config=app_cfg.llm_config
    )

    explain_file_writer = ExplainabilityWriter(
        app_cfg.assessment_paths.explained_folder
    )

    return {
        "project_root": project_root,
        "loader": loader,
        "docx_out": docx_out,
        "ged": ged_service,
        "ocr_model_path": ocr_model_path,
        "ocr_mmproj_path": ocr_mmproj_path,
        "server_bin": server_bin,
        "server_proc": server_proc,
        "llm_client": client,
        "llm_service": llm_service,
        "explain": explainability,
        "explain_file_writer": explain_file_writer
    }
