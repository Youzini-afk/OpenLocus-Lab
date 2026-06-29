#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10aq_heldout_span_surface_source_discovery.v1"
PHASE = "BEA-v1-N10AQ Heldout Span-Surface Validation Source Discovery"
STATUS_PASS = "heldout_span_surface_source_discovery_pass_n10ar_authorized"
STATUS_NO_SOURCE = "no_go_n10aq_no_heldout_span_source_found"
STATUSES = (
    STATUS_PASS,
    STATUS_NO_SOURCE,
    "no_go_n10aq_candidate_sources_schema_invalid",
    "no_go_n10aq_candidate_sources_not_heldout",
    "no_go_n10aq_discovery_scope_invalid",
    "no_go_n10aq_privacy_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
DEFAULT_OUT = Path("artifacts/bea_v1_n10aq_heldout_span_surface_source_discovery/bea_v1_n10aq_heldout_span_surface_source_discovery_report.json")
N10AP_ARTIFACT = Path("artifacts/bea_v1_n10ap_adapter_enabled_variant_evaluator_result_audit_package/bea_v1_n10ap_adapter_enabled_variant_evaluator_result_audit_package_report.json")
N10AP_STATUS = "adapter_enabled_variant_evaluator_result_audit_package_complete_n10aq_authorized"
N10_SOURCE_SUFFIX = ".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl"
ROOT_BUCKETS = {
    "workspace_openlocus": Path("/workspace/OpenLocus"),
    "workspace_openlocus_lab": Path("/workspace/OpenLocus/OpenLocus-Lab"),
    "repo_research_private": Path("/workspace/OpenLocus/OpenLocus-Lab/.openlocus/research-private"),
    "tmp_opencode": Path("/tmp/opencode"),
    "tmp_local_recovery": Path("/tmp/local_n6xfr_recovery"),
}
MAX_SCANNED_ENTRIES = 50000
MAX_CANDIDATE_FILES_SNIFFED = 100
MAX_ROWS_SNIFFED_PER_FILE = 5
MIN_HELDOUT_ROWS = 50
FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "private_path", "source_path", "filename", "filenames", "file_name",
    "content", "raw_content", "raw_row", "raw_rows", "candidate", "candidates", "candidate_list", "candidate_order",
    "p4_evidence", "gold_path", "gold_paths", "gold_line", "gold_lines", "exact_rank", "raw_rank", "rank", "ranks", "score", "scores",
    "repo_id", "repo_name", "repo_url", "task_id", "source_id", "span", "spans", "snippet", "snippets",
    "hash", "hashes", "source_hash", "provider", "provider_payload", "raw_payload", "raw_diff", "diff",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "phase", "claim_level", "generated_by", "generated_at", "status_vocabulary",
    "input_artifact_bucket", "observed_status", "expected_status", "load_status", "forbidden_scan_status",
    "root_bucket", "scope_bucket", "candidate_source_bucket", "extension_bucket", "size_bucket", "schema_bucket",
    "row_count_bucket", "field_presence_bucket", "heldout_classification_bucket", "selection_bucket",
    "privacy_boundary_bucket", "no_execution_bucket", "n10ar_handoff_bucket", "authorization", "next_allowed_phase",
    "next_allowed_scope_bucket", "gate", "threshold_relation",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def root() -> Path:
    return Path(__file__).resolve().parent.parent


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_json(rel: Path) -> tuple[dict[str, Any], str]:
    full = root() / rel
    if not full.exists():
        return {}, "missing"
    try:
        obj = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (obj, "pass") if isinstance(obj, dict) else ({}, "parse_failed")


def write_json(rel: Path, data: dict[str, Any]) -> None:
    full = root() / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    location_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
    digest_re = re.compile(r"\b[0-9a-f]{40,64}\b", re.I)
    line_re = re.compile(r"\b(?:line|lines?)\s*[:=]?\s*\d+|\b\d+\s*-\s*\d+\b", re.I)

    def walk(value: Any, marker: str = "$") -> None:
        if isinstance(value, dict):
            for key, inner in value.items():
                key_s = str(key)
                if key_s in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_public_key", "location_bucket": "public_artifact"})
                walk(inner, marker + "." + key_s)
        elif isinstance(value, list):
            for inner in value:
                walk(inner, marker + "[]")
        elif isinstance(value, str):
            last = marker.rsplit(".", 1)[-1].split("[")[0]
            if last in SAFE_VALUE_KEYS:
                return
            if location_re.search(value):
                violations.append({"category": "location_like_value", "location_bucket": "public_artifact"})
            if digest_re.search(value):
                violations.append({"category": "digest_value", "location_bucket": "public_artifact"})
            if line_re.search(value):
                violations.append({"category": "span_like_value", "location_bucket": "public_artifact"})
    walk(obj)
    return violations


def scan_summary(obj: Any) -> dict[str, Any]:
    violations = scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "violation_categories": [{"category": k, "count": v} for k, v in sorted(counts.items())]}


