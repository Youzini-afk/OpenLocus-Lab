#!/usr/bin/env python3
"""R31 real embedding provider safety smoke.

This smoke uses a local OpenAI-compatible HTTP server, not a vendor endpoint.
It proves the real-provider path can be wired without leaking raw inputs or
secrets and without changing EvidenceCore semantics.

It intentionally does not make quality claims, does not read labels, and does
not promote any strategy.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import http.server
import json
import os
import socketserver
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "r31-real-embedding-provider-smoke-v1"
CANARY_KEY = "r31-local-canary-key-do-not-leak"
CANARY_QUERY = "r31 canary query should not appear in audit"
CANARY_CODE = "r31 canary code should not appear in audit"
MODEL_ID = "r31-local-openai-compatible-smoke"
DIMENSIONS = 8


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


class EmbeddingHandler(http.server.BaseHTTPRequestHandler):
    request_count = 0
    bad_paths: list[str] = []
    bad_auth = 0
    seen_inputs_sha256: list[str] = []

    def log_message(self, format: str, *_args: Any) -> None:  # no request logs
        _ = format
        return

    def do_POST(self) -> None:  # noqa: N802
        type(self).request_count += 1
        if self.path != "/v1/embeddings":
            type(self).bad_paths.append(self.path)
            self.send_error(404)
            return
        if self.headers.get("Authorization") != f"Bearer {CANARY_KEY}":
            type(self).bad_auth += 1
            self.send_error(401)
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        payload = json.loads(body.decode("utf-8"))
        text = payload.get("input", "")
        dims = int(payload.get("dimensions") or DIMENSIONS)
        type(self).seen_inputs_sha256.append(hashlib.sha256(text.encode("utf-8")).hexdigest())
        embedding = deterministic_embedding(text, dims)
        response = {
            "object": "list",
            "model": payload.get("model", MODEL_ID),
            "data": [{"object": "embedding", "index": 0, "embedding": embedding}],
            "usage": {"prompt_tokens": 0, "total_tokens": 0},
        }
        encoded = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def deterministic_embedding(text: str, dims: int) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    for i in range(dims):
        b = digest[i % len(digest)]
        values.append((float(b) / 127.5) - 1.0)
    return values


@contextlib.contextmanager
def local_embedding_server():
    EmbeddingHandler.request_count = 0
    EmbeddingHandler.bad_paths = []
    EmbeddingHandler.bad_auth = 0
    EmbeddingHandler.seen_inputs_sha256 = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), EmbeddingHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", EmbeddingHandler
    finally:
        server.shutdown()
        thread.join(timeout=5)


@dataclass
class CmdResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    def json(self) -> dict[str, Any]:
        return json.loads(self.stdout)


def run_cmd(cmd: list[str], cwd: Path, env: dict[str, str], timeout: int = 60) -> CmdResult:
    completed = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    return CmdResult(cmd, completed.returncode, completed.stdout, completed.stderr)


def sanitized_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("OPENLOCUS_EMBEDDING_") or key == "OPENLOCUS_ALLOW_REMOTE":
            env.pop(key, None)
    return env


def write_test_repo(root: Path) -> None:
    (root / ".openlocus").mkdir(parents=True, exist_ok=True)
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "lib.rs").write_text(
        "pub fn alpha_lookup() -> usize {\n"
        "    // canary is only in source and must not appear in audit artifacts\n"
        f"    let _ = \"{CANARY_CODE}\";\n"
        "    42\n"
        "}\n",
        encoding="utf-8",
    )
    (root / ".openlocus" / "policy.toml").write_text(
        """
[remote]
allow = true
allow_embedding = true
allowed_providers = ["openai-compatible"]
max_data_level = 1

