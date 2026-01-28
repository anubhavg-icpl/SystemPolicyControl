"""Minimal HTTP API surface that shells out to the Swift agent binary."""
from __future__ import annotations

import json
import os
import subprocess
from http import HTTPStatus
from pathlib import Path
from typing import Callable
from wsgiref.simple_server import make_server

from common.models import SystemPolicy
from common.state import PolicyStateStore

AGENT_BIN = Path(os.environ.get("SPC_AGENT_PATH", "bin/system-policy-agent"))
STATE_PATH = Path(os.environ.get("SPC_STATE_PATH", "data/policy_state.json"))
PROFILE_DIR = Path(os.environ.get("SPC_PROFILE_DIR", "data/profiles"))

_store = PolicyStateStore(STATE_PATH)

ResponseBody = list[bytes]
StartResponse = Callable[[str, list[tuple[str, str]]], None]


def _json_response(status: HTTPStatus, payload: dict) -> tuple[str, list[tuple[str, str]], ResponseBody]:
    body = json.dumps(payload).encode("utf-8")
    headers = [
        ("Content-Type", "application/json"),
        ("Content-Length", str(len(body))),
    ]
    return f"{status.value} {status.phrase}", headers, [body]


def _read_body(environ) -> dict:
    length = int(environ.get("CONTENT_LENGTH") or 0)
    raw = environ["wsgi.input"].read(length) if length else b""
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def _agent_args(policy: SystemPolicy, install: bool) -> list[str]:
    args = [
        str(AGENT_BIN),
        "apply",
        "--profile-dir",
        str(PROFILE_DIR),
        "--state-path",
        str(STATE_PATH),
        "--profile-identifier",
        policy.profile_identifier,
        "--display-name",
        policy.display_name,
        "--organization",
        policy.organization,
        "--allow-identified-developers",
        str(policy.allow_identified_developers).lower(),
        "--enable-assessment",
        str(policy.enable_assessment).lower(),
        "--enable-xprotect-malware-upload",
        str(policy.enable_xprotect_malware_upload).lower(),
    ]
    if policy.description:
        args.extend(["--description", policy.description])
    if not install:
        args.append("--no-install")
    return args


def _ensure_agent_binary() -> bool:
    return AGENT_BIN.exists() and AGENT_BIN.is_file()


def application(environ, start_response: StartResponse) -> ResponseBody:
    path = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "GET").upper()

    if path == "/healthz" and method == "GET":
        status, headers, body = _json_response(HTTPStatus.OK, {"status": "ok"})
        start_response(status, headers)
        return body

    if path == "/policy":
        if method == "GET":
            state = _store.load()
            if not state:
                status, headers, body = _json_response(
                    HTTPStatus.NOT_FOUND, {"error": "policy_not_found"}
                )
                start_response(status, headers)
                return body
            status, headers, body = _json_response(HTTPStatus.OK, state.to_dict())
            start_response(status, headers)
            return body
        if method == "POST":
            if not _ensure_agent_binary():
                status, headers, body = _json_response(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {"error": "agent_binary_missing", "path": str(AGENT_BIN)},
                )
                start_response(status, headers)
                return body
            payload = _read_body(environ)
            install = bool(payload.pop("install", True))
            policy = SystemPolicy.from_dict(payload)
            args = _agent_args(policy, install)
            result = subprocess.run(args, capture_output=True, text=True)
            if result.returncode != 0:
                status, headers, body = _json_response(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {
                        "error": "agent_failed",
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    },
                )
                start_response(status, headers)
                return body
            state = _store.load()
            if not state:
                status, headers, body = _json_response(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"error": "state_unavailable"},
                )
                start_response(status, headers)
                return body
            status, headers, body = _json_response(HTTPStatus.CREATED, state.to_dict())
            start_response(status, headers)
            return body

    status, headers, body = _json_response(HTTPStatus.NOT_FOUND, {"error": "not_found"})
    start_response(status, headers)
    return body


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    with make_server(host, port, application) as httpd:
        print(f"SystemPolicyControl API running on http://{host}:{port}")
        httpd.serve_forever()


if __name__ == "__main__":
    host = os.environ.get("SPC_API_HOST", "127.0.0.1")
    port = int(os.environ.get("SPC_API_PORT", "8000"))
    run_server(host, port)