def input_artifact_records() -> tuple[list[dict[str, Any]], bool]:
    artifact, load_status = load_json(N10AP_ARTIFACT)
    observed = str(artifact.get("status", "") or "")
    forbidden = artifact.get("forbidden_scan", {}).get("status", "pass") if isinstance(artifact.get("forbidden_scan"), dict) else "pass"
    ok = load_status == "pass" and observed == N10AP_STATUS and forbidden == "pass"
    return [{"anonymous_input_artifact_id": "n10aqin0000", "input_artifact_bucket": "n10ap_adapter_enabled_variant_audit_package_artifact", "load_status": load_status, "observed_status": observed, "expected_status": N10AP_STATUS, "forbidden_scan_status": str(forbidden), "input_gate_passed_bool": ok}], ok


def size_bucket(size: int) -> str:
    if size <= 0:
        return "none"
    if size < 100_000:
        return "small"
    if size < 5_000_000:
        return "medium"
    return "large"


def row_count_bucket(count: int) -> str:
    if count == 0:
        return "zero"
    if count < MIN_HELDOUT_ROWS:
        return "lt50"
    if count < 213:
        return "ge50_lt213"
    if count == 213:
        return "eq213"
    return "gt213"


def extension_bucket(path: Path) -> str:
    suffix = path.suffix.lower().strip(".")
    if suffix in {"json", "jsonl"}:
        return suffix
    return "other"


def is_candidate(path: Path) -> bool:
    if path.suffix.lower() not in {".json", ".jsonl"}:
        return False
    lowered = path.name.lower()
    return any(token in lowered for token in ("span", "evidence", "gold", "rank", "candidate", "outcome"))


def discover_candidates() -> tuple[list[Path], list[dict[str, Any]], bool, int, bool]:
    candidates: list[Path] = []
    scope_rows: list[dict[str, Any]] = []
    total_entries = 0
    caps_respected = True
    stop_all = False
    approved_roots_ok = True
    approved_resolved = {bucket: path.resolve() for bucket, path in ROOT_BUCKETS.items()}
    for idx, (bucket, base) in enumerate(ROOT_BUCKETS.items()):
        exists = base.exists()
        root_entries = 0
        root_candidates = 0
        if exists:
            for current, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs if d not in {".git", "target", "node_modules", "__pycache__"}]
                entry_count = len(dirs) + len(files)
                if total_entries + entry_count > MAX_SCANNED_ENTRIES:
                    entry_count = MAX_SCANNED_ENTRIES - total_entries
                    stop_all = True
                total_entries += entry_count
                root_entries += entry_count
                for file_name in files:
                    if stop_all:
                        break
                    p = Path(current) / file_name
                    try:
                        resolved = p.resolve()
                    except Exception:
                        continue
                    if not any(resolved == r or r in resolved.parents for r in approved_resolved.values()):
                        approved_roots_ok = False
                        continue
                    if is_candidate(p):
                        candidates.append(p)
                        root_candidates += 1
                if stop_all:
                    break
        scope_rows.append({"anonymous_discovery_scope_id": f"n10aqscope{idx:04d}", "root_bucket": bucket, "scope_bucket": "approved_bounded_local_root", "root_exists_bool": exists, "entry_count": root_entries, "candidate_file_count": root_candidates, "approved_root_bool": True})
        if stop_all:
            break
    unique_candidates = []
    seen = set()
    for p in candidates:
        key = str(p.resolve())
        if key not in seen:
            seen.add(key)
            unique_candidates.append(p)
    return unique_candidates[:MAX_CANDIDATE_FILES_SNIFFED], scope_rows, caps_respected and total_entries <= MAX_SCANNED_ENTRIES, total_entries, approved_roots_ok


def parse_json_line(line: str) -> Any:
    return json.loads(line)


