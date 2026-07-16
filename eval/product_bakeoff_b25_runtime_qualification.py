#!/usr/bin/env python3
"""Synthetic production-runtime qualification for B2.5.

The qualification uses only a tiny public synthetic fixture.  It exercises
the actual OpenLocus binary and strict production ``bakeoff-query`` parser for
ordinary, leading-underscore, punctuation-split, and one-character queries.
Every case must return current BM25 evidence with zero stale/invalid skips and
zero provider calls.  Exact queries, source, paths, binary digest, and runner
profile remain in a private receipt; the public report exposes aggregates only.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import product_bakeoff_b1_adapters as b1a
import product_bakeoff_b2_corpus as b2c
import product_bakeoff_b23_runner_qualification as b23q
import product_bakeoff_b24_runner as b24r
from product_bakeoff_b25_protocol import (
    B25_PARENT_B23_QUALIFICATION_DIGEST,
    B25_PARENT_B24_REPAIR_DIGEST,
    B25_PARENT_B24_REPAIR_SHA256,
    B25_PARENT_B24_REPAIR_SOURCE_CHECKPOINT,
    REPORT_PATH,
    b25_source_bundle_digest,
    b25_spec_digest,
    validate_report as validate_protocol_report,
    validate_parent_b23_qualification,
    validate_parent_b24_failure,
    validate_parent_b24_repair,
)


B25_RUNTIME_QUALIFICATION_VERSION = "product_bakeoff_b25_runtime_qualification.v2"
B25_RUNTIME_QUALIFICATION_SCHEMA = (
    "product_bakeoff_b25_runtime_qualification_report.v2"
)
B25_RUNTIME_PRIVATE_SCHEMA = (
    "product_bakeoff_b25_private_runtime_qualification_receipt.v2"
)
B25_RUNTIME_QUALIFICATION_STATUS = (
    "product_bakeoff_b25_repaired_runtime_synthetically_qualified_"
    "private_authoring_allowed_tournament_not_authorized"
)
B25_RUNTIME_QUALIFICATION_CLAIM = (
    "synthetic_runtime_integrity_only_no_private_holdout_no_tournament_result"
)
B25_RUNTIME_PUBLICATION_LIMITS = {
    "aggregate_only": True,
    "exact_synthetic_query_or_source_public": False,
    "binary_or_runtime_fingerprint_public": False,
    "exact_runner_profile_or_location_public": False,
    "private_receipt_digest_public": False,
    "private_repository_task_or_oracle_public": False,
}
B25_RUNTIME_NEXT_ACTION = (
    "commit this aggregate-only runtime qualification, obtain green public "
    "CI, and only then author a fresh B2.5 private holdout that excludes all "
    "B2, B2.1, and B2.4 repositories"
)
B25_RUNTIME_CASES = (
    {
        "category": "ordinary_identifier",
        "query": "public_symbol",
        "task_family": "symbol_lookup",
        "path": "sample.py",
        "line": 1,
    },
    {
        "category": "leading_underscore_identifier",
        "query": "_hidden_symbol",
        "task_family": "symbol_lookup",
        "path": "sample.py",
        "line": 4,
    },
    {
        "category": "punctuation_split_identifier",
        "query": "feature.flag",
        "task_family": "configuration_discovery",
        "path": "settings.toml",
        "line": 1,
    },
    {
        "category": "one_character_identifier",
        "query": "x",
        "task_family": "symbol_lookup",
        "path": "tiny.py",
        "line": 1,
    },
)
B25_PARENT_MACHINE_ALLOWED_VARIANCE_KEYS = ("cgroup_memory_limit_bytes",)
B25_PARENT_MACHINE_EXACT_KEYS = tuple(
    key
    for key in b23q.STABLE_PROFILE_KEYS
    if not key.startswith("openlocus_")
    and key not in B25_PARENT_MACHINE_ALLOWED_VARIANCE_KEYS
)


class B25RuntimeQualificationError(ValueError):
    """Fail-closed B2.5 runtime qualification error."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(prefix: str, value: Any) -> str:
    return prefix + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head(repo_root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    head = completed.stdout.strip()
    if completed.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", head):
        raise B25RuntimeQualificationError("current source checkpoint is unavailable")
    return head


def _validate_protocol_checkpoint(checkpoint: str) -> None:
    repo_root = Path(__file__).resolve().parents[1].resolve(strict=True)
    report = b2c.load_json(REPORT_PATH)
    if validate_protocol_report(report):
        raise B25RuntimeQualificationError("B2.5 protocol report is invalid")
    relative = REPORT_PATH.resolve(strict=True).relative_to(repo_root).as_posix()
    completed = subprocess.run(
        ["git", "show", f"{checkpoint}:{relative}"],
        cwd=repo_root,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise B25RuntimeQualificationError("B2.5 protocol report is absent from checkpoint")
    if hashlib.sha256(completed.stdout).hexdigest() != _file_sha256(REPORT_PATH):
        raise B25RuntimeQualificationError("B2.5 protocol report differs from checkpoint")


def _parent_machine_profile_changes(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> list[str]:
    """Compare exact parent fields while requalifying CLI bytes and memory."""
    return [
        key
        for key in B25_PARENT_MACHINE_EXACT_KEYS
        if before.get(key) != after.get(key)
    ]


def _parent_memory_gate_errors(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> list[str]:
    """Allow only memory-limit variance that remains inside the frozen class."""
    minimum = int(b23q.B23_RUNNER_CLASS["minimum_cgroup_memory_limit_bytes"])
    errors: list[str] = []
    for label, profile in (("parent", before), ("current", after)):
        observed = profile.get("cgroup_memory_limit_bytes")
        if (
            not isinstance(observed, int)
            or isinstance(observed, bool)
            or observed < minimum
        ):
            errors.append(f"{label}_cgroup_memory_limit_below_runner_class")
    return errors


def qualification_digest(report: Mapping[str, Any]) -> str:
    payload = copy.deepcopy(dict(report))
    payload.pop("qualification_digest", None)
    return _digest("b25qual_", payload)


def private_receipt_digest(receipt: Mapping[str, Any]) -> str:
    payload = copy.deepcopy(dict(receipt))
    payload.pop("private_receipt_digest", None)
    return _digest("b25qpriv_", payload)


def _synthetic_fixture_payload() -> dict[str, str]:
    return {
        "sample.py": "def public_symbol():\n    return 1\n\ndef _hidden_symbol():\n    return 2\n",
        "settings.toml": "feature.flag = true\n",
        "tiny.py": "x = 7\n",
    }


def _build_public_report(
    *,
    protocol_checkpoint: str,
    protocol_ci_run_id: int,
    protocol_ci_conclusion: str,
    case_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    categories = [str(row["category"]) for row in case_rows]
    report: dict[str, Any] = {
        "schema_version": B25_RUNTIME_QUALIFICATION_SCHEMA,
        "qualification_version": B25_RUNTIME_QUALIFICATION_VERSION,
        "phase": "product_bakeoff_b25_repaired_runtime_qualification",
        "status": B25_RUNTIME_QUALIFICATION_STATUS,
        "claim_level": B25_RUNTIME_QUALIFICATION_CLAIM,
        "date": "2026-07-16",
        "protocol_gate": {
            "checkpoint": protocol_checkpoint,
            "ci_run_id": protocol_ci_run_id,
            "ci_conclusion": protocol_ci_conclusion,
            "b25_spec_digest": b25_spec_digest(),
            "b25_source_bundle_digest": b25_source_bundle_digest(),
        },
        "repair_gate": {
            "repair_digest": B25_PARENT_B24_REPAIR_DIGEST,
            "repair_file_sha256": B25_PARENT_B24_REPAIR_SHA256,
            "repair_source_checkpoint": B25_PARENT_B24_REPAIR_SOURCE_CHECKPOINT,
            "production_tokenizer_repair_bound": True,
        },
        "runner_gate": {
            "parent_b23_qualification_digest": B25_PARENT_B23_QUALIFICATION_DIGEST,
            "parent_runner_class_lineage_admitted": True,
            "all_noncapacity_stable_fields_exact": True,
            "memory_limit_meets_frozen_b23_runner_class": True,
            "current_runner_profile_gate_passed": True,
            "current_machine_frozen_for_b25_after_qualification": True,
            "exact_runner_profile_public": False,
        },
        "synthetic_matrix": {
            "case_count": len(case_rows),
            "case_categories": categories,
            "passed_case_count": sum(int(row["passed"]) for row in case_rows),
            "actual_production_cli_used": True,
            "actual_production_bakeoff_query_parser_used": True,
            "private_input_read": False,
            "all_cases_returned_current_evidence": all(
                row["current_evidence"] for row in case_rows
            ),
            "all_bm25_receipts_executed": all(
                row["bm25_executed"] for row in case_rows
            ),
            "all_stale_hits_skipped_zero": all(
                row["stale_hits_skipped"] == 0 for row in case_rows
            ),
            "all_invalid_hits_skipped_zero": all(
                row["invalid_hits_skipped"] == 0 for row in case_rows
            ),
            "provider_network_call_count": 0,
        },
        "decision": {
            "repaired_runtime_qualified": all(row["passed"] for row in case_rows),
            "fresh_private_holdout_authoring_allowed_after_green_publication_ci": all(
                row["passed"] for row in case_rows
            ),
            "tournament_execution_authorized": False,
            "private_holdout_read": False,
            "tournament_result_exists": False,
        },
        "publication_limits": copy.deepcopy(B25_RUNTIME_PUBLICATION_LIMITS),
        "next_authorized_action": B25_RUNTIME_NEXT_ACTION,
        "qualification_digest": "",
    }
    report["qualification_digest"] = qualification_digest(report)
    return report


def validate_public_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["runtime qualification report must be an object"]
    errors: list[str] = []
    expected_keys = {
        "schema_version",
        "qualification_version",
        "phase",
        "status",
        "claim_level",
        "date",
        "protocol_gate",
        "repair_gate",
        "runner_gate",
        "synthetic_matrix",
        "decision",
        "publication_limits",
        "next_authorized_action",
        "qualification_digest",
    }
    if set(report) != expected_keys:
        errors.append("runtime qualification top-level shape drift")
    if report.get("schema_version") != B25_RUNTIME_QUALIFICATION_SCHEMA:
        errors.append("runtime qualification schema mismatch")
    if report.get("qualification_version") != B25_RUNTIME_QUALIFICATION_VERSION:
        errors.append("runtime qualification version mismatch")
    if report.get("status") != B25_RUNTIME_QUALIFICATION_STATUS:
        errors.append("runtime qualification status mismatch")
    if report.get("phase") != "product_bakeoff_b25_repaired_runtime_qualification":
        errors.append("runtime qualification phase mismatch")
    if report.get("claim_level") != B25_RUNTIME_QUALIFICATION_CLAIM:
        errors.append("runtime qualification claim mismatch")
    if report.get("date") != "2026-07-16":
        errors.append("runtime qualification date mismatch")
    protocol = report.get("protocol_gate") or {}
    if set(protocol) != {
        "checkpoint",
        "ci_run_id",
        "ci_conclusion",
        "b25_spec_digest",
        "b25_source_bundle_digest",
    }:
        errors.append("runtime qualification protocol gate shape drifted")
    if not re.fullmatch(r"[0-9a-f]{40}", str(protocol.get("checkpoint", ""))):
        errors.append("runtime qualification protocol checkpoint malformed")
    if not isinstance(protocol.get("ci_run_id"), int) or protocol.get("ci_run_id", 0) <= 0:
        errors.append("runtime qualification protocol CI run id malformed")
    if protocol.get("ci_conclusion") != "success":
        errors.append("runtime qualification protocol CI did not succeed")
    if protocol.get("b25_spec_digest") != b25_spec_digest():
        errors.append("runtime qualification B2.5 spec binding drifted")
    if protocol.get("b25_source_bundle_digest") != b25_source_bundle_digest():
        errors.append("runtime qualification B2.5 source binding drifted")
    expected_repair = {
        "repair_digest": B25_PARENT_B24_REPAIR_DIGEST,
        "repair_file_sha256": B25_PARENT_B24_REPAIR_SHA256,
        "repair_source_checkpoint": B25_PARENT_B24_REPAIR_SOURCE_CHECKPOINT,
        "production_tokenizer_repair_bound": True,
    }
    if report.get("repair_gate") != expected_repair:
        errors.append("runtime qualification repair gate drifted")
    expected_runner = {
        "parent_b23_qualification_digest": B25_PARENT_B23_QUALIFICATION_DIGEST,
        "parent_runner_class_lineage_admitted": True,
        "all_noncapacity_stable_fields_exact": True,
        "memory_limit_meets_frozen_b23_runner_class": True,
        "current_runner_profile_gate_passed": True,
        "current_machine_frozen_for_b25_after_qualification": True,
        "exact_runner_profile_public": False,
    }
    if report.get("runner_gate") != expected_runner:
        errors.append("runtime qualification runner gate drifted")
    matrix = report.get("synthetic_matrix") or {}
    expected_categories = [row["category"] for row in B25_RUNTIME_CASES]
    exact_matrix = {
        "case_count": 4,
        "case_categories": expected_categories,
        "passed_case_count": 4,
        "actual_production_cli_used": True,
        "actual_production_bakeoff_query_parser_used": True,
        "private_input_read": False,
        "all_cases_returned_current_evidence": True,
        "all_bm25_receipts_executed": True,
        "all_stale_hits_skipped_zero": True,
        "all_invalid_hits_skipped_zero": True,
        "provider_network_call_count": 0,
    }
    if matrix != exact_matrix:
        errors.append("runtime qualification synthetic matrix drifted")
    expected_decision = {
        "repaired_runtime_qualified": True,
        "fresh_private_holdout_authoring_allowed_after_green_publication_ci": True,
        "tournament_execution_authorized": False,
        "private_holdout_read": False,
        "tournament_result_exists": False,
    }
    if report.get("decision") != expected_decision:
        errors.append("runtime qualification decision drifted")
    if report.get("publication_limits") != B25_RUNTIME_PUBLICATION_LIMITS:
        errors.append("runtime qualification publication limits drifted")
    if report.get("next_authorized_action") != B25_RUNTIME_NEXT_ACTION:
        errors.append("runtime qualification next action drifted")
    if report.get("qualification_digest") != qualification_digest(report):
        errors.append("runtime qualification digest mismatch")
    raw = json.dumps(report, sort_keys=True, ensure_ascii=False).casefold()
    for token in (
        "_hidden_symbol",
        "public_symbol",
        "feature.flag",
        "b25qpriv_",
        "openlocus_sha256",
        "runtime_bundle_digest",
        "clone_root",
        "task_slug",
        "repo_lock_digest",
        "oracle_manifest_digest",
    ):
        if token in raw:
            errors.append(f"private or exact qualification token is public: {token}")
    return sorted(set(errors))


def _build_private_receipt(
    *,
    public_report: Mapping[str, Any],
    public_report_file_sha256: str,
    cli_path: Path,
    parent_private_receipt: Mapping[str, Any],
    profile: Mapping[str, Any],
    case_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema_version": B25_RUNTIME_PRIVATE_SCHEMA,
        "qualification_version": B25_RUNTIME_QUALIFICATION_VERSION,
        "b25_spec_digest": b25_spec_digest(),
        "b25_source_bundle_digest": b25_source_bundle_digest(),
        "source_checkpoint": public_report["protocol_gate"]["checkpoint"],
        "parent_b23_public_qualification_digest": B25_PARENT_B23_QUALIFICATION_DIGEST,
        "parent_b23_private_receipt_digest": parent_private_receipt[
            "private_receipt_digest"
        ],
        "parent_runner_class_admission": {
            "allowed_variance_keys": list(
                B25_PARENT_MACHINE_ALLOWED_VARIANCE_KEYS
            ),
            "all_other_stable_fields_exact": True,
            "parent_memory_gate_passed": True,
            "current_memory_gate_passed": True,
            "current_machine_frozen_by_receipt": True,
        },
        "profile_after": copy.deepcopy(dict(profile)),
        "cli_bytes": cli_path.stat().st_size,
        "cli_sha256": _file_sha256(cli_path),
        "synthetic_fixture_digest": _digest(
            "b25fixture_",
            _synthetic_fixture_payload(),
        ),
        "case_rows": [copy.deepcopy(dict(row)) for row in case_rows],
        "public_qualification_digest": public_report["qualification_digest"],
        "public_report_file_sha256": public_report_file_sha256,
        "private_input_read": False,
        "private_receipt_digest": "",
    }
    receipt["private_receipt_digest"] = private_receipt_digest(receipt)
    return receipt


def validate_private_receipt(receipt: Any) -> list[str]:
    if not isinstance(receipt, dict):
        return ["private runtime qualification receipt must be an object"]
    errors: list[str] = []
    expected_keys = {
        "schema_version",
        "qualification_version",
        "b25_spec_digest",
        "b25_source_bundle_digest",
        "source_checkpoint",
        "parent_b23_public_qualification_digest",
        "parent_b23_private_receipt_digest",
        "parent_runner_class_admission",
        "profile_after",
        "cli_bytes",
        "cli_sha256",
        "synthetic_fixture_digest",
        "case_rows",
        "public_qualification_digest",
        "public_report_file_sha256",
        "private_input_read",
        "private_receipt_digest",
    }
    if set(receipt) != expected_keys:
        errors.append("private runtime qualification receipt shape drift")
    if receipt.get("schema_version") != B25_RUNTIME_PRIVATE_SCHEMA:
        errors.append("private runtime qualification schema mismatch")
    if receipt.get("qualification_version") != B25_RUNTIME_QUALIFICATION_VERSION:
        errors.append("private runtime qualification version mismatch")
    if receipt.get("b25_spec_digest") != b25_spec_digest():
        errors.append("private runtime qualification spec binding drifted")
    if receipt.get("b25_source_bundle_digest") != b25_source_bundle_digest():
        errors.append("private runtime qualification source binding drifted")
    if not re.fullmatch(r"[0-9a-f]{40}", str(receipt.get("source_checkpoint", ""))):
        errors.append("private runtime qualification checkpoint malformed")
    if receipt.get("parent_b23_public_qualification_digest") != B25_PARENT_B23_QUALIFICATION_DIGEST:
        errors.append("private runtime qualification parent public binding drifted")
    if not isinstance(receipt.get("parent_b23_private_receipt_digest"), str) or not str(
        receipt.get("parent_b23_private_receipt_digest")
    ).startswith("b23qpriv_"):
        errors.append("private runtime qualification parent private binding malformed")
    expected_parent_admission = {
        "allowed_variance_keys": list(B25_PARENT_MACHINE_ALLOWED_VARIANCE_KEYS),
        "all_other_stable_fields_exact": True,
        "parent_memory_gate_passed": True,
        "current_memory_gate_passed": True,
        "current_machine_frozen_by_receipt": True,
    }
    if receipt.get("parent_runner_class_admission") != expected_parent_admission:
        errors.append("private runtime qualification parent runner admission drifted")
    if not isinstance(receipt.get("profile_after"), dict):
        errors.append("private runtime qualification profile missing")
    if not isinstance(receipt.get("cli_bytes"), int) or receipt.get("cli_bytes", 0) <= 0:
        errors.append("private runtime qualification CLI byte count malformed")
    if not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("cli_sha256", ""))):
        errors.append("private runtime qualification CLI digest malformed")
    if receipt.get("synthetic_fixture_digest") != _digest(
        "b25fixture_", _synthetic_fixture_payload()
    ):
        errors.append("private runtime qualification fixture binding drifted")
    rows = receipt.get("case_rows")
    if not isinstance(rows, list) or len(rows) != 4:
        errors.append("private runtime qualification case rows malformed")
    else:
        expected_row_keys = {
            "category",
            "query",
            "task_family",
            "expected_path",
            "expected_line",
            "evidence_count",
            "current_evidence",
            "bm25_executed",
            "stale_hits_skipped",
            "invalid_hits_skipped",
            "provider_remote_calls",
            "provider_outbound_calls",
            "passed",
        }
        for row, case in zip(rows, B25_RUNTIME_CASES):
            if not isinstance(row, dict) or set(row) != expected_row_keys:
                errors.append("private runtime qualification case row shape drifted")
                continue
            expected_case = {
                "category": case["category"],
                "query": case["query"],
                "task_family": case["task_family"],
                "expected_path": case["path"],
                "expected_line": case["line"],
            }
            for key, expected in expected_case.items():
                if row.get(key) != expected:
                    errors.append("private runtime qualification case binding drifted")
            if not isinstance(row.get("evidence_count"), int) or row.get(
                "evidence_count", 0
            ) <= 0:
                errors.append("private runtime qualification evidence count malformed")
            exact_pass = {
                "current_evidence": True,
                "bm25_executed": True,
                "stale_hits_skipped": 0,
                "invalid_hits_skipped": 0,
                "provider_remote_calls": 0,
                "provider_outbound_calls": 0,
                "passed": True,
            }
            for key, expected in exact_pass.items():
                if row.get(key) != expected:
                    errors.append("private runtime qualification contains a failed case")
    if receipt.get("private_input_read") is not False:
        errors.append("private runtime qualification read private input")
    if not isinstance(receipt.get("public_qualification_digest"), str) or not str(
        receipt.get("public_qualification_digest")
    ).startswith("b25qual_"):
        errors.append("private runtime qualification public digest malformed")
    if not re.fullmatch(
        r"[0-9a-f]{64}", str(receipt.get("public_report_file_sha256", ""))
    ):
        errors.append("private runtime qualification public file digest malformed")
    if receipt.get("private_receipt_digest") != private_receipt_digest(receipt):
        errors.append("private runtime qualification receipt digest mismatch")
    return sorted(set(errors))


def _subprocess_env() -> dict[str, str]:
    allowed = (
        "PATH",
        "HOME",
        "USERPROFILE",
        "TMPDIR",
        "TMP",
        "TEMP",
        "SystemRoot",
        "WINDIR",
    )
    env = {key: os.environ[key] for key in allowed if key in os.environ}
    env["OPENLOCUS_ALLOW_REMOTE"] = "0"
    return env


def _run_command(command: Sequence[str], *, cwd: Path, timeout: float) -> bytes:
    try:
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            env=_subprocess_env(),
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise B25RuntimeQualificationError(
            "synthetic runtime command failed to complete: " + type(exc).__name__
        ) from exc
    if completed.returncode != 0:
        raise B25RuntimeQualificationError(
            f"synthetic runtime command failed with returncode {completed.returncode}"
        )
    if completed.stderr:
        raise B25RuntimeQualificationError("synthetic runtime command emitted stderr")
    if not completed.stdout.strip():
        raise B25RuntimeQualificationError("synthetic runtime command emitted no stdout")
    return completed.stdout


def _prepare_fixture(root: Path) -> tuple[str, ...]:
    if root.exists() and any(root.iterdir()):
        raise B25RuntimeQualificationError("runtime qualification fixture root is not empty")
    root.mkdir(parents=True, exist_ok=True)
    payload = _synthetic_fixture_payload()
    for relative, text in payload.items():
        (root / relative).write_text(text, encoding="utf-8")
    return tuple(payload)


def _run_synthetic_cases(cli_path: Path, fixture_root: Path) -> list[dict[str, Any]]:
    visible = _prepare_fixture(fixture_root)
    root_arg = str(fixture_root.resolve())
    _run_command(
        (
            str(cli_path),
            "index",
            "build",
            "--source-root",
            root_arg,
            "--state-root",
            root_arg,
            "--chunk-strategy",
            "line",
            "--json",
        ),
        cwd=fixture_root,
        timeout=600.0,
    )
    audit = fixture_root / ".openlocus" / "audit"
    audit.mkdir(parents=True, exist_ok=True)
    (audit / "embeddings.jsonl").write_bytes(b"")
    rows: list[dict[str, Any]] = []
    for index, case in enumerate(B25_RUNTIME_CASES, start=1):
        stdout = _run_command(
            (
                str(cli_path),
                "bakeoff-query",
                "context",
                "--source-root",
                root_arg,
                "--state-root",
                root_arg,
                "--query",
                case["query"],
                "--components",
                "bm25",
                "--task-family",
                case["task_family"],
                "--max-results",
                "8",
                "--json",
            ),
            cwd=fixture_root,
            timeout=570.0,
        )
        parsed = b1a.parse_bakeoff_query(
            stdout,
            frozenset({"bm25"}),
            visible,
            "context",
            f"b25q-{index}",
            expected_source_root=fixture_root,
            expected_state_root=fixture_root,
            expected_query=case["query"],
            expected_task_family=case["task_family"],
            expected_max_results=8,
        )
        receipt = next(
            (row for row in parsed.receipts if row.component == "bm25"), None
        )
        if receipt is None:
            raise B25RuntimeQualificationError("synthetic BM25 receipt is missing")
        current = any(
            evidence.path == case["path"]
            and evidence.start_line <= int(case["line"]) <= evidence.end_line
            for evidence in parsed.evidence
        )
        stale = int(receipt.diagnostics["stale_hits_skipped"])
        invalid = int(receipt.diagnostics["invalid_hits_skipped"])
        executed = receipt.status == "executed"
        passed = (
            parsed.evidence_count > 0
            and current
            and executed
            and stale == 0
            and invalid == 0
            and parsed.provider.remote_calls == 0
            and parsed.provider.outbound_calls == 0
        )
        rows.append(
            {
                "category": case["category"],
                "query": case["query"],
                "task_family": case["task_family"],
                "expected_path": case["path"],
                "expected_line": case["line"],
                "evidence_count": parsed.evidence_count,
                "current_evidence": current,
                "bm25_executed": executed,
                "stale_hits_skipped": stale,
                "invalid_hits_skipped": invalid,
                "provider_remote_calls": parsed.provider.remote_calls,
                "provider_outbound_calls": parsed.provider.outbound_calls,
                "passed": passed,
            }
        )
    if not all(row["passed"] for row in rows):
        raise B25RuntimeQualificationError("synthetic repaired-runtime gate failed")
    return rows


def qualify_runtime(
    *,
    cli_path: Path,
    qualification_private_receipt_path: Path,
    scratch_root: Path,
    protocol_checkpoint: str,
    protocol_ci_run_id: int,
    protocol_ci_conclusion: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    parent_errors = [
        *validate_parent_b24_failure(),
        *validate_parent_b24_repair(),
        *validate_parent_b23_qualification(),
    ]
    if parent_errors:
        raise B25RuntimeQualificationError("B2.5 public parent locks are invalid")
    if not re.fullmatch(r"[0-9a-f]{40}", protocol_checkpoint):
        raise B25RuntimeQualificationError("protocol checkpoint must be a full commit SHA")
    if not isinstance(protocol_ci_run_id, int) or protocol_ci_run_id <= 0:
        raise B25RuntimeQualificationError("protocol CI run id must be positive")
    if protocol_ci_conclusion != "success":
        raise B25RuntimeQualificationError("protocol CI must conclude success")
    repo_root = Path(__file__).resolve().parents[1]
    if _git_head(repo_root) != protocol_checkpoint:
        raise B25RuntimeQualificationError("checkout is not the protocol CI checkpoint")
    _validate_protocol_checkpoint(protocol_checkpoint)
    cli_path = Path(cli_path).resolve(strict=True)
    if cli_path.is_symlink() or not cli_path.is_file():
        raise B25RuntimeQualificationError("OpenLocus CLI path is missing or unsafe")
    scratch_root = Path(scratch_root)
    if os.path.lexists(scratch_root):
        if scratch_root.is_symlink() or not scratch_root.is_dir() or any(
            scratch_root.iterdir()
        ):
            raise B25RuntimeQualificationError(
                "runtime qualification scratch root must be absent or empty"
            )
    scratch_root.mkdir(parents=True, exist_ok=True)
    parent_private = b24r.validate_qualification_private_receipt(
        b2c.load_json(qualification_private_receipt_path)
    )
    profile = b23q.collect_runner_profile(
        repo_root=repo_root,
        scratch_root=scratch_root,
        cli_path=cli_path,
    )
    failures = b23q.validate_runner_profile(profile)
    changes = _parent_machine_profile_changes(parent_private["profile_after"], profile)
    memory_errors = _parent_memory_gate_errors(
        parent_private["profile_after"], profile
    )
    if failures or changes or memory_errors:
        raise B25RuntimeQualificationError(
            "B2.3 runner-class-compatible machine admission failed"
        )
    fixture_root = scratch_root / "b25_synthetic_tokenizer_fixture"
    try:
        case_rows = _run_synthetic_cases(cli_path, fixture_root)
    finally:
        if fixture_root.exists():
            resolved_fixture = fixture_root.resolve(strict=True)
            resolved_fixture.relative_to(scratch_root.resolve(strict=True))
            shutil.rmtree(resolved_fixture)
    public = _build_public_report(
        protocol_checkpoint=protocol_checkpoint,
        protocol_ci_run_id=protocol_ci_run_id,
        protocol_ci_conclusion=protocol_ci_conclusion,
        case_rows=case_rows,
    )
    errors = validate_public_report(public)
    if errors:
        raise B25RuntimeQualificationError(
            "generated runtime qualification report invalid: " + "; ".join(errors)
        )
    public_raw = (json.dumps(public, indent=2, sort_keys=True) + "\n").encode("utf-8")
    private = _build_private_receipt(
        public_report=public,
        public_report_file_sha256=hashlib.sha256(public_raw).hexdigest(),
        cli_path=cli_path,
        parent_private_receipt=parent_private,
        profile=profile,
        case_rows=case_rows,
    )
    private_errors = validate_private_receipt(private)
    if private_errors:
        raise B25RuntimeQualificationError(
            "generated private runtime receipt invalid: " + "; ".join(private_errors)
        )
    return public, private


def _write_atomic(path: Path, raw: bytes, *, mode: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    parent = path.parent.resolve(strict=True)
    target = parent / path.name
    if os.path.lexists(target):
        raise B25RuntimeQualificationError("runtime qualification output already exists")
    descriptor, temporary_raw = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=parent
    )
    temporary = Path(temporary_raw)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(mode)
        if os.path.lexists(target):
            raise B25RuntimeQualificationError(
                "runtime qualification output appeared concurrently"
            )
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def write_qualification_pair(
    *,
    public_path: Path,
    private_path: Path,
    public_report: Mapping[str, Any],
    private_receipt: Mapping[str, Any],
) -> tuple[Path, Path]:
    repo_root = Path(__file__).resolve().parents[1].resolve(strict=True)
    public_resolved = Path(public_path).resolve(strict=False)
    private_resolved = Path(private_path).resolve(strict=False)
    try:
        public_resolved.relative_to(repo_root)
    except ValueError as exc:
        raise B25RuntimeQualificationError(
            "public runtime qualification must be written inside the checkout"
        ) from exc
    try:
        private_resolved.relative_to(repo_root)
    except ValueError:
        pass
    else:
        raise B25RuntimeQualificationError(
            "private runtime qualification receipt must remain outside the checkout"
        )
    public_errors = validate_public_report(dict(public_report))
    private_errors = validate_private_receipt(dict(private_receipt))
    if public_errors or private_errors:
        raise B25RuntimeQualificationError("refusing to write invalid qualification pair")
    public_raw = (json.dumps(public_report, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    if private_receipt.get("public_report_file_sha256") != hashlib.sha256(
        public_raw
    ).hexdigest():
        raise B25RuntimeQualificationError("private/public qualification bytes do not bind")
    private_raw = (json.dumps(private_receipt, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    private_target = _write_atomic(private_path, private_raw, mode=0o600)
    try:
        public_target = _write_atomic(public_path, public_raw, mode=0o644)
    except Exception:
        if private_target.is_file() and not private_target.is_symlink():
            private_target.unlink()
        raise
    return public_target, private_target


def validate_runtime_binding(
    *,
    public_report_path: Path,
    private_receipt_path: Path,
    cli_path: Path,
    qualification_private_receipt_path: Path,
    scratch_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    parent_errors = [
        *validate_parent_b24_failure(),
        *validate_parent_b24_repair(),
        *validate_parent_b23_qualification(),
    ]
    if parent_errors:
        raise B25RuntimeQualificationError("B2.5 public parent locks are invalid")
    public = b2c.load_json(public_report_path)
    private = b2c.load_json(private_receipt_path)
    public_errors = validate_public_report(public)
    private_errors = validate_private_receipt(private)
    if public_errors or private_errors:
        raise B25RuntimeQualificationError("runtime qualification binding is invalid")
    _validate_protocol_checkpoint(private["source_checkpoint"])
    if private["public_qualification_digest"] != public["qualification_digest"]:
        raise B25RuntimeQualificationError("runtime qualification public digest drifted")
    if private["public_report_file_sha256"] != _file_sha256(public_report_path):
        raise B25RuntimeQualificationError("runtime qualification public bytes drifted")
    repo_root = Path(__file__).resolve().parents[1]
    cli_path = Path(cli_path).resolve(strict=True)
    if cli_path.stat().st_size != private["cli_bytes"] or _file_sha256(cli_path) != private[
        "cli_sha256"
    ]:
        raise B25RuntimeQualificationError("qualified OpenLocus binary bytes drifted")
    parent_private = b24r.validate_qualification_private_receipt(
        b2c.load_json(qualification_private_receipt_path)
    )
    if parent_private["private_receipt_digest"] != private[
        "parent_b23_private_receipt_digest"
    ]:
        raise B25RuntimeQualificationError("runtime qualification parent receipt drifted")
    if _parent_machine_profile_changes(
        parent_private["profile_after"], private["profile_after"]
    ) or _parent_memory_gate_errors(
        parent_private["profile_after"], private["profile_after"]
    ):
        raise B25RuntimeQualificationError(
            "runtime qualification parent runner-class admission drifted"
        )
    current = b23q.collect_runner_profile(
        repo_root=repo_root,
        scratch_root=Path(scratch_root),
        cli_path=cli_path,
    )
    if b23q.validate_runner_profile(current):
        raise B25RuntimeQualificationError("current runner profile gate failed")
    if b23q.stable_runner_profile_changes(private["profile_after"], current):
        raise B25RuntimeQualificationError("current runner differs from qualified runtime profile")
    return public, private


def _synthetic_case_rows() -> list[dict[str, Any]]:
    return [
        {
            "category": case["category"],
            "query": case["query"],
            "task_family": case["task_family"],
            "expected_path": case["path"],
            "expected_line": case["line"],
            "evidence_count": 1,
            "current_evidence": True,
            "bm25_executed": True,
            "stale_hits_skipped": 0,
            "invalid_hits_skipped": 0,
            "provider_remote_calls": 0,
            "provider_outbound_calls": 0,
            "passed": True,
        }
        for case in B25_RUNTIME_CASES
    ]


def run_self_test() -> dict[str, Any]:
    rows = _synthetic_case_rows()
    public = _build_public_report(
        protocol_checkpoint="1" * 40,
        protocol_ci_run_id=1,
        protocol_ci_conclusion="success",
        case_rows=rows,
    )
    with tempfile.TemporaryDirectory(prefix="openlocus-b25q-") as temporary:
        cli = Path(temporary) / "openlocus"
        cli.write_bytes(b"synthetic-openlocus")
        parent = b24r._synthetic_parent_qualification_receipt()
        public_raw = (json.dumps(public, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        )
        private = _build_private_receipt(
            public_report=public,
            public_report_file_sha256=hashlib.sha256(public_raw).hexdigest(),
            cli_path=cli,
            parent_private_receipt=parent,
            profile={},
            case_rows=rows,
        )
    checks = [
        ("four_cases", len(rows) == 4),
        ("public_report_valid", not validate_public_report(public)),
        ("private_receipt_valid", not validate_private_receipt(private)),
        (
            "parent_cli_bytes_are_requalified",
            not _parent_machine_profile_changes(
                {"openlocus_sha256": "old"}, {"openlocus_sha256": "new"}
            ),
        ),
        (
            "memory_is_only_parent_variance",
            B25_PARENT_MACHINE_ALLOWED_VARIANCE_KEYS
            == ("cgroup_memory_limit_bytes",),
        ),
        (
            "qualified_memory_variance_allowed",
            not _parent_machine_profile_changes(
                {"cgroup_memory_limit_bytes": 64 * 1024**3},
                {"cgroup_memory_limit_bytes": 32 * 1024**3},
            )
            and not _parent_memory_gate_errors(
                {"cgroup_memory_limit_bytes": 64 * 1024**3},
                {"cgroup_memory_limit_bytes": 32 * 1024**3},
            ),
        ),
        (
            "subclass_memory_rejected",
            bool(
                _parent_memory_gate_errors(
                    {"cgroup_memory_limit_bytes": 64 * 1024**3},
                    {"cgroup_memory_limit_bytes": 31 * 1024**3},
                )
            ),
        ),
        (
            "parent_machine_drift_still_detected",
            _parent_machine_profile_changes(
                {"effective_cpu_quota_count": 12},
                {"effective_cpu_quota_count": 11},
            )
            == ["effective_cpu_quota_count"],
        ),
        ("leading_underscore_present_private", rows[1]["query"].startswith("_")),
        (
            "leading_underscore_absent_public",
            "_hidden_symbol" not in json.dumps(public, sort_keys=True),
        ),
        ("authoring_only", public["decision"]["tournament_execution_authorized"] is False),
        ("zero_invalid", public["synthetic_matrix"]["all_invalid_hits_skipped_zero"]),
        ("no_private_input", public["synthetic_matrix"]["private_input_read"] is False),
    ]
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def run_fault_test() -> dict[str, Any]:
    rows = _synthetic_case_rows()
    base = _build_public_report(
        protocol_checkpoint="1" * 40,
        protocol_ci_run_id=1,
        protocol_ci_conclusion="success",
        case_rows=rows,
    )
    checks: list[tuple[str, bool]] = []
    mutations = {
        "invalid_skip_nonzero": lambda value: value["synthetic_matrix"].__setitem__(
            "all_invalid_hits_skipped_zero", False
        ),
        "private_input_read": lambda value: value["synthetic_matrix"].__setitem__(
            "private_input_read", True
        ),
        "execution_authorized": lambda value: value["decision"].__setitem__(
            "tournament_execution_authorized", True
        ),
        "case_missing": lambda value: value["synthetic_matrix"].__setitem__(
            "case_count", 3
        ),
        "runner_memory_gate_missing": lambda value: value["runner_gate"].__setitem__(
            "memory_limit_meets_frozen_b23_runner_class", False
        ),
        "query_leaked": lambda value: value.__setitem__("leak", "_hidden_symbol"),
        "digest_drift": lambda value: value.__setitem__(
            "qualification_digest", "b25qual_" + "0" * 64
        ),
    }
    for name, mutator in mutations.items():
        value = copy.deepcopy(base)
        mutator(value)
        checks.append((name, bool(validate_public_report(value))))
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B2.5 repaired-runtime qualification")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--fault-test", action="store_true")
    mode.add_argument("--validate-public", type=Path)
    args = parser.parse_args(argv)
    if args.self_test:
        print(json.dumps(run_self_test(), sort_keys=True))
        return 0
    if args.fault_test:
        print(json.dumps(run_fault_test(), sort_keys=True))
        return 0
    report = b2c.load_json(args.validate_public)
    errors = validate_public_report(report)
    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"Validation passed: {args.validate_public}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "B25RuntimeQualificationError",
    "B25_RUNTIME_QUALIFICATION_SCHEMA",
    "B25_RUNTIME_PRIVATE_SCHEMA",
    "B25_RUNTIME_QUALIFICATION_STATUS",
    "B25_RUNTIME_CASES",
    "qualification_digest",
    "private_receipt_digest",
    "validate_public_report",
    "validate_private_receipt",
    "qualify_runtime",
    "write_qualification_pair",
    "validate_runtime_binding",
    "run_self_test",
    "run_fault_test",
]
