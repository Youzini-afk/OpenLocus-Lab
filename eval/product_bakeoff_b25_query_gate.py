#!/usr/bin/env python3
"""Source-only query compatibility gate for the B2.5 fresh holdout.

The B2.4 failure was caused by a tokenizer contract mismatch after authoring.
This module prevents that class of failure before any treatment output exists.
It mirrors Tantivy 0.25's ``default`` analyzer (SimpleTokenizer,
RemoveLongFilter<40 bytes, LowerCaser), checks every private query is
tokenizable, and checks every answerable oracle-positive source span contains
at least one normalized query token under the production line verifier rule.

The generated report is private.  It contains no query text or source paths,
and public callers may publish only aggregate counts and boolean gates.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import product_bakeoff_b2_corpus as b2c


B25_QUERY_GATE_SCHEMA = "product_bakeoff_b25_private_query_compatibility.v1"
B25_QUERY_GATE_VERSION = "product_bakeoff_b25_query_compatibility.v1"
B25_ANALYZER_CONTRACT = {
    "tantivy_version": "0.25.0",
    "tokenizer_name": "default",
    "tokenizer": "SimpleTokenizer",
    "split_rule": "maximal_unicode_alphanumeric_runs",
    "remove_long_filter_utf8_bytes_strictly_less_than": 40,
    "lowercase_filter": "LowerCaser_per_unicode_scalar",
    "line_verifier_rule": "normalized_query_token_is_substring_of_lowercased_source_line",
    "retrieval_or_adapter_execution_used": False,
}


class B25QueryGateError(ValueError):
    """Fail-closed B2.5 query compatibility error."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _prefixed_digest(prefix: str, value: Any) -> str:
    return prefix + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _rust_scalar_lower(text: str) -> str:
    """Match Tantivy LowerCaser's per-scalar lowercase behavior."""
    return "".join(character.lower() for character in text)


def tantivy_default_tokens(text: str) -> tuple[str, ...]:
    """Mirror Tantivy 0.25's public ``default`` analyzer contract."""
    if not isinstance(text, str):
        raise B25QueryGateError("query text must be a string")
    tokens: list[str] = []
    current: list[str] = []

    def finish() -> None:
        if not current:
            return
        raw = "".join(current)
        current.clear()
        # RemoveLongFilter::limit(40) accepts only token.text.len() < 40.
        if len(raw.encode("utf-8")) < 40:
            tokens.append(_rust_scalar_lower(raw))

    for character in text:
        if character.isalnum():
            current.append(character)
        else:
            finish()
    finish()
    return tuple(tokens)


def query_gate_digest(report: Mapping[str, Any]) -> str:
    payload = copy.deepcopy(dict(report))
    payload.pop("query_gate_digest", None)
    return _prefixed_digest("b25query_", payload)


def _safe_source_lines(repo_row: Mapping[str, Any], span: Any) -> tuple[str, ...]:
    b2c.validate_relative_path(span.path)
    root = Path(repo_row["source"]["clone_root"]).resolve(strict=True)
    source = (root / Path(span.path)).resolve(strict=True)
    try:
        source.relative_to(root)
    except ValueError as exc:
        raise B25QueryGateError("oracle source span escapes repository root") from exc
    if source.is_symlink() or not source.is_file():
        raise B25QueryGateError("oracle source span is missing or unsafe")
    try:
        text = source.read_bytes().decode("utf-8", errors="strict")
    except (OSError, UnicodeError) as exc:
        raise B25QueryGateError(
            "oracle source span could not be read as frozen UTF-8"
        ) from exc
    lines = text.split("\n")
    if span.end_line > len(lines):
        raise B25QueryGateError("oracle source span exceeds current source")
    return tuple(lines[span.start_line - 1 : span.end_line])


def _span_is_compatible(
    repo_row: Mapping[str, Any], span: Any, query_tokens: Sequence[str]
) -> bool:
    for line in _safe_source_lines(repo_row, span):
        lowered = _rust_scalar_lower(line)
        if any(token in lowered for token in query_tokens):
            return True
    return False