def sniff_file(path: Path) -> dict[str, Any]:
    stat = path.stat()
    row_count = 0
    sample_rows: list[dict[str, Any]] = []
    parse_ok = True
    try:
        if path.suffix.lower() == ".jsonl":
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    row_count += 1
                    if len(sample_rows) < MAX_ROWS_SNIFFED_PER_FILE:
                        obj = parse_json_line(line)
                        if isinstance(obj, dict):
                            sample_rows.append(obj)
        else:
            obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            if isinstance(obj, list):
                row_count = len(obj)
                sample_rows = [x for x in obj[:MAX_ROWS_SNIFFED_PER_FILE] if isinstance(x, dict)]
            elif isinstance(obj, dict):
                rows = obj.get("rows") or obj.get("records") or obj.get("data")
                if isinstance(rows, list):
                    row_count = len(rows)
                    sample_rows = [x for x in rows[:MAX_ROWS_SNIFFED_PER_FILE] if isinstance(x, dict)]
                else:
                    row_count = 1
                    sample_rows = [obj]
    except Exception:
        parse_ok = False
    return {"row_count": row_count, "sample_rows": sample_rows, "parse_ok": parse_ok, "size": stat.st_size}


def schema_features(rows: list[dict[str, Any]]) -> dict[str, bool]:
    ordered_evidence = False
    evidence_line_fields = False
    gold_file_refs = False
    gold_ranges = False
    stable_ids = False
    for row in rows:
        evidence = row.get("p4_evidence") or row.get("evidence") or row.get("ordered_evidence")
        if isinstance(evidence, list):
            ordered_evidence = True
            for item in evidence[:5]:
                if isinstance(item, dict) and (("start_line" in item and "end_line" in item) or "line_range" in item or "range" in item):
                    evidence_line_fields = True
        if isinstance(row.get("gold_paths"), list) or isinstance(row.get("gold_files"), list) or isinstance(row.get("gold_file_refs"), list):
            gold_file_refs = True
        if isinstance(row.get("gold_lines"), list) or isinstance(row.get("gold_ranges"), list):
            gold_ranges = True
        if any(key in row for key in ("denominator_index_private", "row_id", "private_row_id", "case_id", "id")):
            stable_ids = True
    return {"ordered_evidence_bool": ordered_evidence, "evidence_line_fields_bool": evidence_line_fields, "gold_file_refs_bool": gold_file_refs, "gold_ranges_bool": gold_ranges, "stable_row_ids_bool": stable_ids}


def classify_same_as_n10(path: Path, row_count: int, features: dict[str, bool]) -> bool:
    suffix_match = str(path).endswith(N10_SOURCE_SUFFIX)
    exact_training_shape = row_count == 213 and all(features.values())
    return suffix_match or exact_training_shape


def inventory_and_sniff(candidates: list[Path]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], bool, int]:
    inventory: list[dict[str, Any]] = []
    sniff_rows: list[dict[str, Any]] = []
    eligibility: list[dict[str, Any]] = []
    eligible_private: list[dict[str, Any]] = []
    for idx, path in enumerate(candidates):
        try:
            sniff = sniff_file(path)
        except Exception:
            sniff = {"row_count": 0, "sample_rows": [], "parse_ok": False, "size": 0}
        features = schema_features(sniff["sample_rows"])
        same = classify_same_as_n10(path, int(sniff["row_count"]), features)
        schema_ok = sniff["parse_ok"] and sniff["row_count"] >= MIN_HELDOUT_ROWS and features["ordered_evidence_bool"] and features["evidence_line_fields_bool"] and features["gold_file_refs_bool"] and features["gold_ranges_bool"] and features["stable_row_ids_bool"]
        heldout = schema_ok and not same
        source_bucket = f"candidate_source_{idx:04d}"
        inventory.append({"anonymous_candidate_file_inventory_id": f"n10aqinv{idx:04d}", "candidate_source_bucket": source_bucket, "extension_bucket": extension_bucket(path), "size_bucket": size_bucket(int(sniff["size"])), "row_count_bucket": row_count_bucket(int(sniff["row_count"])), "schema_sniffed_bool": True})
        sniff_rows.append({"anonymous_schema_sniff_summary_id": f"n10aqsniff{idx:04d}", "candidate_source_bucket": source_bucket, "rows_sniffed_count": min(len(sniff["sample_rows"]), MAX_ROWS_SNIFFED_PER_FILE), "max_rows_sniffed_per_file": MAX_ROWS_SNIFFED_PER_FILE, "parse_success_bool": bool(sniff["parse_ok"]), "row_count_bucket": row_count_bucket(int(sniff["row_count"])), "field_presence_bucket": "span_surface_fields_present" if all(features.values()) else "span_surface_fields_incomplete", **features})
        eligibility_row = {"anonymous_heldout_eligibility_id": f"n10aqelig{idx:04d}", "candidate_source_bucket": source_bucket, "row_count_ge_50_bool": int(sniff["row_count"]) >= MIN_HELDOUT_ROWS, "ordered_evidence_available_bool": features["ordered_evidence_bool"], "evidence_line_fields_available_bool": features["evidence_line_fields_bool"], "gold_file_refs_available_bool": features["gold_file_refs_bool"], "gold_ranges_available_bool": features["gold_ranges_bool"], "stable_row_ids_available_bool": features["stable_row_ids_bool"], "same_as_n10_source_bool": same, "heldout_classification_bucket": "eligible_heldout" if heldout else ("not_heldout_same_as_n10_or_indistinguishable" if same else "schema_incomplete_or_too_small"), "eligible_for_n10ar_bool": heldout}
        eligibility.append(eligibility_row)
        if heldout:
            eligible_private.append(eligibility_row)
    return inventory, sniff_rows, eligibility, eligible_private, len(candidates) <= MAX_CANDIDATE_FILES_SNIFFED, len(candidates)


