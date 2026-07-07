#!/usr/bin/env python3
"""Bounded one-shot public artifact/privacy audit.

This is intentionally a local, manually-run audit helper, not a CI gate.  It
only scans files that are already tracked by git and are intended to be public:

* artifacts/**/*.json
* public artifact text files under artifacts/ (*.md, *.txt)
* docs/**/*.md
* README.md

It never walks ignored/private run directories and never scans untracked files.
Reported locations are path/line/category/JSON-path only; matched values are not
printed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from eval.ci_validate_report import PRIVATE_FIELD_DENYLIST
except Exception:  # pragma: no cover - fallback keeps the script self-contained.
    PRIVATE_FIELD_DENYLIST = [
        "source_category", "risk_public", "intent_guess", "risk_tags",
        "oracle_type", "expected_behavior", "gold_spans",
        "hard_distractors", "must_not_primary", "why_this_is_hard",
        "which_strategy_it_targets",
    ]


ARTIFACT_TEXT_SUFFIXES = {".md", ".txt"}
PUBLIC_ARTIFACT_SUFFIXES = {".json", *ARTIFACT_TEXT_SUFFIXES}

PRIVATE_FIELD_KEYS = frozenset(k.lower() for k in PRIVATE_FIELD_DENYLIST)

RAW_PRIVATE_KEYS = frozenset(
    {
        "raw_prompt",
        "raw_prompts",
        "prompt",
        "prompts",
        "messages",
        "request",
        "request_body",
        "raw_request",
        "response",
        "responses",
        "raw_response",
        "response_body",
        "model_response",
        "model_output",
        "api_response",
        "provider_payload",
        "raw_payload",
        "payload_raw",
        "snippet",
        "snippets",
        "code_snippet",
        "source_snippet",
        "raw_source",
        "source_text",
        "raw_rows",
        "raw_row",
        "per_row",
        "per_task",
        "per_run",
        "trace_rows",
        "raw_trace",
        "raw_traces",
        "event_log",
        "events",
        "provider_metadata",
    }
)

GOLD_LABEL_KEYS = frozenset(
    {
        "gold_label",
        "gold_labels",
        "expected_behavior",
        "expected_answer",
        "expected_output",
        "oracle_label",
        "oracle_labels",
        "qrel",
        "qrels",
    }
)

PRIVATE_TRACE_KEYS = frozenset(
    {
        "private_trace",
        "private_traces",
        "trace",
        "traces",
        "trajectory",
        "trajectories",
        "raw_trace",
        "raw_traces",
        "trace_rows",
        "action_trace",
        "state_action_trace",
        "per_row_trace",
    }
)

UNSAFE_TRUE_KEYS = frozenset(
    {
        "promotion_ready",
        "default_should_change",
        "default_change_authorized",
        "runtime_default_change_authorized",
        "runtime_behavior_changed",
        "retriever_changed",
        "backend_changed",
        "default_policy_changed",
        "provider_expansion_authorized",
        "provider_network_authorized",
        "network_expansion_authorized",
        "retrieval_lift_claimed",
        "retrieval_lift_proven",
        "method_winner_bool",
        "method_winner_claimed",
    }
)

API_KEY_VALUE_RE = re.compile(
    r"(?:\bsk-[A-Za-z0-9_-]{20,}\b"
    r"|\bAIza[0-9A-Za-z_-]{20,}\b"
    r"|\bAKIA[0-9A-Z]{16}\b"
    r"|\bghp_[A-Za-z0-9_]{30,}\b"
    r"|\bgithub_pat_[A-Za-z0-9_]{22,}\b"
    r"|\bxox[baprs]-[A-Za-z0-9-]{20,}\b"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----)",
    re.IGNORECASE,
)

RAW_TEXT_KEY_RE = re.compile(
    r"\b(?:raw_prompt|raw_response|provider_payload|api_response|raw_payload|"
    r"gold_labels?|private_trace|raw_trace|per_row)\b\s*[:=]",
    re.IGNORECASE,
)

UNSAFE_TEXT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "unsafe_claim_promotion_ready_true",
        re.compile(r"\bpromotion_ready\s*[:=]\s*true\b", re.IGNORECASE),
    ),
    (
        "unsafe_claim_default_should_change_true",
        re.compile(r"\bdefault_should_change\s*[:=]\s*true\b", re.IGNORECASE),
    ),
    (
        "unsafe_claim_default_change_authorized",
        re.compile(r"\bdefault\s+change\s+(?:is\s+)?authorized\b", re.IGNORECASE),
    ),
    (
        "unsafe_claim_retrieval_lift",
        re.compile(
            r"\bretrieval\s+lift\s+(?:is\s+)?(?:proven|established|confirmed|achieved)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "unsafe_claim_provider_expansion",
        re.compile(
            r"\bprovider\s+(?:expansion|network)\s+(?:is\s+)?authorized\b",
            re.IGNORECASE,
        ),
    ),
)

NEGATION_RE = re.compile(
    r"\b(?:no|not|never|without|false|unauthorized|forbidden|does\s+not|do\s+not|"
    r"is\s+not|are\s+not|isn't|aren't|cannot|can't)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Issue:
    path: str
    line: int
    category: str
    where: str


def _tracked_files() -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "-z", "--", "README.md", "docs", "artifacts"],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return [p for p in proc.stdout.decode("utf-8").split("\0") if p]


def _is_public_audit_target(path: str) -> bool:
    suffix = Path(path).suffix.lower()
    if path == "README.md":
        return True
    if path.startswith("docs/") and suffix == ".md":
        return True
    if path.startswith("artifacts/") and suffix in PUBLIC_ARTIFACT_SUFFIXES:
        return True
    return False


def public_audit_targets() -> list[str]:
    return sorted(p for p in _tracked_files() if _is_public_audit_target(p))


def _json_line_index(text: str) -> dict[str, list[int]]:
    index: dict[str, list[int]] = {}
    key_re = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"\s*:')
    for line_no, line in enumerate(text.splitlines(), 1):
        for match in key_re.finditer(line):
            try:
                key = json.loads(match.group(0).split(":", 1)[0])
            except json.JSONDecodeError:
                continue
            index.setdefault(str(key), []).append(line_no)
    return index


def _line_for_json_path(key_line_index: dict[str, list[int]], key: str) -> int:
    lines = key_line_index.get(key)
    return lines[0] if lines else 1


def _json_path(parent: str, key: str | int) -> str:
    if isinstance(key, int):
        return f"{parent}[{key}]"
    if parent == "$":
        return f"$.{key}"
    return f"{parent}.{key}"


def scan_json_obj(
    obj: Any,
    public_path: str,
    key_line_index: dict[str, list[int]],
    parent: str = "$",
) -> list[Issue]:
    issues: list[Issue] = []
    if isinstance(obj, dict):
        for key_obj, value in obj.items():
            key = str(key_obj)
            key_lower = key.lower()
            where = _json_path(parent, key)
            line = _line_for_json_path(key_line_index, key)

            if key_lower in PRIVATE_FIELD_KEYS:
                issues.append(Issue(public_path, line, "private_field_key", where))
            if key_lower in RAW_PRIVATE_KEYS:
                issues.append(Issue(public_path, line, "raw_private_payload_key", where))
            if key_lower in GOLD_LABEL_KEYS and not (
                key_lower == "qrels" and isinstance(value, (int, float))
            ):
                issues.append(Issue(public_path, line, "gold_label_key", where))
            if key_lower in PRIVATE_TRACE_KEYS:
                issues.append(Issue(public_path, line, "private_trace_key", where))
            if key_lower in UNSAFE_TRUE_KEYS and value is True:
                issues.append(Issue(public_path, line, "unsafe_true_claim", where))

            issues.extend(scan_json_obj(value, public_path, key_line_index, where))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            issues.extend(
                scan_json_obj(value, public_path, key_line_index, _json_path(parent, idx))
            )
    elif isinstance(obj, str):
        if API_KEY_VALUE_RE.search(obj):
            issues.append(Issue(public_path, 1, "api_key_shaped_value", parent))
    return issues


def scan_json_file(path: str) -> list[Issue]:
    full_path = REPO_ROOT / path
    text = full_path.read_text(encoding="utf-8")
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        return [Issue(path, exc.lineno, "json_parse_error", "$")]
    return scan_json_obj(obj, path, _json_line_index(text))


def _line_is_negated(line: str) -> bool:
    prefix = line[:160]
    return bool(NEGATION_RE.search(prefix))


def scan_text_file(path: str) -> list[Issue]:
    issues: list[Issue] = []
    full_path = REPO_ROOT / path
    for line_no, line in enumerate(full_path.read_text(encoding="utf-8").splitlines(), 1):
        if API_KEY_VALUE_RE.search(line):
            issues.append(Issue(path, line_no, "api_key_shaped_value", "line"))
        if RAW_TEXT_KEY_RE.search(line):
            issues.append(Issue(path, line_no, "raw_private_text_key", "line"))
        for category, pattern in UNSAFE_TEXT_PATTERNS:
            if pattern.search(line) and not _line_is_negated(line):
                issues.append(Issue(path, line_no, category, "line"))
    return issues


def run_audit(paths: Iterable[str] | None = None) -> tuple[list[str], list[Issue]]:
    targets = list(paths) if paths is not None else public_audit_targets()
    issues: list[Issue] = []
    for path in targets:
        suffix = Path(path).suffix.lower()
        if suffix == ".json":
            issues.extend(scan_json_file(path))
        else:
            issues.extend(scan_text_file(path))
    return targets, issues


def _print_summary(targets: list[str], issues: list[Issue]) -> None:
    suffix_counts: dict[str, int] = {}
    for path in targets:
        suffix = Path(path).suffix.lower() or "<none>"
        suffix_counts[suffix] = suffix_counts.get(suffix, 0) + 1

    category_counts: dict[str, int] = {}
    for issue in issues:
        category_counts[issue.category] = category_counts.get(issue.category, 0) + 1

    print("PUBLIC ARTIFACT PRIVACY AUDIT SUMMARY")
    print("scope: committed public files only (git ls-files; no ignored/private runs)")
    print("ci_gate: false")
    print(f"files_scanned: {len(targets)}")
    for suffix, count in sorted(suffix_counts.items()):
        print(f"files_scanned[{suffix}]: {count}")
    print(f"issues_total: {len(issues)}")
    for category, count in sorted(category_counts.items()):
        print(f"issues[{category}]: {count}")

    if issues:
        print("sanitized_locations:")
        for issue in sorted(issues, key=lambda i: (i.path, i.line, i.category, i.where)):
            print(f"  - {issue.path}:{issue.line} {issue.category} {issue.where}")


def run_self_test() -> list[str]:
    failures: list[str] = []
    clean = {
        "promotion_ready": False,
        "default_should_change": False,
        "input_hashes": {"labels": "a" * 64},
        "privacy": {"raw_prompts_stored": False, "private_rows_bucket": "count_gt_50"},
    }
    dirty = {
        "source_category": "private",
        "prompt": "hidden",
        "gold_label": "hidden",
        "provider_payload": {"x": 1},
        "promotion_ready": True,
        "token": "sk-" + "a" * 24,
    }
    key_lines = _json_line_index(json.dumps(clean, indent=2))
    if scan_json_obj(clean, "synthetic.json", key_lines):
        failures.append("clean aggregate JSON fixture should pass")
    dirty_issues = scan_json_obj(dirty, "synthetic.json", _json_line_index(json.dumps(dirty)))
    expected_categories = {
        "private_field_key",
        "raw_private_payload_key",
        "gold_label_key",
        "unsafe_true_claim",
        "api_key_shaped_value",
    }
    got_categories = {issue.category for issue in dirty_issues}
    missing = expected_categories - got_categories
    if missing:
        failures.append(f"dirty JSON fixture missing categories: {sorted(missing)}")
    if UNSAFE_TEXT_PATTERNS[3][1].search("not retrieval lift evidence") and not _line_is_negated(
        "not retrieval lift evidence"
    ):
        failures.append("negated retrieval-lift text should not fail")
    if not UNSAFE_TEXT_PATTERNS[3][1].search("retrieval lift proven"):
        failures.append("positive retrieval-lift text should match")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run synthetic scanner tests")
    args = parser.parse_args()

    if args.self_test:
        failures = run_self_test()
        if failures:
            print("PUBLIC ARTIFACT PRIVACY AUDIT SELF-TEST FAILED", file=sys.stderr)
            for failure in failures:
                print(f"  - {failure}", file=sys.stderr)
            return 1
        print("PUBLIC ARTIFACT PRIVACY AUDIT SELF-TEST PASSED")
        return 0

    targets, issues = run_audit()
    _print_summary(targets, issues)
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