[secrets]
scan_before_remote = true
block_on_match = true
redact = true
""".lstrip(),
        encoding="utf-8",
    )


def raw_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def scan_for_leaks(paths: list[Path], forbidden: list[str]) -> list[dict[str, str]]:
    leaks: list[dict[str, str]] = []
    for path in paths:
        text = raw_text(path)
        for token in forbidden:
            if token and token in text:
                leaks.append({"path": path.name, "token": token})
    return leaks


def build_report(openlocus: Path, out: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="openlocus-r31-smoke-") as tmp, local_embedding_server() as (base_url, handler):
        repo = Path(tmp)
        write_test_repo(repo)

        base_env = sanitized_env()
        status_default = run_cmd([str(openlocus), "provider", "status", "--json"], repo, base_env)
        deny_build = run_cmd(
            [str(openlocus), "dense", "build", "--provider", "openai-compatible", "--experimental", "--json"],
            repo,
            base_env,
        )

        remote_env = base_env | {
            "OPENLOCUS_ALLOW_REMOTE": "1",
            "OPENLOCUS_EMBEDDING_BASE_URL": base_url,
            "OPENLOCUS_EMBEDDING_API_KEY": CANARY_KEY,
            "OPENLOCUS_EMBEDDING_MODEL": MODEL_ID,
            "OPENLOCUS_EMBEDDING_DIMENSIONS": str(DIMENSIONS),
        }
        status_remote = run_cmd([str(openlocus), "provider", "status", "--json"], repo, remote_env)
        build = run_cmd(
            [str(openlocus), "dense", "build", "--provider", "openai-compatible", "--experimental", "--json"],
            repo,
            remote_env,
        )
        search = run_cmd(
            [str(openlocus), "dense", "search", CANARY_QUERY, "--provider", "openai-compatible", "--limit", "3", "--json"],
            repo,
            remote_env,
        )

        audit_path = repo / ".openlocus" / "audit" / "embeddings.jsonl"
        store_path = repo / ".openlocus" / "embeddings" / "vectors.jsonl"
        trace_dir = repo / ".openlocus" / "traces"
        trace_paths = sorted(trace_dir.glob("*.jsonl")) if trace_dir.exists() else []
        forbidden_tokens = [CANARY_KEY, base_url, CANARY_QUERY, CANARY_CODE]
        leak_scan = scan_for_leaks([audit_path, store_path, *trace_paths], forbidden_tokens)
        command_outputs = "\n".join(
            result.stdout + "\n" + result.stderr
            for result in [status_default, deny_build, status_remote, build, search]
        )
        for token in [CANARY_KEY, base_url, CANARY_QUERY]:
            if token and token in command_outputs:
                leak_scan.append({"path": "command_output", "token": token})

        build_json = build.json() if build.stdout.strip().startswith("{") else {}
        search_json = search.json() if search.stdout.strip().startswith("{") else {}
        status_default_json = status_default.json() if status_default.stdout.strip().startswith("{") else {}
        status_remote_json = status_remote.json() if status_remote.stdout.strip().startswith("{") else {}
        deny_json = deny_build.json() if deny_build.stdout.strip().startswith("{") else {}
        evidence = search_json.get("evidence", [])

        report = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "promotion_ready": False,
            "default_should_change": False,
            "not_promotion_evidence": True,
            "core_changes": False,
            "evidencecore_semantics_changed": False,
            "provider_protocol": "openai-compatible",
            "provider_status": {
                "default_supported_providers": status_default_json.get("supported_providers", []),
                "remote_supported_providers": status_remote_json.get("supported_providers", []),
                "remote_default": status_remote_json.get("remote_default"),
                "outbound_default": status_remote_json.get("outbound_default"),
            },
            "safety_gates": {
                "remote_denied_by_default": deny_json.get("success") is False,
                "openai_compatible_hidden_until_env_enabled": "openai-compatible" not in status_default_json.get("supported_providers", []),
                "openai_compatible_visible_when_env_enabled": "openai-compatible" in status_remote_json.get("supported_providers", []),
                "provider_build_success": build_json.get("success") is True,
                "provider_search_success": search_json.get("success") is True,
                "audit_file_exists": audit_path.exists(),
                "vector_store_exists": store_path.exists(),
                "audit_contains_no_raw_query": not any(item["token"] == CANARY_QUERY for item in leak_scan),
                "audit_contains_no_raw_code": not any(item["token"] == CANARY_CODE for item in leak_scan),
                "artifacts_contain_no_api_key": not any(item["token"] == CANARY_KEY for item in leak_scan),
                "artifacts_contain_no_base_url": not any(item["token"] == base_url for item in leak_scan),
                "evidence_materialized": bool(evidence),
                "citation_shape_present": bool(evidence)
                and all({"path", "start_line", "end_line", "content_sha"}.issubset(ev) for ev in evidence),
                "no_quality_claim": True,
            },
            "counts": {
                "server_embedding_requests": handler.request_count,
                "server_bad_paths": len(handler.bad_paths),
                "server_bad_auth": handler.bad_auth,
                "build_remote_calls": build_json.get("remote_calls", 0),
                "search_remote_calls": search_json.get("remote_calls", 0),
                "record_count": build_json.get("record_count", 0),
                "evidence_count": len(evidence),
                "leak_count": len(leak_scan),
            },
            "leak_scan": {
                "clean": not leak_scan,
                "violations": leak_scan,
                "scanned_artifacts": [
                    "audit",
                    "vector_store",
                    "trace_jsonl",
                    "command_stdout_stderr_for_key_url_query_only",
                ],
            },
            "notes": [
                "Smoke uses a local OpenAI-compatible server, not the user's configured provider.",
                "DenseReal remains candidate/supporting-only; this smoke is not quality or promotion evidence.",
            ],
        }

    failed = [key for key, passed in report["safety_gates"].items() if passed is not True]
    if failed:
        raise SystemExit("R31 provider smoke failed safety gates: " + ", ".join(failed))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def write_doc(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# R31 Real Embedding Provider Smoke",
        "",
        "R31 adds an OpenAI-compatible embedding provider scaffold and validates it with a local HTTP server. It does not call the user's real provider, does not read labels, does not change EvidenceCore, and does not promote DenseReal.",
        "",
        "## Safety Gates",
        "",
    ]
    for key, value in report["safety_gates"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend([
        "",
        "## Counts",
        "",
    ])
    for key, value in report["counts"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend([
        "",
        "## Decision",
        "",
        "- `promotion_ready=false`",
        "- `default_should_change=false`",
        "- DenseReal remains candidate/supporting-only.",
        "- No runtime artifact may contain raw query, raw code, provider URL, or API key.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openlocus", type=Path, default=Path("target/debug/openlocus"))
    parser.add_argument("--out", type=Path, default=Path("artifacts/r31/provider_smoke.json"))
    parser.add_argument("--doc", type=Path, default=Path("docs/en/r31-real-embedding-provider.md"))
    args = parser.parse_args(argv)

    openlocus = args.openlocus.resolve()
    if not openlocus.exists():
        print(f"ERROR: openlocus binary not found: {openlocus}", file=sys.stderr)
        sys.exit(1)

    report = build_report(openlocus, args.out)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    write_doc(report, args.doc)
    print(f"Wrote {args.out}")
    print(f"Wrote {args.doc}")


if __name__ == "__main__":
    main()