def source_selection_records(eligible_count: int) -> tuple[list[dict[str, Any]], bool]:
    selected = eligible_count >= 1
    return [{"anonymous_source_selection_id": "n10aqselect0000", "selection_bucket": "selected_heldout_source_available" if selected else "no_valid_heldout_span_surface_source", "eligible_heldout_source_count": eligible_count, "selected_source_has_ordered_evidence_bool": selected, "selected_source_has_gold_lines_bool": selected, "selected_source_row_count_ge_50_bool": selected, "selected_source_same_as_n10_bool": False if selected else True, "coverage_sufficient_bool": selected}], selected


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10aqprivacy0000", "privacy_boundary_bucket": "metadata_and_schema_sniff_only_no_public_source_details", "exact_location_public_bool": False, "private_filename_public_bool": False, "raw_row_public_bool": False, "candidate_list_public_bool": False, "gold_path_public_bool": False, "gold_line_public_bool": False, "exact_rank_public_bool": False, "span_public_bool": False, "snippet_public_bool": False, "hash_public_bool": False, "repo_or_task_id_public_bool": False, "privacy_boundary_valid_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10aqnoexec0000", "no_execution_bucket": "bounded_discovery_schema_sniff_only", "metric_validation_execution_count": 0, "n10ao_metric_rerun_count": 0, "n10al_metric_rerun_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "candidate_materialization_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "runtime_default_change_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10ar_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10ar_handoff_id": "n10aqhandoff0000", "n10ar_handoff_bucket": "n10ar_heldout_validation_authorized" if complete else "n10ar_not_authorized", "n10ar_heldout_validation_authorized_bool": complete, "selected_source_read_authorized_bool": complete, "direct_experiment_execution_authorized_bool": complete, "runtime_default_enablement_authorized_bool": False, "retrieval_or_rerun_authorized_bool": False}]


def gate_records(input_ok: bool, scope_ok: bool, cap_ok: bool, sniff_cap_ok: bool, source_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("n10ap_status", input_ok), ("approved_roots_only", scope_ok), ("entry_cap_respected", cap_ok), ("schema_sniff_cap_respected", sniff_cap_ok), ("eligible_heldout_source", source_ok), ("privacy_boundary", privacy_ok), ("no_forbidden_execution", noexec_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(passed), "threshold_relation": "equals", "value": int(passed), "threshold_value": 1} for name, passed in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10ar_heldout_validation_authorized" if complete else "n10ar_not_authorized", "next_allowed_phase": "BEA-v1-N10AR Heldout Span-Surface Validation" if complete else "none_until_heldout_span_surface_rows_are_supplied", "next_allowed_scope_bucket": "selected_heldout_source_validation_only" if complete else "no_next_phase", "n10ar_authorized": complete, "private_read_authorized": complete, "direct_experiment_execution_authorized": complete, "runtime_or_default_enablement_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, scope_ok: bool, cap_ok: bool, sniff_ok: bool, source_ok: bool, privacy_ok: bool, noexec_ok: bool, any_candidate_file: bool, any_complete_schema_candidate: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return STATUS_NO_SOURCE
    if not scope_ok or not cap_ok or not sniff_ok:
        return "no_go_n10aq_discovery_scope_invalid"
    if not any_candidate_file:
        return STATUS_NO_SOURCE
    if not any_complete_schema_candidate:
        return "no_go_n10aq_candidate_sources_schema_invalid"
    if not source_ok:
        return "no_go_n10aq_candidate_sources_not_heldout"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10aq_privacy_boundary_failed"
    return STATUS_PASS


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, input_ok = input_artifact_records()
    candidates, scope_rows, cap_ok, total_entries, approved_roots_ok = discover_candidates()
    inventory, sniff_rows, eligibility_rows, eligible_rows, sniff_cap_ok, sniffed_count = inventory_and_sniff(candidates)
    selection_rows, source_ok = source_selection_records(len(eligible_rows))
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    any_candidate_file = bool(sniff_rows)
    any_complete_schema_candidate = any(row.get("field_presence_bucket") == "span_surface_fields_present" and row.get("row_count_bucket") in {"ge50_lt213", "eq213", "gt213"} for row in sniff_rows)
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, approved_roots_ok, cap_ok, sniff_cap_ok, source_ok, privacy_ok, noexec_ok, any_candidate_file, any_complete_schema_candidate)
    complete = status == STATUS_PASS
    for row in scope_rows:
        row["total_scanned_entries"] = total_entries
        row["max_scanned_entries"] = MAX_SCANNED_ENTRIES
        row["cap_respected_bool"] = cap_ok
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "bounded_local_source_discovery_only", "generated_by": "bea_v1_n10aq_heldout_span_surface_source_discovery", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": inputs, "discovery_scope_records": scope_rows, "candidate_file_inventory_records": inventory, "schema_sniff_summary_records": sniff_rows, "heldout_eligibility_records": eligibility_rows, "source_selection_records": selection_rows, "privacy_boundary_records": privacy_rows, "no_forbidden_execution_records": noexec_rows, "n10ar_handoff_records": n10ar_handoff_records(complete), "gate_records": gate_records(input_ok, approved_roots_ok, cap_ok, sniff_cap_ok, source_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "aggregate_candidate_files_sniffed": sniffed_count, "aggregate_candidate_files_schema_sniffed": sniffed_count, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_PASS
    report["gate_records"] = gate_records(input_ok, approved_roots_ok, cap_ok, sniff_cap_ok, source_ok, privacy_ok, noexec_ok, scanner_ok)
    report["n10ar_handoff_records"] = n10ar_handoff_records(complete)
    report["stop_go_records"] = stop_go_records(complete)
    return report


