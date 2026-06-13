#!/usr/bin/env python3
"""R39-R40 symbol extraction and regex normalization repair bakeoff.

This harness evaluates repair ideas without changing default retrieval paths:

R39 symbol extraction repair:
  * old extractor: the current R32 regex symbol subset,
  * new extractor: extra impl/trait/decorator/arrow/export/method patterns.

R40 regex normalization repair:
  * raw regex,
  * escaped literal,
  * tokenized AND-style literal matching,
  * identifier mode,
  * path mode,
  * hybrid normalized mode.

The committed run is an offline self-test.  It emits no promotion decision and
does not alter EvidenceCore or default CLI behavior.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

try:
    import r32_embedding_view_bakeoff as r32  # type: ignore
except Exception:  # pragma: no cover
    sys.path.append(str(Path(__file__).resolve().parent))
    import r32_embedding_view_bakeoff as r32  # type: ignore


SCHEMA_VERSION = "r39-r40-symbol-regex-repair-v1"
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[A-Za-z0-9_.:/{}\[\]()-]+")


NEW_SYMBOL_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("rust", re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?impl(?:<[^>]+>)?\s+([A-Za-z_][\w:]*)", re.M), "impl"),
    ("rust", re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+(\w+)", re.M), "function"),
    ("rust", re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:struct|enum|trait|mod)\s+(\w+)", re.M), "type"),
    ("python", re.compile(r"^\s*@([A-Za-z_][\w.]+)", re.M), "decorator"),
    ("python", re.compile(r"^\s*(?:async\s+def|def)\s+(\w+)", re.M), "function"),
    ("python", re.compile(r"^\s*class\s+(\w+)", re.M), "class"),
    ("go", re.compile(r"^func\s+(?:\([^)]*\)\s+)?(\w+)", re.M), "function"),
    ("go", re.compile(r"^type\s+(\w+)\s+(?:struct|interface)", re.M), "type"),
    ("go", re.compile(r"^const\s+(?:\(\s*)?(\w+)", re.M), "const"),
    ("javascript", re.compile(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)", re.M), "function"),
    ("javascript", re.compile(r"(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>", re.M), "arrow_function"),
    ("javascript", re.compile(r"(?:export\s+default\s+)?(?:function\s+)?([A-Z][A-Za-z0-9_]*)\s*=\s*\(", re.M), "component"),
    ("javascript", re.compile(r"(?:export\s+)?(?:default\s+)?class\s+(\w+)", re.M), "class"),
    ("typescript", re.compile(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)", re.M), "function"),
    ("typescript", re.compile(r"(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>", re.M), "arrow_function"),
    ("typescript", re.compile(r"(?:export\s+)?(?:interface|type|class|enum)\s+(\w+)", re.M), "type"),
]


@dataclass
class SourceFile:
    repo_id: str
    path: str
    text: str
    lines: list[str]
    language: str
    content_sha: str


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_inputs(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Path], Any | None]:
    if args.self_test:
        tmp_ctx = tempfile.TemporaryDirectory(prefix="openlocus-r39-r40-")
        repo = Path(tmp_ctx.name) / "repair-repo"
        (repo / "src").mkdir(parents=True)
        (repo / "tests").mkdir(parents=True)
        (repo / "src" / "lib.rs").write_text(
            "pub(crate) struct AlphaThing;\n"
            "impl AlphaThing {\n"
            "    pub async fn handle_route_param(user_id: &str) -> usize { 1 }\n"
            "}\n"
            "fn regex_special_path() { let _ = \"/api/users/{id}\"; }\n",
            encoding="utf-8",
        )
        (repo / "src" / "app.tsx").write_text(
            "export const UserCard = ({id}) => <div>{id}</div>;\n"
            "export async function fetchUser(id: string) { return id }\n"
            "router.get('/api/users/:id', fetchUser)\n",
            encoding="utf-8",
        )
        (repo / "tests" / "test_app.py").write_text(
            "@pytest.fixture\n"
            "def alpha_fixture():\n"
            "    return 'alpha'\n"
            "async def test_handle_route_param():\n"
            "    assert alpha_fixture() == 'alpha'\n",
            encoding="utf-8",
        )
        tasks_path = Path(tmp_ctx.name) / "tasks.jsonl"
        rows = [
            {"test_id": "r39-001", "repo_id": "repair", "query": "handle_route_param", "public_version": "r39", "source": "self_test"},
            {"test_id": "r39-002", "repo_id": "repair", "query": "UserCard", "public_version": "r39", "source": "self_test"},
            {"test_id": "r40-001", "repo_id": "repair", "query": "/api/users/{id}", "public_version": "r40", "source": "self_test"},
            {"test_id": "r40-002", "repo_id": "repair", "query": "router.get('/api/users/:id')", "public_version": "r40", "source": "self_test"},
            {"test_id": "r40-003", "repo_id": "repair", "query": "AlphaThing::handle_route_param", "public_version": "r40", "source": "self_test"},
        ]
        tasks_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        args._tmp_ctx = tmp_ctx
        return rows, {"repair": repo}, tmp_ctx
    repo_roots = r32.load_repo_lock(args.repo_lock)
    tasks = [task for task in r32.load_jsonl(args.tasks) if task["repo_id"] in repo_roots][: args.max_tasks]
    args._tmp_ctx = None
    return tasks, repo_roots, None


def source_files(repo_roots: dict[str, Path], args: argparse.Namespace) -> list[SourceFile]:
    files: list[SourceFile] = []
    for repo_id, root in repo_roots.items():
        scan_map = r32.run_scan(args.openlocus, root)
        for path in r32.iter_source_files(root):
            rel = str(path.relative_to(root)).replace("\\", "/")
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            scan = scan_map.get(rel, {})
            files.append(SourceFile(repo_id, rel, text, text.splitlines(), scan.get("language") or r32.ext_to_language(rel), scan.get("content_sha") or r32.fallback_file_sha(path)))
            if len(files) >= args.max_files:
                return files
    return files


def line_no(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def old_symbols(file: SourceFile) -> list[dict[str, Any]]:
    out = []
    for sym in r32.extract_symbols(Path(file.path), file.path, file.language, file.text):
        out.append({"name": sym["name"], "kind": sym["kind"], "line": sym["line"], "path": file.path})
    return out


def new_symbols(file: SourceFile) -> list[dict[str, Any]]:
    old = old_symbols(file)
    seen = {(s["name"], s["line"], s["kind"]) for s in old}
    out = list(old)
    language_aliases = {file.language}
    if file.language == "typescript":
        language_aliases.add("javascript")
    for lang, pattern, kind in NEW_SYMBOL_PATTERNS:
        if lang not in language_aliases:
            continue
        for m in pattern.finditer(file.text):
            name = m.group(1)
            line = line_no(file.text, m.start())
            key = (name, line, kind)
            if key not in seen:
                seen.add(key)
                out.append({"name": name, "kind": kind, "line": line, "path": file.path})
    return sorted(out, key=lambda item: (item["path"], item["line"], item["name"]))


def evidence_from_symbol(file: SourceFile, symbol: dict[str, Any], strategy: str) -> dict[str, Any]:
    line = int(symbol["line"])
    return {
        "path": file.path,
        "start_line": line,
        "end_line": min(len(file.lines), line + 2),
        "content_sha": file.content_sha,
        "score": 1.0,
        "why": [strategy, f"symbol:{symbol['name']}", "candidate_not_fact"],
        "channels": ["symbol"],
    }


def symbol_strategy(tasks: list[dict[str, Any]], files: list[SourceFile], extractor: Callable[[SourceFile], list[dict[str, Any]]], name: str) -> list[dict[str, Any]]:
    by_repo = {repo_id: [f for f in files if f.repo_id == repo_id] for repo_id in {f.repo_id for f in files}}
    preds = []
    for task in tasks:
        query_tokens = {tok.lower() for tok in TOKEN_RE.findall(task["query"]) if len(tok) > 2}
        evidence = []
        for file in by_repo.get(task["repo_id"], []):
            for sym in extractor(file):
                if sym["name"].lower() in query_tokens or any(tok in sym["name"].lower() for tok in query_tokens):
                    evidence.append(evidence_from_symbol(file, sym, name))
        preds.append({"task_id": task.get("test_id") or task.get("task_id"), "repo_id": task["repo_id"], "strategy": name, "evidence": evidence[:10], "latency_ms": 0, "returncode": 0})
    return preds


def compile_pattern(query: str, mode: str) -> re.Pattern[str] | None:
    try:
        if mode == "regex_raw":
            return re.compile(query, re.I)
        if mode == "regex_escaped_literal":
            return re.compile(re.escape(query), re.I)
        if mode == "regex_tokenized":
            toks = [re.escape(t) for t in TOKEN_RE.findall(query) if len(t) > 1]
            return re.compile(".*".join(toks), re.I) if toks else None
        if mode == "regex_identifier_mode":
            toks = [re.escape(t) for t in TOKEN_RE.findall(query) if re.match(r"[A-Za-z_]", t)]
            return re.compile(r"\b(" + "|".join(toks) + r")\b", re.I) if toks else None
        if mode == "regex_path_mode":
            simplified = query.replace("\\", "/")
            return re.compile(re.escape(simplified), re.I)
        if mode == "regex_hybrid_normalized":
            toks = [re.escape(t.strip("'\"`")) for t in TOKEN_RE.findall(query.replace("::", " ")) if len(t.strip("'\"`")) > 1]
            return re.compile("|".join(toks), re.I) if toks else re.compile(re.escape(query), re.I)
    except re.error:
        return None
    return None


def regex_strategy(tasks: list[dict[str, Any]], files: list[SourceFile], mode: str) -> tuple[list[dict[str, Any]], int]:
    parse_errors = 0
    preds = []
    by_repo = {repo_id: [f for f in files if f.repo_id == repo_id] for repo_id in {f.repo_id for f in files}}
    for task in tasks:
        pattern = compile_pattern(task["query"], mode)
        if pattern is None:
            parse_errors += 1
            preds.append({"task_id": task.get("test_id") or task.get("task_id"), "repo_id": task["repo_id"], "strategy": mode, "evidence": [], "latency_ms": 0, "returncode": 0})
            continue
        evidence = []
        for file in by_repo.get(task["repo_id"], []):
            haystacks = [(file.path, 1)] + [(line, i + 1) for i, line in enumerate(file.lines)]
            for text, line in haystacks:
                if pattern.search(text):
                    evidence.append({"path": file.path, "start_line": line, "end_line": line, "content_sha": file.content_sha, "score": 1.0, "why": [mode, "candidate_not_fact"], "channels": ["regex"]})
                    break
        preds.append({"task_id": task.get("test_id") or task.get("task_id"), "repo_id": task["repo_id"], "strategy": mode, "evidence": evidence[:10], "latency_ms": 0, "returncode": 0})
    return preds, parse_errors


def synthetic_labels(tasks: list[dict[str, Any]], files: list[SourceFile]) -> dict[str, dict[str, Any]]:
    labels: dict[str, dict[str, Any]] = {}
    for task in tasks:
        tid = task.get("test_id") or task.get("task_id")
        if not tid:
            continue
        query_l = task["query"].lower()
        spans = []
        for file in files:
            if file.repo_id != task["repo_id"]:
                continue
            for i, line in enumerate(file.lines, 1):
                if any(tok.lower().strip("'\"`") in line.lower() or tok.lower().strip("'\"`") in file.path.lower() for tok in TOKEN_RE.findall(task["query"]) if len(tok) > 2):
                    spans.append({"path": file.path, "start_line": i, "end_line": i})
                    break
            if spans:
                break
        labels[tid] = {"task_id": tid, "gold_spans": spans, "gold_paths": [s["path"] for s in spans], "gold_lines": [[s["start_line"], s["end_line"]] for s in spans], "expected_behavior": "primary_evidence" if spans else "no_primary"}
    return labels


def metrics(preds: list[dict[str, Any]], labels: dict[str, dict[str, Any]], parse_errors: int = 0) -> dict[str, Any]:
    task_count = len(preds)
    return {
        "task_count": task_count,
        "FileRecall@1": r32.score_mod.file_recall_at_k(preds, labels, 1),
        "FileRecall@5": r32.score_mod.file_recall_at_k(preds, labels, 5),
        "SpanF0.5": r32.score_mod.span_f_beta_at_k(preds, labels, 10, 0.5),
        "SpanPrecision": r32.score_mod.line_precision_at_k(preds, labels, 10),
        "SpanRecall": r32.score_mod.line_recall_at_k(preds, labels, 10),
        "parse_error_rate": parse_errors / task_count if task_count else 0.0,
        "primary_false_positive_rate": sum(1 for p in preds if p.get("evidence") and not labels.get(p["task_id"], {}).get("gold_spans")) / task_count if task_count else 0.0,
        "abstain_rate": sum(1 for p in preds if not p.get("evidence")) / task_count if task_count else 0.0,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    tasks, repo_roots, tmp_ctx = load_inputs(args)
    issues = r32.validate_public_tasks(tasks)
    if issues:
        raise SystemExit("public task validation failed: " + "; ".join(issues[:5]))
    files = source_files(repo_roots, args)
    labels = synthetic_labels(tasks, files)
    old_preds = symbol_strategy(tasks, files, old_symbols, "symbol_old")
    new_preds = symbol_strategy(tasks, files, new_symbols, "symbol_new")
    symbol_old = metrics(old_preds, labels)
    symbol_new = metrics(new_preds, labels)
    regex_results: dict[str, Any] = {}
    for mode in ["regex_raw", "regex_escaped_literal", "regex_tokenized", "regex_identifier_mode", "regex_path_mode", "regex_hybrid_normalized"]:
        preds, errors = regex_strategy(tasks, files, mode)
        regex_results[mode] = metrics(preds, labels, errors)
    best_regex = sorted(regex_results.items(), key=lambda kv: (kv[1]["parse_error_rate"] * -1, kv[1]["SpanF0.5"]), reverse=True)[0][0]
    if tmp_ctx is not None:
        tmp_ctx.cleanup()
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_ms": int((time.time() - started) * 1000),
        "promotion_ready": False,
        "default_should_change": False,
        "not_promotion_evidence": True,
        "core_changes": False,
        "evidencecore_semantics_changed": False,
        "run_phase_public_only": True,
        "task_count": len(tasks),
        "file_count": len(files),
        "symbol_repair": {
            "symbol_old": symbol_old,
            "symbol_new": symbol_new,
            "symbol_abstain_delta": symbol_new["abstain_rate"] - symbol_old["abstain_rate"],
            "symbol_FileRecall_delta": symbol_new["FileRecall@1"] - symbol_old["FileRecall@1"],
            "symbol_false_primary_delta": symbol_new["primary_false_positive_rate"] - symbol_old["primary_false_positive_rate"],
            "promotion_gate": {
                "false_primary_within_plus_0_02": symbol_new["primary_false_positive_rate"] <= symbol_old["primary_false_positive_rate"] + 0.02,
                "recall_not_lower": symbol_new["FileRecall@1"] >= symbol_old["FileRecall@1"],
            },
        },
        "regex_repair": {
            "results": regex_results,
            "best_regex_mode": best_regex,
            "default_recommendation": "do_not_use_raw_regex_for_user_query_by_default",
            "separate_modes_required": ["literal_search", "regex_search_explicit", "identifier_search", "path_search"],
        },
    }


def write_doc(report: dict[str, Any], path: Path) -> None:
    s = report["symbol_repair"]
    r = report["regex_repair"]
    lines = [
        "# R39-R40 Symbol and Regex Repair",
        "",
        "This phase evaluates symbol extraction and regex normalization repairs without changing default retrieval behavior.",
        "",
        "## Safety",
        "",
        f"- promotion_ready: `{report.get('promotion_ready')}`",
        f"- default_should_change: `{report.get('default_should_change')}`",
        f"- evidencecore_semantics_changed: `{report.get('evidencecore_semantics_changed')}`",
        f"- run_phase_public_only: `{report.get('run_phase_public_only')}`",
        "",
        "## Symbol Repair",
        "",
        f"- symbol_FileRecall_delta: `{s.get('symbol_FileRecall_delta')}`",
        f"- symbol_abstain_delta: `{s.get('symbol_abstain_delta')}`",
        f"- symbol_false_primary_delta: `{s.get('symbol_false_primary_delta')}`",
        f"- gate_false_primary_within_plus_0_02: `{s.get('promotion_gate', {}).get('false_primary_within_plus_0_02')}`",
        "",
        "## Regex Repair",
        "",
        f"- best_regex_mode: `{r.get('best_regex_mode')}`",
        f"- default_recommendation: `{r.get('default_recommendation')}`",
        "",
        "| Mode | parse_error_rate | FileRecall@1 | SpanF0.5 | primary_false_positive_rate |",
        "|---|---:|---:|---:|---:|",
    ]
    for mode, m in r.get("results", {}).items():
        lines.append(f"| {mode} | {m.get('parse_error_rate')} | {m.get('FileRecall@1')} | {m.get('SpanF0.5')} | {m.get('primary_false_positive_rate')} |")
    lines.extend([
        "",
        "## Decision",
        "",
        "- User queries should not be interpreted as raw regex by default.",
        "- Symbol repair remains a candidate for later integration only after broader R26/R38 validation.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-lock", type=Path, default=Path("fixtures/r26_auto_stress/repos.lock.jsonl"))
    parser.add_argument("--tasks", type=Path, default=Path("fixtures/r26_auto_stress/tasks/auto_stress.jsonl"))
    parser.add_argument("--openlocus", type=Path, default=Path("target/debug/openlocus"))
    parser.add_argument("--max-tasks", type=int, default=200)
    parser.add_argument("--max-files", type=int, default=2000)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("artifacts/r39_r40/symbol_regex_repair.json"))
    parser.add_argument("--doc", type=Path, default=Path("docs/r39-r40-symbol-regex-repair.md"))
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
