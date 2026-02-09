# Import services


# Import llm server process
from nlp.llm.llm_server_process import LlmServerProcess
from nlp.llm.llm_client import OpenAICompatChatClient
from services.llm_service import LlmService


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
    print(project_root)
    

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

        # Ensure the server is stopped clearnly on program exit
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



    def _cleanup() -> None:
        # Placeholder for future server process cleanup.
        if server_proc is not None:
            return

    atexit.register(_cleanup)
    return {
        "project_root": project_root,
        "server_bin": server_bin,
        "server_proc": server_proc,
        "llm_client": client,
        "llm_service": llm_service,
    }
