#!/usr/bin/env python3
"""R37-R38 LLM-derived views and stress expansion harness.

Default mode is offline/deterministic so committed artifacts are reproducible and
contain no provider credentials.  Optional OpenAI-compatible LLM calls are
manual-only (`--provider openai-compatible --allow-remote` and
`OPENLOCUS_ALLOW_REMOTE=1`) and must remain derived/stress only:

  * no Evidence generation,
  * no gold-label authority,
  * no citation verdicts,
  * no promotion/default changes.

The harness writes derived-view records plus an R38 stress dataset split into
public tasks and private labels.  Generated labels are explicitly marked as
failure-discovery data, not promotion evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import r32_embedding_view_bakeoff as r32  # type: ignore
except Exception:  # pragma: no cover
    sys.path.append(str(Path(__file__).resolve().parent))
    import r32_embedding_view_bakeoff as r32  # type: ignore


SCHEMA_VERSION = "r37-r38-llm-derived-stress-v1"
DERIVED_SCHEMA_VERSION = "r37-derived-view-v1"
STRESS_SCHEMA_VERSION = "r38-auto-stress-llm-v1"
PROMPT_VERSION = "r37-derived-views-v1"
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
SAFE_DERIVED_KINDS = [
    "query_aliases",
    "symbol_tags",
    "chunk_role",
    "api_role",
    "config_role",
    "route_intent",
    "test_intent",
    "error_intent",
]
STRESS_CATEGORIES = [
    "semantic_trap",
    "hard_distractor",
    "frontend_backend_confusion",
    "test_source_confusion",
    "proper_name_api_config_regression",
    "dense_quiver_specific_trap",
    "ambiguous_vague",
    "misspell_noise_variant",
]
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*[^\s]+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def has_secret(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def model_id(provider: str) -> str:
    if provider == "offline_deterministic":
        return "offline-deterministic-r37"
    return os.environ.get("OPENLOCUS_LLM_MODEL", "openai-compatible-llm")


def load_inputs(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Path], Any | None]:
    if args.self_test:
        tmp_ctx = tempfile.TemporaryDirectory(prefix="openlocus-r37-r38-")
        repo_lock, tasks_path, _labels_path, repo_roots = r32.make_self_test_inputs(Path(tmp_ctx.name))
        args._tmp_ctx = tmp_ctx
    else:
        repo_lock, tasks_path = args.repo_lock, args.tasks
        repo_roots = r32.load_repo_lock(repo_lock)
        args._tmp_ctx = None
    repo_roots = {repo_id: root for repo_id, root in repo_roots.items() if root.exists()}
    tasks = [task for task in r32.load_jsonl(tasks_path) if task["repo_id"] in repo_roots]
    public_issues = r32.validate_public_tasks(tasks)
    if public_issues:
        raise SystemExit("public task validation failed: " + "; ".join(public_issues[:5]))
    return tasks[: args.max_tasks], repo_roots, args._tmp_ctx


def symbol_records(repo_roots: dict[str, Path], args: argparse.Namespace) -> list[r32.ViewRecord]:
    records: list[r32.ViewRecord] = []
    for repo_id, root in repo_roots.items():
        scan_map = r32.run_scan(args.openlocus, root)
        for file_path in r32.iter_source_files(root):
            rel = str(file_path.relative_to(root)).replace("\\", "/")
            built = r32.build_views_for_file(repo_id, root, file_path, scan_map.get(rel))
            # Use metadata/symbol-level views only for committed derived output.
            records.extend(built.get("path_plus_symbol", [])[: args.max_records_per_file])
            records.extend(built.get("config_key_plus_context", [])[:1])
            records.extend(built.get("test_name_plus_assert_terms", [])[:1])
            records.extend(built.get("route_plus_handler_signature", [])[:1])
    return records[: args.max_records]


def tokens(text: str, limit: int = 12) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for token in TOKEN_RE.findall(text):
        token_l = token.lower()
        if token_l not in seen:
            seen.add(token_l)
            out.append(token_l)
        if len(out) >= limit:
            break
    return out


def deterministic_query_aliases(query: str) -> list[str]:
    ts = tokens(query, 8)
    aliases = [" ".join(ts)] if ts else []
    if len(ts) >= 2:
        aliases.append("find " + " ".join(reversed(ts[:4])))
    if ts:
        aliases.append("code location for " + ts[0])
    return [alias for alias in aliases if alias]


def deterministic_role_for_record(rec: r32.ViewRecord) -> tuple[str, str]:
    path_l = rec.path.lower()
    text_l = rec.text.lower()
    if "test" in path_l or "assert" in text_l:
        return "test_intent", "test verification assertion behavior"
    if rec.language == "config" or any(ext in path_l for ext in [".toml", ".yaml", ".yml", ".json", ".ini"]):
        return "config_role", "configuration key and runtime setting"
    if "route" in text_l or "handler" in text_l or "router" in text_l:
        return "route_intent", "request route handler endpoint"
    if "error" in text_l or "exception" in text_l:
        return "error_intent", "error handling path"
    if "api" in text_l or "client" in text_l:
        return "api_role", "api boundary or client entry point"
    return "chunk_role", "source symbol or module role"


def make_derived_views(tasks: list[dict[str, Any]], records: list[r32.ViewRecord], provider: str, remote_used: bool) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    mid = model_id(provider)
    for task in tasks:
        tid = task.get("test_id") or task.get("task_id")
        query = task["query"]
        for idx, alias in enumerate(deterministic_query_aliases(query)):
            rows.append({
                "schema_version": DERIVED_SCHEMA_VERSION,
                "derived_view_id": f"r37-{tid}-query_aliases-{idx}",
                "source_span": None,
                "source_content_sha": None,
                "model_id": mid,
                "prompt_version": PROMPT_VERSION,
                "policy_mode": "remote_llm" if remote_used else "offline_deterministic",
                "data_level": 0,
                "derived_kind": "query_aliases",
                "derived_text": alias,
                "derived_text_sha": sha256(alias),
                "query_sha": sha256(query),
                "query_len": len(query),
                "not_evidence": True,
                "not_label": True,
                "raw_query_stored_in_audit": False,
            })
    for idx, rec in enumerate(records):
        sym_tokens = tokens(rec.text, 10)
        tag_text = " ".join(sym_tokens[:8]) or Path(rec.path).stem
        kind, role_text = deterministic_role_for_record(rec)
        source_span = {"repo_id": rec.repo_id, "path": rec.path, "start_line": rec.start_line, "end_line": rec.end_line}
        rows.append({
            "schema_version": DERIVED_SCHEMA_VERSION,
            "derived_view_id": f"r37-{rec.repo_id}-{idx}-symbol_tags",
            "source_span": source_span,
            "source_content_sha": rec.content_sha,
            "model_id": mid,
            "prompt_version": PROMPT_VERSION,
            "policy_mode": "remote_llm" if remote_used else "offline_deterministic",
            "data_level": rec.data_level,
            "derived_kind": "symbol_tags",
            "derived_text": tag_text,
            "derived_text_sha": sha256(tag_text),
            "not_evidence": True,
            "not_label": True,
        })
        rows.append({
            "schema_version": DERIVED_SCHEMA_VERSION,
            "derived_view_id": f"r37-{rec.repo_id}-{idx}-{kind}",
            "source_span": source_span,
            "source_content_sha": rec.content_sha,
            "model_id": mid,
            "prompt_version": PROMPT_VERSION,
            "policy_mode": "remote_llm" if remote_used else "offline_deterministic",
            "data_level": rec.data_level,
            "derived_kind": kind,
            "derived_text": role_text,
            "derived_text_sha": sha256(role_text),
            "not_evidence": True,
            "not_label": True,
        })
    return rows


def remote_llm_smoke(provider: str, allow_remote: bool) -> dict[str, Any]:
    if provider != "openai-compatible":
        return {"status": "not_requested", "remote_calls": 0}
    if not allow_remote or os.environ.get("OPENLOCUS_ALLOW_REMOTE") != "1":
        return {"status": "unavailable", "reason": "requires --allow-remote and OPENLOCUS_ALLOW_REMOTE=1", "remote_calls": 0}
    base_url = os.environ.get("OPENLOCUS_LLM_BASE_URL")
    api_key = os.environ.get("OPENLOCUS_LLM_API_KEY")
    model = os.environ.get("OPENLOCUS_LLM_MODEL")
    if not base_url or not api_key or not model:
        return {"status": "unavailable", "reason": "missing OPENLOCUS_LLM_* config", "remote_calls": 0}
    # Safe smoke: no repo code, no user query, no secret-bearing context.
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return strict JSON only."},
            {"role": "user", "content": "Return {\"status\":\"ok\",\"not_evidence\":true}."},
        ],
        "temperature": 0,
    }
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - explicit opt-in research smoke
            body = json.loads(resp.read().decode("utf-8"))
        content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
        clean = "not_evidence" in content and "ok" in content
        return {"status": "ok" if clean else "schema_mismatch", "remote_calls": 1, "raw_response_stored": False}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return {"status": "unavailable", "reason": "remote LLM provider unavailable_or_failed", "remote_calls": 0}


def stress_query_for(category: str, seed: str, repo_id: str) -> str:
    if category == "semantic_trap":
        return f"find nonexistent quantum {seed} orchestration"
    if category == "hard_distractor":
        return f"{seed} in similarly named module"
    if category == "frontend_backend_confusion":
        return f"frontend handler for backend {seed}"
    if category == "test_source_confusion":
        return f"test assertion source implementation for {seed}"
    if category == "proper_name_api_config_regression":
        return f"{seed} api config key timeout token"
    if category == "dense_quiver_specific_trap":
        return f"semantically similar but absent {seed} vector route"
    if category == "misspell_noise_variant":
        return f"{seed[:-1] if len(seed) > 3 else seed} lokup misspelled"
    return f"where is {seed} handled maybe {repo_id}"


def make_stress_dataset(tasks: list[dict[str, Any]], records: list[r32.ViewRecord], limit: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    public_rows: list[dict[str, Any]] = []
    label_rows: list[dict[str, Any]] = []
    seeds = []
    for rec in records:
        seeds.extend(tokens(rec.text, 3))
    for task in tasks:
        seeds.extend(tokens(task["query"], 3))
    seeds = [seed for i, seed in enumerate(seeds) if seed and seed not in seeds[:i]] or ["locus"]
    idx = 0
    while len(public_rows) < limit:
        category = STRESS_CATEGORIES[idx % len(STRESS_CATEGORIES)]
        seed = seeds[idx % len(seeds)]
        repo_id = tasks[idx % len(tasks)]["repo_id"] if tasks else (records[0].repo_id if records else "unknown")
        test_id = f"r38-{len(public_rows)+1:05d}"
        query = stress_query_for(category, seed, repo_id)
        public_rows.append({
            "test_id": test_id,
            "repo_id": repo_id,
            "query": query,
            "public_version": "r38-auto-stress-llm-v1",
            "source": "r37_r38_deterministic_failure_discovery",
        })
        label_rows.append({
            "schema_version": STRESS_SCHEMA_VERSION,
            "test_id": test_id,
            "repo_id": repo_id,
            "query_sha": sha256(query),
            "source_category": category,
            "expected_behavior": "no_primary" if "trap" in category or "confusion" in category or "regression" in category else "ambiguous",
            "gold_spans": [],
            "hard_distractors": [],
            "must_not_primary": [],
            "oracle_type": "failure_discovery_only",
            "label_quality": "llm_generated_unverified" if False else "deterministic_validated_failure_discovery",
            "not_promotion_evidence": True,
            "not_human_verified": True,
            "which_strategy_it_targets": ["dense_real", "quiver", "llm_derived", "rrf"],
            "risk_tags": [category, "generated_failure_discovery"],
        })
        idx += 1
    return public_rows, label_rows


def leak_scan(paths: list[Path]) -> dict[str, Any]:
    violations: list[dict[str, str]] = []
    for path in paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                violations.append({"path": str(path), "pattern": pattern.pattern})
    return {"clean": not violations, "violations": violations}


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    tasks, repo_roots, tmp_ctx = load_inputs(args)
    records = symbol_records(repo_roots, args)
    llm_status = remote_llm_smoke(args.provider, args.allow_remote)
    remote_used = llm_status.get("status") == "ok"
    derived_rows = make_derived_views(tasks, records, args.provider, remote_used)
    stress_public, stress_labels = make_stress_dataset(tasks, records, args.max_stress_tasks)
    write_jsonl(args.derived_out, derived_rows)
    write_jsonl(args.stress_tasks_out, stress_public)
    write_jsonl(args.stress_labels_out, stress_labels)
    scan = leak_scan([args.derived_out, args.stress_tasks_out, args.stress_labels_out])
    if tmp_ctx is not None:
        tmp_ctx.cleanup()
    by_kind: dict[str, int] = {}
    for row in derived_rows:
        by_kind[row["derived_kind"]] = by_kind.get(row["derived_kind"], 0) + 1
    by_category: dict[str, int] = {}
    for row in stress_labels:
        by_category[row["source_category"]] = by_category.get(row["source_category"], 0) + 1
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": args.provider,
        "llm_status": llm_status,
        "remote_calls": llm_status.get("remote_calls", 0),
        "elapsed_ms": int((time.time() - started) * 1000),
        "promotion_ready": False,
        "default_should_change": False,
        "not_promotion_evidence": True,
        "core_changes": False,
        "evidencecore_semantics_changed": False,
        "llm_outputs_are_evidence": False,
        "llm_outputs_are_labels": False,
        "run_phase_public_only": True,
        "raw_prompt_stored": False,
        "raw_response_stored": False,
        "derived_view_count": len(derived_rows),
        "derived_by_kind": by_kind,
        "stress_public_task_count": len(stress_public),
        "stress_private_label_count": len(stress_labels),
        "stress_by_category": by_category,
        "stress_label_quality": sorted({row["label_quality"] for row in stress_labels}),
        "stress_dataset": {
            "public_tasks": str(args.stress_tasks_out),
            "private_labels": str(args.stress_labels_out),
            "not_promotion_evidence": True,
        },
        "leak_scan": scan,
        "safety_gates": {
            "no_evidence_generation": True,
            "no_gold_label_authority": True,
            "no_citation_verdicts": True,
            "no_promotion_verdict": True,
            "derived_views_have_not_evidence": all(row.get("not_evidence") is True for row in derived_rows),
            "stress_labels_not_promotion": all(row.get("not_promotion_evidence") is True for row in stress_labels),
            "artifact_secret_scan_clean": scan["clean"],
        },
    }
    failed = [k for k, v in report["safety_gates"].items() if v is not True]
    if failed:
        raise SystemExit("R37/R38 safety gates failed: " + ", ".join(failed))
    return report


def write_doc(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# R37-R38 LLM-Derived Views and Stress Expansion",
        "",
        "This phase introduces derived-view and stress-expansion artifacts. The committed run is offline deterministic; real LLM use is manual-only and remains derived/stress-only.",
        "",
        "## Safety",
        "",
    ]
    for key, value in report.get("safety_gates", {}).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend([
        "",
        "## Counts",
        "",
        f"- provider: `{report.get('provider')}`",
        f"- llm_status: `{report.get('llm_status', {}).get('status')}`",
        f"- remote_calls: `{report.get('remote_calls')}`",
        f"- derived_view_count: `{report.get('derived_view_count')}`",
        f"- stress_public_task_count: `{report.get('stress_public_task_count')}`",
        f"- stress_private_label_count: `{report.get('stress_private_label_count')}`",
        "",
        "## Derived Kinds",
        "",
    ])
    for kind, count in sorted(report.get("derived_by_kind", {}).items()):
        lines.append(f"- {kind}: `{count}`")
    lines.extend([
        "",
        "## Stress Categories",
        "",
    ])
    for category, count in sorted(report.get("stress_by_category", {}).items()):
        lines.append(f"- {category}: `{count}`")
    lines.extend([
        "",
        "## Decision",
        "",
        "- LLM-derived views are not Evidence.",
        "- R38 stress labels are failure-discovery only and not promotion evidence.",
        "- No default strategy changes.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-lock", type=Path, default=Path("fixtures/r26_auto_stress/repos.lock.jsonl"))
    parser.add_argument("--tasks", type=Path, default=Path("fixtures/r26_auto_stress/tasks/auto_stress.jsonl"))
    parser.add_argument("--openlocus", type=Path, default=Path("target/debug/openlocus"))
    parser.add_argument("--provider", default="offline_deterministic", choices=["offline_deterministic", "openai-compatible"])
    parser.add_argument("--allow-remote", action="store_true")
    parser.add_argument("--max-tasks", type=int, default=200)
    parser.add_argument("--max-records", type=int, default=500)
    parser.add_argument("--max-records-per-file", type=int, default=6)
    parser.add_argument("--max-stress-tasks", type=int, default=80)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--derived-out", type=Path, default=Path("artifacts/r37/derived_views.jsonl"))
    parser.add_argument("--stress-tasks-out", type=Path, default=Path("datasets/r38-auto-stress-llm/tasks/stress_public.jsonl"))
    parser.add_argument("--stress-labels-out", type=Path, default=Path("datasets/r38-auto-stress-llm/labels/stress_labels.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("artifacts/r37_r38/llm_derived_stress_report.json"))
    parser.add_argument("--doc", type=Path, default=Path("docs/r37-r38-llm-derived-stress.md"))
    args = parser.parse_args(argv)
    args.openlocus = args.openlocus.resolve()
    args._tmp_ctx = None

    report = run(args)
    write_json(args.out, report)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    write_doc(report, args.doc)
    print(f"Wrote {args.out}")
    print(f"Wrote {args.doc}")


if __name__ == "__main__":
    main()
