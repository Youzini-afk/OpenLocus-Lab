#!/usr/bin/env python3
"""Phase 6B repo-heldout tiny strategy screen.

Reads existing ignored Phase 5B private rows only after explicit confirmation.
No source reads, repo fetches, new tasks, network calls, or reusable artifact.
Public report is aggregate-only and no-claim.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
PHASE = "phase6b_repo_heldout_strategy_selection_screen"
SCHEMA_VERSION = "phase6b_repo_heldout_strategy_selection_screen_public_report_v1"
STATUS_POSITIVE = "strategy_selection_screen_positive_no_claim"
STATUS_STOP = "stop_no_claim"
STATUS_REPAIR = "repair_strategy_selection_screen_no_claim"
DEFAULT_REPORT = REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
PHASE6A_REPORT = REPO / "artifacts" / "phase6a_strategy_selection_screen_protocol_freeze" / "phase6a_strategy_selection_screen_protocol_freeze_report.json"
PHASE5B_ROOT = REPO / "runs" / "phase5b_public_repo_formal_validation"
PHASE5B_ROWS_FILENAME = "phase5b_private_rows.jsonl"
PHASE5B_ROW_SCHEMA = "phase5b_public_repo_formal_validation_private_row_v1"
PHASE5B_PHASE = "interventional_evidence_acquisition_phase5b_public_repo_formal_validation"
PHASE6A_STATUS = "phase6a_strategy_selection_screen_protocol_freeze_no_claim"
LABELS = (
    "bm25_then_read_top1",
    "bm25_then_read_next_unique_file",
    "symbol_regex_then_read_top1",
    "symbol_regex_then_read_next_unique_file",
    "read_related_test_when_available",
    "stop",
    "abstain",
)
CONTROL_LABELS = {"stop", "abstain"}
PRIVATE_ROW_KEYS = {
    "schema_version", "phase", "row_index", "private_task_id", "repo_id",
    "action_label", "assignment_mode", "canary_mode", "candidate_found",
    "read_attempted", "materialized_current_source", "evidence_success",
    "failure_bucket", "private_materialization", "evidencecore", "privacy",
}
FORBIDDEN_PUBLIC_WORDS = re.compile(r"\b(winner|lift|product|default|runtime|training|selected method|beat|beats)\b", re.I)
LEAK_KEY_RE = re.compile(r"(private_task|task_id|repo_id|path|range|hash|snippet|run_dir|manifest|row_index|materialization)", re.I)
LEAK_VALUE_RE = re.compile(r"([A-Za-z]:)?[\\/][A-Za-z0-9_.\\/-]+|\b[a-f0-9]{32,}\b|\b\d+\s*-\s*\d+\b", re.I)


class ScreenError(Exception):
    pass


def bucket_count(count: int) -> str:
    if count <= 0:
        return "bucket_zero"
    if count <= 5:
        return "bucket_nonzero_to_five"
    if count <= 20:
        return "bucket_six_to_twenty"
    if count <= 50:
        return "bucket_twenty_one_to_fifty"
    if count <= 99:
        return "bucket_fifty_one_to_ninetynine"
    if count <= 150:
        return "bucket_hundred_to_task_cap"
    if count <= 1050:
        return "bucket_task_cap_to_row_cap"
    return "bucket_over_row_cap"


def bucket_shuffled_control_comparison(main_success: int, shuffled_success: int) -> str:
    gap = main_success - shuffled_success
    if gap <= 0:
        return "not_above_shuffled_control"
    if gap <= 5:
        return "above_shuffled_control_nonzero_to_five"
    if gap <= 20:
        return "above_shuffled_control_six_to_twenty"
    return "above_shuffled_control_over_twenty"


def bucket_rate(success: int, total: int) -> str:
    if total <= 0 or success <= 0:
        return "rate_zero"
    value = success / total
    if value < 0.25:
        return "rate_gt_zero_lt_quarter"
    if value < 0.50:
        return "rate_quarter_to_half"
    if value < 0.75:
        return "rate_half_to_three_quarters"
    if value < 1.0:
        return "rate_three_quarters_to_below_full"
    return "rate_full"


def path_is_ignored_runs(path: Path) -> bool:
    try:
        rel = path.resolve().relative_to(REPO.resolve())
    except ValueError:
        return False
    return bool(rel.parts) and rel.parts[0] == "runs"


def latest_rows_path() -> Path:
    candidates = sorted(PHASE5B_ROOT.glob(f"*/{PHASE5B_ROWS_FILENAME}"), key=lambda item: item.stat().st_mtime, reverse=True)
    if not candidates:
        raise ScreenError("no Phase 5B private rows found under ignored runs")
    return candidates[0]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path_is_ignored_runs(path):
        raise ScreenError("private input outside ignored runs refused")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ScreenError(f"private row {line_number} is not an object")
            rows.append(item)
    if not rows:
        raise ScreenError("private rows empty")
    return rows


def validate_phase6a_gate(path: Path = PHASE6A_REPORT) -> list[str]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Phase 6A gate unavailable: {exc}"]
    errors: list[str] = []
    if report.get("schema_version") != "phase6a_strategy_selection_screen_protocol_freeze_report_v1":
        errors.append("Phase 6A schema drift")
    if report.get("status") != PHASE6A_STATUS:
        errors.append("Phase 6A status not frozen")
    boundary = report.get("execution_boundary", {})
    for key in ("private_rows_read", "source_reads_executed", "new_tasks_or_repos_created", "model_fit_executed", "screen_execution_executed"):
        if boundary.get(key) is not False:
            errors.append(f"Phase 6A boundary drift: {key}")
    labels = report.get("phase6b_frozen_screen_design", {}).get("same_seven_labels_exact", [])
    if tuple(labels) != LABELS:
        errors.append("Phase 6A label freeze drift")
    return errors


def validate_private_rows(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    task_actions: dict[str, set[str]] = defaultdict(set)
    task_repos: dict[str, set[str]] = defaultdict(set)
    repos: set[str] = set()
    for row in rows:
        extra = set(row) - PRIVATE_ROW_KEYS
        missing = {"schema_version", "phase", "private_task_id", "repo_id", "action_label", "evidence_success", "evidencecore"} - set(row)
        if extra:
            errors.append("private row schema has unexpected keys")
        if missing:
            errors.append("private row schema missing required keys")
        if row.get("schema_version") != PHASE5B_ROW_SCHEMA or row.get("phase") != PHASE5B_PHASE:
            errors.append("private row identity drift")
        action = str(row.get("action_label", ""))
        if action not in LABELS:
            errors.append("private row label drift")
        task = str(row.get("private_task_id", ""))
        repo = str(row.get("repo_id", ""))
        if not task or not repo:
            errors.append("private row lacks task or repo group")
        task_actions[task].add(action)
        task_repos[task].add(repo)
        repos.add(repo)
        if action in CONTROL_LABELS and row.get("evidence_success") is True:
            errors.append("stop/abstain success nonzero")
        ec = row.get("evidencecore", {})
        if not isinstance(ec, dict):
            errors.append("EvidenceCore field missing")
            continue
        if ec.get("candidate_found_alone_is_evidence") is not False:
            errors.append("candidate-found evidence invariant drift")
        for key in ("success_requires_current_source_read", "success_requires_materialization", "success_requires_hash_currentness_task_tie"):
            if ec.get(key) is not True:
                errors.append(f"EvidenceCore invariant drift: {key}")
        if row.get("evidence_success") is True:
            for key in ("content_sha256_present", "currentness_reread_match", "range_content_match", "task_tie"):
                if ec.get(key) is not True:
                    errors.append(f"success without EvidenceCore {key}")
    for actions in task_actions.values():
        if actions != set(LABELS):
            errors.append("task does not have exactly seven labels")
    for grouped_repos in task_repos.values():
        if len(grouped_repos) != 1:
            errors.append("task spans multiple repo groups")
    if len(repos) < 2:
        errors.append("repo-heldout split requires at least two repo groups")
    if len(rows) > 1050:
        errors.append("private row hard cap exceeded")
    return sorted(set(errors))


def row_item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "repo": str(row["repo_id"]),
        "task": str(row["private_task_id"]),
        "action": str(row["action_label"]),
        "target": bool(row.get("evidence_success") is True),
    }


def action_counts(items: list[dict[str, Any]], *, shuffled: bool = False) -> dict[str, list[int]]:
    copied = [dict(item) for item in items]
    if shuffled and copied:
        shifted = [item["target"] for item in copied[1:]] + [copied[0]["target"]]
        for item, target in zip(copied, shifted):
            item["target"] = target
    table: dict[str, list[int]] = {label: [0, 0] for label in LABELS}
    for item in copied:
        table[item["action"]][1] += 1
        if item["target"]:
            table[item["action"]][0] += 1
    return table


def smoothed_rate(pair: list[int]) -> float:
    return (pair[0] + 1.0) / (pair[1] + 2.0)


def choose_action(train_items: list[dict[str, Any]], *, shuffled: bool = False) -> str:
    table = action_counts(train_items, shuffled=shuffled)
    return max(LABELS, key=lambda label: (smoothed_rate(table[label]), label))


def success_for_action(items: list[dict[str, Any]], action: str) -> int:
    return sum(1 for item in items if item["action"] == action and item["target"])


def repo_heldout_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    repos = sorted({item["repo"] for item in items})
    main_success = 0
    shuffled_success = 0
    folds = 0
    fixed_success = {label: 0 for label in LABELS}
    for repo in repos:
        train = [item for item in items if item["repo"] != repo]
        holdout = [item for item in items if item["repo"] == repo]
        if not train or not holdout:
            continue
        folds += 1
        main_action = choose_action(train, shuffled=False)
        shuffled_action = choose_action(train, shuffled=True)
        main_success += success_for_action(holdout, main_action)
        shuffled_success += success_for_action(holdout, shuffled_action)
        for label in LABELS:
            fixed_success[label] += success_for_action(holdout, label)
    return {
        "folds": folds,
        "main_success": main_success,
        "shuffled_success": shuffled_success,
        "fixed_control_success": max(fixed_success.values()) if fixed_success else 0,
        "stop_abstain_success": fixed_success.get("stop", 0) + fixed_success.get("abstain", 0),
    }


def contains_count_one(value: Any) -> bool:
    if isinstance(value, dict):
        return any(contains_count_one(child) for child in value.values())
    if isinstance(value, list):
        return any(contains_count_one(child) for child in value)
    return isinstance(value, str) and (
        "count_1" in value
        or "nonzero_lt_two" in value
        or "bucket_two_to_five" in value
        or value.startswith("delta_")
    )


def public_leak_errors(value: Any, path: str = "$", key: str = "") -> list[str]:
    errors: list[str] = []
    lowered = key.lower()
    allowed_false_flags = path.startswith("$.privacy_summary.") or path.startswith("$.authorization_attestation.")
    if LEAK_KEY_RE.search(lowered) and not allowed_false_flags:
        errors.append(f"private-shaped key at {path}")
    if isinstance(value, dict):
        for child_key, child in value.items():
            errors.extend(public_leak_errors(child, f"{path}.{child_key}" if path != "$" else f"$.{child_key}", str(child_key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(public_leak_errors(child, f"{path}[{index}]", ""))
    elif isinstance(value, str):
        if FORBIDDEN_PUBLIC_WORDS.search(value):
            errors.append(f"forbidden public wording at {path}")
        if LEAK_VALUE_RE.search(value) or "count_1" in value:
            errors.append(f"private-shaped or singleton value at {path}")
    return errors


def build_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    row_errors = validate_private_rows(rows)
    items = [row_item(row) for row in rows] if not row_errors else []
    counts = repo_heldout_counts(items) if items else {"folds": 0, "main_success": 0, "shuffled_success": 0, "fixed_control_success": 0, "stop_abstain_success": 0}
    task_count = len({item["task"] for item in items})
    repo_count = len({item["repo"] for item in items})
    nondegenerate = (
        counts["folds"] >= 2
        and counts["main_success"] > counts["shuffled_success"]
        and counts["stop_abstain_success"] == 0
        and not row_errors
    )
    status = STATUS_POSITIVE if nondegenerate else (STATUS_REPAIR if row_errors else STATUS_STOP)
    report = {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": status,
        "authorization_attestation": {
            "confirm_private_input_required": True,
            "confirm_private_input_used": True,
            "phase6a_gate_required": True,
            "phase6a_gate_passed": True,
            "private_rows_read_locally": True,
            "private_rows_published": False,
            "source_reads_executed": False,
            "new_tasks_or_repos_created": False,
            "network_used": False,
            "provider_or_remote_call_used": False,
            "model_fit_persisted": False,
            "release_setting_changed": False,
            "new_retrieval_family_added": False,
            "claim_made": False,
        },
        "frozen_boundary_summary": {
            "stdlib_only": True,
            "repo_heldout": True,
            "same_seven_labels_exact": list(LABELS),
            "feature_set": "action_label_only",
            "private_input_source": "existing_ignored_phase5b_rows_only",
            "reusable_artifact_written": False,
        },
        "aggregate_buckets": {
            "task_count_bucket": bucket_count(task_count),
            "repo_group_count_bucket": bucket_count(repo_count),
            "private_row_count_bucket": bucket_count(len(rows)),
            "fold_count_bucket": bucket_count(counts["folds"]),
            "main_screen_success_bucket": bucket_count(counts["main_success"]),
            "main_screen_rate_bucket": bucket_rate(counts["main_success"], task_count),
            "fixed_label_control_success_bucket": bucket_count(counts["fixed_control_success"]),
            "shuffled_target_control_success_bucket": bucket_count(counts["shuffled_success"]),
            "shuffled_control_comparison_bucket": bucket_shuffled_control_comparison(counts["main_success"], counts["shuffled_success"]),
            "stop_abstain_success_bucket": bucket_count(counts["stop_abstain_success"]),
            "private_row_validation_error_bucket": bucket_count(len(row_errors)),
        },
        "controls_summary": {
            "fixed_label_control_included": True,
            "action_only_control_same_as_main": True,
            "shuffled_target_control_included": True,
            "stop_abstain_control_zero_required": True,
        },
        "privacy_summary": {
            "publication_level": "aggregate_only",
            "raw_private_rows_public": False,
            "raw_task_ids_public": False,
            "repo_names_public": False,
            "paths_public": False,
            "ranges_public": False,
            "hashes_public": False,
            "snippets_public": False,
            "run_dirs_public": False,
            "manifests_public": False,
            "per_repo_or_fold_details_public": False,
            "singleton_buckets_public": False,
        },
        "interpretation": {
            "no_claim_boundary": True,
            "repo_heldout_screen_above_shuffled_control": counts["main_success"] > counts["shuffled_success"],
            "candidate_found_alone_counted": False,
            "requires_phase5b_evidencecore_success": True,
            "next_step": "write_phase6b_closeout_no_claim_summary_before_any_new_empirical_step",
        },
        "validation_summary": {
            "route_specific_validation": "pending",
            "self_test_available": True,
        },
    }
    validation_errors = validate_report(report, include_pending=False)
    report["validation_summary"]["route_specific_validation"] = "passed" if not validation_errors else "failed"
    return report


def validate_report(report: Any, *, include_pending: bool = True) -> list[str]:
    if not isinstance(report, dict):
        return ["report must be object"]
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION or report.get("phase") != PHASE:
        errors.append("identity drift")
    if report.get("status") not in {STATUS_POSITIVE, STATUS_STOP, STATUS_REPAIR}:
        errors.append("status drift")
    auth = report.get("authorization_attestation", {})
    for key in ("private_rows_published", "source_reads_executed", "new_tasks_or_repos_created", "network_used", "provider_or_remote_call_used", "model_fit_persisted", "release_setting_changed", "new_retrieval_family_added", "claim_made"):
        if auth.get(key) is not False:
            errors.append(f"authorization boundary failed: {key}")
    for key in ("confirm_private_input_required", "confirm_private_input_used", "phase6a_gate_required", "phase6a_gate_passed", "private_rows_read_locally"):
        if auth.get(key) is not True:
            errors.append(f"authorization attestation missing: {key}")
    frozen = report.get("frozen_boundary_summary", {})
    if tuple(frozen.get("same_seven_labels_exact", [])) != LABELS:
        errors.append("label set drift")
    if frozen.get("stdlib_only") is not True or frozen.get("repo_heldout") is not True or frozen.get("reusable_artifact_written") is not False:
        errors.append("frozen boundary drift")
    if report.get("aggregate_buckets", {}).get("stop_abstain_success_bucket") != "bucket_zero":
        errors.append("stop/abstain success nonzero")
    buckets = report.get("aggregate_buckets", {})
    if "main_minus_shuffled_bucket" in buckets:
        errors.append("minus-shaped control comparison is public")
    if "shuffled_control_comparison_bucket" not in buckets:
        errors.append("shuffled control comparison bucket missing")
    privacy = report.get("privacy_summary", {})
    if privacy.get("publication_level") != "aggregate_only":
        errors.append("publication level drift")
    for key in ("raw_private_rows_public", "raw_task_ids_public", "repo_names_public", "paths_public", "ranges_public", "hashes_public", "snippets_public", "run_dirs_public", "manifests_public", "per_repo_or_fold_details_public", "singleton_buckets_public"):
        if privacy.get(key) is not False:
            errors.append(f"privacy boundary failed: {key}")
    if contains_count_one(report):
        errors.append("singleton count bucket public")
    errors.extend(public_leak_errors(report))
    if include_pending and report.get("validation_summary", {}).get("route_specific_validation") != "passed":
        errors.append("route-specific validation not passed")
    return sorted(set(errors))


def write_report(report: dict[str, Any], output: Path) -> None:
    errors = validate_report(report)
    if errors:
        raise ScreenError("public report validation failed: " + "; ".join(errors[:10]))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_screen(confirm_private_input: bool, rows_path: Path | None, output: Path) -> dict[str, Any]:
    if not confirm_private_input:
        raise ScreenError("--confirm-private-input is required before reading ignored private rows")
    gate_errors = validate_phase6a_gate()
    if gate_errors:
        raise ScreenError("Phase 6A gate failed: " + "; ".join(gate_errors[:6]))
    path = rows_path if rows_path is not None else latest_rows_path()
    rows = load_jsonl(path)
    report = build_report(rows)
    write_report(report, output)
    return report


def sample_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    idx = 0
    for repo in ("repo_a", "repo_b", "repo_c"):
        for task_num in range(4):
            task = f"{repo}_task_{task_num}"
            for label in LABELS:
                success = label == "symbol_regex_then_read_top1" and task_num in {0, 1}
                rows.append({
                    "schema_version": PHASE5B_ROW_SCHEMA,
                    "phase": PHASE5B_PHASE,
                    "row_index": idx,
                    "private_task_id": task,
                    "repo_id": repo,
                    "action_label": label,
                    "assignment_mode": "deterministic_full_panel_all_frozen_labels",
                    "canary_mode": False,
                    "candidate_found": label not in CONTROL_LABELS,
                    "read_attempted": label not in CONTROL_LABELS,
                    "materialized_current_source": label not in CONTROL_LABELS,
                    "evidence_success": success,
                    "failure_bucket": "none" if success else ("control_no_acquisition" if label in CONTROL_LABELS else "no_task_tie"),
                    "private_materialization": {"content_sha256_private": "a" * 64} if success else {},
                    "evidencecore": {
                        "candidate_found_alone_is_evidence": False,
                        "success_requires_current_source_read": True,
                        "success_requires_materialization": True,
                        "success_requires_hash_currentness_task_tie": True,
                        "content_sha256_present": success,
                        "currentness_reread_match": success,
                        "range_content_match": success,
                        "task_tie": success,
                    },
                    "privacy": {
                        "private_row": True,
                        "public_artifact_allowed": False,
                        "provider_network_used": False,
                        "llm_used": False,
                        "search_api_used": False,
                        "remote_model_used": False,
                        "model_training_executed": False,
                        "runtime_default_changed": False,
                        "new_retrieval_family_added": False,
                    },
                })
                idx += 1
    return rows


def run_self_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    rows = sample_rows()
    checks.append(("sample_private_rows_valid", not validate_private_rows(rows)))
    report = build_report(rows)
    checks.append(("sample_report_valid", not validate_report(report)))
    checks.append(("sample_status_positive", report["status"] == STATUS_POSITIVE))
    mutated_rows = copy.deepcopy(rows)
    for row in mutated_rows:
        if row["action_label"] == "stop":
            row["evidence_success"] = True
            break
    checks.append(("stop_success_rejected", bool(validate_private_rows(mutated_rows))))
    mutated_report = copy.deepcopy(report)
    mutated_report["privacy_summary"]["paths_public"] = True
    checks.append(("privacy_mutation_rejected", bool(validate_report(mutated_report))))
    mutated_report = copy.deepcopy(report)
    mutated_report["frozen_boundary_summary"]["same_seven_labels_exact"] = list(LABELS[:-1])
    checks.append(("label_mutation_rejected", bool(validate_report(mutated_report))))
    mutated_report = copy.deepcopy(report)
    mutated_report["interpretation"]["next_step"] = "winner"
    checks.append(("claim_word_rejected", bool(validate_report(mutated_report))))
    try:
        run_screen(False, None, DEFAULT_REPORT)
        refused = False
    except ScreenError:
        refused = True
    checks.append(("refuses_without_confirm", refused))
    with tempfile.TemporaryDirectory(prefix="phase6b_selftest_") as tmp:
        outside = Path(tmp) / "rows.jsonl"
        outside.write_text("{}\n", encoding="utf-8")
        try:
            load_jsonl(outside)
            outside_refused = False
        except ScreenError:
            outside_refused = True
    checks.append(("outside_runs_refused", outside_refused))
    failed = [name for name, ok in checks if not ok]
    if failed:
        raise ScreenError("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 6B repo-heldout strategy screen")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--validate-report", type=Path)
    parser.add_argument("--confirm-private-input", action="store_true")
    parser.add_argument("--rows", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            print(json.dumps(run_self_test(), indent=2, sort_keys=True))
            return 0
        if args.validate_report:
            report = json.loads(args.validate_report.read_text(encoding="utf-8"))
            errors = validate_report(report)
            if errors:
                for error in errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print("Validation passed")
            return 0
        report = run_screen(args.confirm_private_input, args.rows, args.output)
        print(json.dumps({"status": report["status"], "public_report_written": True, "private_rows_read_under_confirm": True}, indent=2, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, ScreenError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
