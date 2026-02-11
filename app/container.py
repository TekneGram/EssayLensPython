# Import services and processes
import shutil
from nlp.llm.llm_server_process import LlmServerProcess
from nlp.llm.llm_client import OpenAICompatChatClient
from nlp.ocr.ocr_server_process import OcrServerProcess
from nlp.ocr.ocr_client import OcrClient
from services.llm_service import LlmService
from services.ocr_service import OcrService
from services.explainability import ExplainabilityRecorder
from inout.explainability_writer import ExplainabilityWriter
from services.ged_service import GedService
from nlp.ged.ged_bert import GedBertDetector
from inout.docx_loader import DocxLoader
from inout.pdf_loader import PdfLoader
from services.docx_output_service import DocxOutputService
from services.document_input_service import DocumentInputService
from services.input_discovery_service import InputDiscoveryService
from services.power_sampler import NullPowerSampler, PowermetricsPowerSampler
from services.sustainability_service import Sustainability
from config.ocr_request_config import OcrRequestConfig


# Standard utilities
from pathlib import Path
from app.settings import AppConfig

def _resolve_path(p: str | Path, project_root: Path) -> Path:
    """
    Resolve a path string to an absolute path
    - Expands ~
    - If relative, resolve it against the project root.
    """
    pp = Path(p).expanduser()
    return pp if pp.is_absolute() else (project_root / pp).resolve()


def _build_power_sampler(app_cfg: AppConfig):
    cfg = app_cfg.sustainability_config
    if not cfg.enabled or cfg.power_backend == "none":
        return NullPowerSampler()

    command_exists = shutil.which(cfg.powermetrics_command) is not None
    if not command_exists:
        sampler = NullPowerSampler()
        sampler.add_diagnostic(
            f"powermetrics command not found: {cfg.powermetrics_command}"
        )
        return sampler

    return PowermetricsPowerSampler(
        command=cfg.powermetrics_command,
        sample_interval_s=cfg.sample_interval_s,
    )

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

    # ----- Input layer -----
    docx_loader = DocxLoader(
        strip_whitespace=True,
        keep_empty_paragraphs=False
    )
    pdf_loader = PdfLoader(
        strip_whitespace=False,
        keep_empty_pages=True,
    )
    document_input_service = DocumentInputService(
        docx_loader=docx_loader,
        pdf_loader=pdf_loader,
    )
    input_discovery_service = InputDiscoveryService(
        input_root=app_cfg.assessment_paths.input_folder,
        output_root=app_cfg.assessment_paths.output_folder,
        explainability_root=app_cfg.assessment_paths.explained_folder
    )

    docx_out_service = DocxOutputService(
        author=app_cfg.run_config.author
    )

    # ----- GED BERT -----
    # Load the GED BERT model and wrap the grammar detector in a service abstraction
    ged_detector = GedBertDetector(model_name=app_cfg.ged_config.model_name)
    ged_service = GedService(detector=ged_detector)
    

    # ----- OCR Wiring (server mode) -----
    ocr_server_proc: OcrServerProcess | None = None
    ocr_client: OcrClient | None = None
    ocr_service: OcrService | None = None
    if app_cfg.llm_server.llama_backend == "server":
        ocr_server_proc = OcrServerProcess(
            server_cfg=app_cfg.llm_server,
            ocr_cfg=app_cfg.ocr_config,
        )
        ocr_request_cfg = OcrRequestConfig.from_values()
        ocr_client = OcrClient(
            server_url=app_cfg.llm_server.llama_server_url,
            model_name=app_cfg.ocr_config.ocr_model_alias,
            request_cfg=ocr_request_cfg,
        )
        ocr_service = OcrService(client=ocr_client)

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

    sustainability = Sustainability(
        cfg=app_cfg.sustainability_config,
        sampler=_build_power_sampler(app_cfg),
    )

    return {
        "project_root": project_root,
        "input_discovery_service": input_discovery_service,
        "document_input_service": document_input_service,
        "docx_out_service": docx_out_service,
        "ged": ged_service,
        "ocr_server_proc": ocr_server_proc,
        "ocr_service": ocr_service,
        "server_bin": server_bin,
        "server_proc": server_proc,
        "llm_client": client,
        "llm_service": llm_service,
        "explain": explainability,
        "explain_file_writer": explain_file_writer,
        "sustainability": sustainability,
    }
