from __future__ import annotations

from contextlib import redirect_stdout
import io
import signal
import sys
from typing import Any

from cli.runner import CliSession, RuntimeStageError
from cli.worker_protocol import (
    WorkerErrorEnvelope,
    WorkerRequest,
    WorkerResponse,
    decode_request,
    encode_response,
)


def _handle_request(
    session: CliSession,
    req: WorkerRequest,
) -> tuple[WorkerResponse, bool]:
    diagnostics: list[dict[str, str]] = []

    def _diag(stage: str, detail: str, _traceback_text: str) -> None:
        diagnostics.append({"stage": stage, "detail": detail})

    session.diagnostics_hook = _diag

    if req.method == "shutdown":
        try:
            session.stop_llm()
        finally:
            return (
                WorkerResponse(
                    id=req.id,
                    ok=True,
                    result={"message": "shutdown"},
                    diagnostics=diagnostics,
                ),
                True,
            )

    try:
        captured_stdout = io.StringIO()
        with redirect_stdout(captured_stdout):
            if req.method == "health":
                result: dict[str, Any] = {"status": "ok"}
            elif req.method == "llm-list":
                result = session.list_models()
            elif req.method == "llm-start":
                result = session.configure_llm_selection(req.params.get("model_key"))
            elif req.method == "ocr-start":
                result = session.configure_ocr_selection(req.params.get("model_key"))
            elif req.method == "llm-stop":
                result = {"stopped": session.stop_llm()}
            elif req.method == "llm-switch":
                model_key = req.params.get("model_key")
                if not isinstance(model_key, str) or not model_key.strip():
                    raise ValueError("model_key is required for llm-switch.")
                result = session.switch_llm(model_key)
            elif req.method == "llm-status":
                result = session.status()
            elif req.method == "topic-sentence":
                file_path = req.params.get("file")
                if not isinstance(file_path, str) or not file_path.strip():
                    raise ValueError("file is required for topic-sentence.")
                max_concurrency = req.params.get("max_concurrency")
                if max_concurrency is not None and not isinstance(max_concurrency, int):
                    raise ValueError("max_concurrency must be int when provided.")
                json_out = req.params.get("json_out")
                if json_out is not None and not isinstance(json_out, str):
                    raise ValueError("json_out must be string when provided.")
                result = session.run_topic_sentence(
                    file_path,
                    max_concurrency=max_concurrency,
                    json_out=json_out,
                )
            else:
                raise ValueError(f"Unknown method: {req.method}")

        leaked_stdout = captured_stdout.getvalue().strip()
        if leaked_stdout:
            diagnostics.append({"stage": "worker_stdout", "detail": "captured non-protocol stdout"})
            print(f"[worker-stdout] {leaked_stdout}", file=sys.stderr, flush=True)

        return (WorkerResponse(id=req.id, ok=True, result=result, diagnostics=diagnostics), False)
    except RuntimeStageError as exc:
        return (
            WorkerResponse(
                id=req.id,
                ok=False,
                error=WorkerErrorEnvelope(
                    code="runtime_stage_error",
                    message=exc.detail,
                    stage=exc.stage,
                    traceback=exc.traceback_text,
                ),
                diagnostics=diagnostics,
            ),
            False,
        )
    except ValueError as exc:
        return (
            WorkerResponse(
                id=req.id,
                ok=False,
                error=WorkerErrorEnvelope(
                    code="validation_error",
                    message=str(exc),
                ),
                diagnostics=diagnostics,
            ),
            False,
        )
    except Exception as exc:
        return (
            WorkerResponse(
                id=req.id,
                ok=False,
                error=WorkerErrorEnvelope(
                    code="internal_error",
                    message=str(exc),
                ),
                diagnostics=diagnostics,
            ),
            False,
        )


def main() -> int:
    session = CliSession()
    running = True

    def _stop(_signum: int, _frame: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    while running:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            req = decode_request(line)
            resp, should_stop = _handle_request(session, req)
            if should_stop:
                running = False
        except Exception as exc:
            resp = WorkerResponse(
                id=-1,
                ok=False,
                error=WorkerErrorEnvelope(
                    code="protocol_error",
                    message=str(exc),
                ),
                diagnostics=[],
            )
        sys.stdout.write(encode_response(resp) + "\n")
        sys.stdout.flush()

    session.stop_llm()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