def check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def parser_hides_unknown() -> bool:
    try:
        build_parser().parse_args(["--bad", "SECRET"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SECRET" not in str(exc)
    return False


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    inputs, input_ok = input_artifact_records()
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    sample = {"p4_evidence": [{"start_line": 1, "end_line": 2}], "gold_paths": ["x"], "gold_lines": [[1, 2]], "denominator_index_private": 1}
    features = schema_features([sample])
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_PASS, STATUS_NO_SOURCE, "no_go_n10aq_candidate_sources_schema_invalid", "no_go_n10aq_candidate_sources_not_heldout", "no_go_n10aq_discovery_scope_invalid", "no_go_n10aq_privacy_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_forbidden", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "p4_evidence", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("input", input_ok and len(inputs) == 1),
        check("approved_roots", set(ROOT_BUCKETS) == {"workspace_openlocus", "workspace_openlocus_lab", "repo_research_private", "tmp_opencode", "tmp_local_recovery"}),
        check("caps", MAX_SCANNED_ENTRIES == 50000 and MAX_CANDIDATE_FILES_SNIFFED == 100 and MAX_ROWS_SNIFFED_PER_FILE == 5),
        check("schema_features", all(features.values())),
        check("same_source_classification", classify_same_as_n10(Path(N10_SOURCE_SUFFIX), 213, features) is True),
        check("selection_no_source", source_selection_records(0)[0][0]["coverage_sufficient_bool"] is False),
        check("privacy", privacy_ok and privacy_rows[0]["exact_location_public_bool"] is False),
        check("no_execution", noexec_ok and noexec_rows[0]["metric_validation_execution_count"] == 0),
        check("handoff_no_go", n10ar_handoff_records(False)[0]["n10ar_heldout_validation_authorized_bool"] is False and stop_go_records(False)[0]["private_read_authorized"] is False),
        check("status_no_source", status_for(True, True, True, True, True, False, True, True, False, False) == STATUS_NO_SOURCE),
        check("status_schema_invalid", status_for(True, True, True, True, True, False, True, True, True, False) == "no_go_n10aq_candidate_sources_schema_invalid"),
        check("status_pass", status_for(True, True, True, True, True, True, True, True, True, True) == STATUS_PASS),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10AQ heldout span-surface source discovery")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checks, ok = run_self_test()
    if args.self_test:
        for item in checks:
            print(f"[{'PASS' if item['passed'] else 'FAIL'}] {item['name']}")
        print(f"self_test_passed={ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        raise SystemExit(0 if ok else 1)
    report = build_report(checks)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    write_json(args.out, report)
    selected = report["source_selection_records"][0]
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, eligible_heldout_sources={selected['eligible_heldout_source_count']})")


if __name__ == "__main__":
    main()
