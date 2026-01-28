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


def _agent_args(
    agent_bin: Path, policy: SystemPolicy, install: bool, profile_dir: Path, state_path: Path
) -> list[str]:
    args = [
        str(agent_bin),
        "apply",
        "--profile-dir",
        str(profile_dir),
        "--state-path",
        str(state_path),
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


def _remove_args(agent_bin: Path, identifier: str, profile_dir: Path, state_path: Path) -> list[str]:
    args = [
        str(agent_bin),
        "remove",
        identifier,
        "--profile-dir",
        str(profile_dir),
        "--state-path",
        str(state_path),
    ]
    return args


def _list_args(agent_bin: Path) -> list[str]:
    args = [str(agent_bin), "list"]
    return args


def application(environ, start_response: StartResponse) -> ResponseBody:
    path = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "GET").upper()

    # Re-read environment variables for each request to support testing
    agent_bin = Path(os.environ.get("SPC_AGENT_PATH", "bin/system-policy-agent"))
    state_path = Path(os.environ.get("SPC_STATE_PATH", "data/policy_state.json"))
    profile_dir = Path(os.environ.get("SPC_PROFILE_DIR", "data/profiles"))

    store = PolicyStateStore(state_path)

    if path == "/healthz" and method == "GET":
        status, headers, body = _json_response(HTTPStatus.OK, {"status": "ok"})
        start_response(status, headers)
        return body

    if path == "/policies" and method == "GET":
        if not agent_bin.exists() or not agent_bin.is_file():
            status, headers, body = _json_response(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {"error": "agent_binary_missing", "path": str(agent_bin)},
            )
            start_response(status, headers)
            return body
        args = _list_args(agent_bin)
        result = subprocess.run(args, capture_output=True, text=True)
        if result.returncode != 0:
            status, headers, body = _json_response(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "agent_failed", "stderr": result.stderr},
            )
            start_response(status, headers)
            return body
        try:
            policies = json.loads(result.stdout)
        except json.JSONDecodeError:
            policies = []
        status, headers, body = _json_response(HTTPStatus.OK, {"policies": policies})
        start_response(status, headers)
        return body

    if path == "/policy":
        if method == "GET":
            state = store.load()
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
            if not agent_bin.exists() or not agent_bin.is_file():
                status, headers, body = _json_response(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {"error": "agent_binary_missing", "path": str(agent_bin)},
                )
                start_response(status, headers)
                return body
            payload = _read_body(environ)
            install = bool(payload.pop("install", True))
            policy = SystemPolicy.from_dict(payload)
            args = _agent_args(agent_bin, policy, install, profile_dir, state_path)
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
            state = store.load()
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

        if method == "PUT":
            if not agent_bin.exists() or not agent_bin.is_file():
                status, headers, body = _json_response(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {"error": "agent_binary_missing", "path": str(agent_bin)},
                )
                start_response(status, headers)
                return body
            payload = _read_body(environ)
            install = bool(payload.pop("install", True))
            policy = SystemPolicy.from_dict(payload)
            args = _agent_args(agent_bin, policy, install, profile_dir, state_path)
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
            state = store.load()
            if not state:
                status, headers, body = _json_response(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"error": "state_unavailable"},
                )
                start_response(status, headers)
                return body
            status, headers, body = _json_response(HTTPStatus.OK, state.to_dict())
            start_response(status, headers)
            return body

        if method == "DELETE":
            if not agent_bin.exists() or not agent_bin.is_file():
                status, headers, body = _json_response(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {"error": "agent_binary_missing", "path": str(agent_bin)},
                )
                start_response(status, headers)
                return body
            state = store.load()
            if not state:
                status, headers, body = _json_response(
                    HTTPStatus.NOT_FOUND,
                    {"error": "policy_not_found"},
                )
                start_response(status, headers)
                return body
            identifier = state.policy.profile_identifier
            args = _remove_args(agent_bin, identifier, profile_dir, state_path)
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
            status, headers, body = _json_response(HTTPStatus.OK, {"message": "Policy removed"})
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
