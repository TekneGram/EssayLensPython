from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any


@dataclass(frozen=True)
class WorkerRequest:
    id: int
    method: str
    params: dict[str, Any]


@dataclass(frozen=True)
class WorkerErrorEnvelope:
    code: str
    message: str
    stage: str | None = None
    traceback: str | None = None


@dataclass(frozen=True)
class WorkerResponse:
    id: int
    ok: bool
    result: dict[str, Any] | None = None
    error: WorkerErrorEnvelope | None = None
    diagnostics: list[dict[str, str]] | None = None


def encode_request(req: WorkerRequest) -> str:
    payload = {
        "id": req.id,
        "method": req.method,
        "params": req.params,
    }
    return json.dumps(payload, ensure_ascii=True)


def decode_request(line: str) -> WorkerRequest:
    data = json.loads(line)
    if not isinstance(data, dict):
        raise ValueError("Request payload must be an object.")
    req_id = data.get("id")
    method = data.get("method")
    params = data.get("params", {})
    if not isinstance(req_id, int):
        raise ValueError("Request field 'id' must be int.")
    if not isinstance(method, str) or not method.strip():
        raise ValueError("Request field 'method' must be non-empty string.")
    if not isinstance(params, dict):
        raise ValueError("Request field 'params' must be an object.")
    return WorkerRequest(id=req_id, method=method, params=params)


def encode_response(resp: WorkerResponse) -> str:
    payload: dict[str, Any] = {
        "id": resp.id,
        "ok": resp.ok,
        "diagnostics": resp.diagnostics or [],
    }
    if resp.ok:
        payload["result"] = resp.result or {}
    else:
        payload["error"] = {
            "code": resp.error.code if resp.error else "internal_error",
            "message": resp.error.message if resp.error else "Unknown worker error",
            "stage": resp.error.stage if resp.error else None,
            "traceback": resp.error.traceback if resp.error else None,
        }
    return json.dumps(payload, ensure_ascii=True)


def decode_response(line: str) -> WorkerResponse:
    data = json.loads(line)
    if not isinstance(data, dict):
        raise ValueError("Response payload must be an object.")
    resp_id = data.get("id")
    ok = data.get("ok")
    diagnostics = data.get("diagnostics")
    if not isinstance(resp_id, int):
        raise ValueError("Response field 'id' must be int.")
    if not isinstance(ok, bool):
        raise ValueError("Response field 'ok' must be bool.")
    if diagnostics is None:
        diagnostics = []
    if not isinstance(diagnostics, list):
        raise ValueError("Response field 'diagnostics' must be list.")

    if ok:
        result = data.get("result", {})
        if not isinstance(result, dict):
            raise ValueError("Response field 'result' must be object when ok=true.")
        return WorkerResponse(id=resp_id, ok=True, result=result, diagnostics=diagnostics)

    err = data.get("error", {})
    if not isinstance(err, dict):
        raise ValueError("Response field 'error' must be object when ok=false.")
    code = err.get("code", "internal_error")
    message = err.get("message", "Unknown worker error")
    stage = err.get("stage")
    traceback_text = err.get("traceback")
    if not isinstance(code, str):
        code = "internal_error"
    if not isinstance(message, str):
        message = "Unknown worker error"
    if stage is not None and not isinstance(stage, str):
        stage = None
    if traceback_text is not None and not isinstance(traceback_text, str):
        traceback_text = None
    return WorkerResponse(
        id=resp_id,
        ok=False,
        error=WorkerErrorEnvelope(code=code, message=message, stage=stage, traceback=traceback_text),
        diagnostics=diagnostics,
    )