def _build_report_from_rows(
    *,
    repo_lock_digest: str,
    task_manifest_digest: str,
    oracle_manifest_digest: str,
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    task_rows = [dict(row) for row in rows]
    report: dict[str, Any] = {
        "schema_version": B25_QUERY_GATE_SCHEMA,
        "gate_version": B25_QUERY_GATE_VERSION,
        "analyzer_contract": copy.deepcopy(B25_ANALYZER_CONTRACT),
        "repo_lock_digest": repo_lock_digest,
        "task_manifest_digest": task_manifest_digest,
        "oracle_manifest_digest": oracle_manifest_digest,
        "task_count": len(task_rows),
        "tokenizable_query_count": sum(
            int(row["query_token_count"] > 0) for row in task_rows
        ),
        "answerable_task_count": sum(
            int(row["oracle_kind"] != "abstain") for row in task_rows
        ),
        "abstain_task_count": sum(
            int(row["oracle_kind"] == "abstain") for row in task_rows
        ),
        "positive_span_count": sum(
            int(row["positive_span_count"]) for row in task_rows
        ),
        "compatible_positive_span_count": sum(
            int(row["compatible_positive_span_count"]) for row in task_rows
        ),
        "all_queries_tokenizable": all(
            row["query_token_count"] > 0 for row in task_rows
        ),
        "all_positive_spans_compatible": all(
            row["positive_span_count"] == row["compatible_positive_span_count"]
            for row in task_rows
        ),
        "retrieval_or_adapter_execution_used": False,
        "tasks": task_rows,
        "query_gate_digest": "",
    }
    report["query_gate_digest"] = query_gate_digest(report)
    return report


def build_query_compatibility_report(
    *,
    repo_lock: Mapping[str, Any],
    task_manifest: Mapping[str, Any],
    oracle_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the private source-only gate report from frozen manifests."""
    lock = b2c.validate_repo_lock(dict(repo_lock), require_sources=True)
    tasks = b2c.validate_task_manifest(
        dict(task_manifest), repo_lock_digest=lock["repo_lock_digest"]
    )
    oracle = importlib.import_module("product_bakeoff_b2_oracle")
    oracle_rows = oracle.validate_oracle_manifest(
        dict(oracle_manifest),
        tasks=tasks,
        repo_lock=lock,
        task_manifest_digest=task_manifest["task_manifest_digest"],
    )
    repo_by_slot = b2c.repo_by_slot(lock)
    oracle_by_slot = {row.slot_id: row for row in oracle_rows}
    rows: list[dict[str, Any]] = []
    for task in sorted(tasks, key=lambda item: item.slot_id):
        oracle_row = oracle_by_slot[task.slot_id]
        tokens = tantivy_default_tokens(task.query)
        compatible = sum(
            int(_span_is_compatible(repo_by_slot[task.repo_slot], span, tokens))
            for span in oracle_row.positive_spans
        )
        rows.append(
            {
                "slot_id": task.slot_id,
                "task_slug": task.task_slug,
                "oracle_kind": oracle_row.oracle_kind,
                "query_token_count": len(tokens),
                "positive_span_count": len(oracle_row.positive_spans),
                "compatible_positive_span_count": compatible,
                "task_gate_passed": bool(tokens)
                and compatible == len(oracle_row.positive_spans),
            }
        )
    report = _build_report_from_rows(
        repo_lock_digest=lock["repo_lock_digest"],
        task_manifest_digest=task_manifest["task_manifest_digest"],
        oracle_manifest_digest=oracle_manifest["oracle_manifest_digest"],
        rows=rows,
    )
    errors = validate_query_compatibility_report(report)
    if errors:
        raise B25QueryGateError(
            "generated query compatibility report is invalid: " + "; ".join(errors)
        )
    if not report["all_queries_tokenizable"]:
        raise B25QueryGateError("at least one B2.5 query has no production tokens")
    if not report["all_positive_spans_compatible"]:
        raise B25QueryGateError(
            "at least one B2.5 positive span has no production query-token overlap"
        )
    return report


def validate_query_compatibility_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["query compatibility report must be an object"]
    errors: list[str] = []
    expected_keys = {
        "schema_version",
        "gate_version",
        "analyzer_contract",
        "repo_lock_digest",
        "task_manifest_digest",
        "oracle_manifest_digest",
        "task_count",
        "tokenizable_query_count",
        "answerable_task_count",
        "abstain_task_count",
        "positive_span_count",
        "compatible_positive_span_count",
        "all_queries_tokenizable",
        "all_positive_spans_compatible",
        "retrieval_or_adapter_execution_used",
        "tasks",
        "query_gate_digest",
    }
    if set(report) != expected_keys:
        errors.append("query compatibility report top-level shape drift")
    if report.get("schema_version") != B25_QUERY_GATE_SCHEMA:
        errors.append("query compatibility report schema mismatch")
    if report.get("gate_version") != B25_QUERY_GATE_VERSION:
        errors.append("query compatibility report version mismatch")
    if report.get("analyzer_contract") != B25_ANALYZER_CONTRACT:
        errors.append("query compatibility analyzer contract drift")
    for key, prefix in (
        ("repo_lock_digest", "b2repos_"),
        ("task_manifest_digest", "b2tasks_"),
        ("oracle_manifest_digest", "b2oracles_"),
    ):
        value = report.get(key)
        if not isinstance(value, str) or not value.startswith(prefix):
            errors.append(f"query compatibility {key} malformed")
    rows = report.get("tasks")
    if not isinstance(rows, list) or len(rows) != 48:
        errors.append("query compatibility report must contain 48 task rows")
        rows = []
    expected_row_keys = {
        "slot_id",
        "task_slug",
        "oracle_kind",
        "query_token_count",
        "positive_span_count",
        "compatible_positive_span_count",
        "task_gate_passed",
    }
    seen_slots: set[str] = set()
    seen_slugs: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != expected_row_keys:
            errors.append("query compatibility task row shape drift")
            continue
        slot_id = row.get("slot_id")
        task_slug = row.get("task_slug")
        if not isinstance(slot_id, str) or not slot_id:
            errors.append("query compatibility slot id malformed")
        elif slot_id in seen_slots:
            errors.append("query compatibility duplicate slot id")
        else:
            seen_slots.add(slot_id)
        if not isinstance(task_slug, str) or not task_slug:
            errors.append("query compatibility task slug malformed")
        elif task_slug in seen_slugs:
            errors.append("query compatibility duplicate task slug")
        else:
            seen_slugs.add(task_slug)
        if row.get("oracle_kind") not in {"deterministic", "multi_target", "abstain"}:
            errors.append("query compatibility oracle kind malformed")
        for key in (
            "query_token_count",
            "positive_span_count",
            "compatible_positive_span_count",
        ):
            value = row.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                errors.append(f"query compatibility {key} malformed")
        expected_pass = bool(row.get("query_token_count", 0)) and row.get(
            "positive_span_count"
        ) == row.get("compatible_positive_span_count")
        if row.get("task_gate_passed") is not expected_pass:
            errors.append("query compatibility task gate reconciliation failed")
    if rows:
        reconciled = {
            "task_count": len(rows),
            "tokenizable_query_count": sum(
                int(row.get("query_token_count", 0) > 0) for row in rows
            ),
            "answerable_task_count": sum(
                int(row.get("oracle_kind") != "abstain") for row in rows
            ),
            "abstain_task_count": sum(
                int(row.get("oracle_kind") == "abstain") for row in rows
            ),
            "positive_span_count": sum(
                int(row.get("positive_span_count", 0)) for row in rows
            ),
            "compatible_positive_span_count": sum(
                int(row.get("compatible_positive_span_count", 0)) for row in rows
            ),
            "all_queries_tokenizable": all(
                row.get("query_token_count", 0) > 0 for row in rows
            ),
            "all_positive_spans_compatible": all(
                row.get("positive_span_count")
                == row.get("compatible_positive_span_count")
                for row in rows
            ),
        }
        for key, expected in reconciled.items():
            if report.get(key) != expected:
                errors.append(f"query compatibility {key} does not reconcile")
    if report.get("retrieval_or_adapter_execution_used") is not False:
        errors.append("query compatibility gate must remain source-only")
    observed_digest = report.get("query_gate_digest")
    if observed_digest != query_gate_digest(report):
        errors.append("query compatibility report digest mismatch")
    return sorted(set(errors))


def validate_report_binding(
    report: Any,
    *,
    repo_lock_digest: str,
    task_manifest_digest: str,
    oracle_manifest_digest: str,
) -> dict[str, Any]:
    errors = validate_query_compatibility_report(report)
    if errors:
        raise B25QueryGateError("query compatibility report invalid")
    expected = {
        "repo_lock_digest": repo_lock_digest,
        "task_manifest_digest": task_manifest_digest,
        "oracle_manifest_digest": oracle_manifest_digest,
    }
    for key, value in expected.items():
        if report.get(key) != value:
            raise B25QueryGateError("query compatibility manifest binding drifted")
    if report.get("all_queries_tokenizable") is not True:
        raise B25QueryGateError("query compatibility tokenization gate did not pass")
    if report.get("all_positive_spans_compatible") is not True:
        raise B25QueryGateError("query compatibility positive-span gate did not pass")
    return dict(report)


def write_private_report(path: Path, report: Mapping[str, Any]) -> Path:
    errors = validate_query_compatibility_report(dict(report))
    if errors:
        raise B25QueryGateError("refusing to write invalid private query report")
    path.parent.mkdir(parents=True, exist_ok=True)
    parent = path.parent.resolve(strict=True)
    target = parent / path.name
    if os.path.lexists(target):
        raise B25QueryGateError("private query compatibility report already exists")
    raw = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor, temporary_raw = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=parent
    )
    temporary = Path(temporary_raw)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o600)
        if os.path.lexists(target):
            raise B25QueryGateError("private query report appeared concurrently")
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def _synthetic_report() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for index in range(48):
        abstain = index >= 42
        positives = 0 if abstain else (2 if index >= 36 else 1)
        rows.append(
            {
                "slot_id": f"b2_slot_{index + 1:02d}",
                "task_slug": f"b2_t{index + 1:02d}_{index:012x}",
                "oracle_kind": (
                    "abstain" if abstain else "multi_target" if index >= 36 else "deterministic"
                ),
                "query_token_count": 1,
                "positive_span_count": positives,
                "compatible_positive_span_count": positives,
                "task_gate_passed": True,
            }
        )
    return _build_report_from_rows(
        repo_lock_digest="b2repos_" + "1" * 64,
        task_manifest_digest="b2tasks_" + "2" * 64,
        oracle_manifest_digest="b2oracles_" + "3" * 64,
        rows=rows,
    )


def run_self_test() -> dict[str, Any]:
    report = _synthetic_report()
    checks: list[tuple[str, bool]] = [
        (
            "leading_underscore_contract",
            tantivy_default_tokens("_hidden_symbol") == ("hidden", "symbol"),
        ),
        (
            "punctuation_contract",
            tantivy_default_tokens("feature.flag") == ("feature", "flag"),
        ),
        ("one_character_contract", tantivy_default_tokens("x") == ("x",)),
        (
            "remove_long_contract",
            tantivy_default_tokens("a" * 39 + " " + "b" * 40)
            == ("a" * 39,),
        ),
        (
            "unicode_lower_contract",
            tantivy_default_tokens("TREE") == ("tree",),
        ),
        ("synthetic_report_valid", not validate_query_compatibility_report(report)),
        ("source_only", report["retrieval_or_adapter_execution_used"] is False),
        ("all_48_tokenizable", report["tokenizable_query_count"] == 48),
    ]
    with tempfile.TemporaryDirectory(prefix="openlocus-b25-query-source-") as temporary:
        root = Path(temporary)
        (root / "sample.py").write_text(
            "def _hidden_symbol():\n    return 1\n", encoding="utf-8"
        )
        checks.append(
            (
                "source_span_underscore_compatible",
                _span_is_compatible(
                    {"source": {"clone_root": str(root)}},
                    SimpleNamespace(path="sample.py", start_line=1, end_line=1),
                    tantivy_default_tokens("_hidden_symbol"),
                ),
            )
        )
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def run_fault_test() -> dict[str, Any]:
    base = _synthetic_report()
    checks: list[tuple[str, bool]] = []
    mutations = {
        "empty_query_tokens": lambda value: value["tasks"][0].__setitem__(
            "query_token_count", 0
        ),
        "positive_span_mismatch": lambda value: value["tasks"][0].__setitem__(
            "compatible_positive_span_count", 0
        ),
        "retrieval_used": lambda value: value.__setitem__(
            "retrieval_or_adapter_execution_used", True
        ),
        "analyzer_drift": lambda value: value["analyzer_contract"].__setitem__(
            "remove_long_filter_utf8_bytes_strictly_less_than", 41
        ),
        "digest_drift": lambda value: value.__setitem__(
            "query_gate_digest", "b25query_" + "0" * 64
        ),
    }
    for name, mutator in mutations.items():
        value = copy.deepcopy(base)
        mutator(value)
        checks.append((name, bool(validate_query_compatibility_report(value))))
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B2.5 source-only query gate")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--fault-test", action="store_true")
    mode.add_argument("--validate-private", type=Path)
    args = parser.parse_args(argv)
    if args.self_test:
        print(json.dumps(run_self_test(), sort_keys=True))
        return 0
    if args.fault_test:
        print(json.dumps(run_fault_test(), sort_keys=True))
        return 0
    report = b2c.load_json(args.validate_private)
    errors = validate_query_compatibility_report(report)
    if errors:
        return 1
    print(json.dumps({"passed": True, "private_values_printed": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "B25QueryGateError",
    "B25_QUERY_GATE_SCHEMA",
    "B25_QUERY_GATE_VERSION",
    "B25_ANALYZER_CONTRACT",
    "tantivy_default_tokens",
    "query_gate_digest",
    "build_query_compatibility_report",
    "validate_query_compatibility_report",
    "validate_report_binding",
    "write_private_report",
    "run_self_test",
    "run_fault_test",
]
