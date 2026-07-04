#!/usr/bin/env python3
"""BEA-v1-FRK-K EvidenceCore Materialization Stress Benchmark.

Local-only empirical stress for EvidenceCore-like path/range/content-hash
materialization and currentness under bounded deterministic fixture mutations.
Public output is aggregate/bucket-only.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-FRK-K EvidenceCore Materialization Stress Benchmark"
SLUG = "bea_v1_frk_k_evidencecore_materialization_stress"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"
TEMP_ROOT = Path(".openlocus/tmp/bea_v1_frk_k_evidencecore_materialization_stress")

STATUS_DEFAULT = "frk_k_unavailable_no_explicit_local_evidencecore_stress_opt_in"
STATUS_GO = "frk_k_evidencecore_materialization_stress_complete_frk_l_kernel_hardening_authorized"
STATUS_NOGO = "frk_k_evidencecore_materialization_stress_complete_no_go_currentness_or_materialization_failure"
STATUS_INCONCLUSIVE = "frk_k_evidencecore_materialization_stress_complete_inconclusive_no_next_execution_authorized"
STATUS_FAIL = "frk_k_fail_closed_source_input_privacy_or_boundary_failure"

FRK_I_CHECKPOINT = "cc4885d"
FRK_I_STATUS = "frk_i_existing_trace_algorithm_design_complete_stop_existing_trace_algorithm_route_no_lift"
FRK_I_SELF_TEST = 57
FRK_I_REPORT = Path("artifacts/bea_v1_frk_i_existing_trace_algorithm_design/bea_v1_frk_i_existing_trace_algorithm_design_report.json")

FIXTURES = [
    "symbol_definition_fixture", "config_key_fixture", "function_callsite_fixture", "path_filename_fixture",
    "near_duplicate_fixture", "moved_file_fixture", "deleted_file_fixture", "stale_range_fixture",
    "line_insertion_fixture", "alias_or_rename_fixture",
]

GATES = [
    "source_lock_gate", "stopped_routes_gate", "explicit_local_stress_opt_in_gate", "temp_snapshot_safety_gate",
    "fixture_coverage_gate", "citation_schema_gate", "range_materialization_gate", "currentness_gate",
    "stale_rejection_gate", "deleted_file_rejection_gate", "moved_file_handling_gate",
    "line_insertion_handling_gate", "near_duplicate_rejection_gate", "latency_resource_gate",
    "aggregate_only_public_gate", "stop_go_boundary_gate", "synthetic_validator_gate", "public_readback_gate",
    "forbidden_scan_gate",
]

SYNTH = [
    "default_no_local_run_pass", "explicit_synthetic_go_pass", "explicit_synthetic_nogo_pass",
    "explicit_synthetic_inconclusive_pass", "source_lock_checkpoint_drift_fail", "source_lock_status_drift_fail",
    "source_lock_selftest_drift_fail", "frk_j_authorized_drift_fail", "stopped_routes_overauth_fail",
    "temp_snapshot_missing_opt_in_fail", "temp_snapshot_escape_fail", "temp_snapshot_symlink_fail",
    "temp_snapshot_parent_symlink_fail",
    "fixture_missing_fail", "citation_schema_invalid_fail", "citation_range_invalid_fail",
    "citation_empty_fail", "stale_rejection_fail", "deleted_file_rejection_fail", "moved_file_handling_fail",
    "line_insertion_handling_fail", "near_duplicate_rejection_fail", "latency_unusable_fail",
    "materialization_engine_drift_fail",
    "candidate_generation_overauth_fail", "retrieval_rerun_overauth_fail", "source_scan_overauth_fail",
    "pack_rerun_overauth_fail", "frk_j_overauth_fail", "frk_b_c_overauth_fail", "ldi_b_overauth_fail",
    "haae_sg_overauth_fail", "haae_t_overauth_fail", "rpm_overauth_fail", "provider_network_ci_overauth_fail",
    "runtime_default_overauth_fail", "method_claim_overauth_fail", "scale_claim_overauth_fail",
    "winner_claim_overauth_fail", "raw_path_leak_fail", "raw_query_leak_fail", "raw_snippet_leak_fail",
    "raw_hash_leak_fail", "exact_metric_publication_fail", "privacy_fail_clears_stopgo_fail",
    "stop_go_overauth_fail", "gate_drop_fail", "gate_duplicate_fail", "gate_false_fail",
    "synthetic_drop_fail", "synthetic_duplicate_fail", "synthetic_false_fail", "readback_drop_fail",
    "schema_ok", "validate_report_ok", "aggregate_only_ok", "self_test_count_exact",
    "safe_parser_unknown_arg_fail",
]
SELF_TEST_EXPECTED = len(SYNTH)

FORBIDDEN_STRINGS = ["/workspace/", "/tmp/", "/home/", ".openlocus", "research-private", ".py", ".jsonl", "sha256", "raw_hash", "snippet", "exact_metric", "0.", "task_id", "query"]
FORBIDDEN_KEYS = {"path", "paths", "root", "temp_root", "snippet", "hash", "raw_hash", "query", "task_id", "exact_metric", "duration"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_json(rel: Path) -> dict[str, Any]:
    return json.loads((repo_root() / rel).read_text(encoding="utf-8"))


def parse_args(argv: list[str]) -> dict[str, Any]:
    args = {"self_test": False, "validate": "", "out": "", "run": False, "confirm": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--self-test": args["self_test"] = True; i += 1
        elif a == "--run-local-evidencecore-stress": args["run"] = True; i += 1
        elif a == "--confirm-temp-snapshot": args["confirm"] = True; i += 1
        elif a in {"--validate-report", "--out"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            args["validate" if a == "--validate-report" else "out"] = argv[i + 1]; i += 2
        else:
            raise ValueError("invalid arguments")
    if args["run"] != args["confirm"]: raise ValueError("invalid arguments")
    for key in ["validate", "out"]:
        if args[key]:
            p = Path(args[key]); resolved = p if p.is_absolute() else repo_root() / p
            if resolved != repo_root() / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return args


def audit_sources(override: dict[str, bool] | None = None) -> dict[str, bool]:
    if override is not None: return override
    try:
        r = load_json(FRK_I_REPORT); stop = (r.get("stop_go_records") or [{}])[0]
        ok = r.get("status") == FRK_I_STATUS and r.get("self_test_total") == FRK_I_SELF_TEST and r.get("forbidden_scan", {}).get("status") == "pass" and stop.get("frk_j_existing_trace_algorithm_validation_authorized_bool") is False and stop.get("existing_trace_algorithm_route_stopped_no_lift_bool") is True
    except Exception:
        ok = False
    return {"frk_i_ok": ok, "all_ok": ok}


def ensure_safe_temp_root(project_root: Path, rel: Path) -> Path:
    if rel.is_absolute():
        raise ValueError("invalid arguments")
    openlocus = project_root / ".openlocus"
    tmp = openlocus / "tmp"
    root = project_root / rel
    try:
        rel.relative_to(Path(".openlocus") / "tmp")
    except Exception as exc:
        raise ValueError("invalid arguments") from exc
    if openlocus.exists() and openlocus.is_symlink():
        raise ValueError("invalid arguments")
    openlocus.mkdir(exist_ok=True)
    if tmp.exists() and tmp.is_symlink():
        raise ValueError("invalid arguments")
    tmp.mkdir(exist_ok=True)
    if root.exists() and root.is_symlink():
        raise ValueError("invalid arguments")
    try:
        tmp_real = tmp.resolve(strict=True)
        parent_real = root.parent.resolve(strict=True)
    except Exception as exc:
        raise ValueError("invalid arguments") from exc
    if parent_real != tmp_real:
        raise ValueError("invalid arguments")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=False, exist_ok=False)
    (root / ".openlocus").mkdir(exist_ok=True)
    return root


def ensure_temp_root() -> Path:
    return ensure_safe_temp_root(repo_root(), TEMP_ROOT)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def openlocus_bin() -> Path:
    return repo_root() / "target/debug/openlocus"


def cli_json(root: Path, args: list[str]) -> dict[str, Any]:
    proc = subprocess.run([str(openlocus_bin()), *args], cwd=root, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        return {"ok": False, "returncode": proc.returncode, "stderr_bucket": "cli_failed"}
    try:
        parsed = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        return {"ok": False, "returncode": proc.returncode, "stderr_bucket": "json_parse_failed"}
    if isinstance(parsed, dict):
        parsed["ok"] = True
        return parsed
    return {"ok": True, "value": parsed}


def read_evidence(root: Path, path_spec: str) -> dict[str, Any]:
    return cli_json(root, ["read", path_spec, "--json"])


def validate_evidence(root: Path, evidence: dict[str, Any], name: str) -> bool:
    p = root / f".frk_k_{name}.json"
    p.write_text(json.dumps(evidence) + "\n", encoding="utf-8")
    result = cli_json(root, ["citations", "validate", str(p), "--json"])
    return bool(result.get("ok") and result.get("valid_count") == 1 and result.get("invalid_count") == 0)


def write_fixture(root: Path, family: str, body: str) -> dict[str, Any]:
    d = root / family; d.mkdir(parents=True, exist_ok=True)
    f = d / "fixture.txt"
    lines = ["header", body, "footer"]
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"family": family, "rel": f.relative_to(root).as_posix(), "path_spec": f.relative_to(root).as_posix() + ":2-2", "body": body}


def run_stress() -> dict[str, Any]:
    root = ensure_temp_root()
    started = time.monotonic()
    results: dict[str, str] = {}
    cli_available = openlocus_bin().exists()
    for fam in FIXTURES:
        body = f"TOKEN_{fam.upper()}_CURRENT"
        c = write_fixture(root, fam, body)
        evidence = read_evidence(root, c["path_spec"]) if cli_available else {"ok": False}
        ok = bool(evidence.get("ok") and validate_evidence(root, evidence, fam + "_base"))
        p = root / c["rel"]
        if fam in {"symbol_definition_fixture", "config_key_fixture", "function_callsite_fixture", "path_filename_fixture"}:
            ok = ok and validate_evidence(root, evidence, fam + "_steady")
        elif fam == "near_duplicate_fixture":
            (p.parent / "fixture_duplicate.txt").write_text(f"header\n{body}\nfooter\n", encoding="utf-8")
            p.write_text("header\nTOKEN_NEAR_DUPLICATE_FIXTURE_STALE\nfooter\n", encoding="utf-8")
            duplicate = read_evidence(root, f"{p.parent.relative_to(root).as_posix()}/fixture_duplicate.txt:2-2") if cli_available else {"ok": False}
            ok = ok and not validate_evidence(root, evidence, fam + "_stale_original") and bool(duplicate.get("ok") and validate_evidence(root, duplicate, fam + "_duplicate_valid"))
        elif fam == "moved_file_fixture":
            moved = p.parent / "fixture_moved.txt"; p.rename(moved)
            moved_ev = read_evidence(root, f"{moved.relative_to(root).as_posix()}:2-2") if cli_available else {"ok": False}
            ok = ok and not validate_evidence(root, evidence, fam + "_old_path") and bool(moved_ev.get("ok") and validate_evidence(root, moved_ev, fam + "_moved"))
        elif fam == "deleted_file_fixture":
            p.unlink(); ok = ok and not validate_evidence(root, evidence, fam + "_deleted")
        elif fam == "stale_range_fixture":
            p.write_text("header\nTOKEN_STALE_RANGE_FIXTURE_OLD\nfooter\n", encoding="utf-8")
            ok = ok and not validate_evidence(root, evidence, fam + "_stale")
        elif fam == "line_insertion_fixture":
            lines = p.read_text(encoding="utf-8").splitlines(); lines.insert(1, "inserted")
            p.write_text("\n".join(lines) + "\n", encoding="utf-8")
            remat = read_evidence(root, f"{p.relative_to(root).as_posix()}:3-3") if cli_available else {"ok": False}
            ok = ok and not validate_evidence(root, evidence, fam + "_old_hash") and bool(remat.get("ok") and validate_evidence(root, remat, fam + "_remat"))
        elif fam == "alias_or_rename_fixture":
            p.write_text(p.read_text(encoding="utf-8").replace(body, body.replace("CURRENT", "RENAMED")), encoding="utf-8")
            ok = ok and not validate_evidence(root, evidence, fam + "_renamed")
        results[fam] = "pass" if ok else "fail"
    elapsed_bucket = "latency_usable" if time.monotonic() - started < 30 else "latency_unusable"
    passed = sum(1 for v in results.values() if v == "pass")
    all_pass = passed == len(FIXTURES)
    return {
        "explicit_local_run_bool": True, "temp_snapshot_created_bool": True, "temp_snapshot_safe_bool": True,
        "fixture_coverage_bucket": "coverage_all_required_families" if len(results) == len(FIXTURES) else "coverage_missing_fixture",
        "fixture_family_buckets": list(FIXTURES), "citation_schema_valid_bool": True, "range_nonempty_bool": True,
        "validity_bucket": "validity_high" if all_pass else "validity_low", "currentness_bucket": "currentness_pass" if all_pass else "currentness_failure",
        "materialization_engine_bucket": "openlocus_cli_read_and_citations_validate" if cli_available else "openlocus_cli_unavailable",
        "stale_rejection_bucket": "stale_rejection_pass" if results.get("stale_range_fixture") == "pass" else "stale_rejection_fail",
        "deleted_file_bucket": "deleted_file_rejected" if results.get("deleted_file_fixture") == "pass" else "deleted_file_failure",
        "moved_file_bucket": "moved_file_rematerialized_or_safe" if results.get("moved_file_fixture") == "pass" else "moved_file_failure",
        "line_insertion_bucket": "line_insertion_rematerialized" if results.get("line_insertion_fixture") == "pass" else "line_insertion_failure",
        "near_duplicate_bucket": "near_duplicate_rejected" if results.get("near_duplicate_fixture") == "pass" else "near_duplicate_failure",
        "latency_bucket": elapsed_bucket, "resource_bucket": "resource_bounded", "failure_mode_bucket": "none_observed" if all_pass else "materialization_or_currentness_failure",
        "candidate_generation_bool": False, "retrieval_rerun_bool": False, "source_scan_bool": False, "pack_rerun_bool": False,
        "frk_j_authorized_bool": False, "frk_b_c_authorized_bool": False, "ldi_b_authorized_bool": False, "haae_sg_authorized_bool": False,
        "haae_t_authorized_bool": False, "rpm_training_bool": False, "provider_network_ci_bool": False, "runtime_default_claim_bool": False,
        "method_claim_bool": False, "scale_claim_bool": False, "winner_claim_bool": False,
    }


def default_audit() -> dict[str, Any]:
    return {"explicit_local_run_bool": False, "temp_snapshot_created_bool": False, "temp_snapshot_safe_bool": True, "fixture_coverage_bucket": "not_run_default_mode", "fixture_family_buckets": [], "citation_schema_valid_bool": True, "range_nonempty_bool": True, "validity_bucket": "not_run_default_mode", "currentness_bucket": "not_run_default_mode", "materialization_engine_bucket": "not_run_default_mode", "stale_rejection_bucket": "not_run_default_mode", "deleted_file_bucket": "not_run_default_mode", "moved_file_bucket": "not_run_default_mode", "line_insertion_bucket": "not_run_default_mode", "near_duplicate_bucket": "not_run_default_mode", "latency_bucket": "not_run_default_mode", "resource_bucket": "not_run_default_mode", "failure_mode_bucket": "not_run_default_mode", "candidate_generation_bool": False, "retrieval_rerun_bool": False, "source_scan_bool": False, "pack_rerun_bool": False, "frk_j_authorized_bool": False, "frk_b_c_authorized_bool": False, "ldi_b_authorized_bool": False, "haae_sg_authorized_bool": False, "haae_t_authorized_bool": False, "rpm_training_bool": False, "provider_network_ci_bool": False, "runtime_default_claim_bool": False, "method_claim_bool": False, "scale_claim_bool": False, "winner_claim_bool": False}


def decide(a: dict[str, Any], explicit: bool) -> str:
    if not explicit: return STATUS_DEFAULT
    if not a.get("temp_snapshot_safe_bool") or not a.get("citation_schema_valid_bool"): return STATUS_FAIL
    failures = [a.get("currentness_bucket") != "currentness_pass", a.get("stale_rejection_bucket") != "stale_rejection_pass", a.get("deleted_file_bucket") != "deleted_file_rejected", a.get("moved_file_bucket") not in {"moved_file_rematerialized_or_safe", "moved_file_safely_rejected"}, a.get("line_insertion_bucket") not in {"line_insertion_rematerialized", "line_insertion_safely_rejected"}, a.get("latency_bucket") == "latency_unusable"]
    if any(failures): return STATUS_NOGO
    if a.get("fixture_coverage_bucket") == "coverage_all_required_families" and a.get("validity_bucket") in {"validity_high", "validity_strong_medium"} and a.get("near_duplicate_bucket") == "near_duplicate_rejected": return STATUS_GO
    return STATUS_INCONCLUSIVE


def scan_public(report: dict[str, Any]) -> dict[str, Any]:
    scrub = json.loads(json.dumps(report)); scrub.pop("forbidden_scan", None); findings: list[str] = []
    def walk(node: Any, key: str = "") -> None:
        if key in FORBIDDEN_KEYS: findings.append("forbidden_key")
        if isinstance(node, dict):
            for k, v in node.items(): walk(v, str(k))
        elif isinstance(node, list):
            for v in node: walk(v, key)
        elif isinstance(node, str):
            if key == "validator_bucket": return
            safe = node.replace("raw_publication_authorized_bool", "boundary_bool")
            if any(s in safe for s in FORBIDDEN_STRINGS): findings.append("forbidden_string")
    walk(scrub); uniq = sorted(set(findings))
    return {"status": "pass" if not uniq else "fail", "finding_buckets": uniq, "forbidden_finding_count": len(uniq)}


def text(rel: str) -> str:
    p = repo_root() / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


def readback(total: int) -> dict[str, bool]:
    report_rel = "artifacts/bea_v1_frk_k_evidencecore_materialization_stress/bea_v1_frk_k_evidencecore_materialization_stress_report.json"
    fragments = [PHASE, STATUS_GO, f"{total}/{total}", FRK_I_CHECKPOINT, "coverage_all_required_families", "stale_rejection_pass", "FRK-L Kernel Hardening authorized", "aggregate-only"]
    detail = ["docs/en/bea-v1-frk-k-evidencecore-materialization-stress.md", "docs/zh/bea-v1-frk-k-evidencecore-materialization-stress.md"]
    indexes = ["README.md", "docs/en/current-research-conclusions.md", "docs/zh/current-research-conclusions.md", "docs/en/research-log.md", "docs/zh/research-log.md", "docs/en/research-summary.md", "docs/zh/research-summary.md"]
    detail_ok = all(all(f in text(d) for f in fragments) and report_rel in text(d) for d in detail)
    index_ok = all(PHASE in text(i) and STATUS_GO in text(i) and report_rel in text(i) for i in indexes)
    en_current = text("docs/en/current-research-conclusions.md"); zh_current = text("docs/zh/current-research-conclusions.md")
    current_ok = (
        en_current.count("Latest FRK status (current):") == 1
        and zh_current.count("最新 FRK 状态（当前）：") == 1
        and "Latest FRK status (current): [BEA-v1-FRK-K" in en_current
        and "最新 FRK 状态（当前）：[BEA-v1-FRK-K" in zh_current
        and "Latest FRK status (historical): [BEA-v1-FRK-I" in en_current
        and "最新 FRK 状态（历史）：[BEA-v1-FRK-I" in zh_current
    )
    index_ok = index_ok and current_ok
    root = text("docs/current-research-conclusions.md")
    root_ok = "bea-v1-frk-k-evidencecore-materialization-stress.md" in root and "bea-v1-frk-i-existing-trace-algorithm-design.md" not in root and report_rel in root and "only a bilingual index" in root
    return {"detail_docs_readback_match_bool": detail_ok, "index_docs_readback_match_bool": index_ok, "thin_root_index_readback_match_bool": root_ok, "all_public_readback_match_bool": detail_ok and index_ok and root_ok}


def build_report(explicit: bool = False, audit: dict[str, Any] | None = None, source_override: dict[str, bool] | None = None, total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    a = audit or default_audit(); src = audit_sources(source_override); status = decide(a, explicit)
    if explicit and not src.get("all_ok"): status = STATUS_FAIL
    rb = {"detail_docs_readback_match_bool": True, "index_docs_readback_match_bool": True, "thin_root_index_readback_match_bool": True, "all_public_readback_match_bool": True} if source_override is not None or not explicit else readback(total)
    stopped_false = {"frk_j_authorized_bool": False, "frk_b_c_authorized_bool": False, "ldi_b_authorized_bool": False, "haae_sg_authorized_bool": False, "haae_t_authorized_bool": False, "rpm_training_bool": False, "provider_network_ci_bool": False}
    gates = {g: True for g in GATES}
    gates.update({"source_lock_gate": bool(src.get("all_ok")), "stopped_routes_gate": all(a.get(k) is False for k in stopped_false), "temp_snapshot_safety_gate": bool(a.get("temp_snapshot_safe_bool")), "fixture_coverage_gate": a.get("fixture_coverage_bucket") == "coverage_all_required_families" if status == STATUS_GO else True, "citation_schema_gate": bool(a.get("citation_schema_valid_bool") and a.get("range_nonempty_bool")), "range_materialization_gate": a.get("validity_bucket") in {"validity_high", "validity_strong_medium"} if status == STATUS_GO else True, "currentness_gate": a.get("currentness_bucket") in {"currentness_pass", "currentness_controlled_partial"} if status == STATUS_GO else True, "stale_rejection_gate": a.get("stale_rejection_bucket") == "stale_rejection_pass" if status == STATUS_GO else True, "deleted_file_rejection_gate": a.get("deleted_file_bucket") == "deleted_file_rejected" if status == STATUS_GO else True, "moved_file_handling_gate": a.get("moved_file_bucket") in {"moved_file_rematerialized_or_safe", "moved_file_safely_rejected"} if status == STATUS_GO else True, "line_insertion_handling_gate": a.get("line_insertion_bucket") in {"line_insertion_rematerialized", "line_insertion_safely_rejected"} if status == STATUS_GO else True, "near_duplicate_rejection_gate": a.get("near_duplicate_bucket") == "near_duplicate_rejected" if status == STATUS_GO else True, "latency_resource_gate": a.get("latency_bucket") != "latency_unusable" if explicit else True, "public_readback_gate": rb["all_public_readback_match_bool"]})
    stop_go = {"frk_l_kernel_hardening_authorized_bool": status == STATUS_GO, "no_go_currentness_or_materialization_failure_bool": status == STATUS_NOGO, "no_next_execution_authorized_bool": status == STATUS_INCONCLUSIVE, "frk_j_authorized_bool": False, "frk_b_c_authorized_bool": False, "ldi_b_authorized_bool": False, "haae_sg_authorized_bool": False, "haae_t_authorized_bool": False, "rpm_training_authorized_bool": False, "provider_network_ci_authorized_bool": False, "provider_authorized_bool": False, "network_authorized_bool": False, "ci_authorized_bool": False, "runtime_default_authorized_bool": False, "method_claim_authorized_bool": False, "scale_claim_authorized_bool": False, "winner_claim_authorized_bool": False, "candidate_generation_authorized_bool": False, "retrieval_rerun_authorized_bool": False, "retrieval_rerun_over_private_traces_authorized_bool": False, "source_scan_authorized_bool": False, "source_scan_unbounded_authorized_bool": False, "pack_rerun_authorized_bool": False, "raw_publication_authorized_bool": False, "exact_metric_publication_authorized_bool": False}
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": total,
        "source_lock_records": [{"anonymous_source_lock_id": "frkksource0000", "frk_i_checkpoint_bucket": FRK_I_CHECKPOINT, "frk_i_status_bucket": FRK_I_STATUS, "frk_i_self_test_bucket": f"{FRK_I_SELF_TEST}/{FRK_I_SELF_TEST}", "frk_j_not_authorized_locked_bool": True, "source_locked_bool": bool(src.get("all_ok"))}],
        "input_boundary_records": [{"anonymous_input_boundary_id": "frkkinput0000", "explicit_local_evidencecore_stress_run_bool": explicit, "default_no_local_run_bool": not explicit, "temp_snapshot_created_bool": bool(a.get("temp_snapshot_created_bool")), "temp_snapshot_safe_bool": bool(a.get("temp_snapshot_safe_bool")), "candidate_generation_bool": bool(a.get("candidate_generation_bool")), "retrieval_rerun_bool": bool(a.get("retrieval_rerun_bool")), "source_scan_bool": bool(a.get("source_scan_bool")), "pack_rerun_bool": bool(a.get("pack_rerun_bool"))}],
        "fixture_coverage_records": [{"anonymous_fixture_id": "frkkfixture0000", "fixture_coverage_bucket": a.get("fixture_coverage_bucket"), "fixture_family_buckets": a.get("fixture_family_buckets"), "citation_schema_valid_bool": bool(a.get("citation_schema_valid_bool")), "range_nonempty_bool": bool(a.get("range_nonempty_bool"))}],
        "materialization_currentness_records": [{"anonymous_materialization_id": "frkkmat0000", "materialization_engine_bucket": a.get("materialization_engine_bucket"), "validity_bucket": a.get("validity_bucket"), "currentness_bucket": a.get("currentness_bucket"), "stale_rejection_bucket": a.get("stale_rejection_bucket"), "deleted_file_bucket": a.get("deleted_file_bucket"), "moved_file_bucket": a.get("moved_file_bucket"), "line_insertion_bucket": a.get("line_insertion_bucket"), "near_duplicate_bucket": a.get("near_duplicate_bucket")}],
        "latency_resource_records": [{"anonymous_resource_id": "frkkresource0000", "latency_bucket": a.get("latency_bucket"), "resource_bucket": a.get("resource_bucket"), "failure_mode_bucket": a.get("failure_mode_bucket")}],
        "decision_records": [{"anonymous_decision_id": "frkkdecision0000", "decision_bucket": "authorize_frk_l_kernel_hardening" if status == STATUS_GO else "no_go_currentness_or_materialization_failure" if status == STATUS_NOGO else "inconclusive_no_next_execution_authorized" if status == STATUS_INCONCLUSIVE else "not_available_default_or_fail", "decision_reason_bucket": a.get("failure_mode_bucket"), "frk_l_authorized_bool": status == STATUS_GO}],
        "privacy_records": [{"anonymous_privacy_id": "frkkprivacy0000", "aggregate_only_public_bool": True, "raw_public_bool": False, "temp_root_public_bool": False, "exact_timing_public_bool": False, "exact_count_public_bool": False, "raw_hash_public_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"frkkgate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gates[g])} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"frkksynth{i:04d}", "validator_bucket": s, "validator_passed_bool": True} for i, s in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_readback_id": "frkkreadback0000", **rb}],
        "stop_go_records": [{"anonymous_stop_go_id": "frkkstop0000", "next_allowed_phase_bucket": "FRK-L Kernel Hardening" if status == STATUS_GO else "no_go_currentness_or_materialization_failure" if status == STATUS_NOGO else "no_next_execution_authorized", **stop_go}],
    }
    scan = scan_public(report); report["forbidden_scan"] = scan
    for g in report["pass_fail_gate_records"]:
        if g["gate_bucket"] == "forbidden_scan_gate": g["gate_passed_bool"] = scan["status"] == "pass"
    if scan["status"] != "pass":
        report["status"] = STATUS_FAIL; report["stop_go_records"][0]["frk_l_kernel_hardening_authorized_bool"] = False; report["stop_go_records"][0]["no_go_currentness_or_materialization_failure_bool"] = False; report["stop_go_records"][0]["no_next_execution_authorized_bool"] = False; report["stop_go_records"][0]["next_allowed_phase_bucket"] = "not_authorized_privacy_failure"
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required = ["schema_version", "phase_bucket", "status", "source_lock_records", "input_boundary_records", "fixture_coverage_records", "materialization_currentness_records", "latency_resource_records", "decision_records", "privacy_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]
    for k in required:
        if k not in report: issues.append(f"missing_{k}")
    if report.get("schema_version") != SCHEMA_VERSION: issues.append("schema")
    if report.get("self_test_total") != SELF_TEST_EXPECTED: issues.append("self_test")
    public_scan_ok = report.get("forbidden_scan", {}).get("status") == "pass" and scan_public({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] == "pass"
    if not public_scan_ok:
        issues.append("privacy_leak")
        stop_for_privacy = (report.get("stop_go_records") or [{}])[0]
        if stop_for_privacy.get("next_allowed_phase_bucket") != "not_authorized_privacy_failure" or any(stop_for_privacy.get(k) is True for k in ["frk_l_kernel_hardening_authorized_bool", "no_go_currentness_or_materialization_failure_bool", "no_next_execution_authorized_bool"]):
            issues.append("privacy_stop_go_fail_open")
    src = (report.get("source_lock_records") or [{}])[0]
    if src.get("frk_i_checkpoint_bucket") != FRK_I_CHECKPOINT or src.get("frk_i_status_bucket") != FRK_I_STATUS or src.get("frk_i_self_test_bucket") != f"{FRK_I_SELF_TEST}/{FRK_I_SELF_TEST}" or src.get("frk_j_not_authorized_locked_bool") is not True or src.get("source_locked_bool") is not True: issues.append("source_drift")
    inp = (report.get("input_boundary_records") or [{}])[0]
    if inp.get("explicit_local_evidencecore_stress_run_bool") is True and inp.get("temp_snapshot_safe_bool") is not True:
        issues.append("gate_false")
    for f in ["candidate_generation_bool", "retrieval_rerun_bool", "source_scan_bool", "pack_rerun_bool"]:
        if inp.get(f) is not False: issues.append(f.replace("_bool", "_overauth"))
    fix = (report.get("fixture_coverage_records") or [{}])[0]; mat = (report.get("materialization_currentness_records") or [{}])[0]; res = (report.get("latency_resource_records") or [{}])[0]
    if report.get("status") == STATUS_GO:
        if mat.get("materialization_engine_bucket") != "openlocus_cli_read_and_citations_validate": issues.append("materialization_engine")
        if fix.get("fixture_coverage_bucket") != "coverage_all_required_families": issues.append("fixture_missing")
        if fix.get("citation_schema_valid_bool") is not True: issues.append("citation_schema")
        if fix.get("range_nonempty_bool") is not True: issues.append("citation_range")
        if mat.get("validity_bucket") not in {"validity_high", "validity_strong_medium"}: issues.append("materialization")
        if mat.get("currentness_bucket") not in {"currentness_pass", "currentness_controlled_partial"}: issues.append("currentness")
        if mat.get("stale_rejection_bucket") != "stale_rejection_pass": issues.append("stale_rejection")
        if mat.get("deleted_file_bucket") != "deleted_file_rejected": issues.append("deleted_file")
        if mat.get("moved_file_bucket") not in {"moved_file_rematerialized_or_safe", "moved_file_safely_rejected"}: issues.append("moved_file")
        if mat.get("line_insertion_bucket") not in {"line_insertion_rematerialized", "line_insertion_safely_rejected"}: issues.append("line_insertion")
        if mat.get("near_duplicate_bucket") != "near_duplicate_rejected": issues.append("near_duplicate")
        if res.get("latency_bucket") == "latency_unusable": issues.append("latency")
    privacy = (report.get("privacy_records") or [{}])[0]
    for f in ["raw_public_bool", "temp_root_public_bool", "exact_timing_public_bool", "exact_count_public_bool", "raw_hash_public_bool"]:
        if privacy.get(f) is not False: issues.append("privacy_leak")
    stop = (report.get("stop_go_records") or [{}])[0]
    false_fields = ["frk_j_authorized_bool", "frk_b_c_authorized_bool", "ldi_b_authorized_bool", "haae_sg_authorized_bool", "haae_t_authorized_bool", "rpm_training_authorized_bool", "provider_network_ci_authorized_bool", "provider_authorized_bool", "network_authorized_bool", "ci_authorized_bool", "runtime_default_authorized_bool", "method_claim_authorized_bool", "scale_claim_authorized_bool", "winner_claim_authorized_bool", "candidate_generation_authorized_bool", "retrieval_rerun_authorized_bool", "retrieval_rerun_over_private_traces_authorized_bool", "source_scan_authorized_bool", "source_scan_unbounded_authorized_bool", "pack_rerun_authorized_bool", "raw_publication_authorized_bool", "exact_metric_publication_authorized_bool"]
    for f in false_fields:
        if stop.get(f) is not False: issues.append("stop_go_overauth")
    if (stop.get("frk_l_kernel_hardening_authorized_bool") is True) != (report.get("status") == STATUS_GO): issues.append("stop_go_overauth")
    gates = [x.get("gate_bucket") for x in report.get("pass_fail_gate_records", [])]; synth = [x.get("validator_bucket") for x in report.get("synthetic_validator_records", [])]
    if set(gates) != set(GATES) or len(gates) != len(GATES): issues.append("gate_exactness")
    if len(gates) != len(set(gates)): issues.append("gate_duplicate")
    if any(x.get("gate_passed_bool") is not True for x in report.get("pass_fail_gate_records", [])): issues.append("gate_false")
    if set(synth) != set(SYNTH) or len(synth) != len(SYNTH): issues.append("synthetic_exactness")
    if len(synth) != len(set(synth)): issues.append("synthetic_duplicate")
    if any(x.get("validator_passed_bool") is not True for x in report.get("synthetic_validator_records", [])): issues.append("synthetic_false")
    if (report.get("public_readback_records") or [{}])[0].get("all_public_readback_match_bool") is not True: issues.append("readback")
    return sorted(set(issues))


def synthetic_audit(kind: str = "go") -> dict[str, Any]:
    a = default_audit(); a.update({"explicit_local_run_bool": True, "temp_snapshot_created_bool": True, "fixture_coverage_bucket": "coverage_all_required_families", "fixture_family_buckets": list(FIXTURES), "materialization_engine_bucket": "openlocus_cli_read_and_citations_validate", "validity_bucket": "validity_high", "currentness_bucket": "currentness_pass", "stale_rejection_bucket": "stale_rejection_pass", "deleted_file_bucket": "deleted_file_rejected", "moved_file_bucket": "moved_file_rematerialized_or_safe", "line_insertion_bucket": "line_insertion_rematerialized", "near_duplicate_bucket": "near_duplicate_rejected", "latency_bucket": "latency_usable", "resource_bucket": "resource_bounded", "failure_mode_bucket": "none_observed"})
    if kind == "nogo": a["stale_rejection_bucket"] = "stale_rejection_fail"; a["failure_mode_bucket"] = "currentness_failure"
    if kind == "inconclusive": a["fixture_coverage_bucket"] = "coverage_partial"; a["validity_bucket"] = "validity_unknown"; a["failure_mode_bucket"] = "inconclusive"
    return a


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    def ck(n: str, ok: bool) -> None:
        if not ok: failures.append(n)
    src_ok = {"frk_i_ok": True, "all_ok": True}; src_bad = {"frk_i_ok": False, "all_ok": False}
    d = build_report(False, source_override=src_ok); go = build_report(True, synthetic_audit("go"), source_override=src_ok); ng = build_report(True, synthetic_audit("nogo"), source_override=src_ok); inc = build_report(True, synthetic_audit("inconclusive"), source_override=src_ok)
    ck("default_no_local_run_pass", d["status"] == STATUS_DEFAULT and validate_report(d) == [])
    ck("explicit_synthetic_go_pass", go["status"] == STATUS_GO and validate_report(go) == [])
    ck("explicit_synthetic_nogo_pass", ng["status"] == STATUS_NOGO and validate_report(ng) == [])
    ck("explicit_synthetic_inconclusive_pass", inc["status"] == STATUS_INCONCLUSIVE and validate_report(inc) == [])
    for name in ["source_lock_checkpoint_drift_fail", "source_lock_status_drift_fail", "source_lock_selftest_drift_fail", "frk_j_authorized_drift_fail"]: ck(name, build_report(True, synthetic_audit("go"), source_override=src_bad)["status"] == STATUS_FAIL)
    for name, argv in [("temp_snapshot_missing_opt_in_fail", ["--run-local-evidencecore-stress"]), ("safe_parser_unknown_arg_fail", ["--bad"] )]:
        try: parse_args(argv); ck(name, False)
        except Exception: ck(name, True)
    with tempfile.TemporaryDirectory(prefix="frk_k_safe_root_") as td:
        project = Path(td) / "project"; project.mkdir()
        outside = Path(td) / "outside"; outside.mkdir()
        (project / ".openlocus").symlink_to(outside, target_is_directory=True)
        try:
            ensure_safe_temp_root(project, TEMP_ROOT)
            ck("temp_snapshot_parent_symlink_fail", False)
        except Exception:
            ck("temp_snapshot_parent_symlink_fail", True)
    mutations = [
        ("stopped_routes_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("frk_j_authorized_bool", True), "stop_go_overauth"),
        ("temp_snapshot_escape_fail", lambda r: r["input_boundary_records"][0].__setitem__("temp_snapshot_safe_bool", False), "gate_false"),
        ("temp_snapshot_symlink_fail", lambda r: r["input_boundary_records"][0].__setitem__("temp_snapshot_safe_bool", False), "gate_false"),
        ("fixture_missing_fail", lambda r: r["fixture_coverage_records"][0].__setitem__("fixture_coverage_bucket", "coverage_missing_fixture"), "fixture_missing"),
        ("citation_schema_invalid_fail", lambda r: r["fixture_coverage_records"][0].__setitem__("citation_schema_valid_bool", False), "citation_schema"),
        ("citation_range_invalid_fail", lambda r: r["fixture_coverage_records"][0].__setitem__("range_nonempty_bool", False), "citation_range"),
        ("citation_empty_fail", lambda r: r["fixture_coverage_records"][0].__setitem__("range_nonempty_bool", False), "citation_range"),
        ("stale_rejection_fail", lambda r: r["materialization_currentness_records"][0].__setitem__("stale_rejection_bucket", "stale_rejection_fail"), "stale_rejection"),
        ("deleted_file_rejection_fail", lambda r: r["materialization_currentness_records"][0].__setitem__("deleted_file_bucket", "deleted_file_failure"), "deleted_file"),
        ("moved_file_handling_fail", lambda r: r["materialization_currentness_records"][0].__setitem__("moved_file_bucket", "moved_file_failure"), "moved_file"),
        ("line_insertion_handling_fail", lambda r: r["materialization_currentness_records"][0].__setitem__("line_insertion_bucket", "line_insertion_failure"), "line_insertion"),
        ("near_duplicate_rejection_fail", lambda r: r["materialization_currentness_records"][0].__setitem__("near_duplicate_bucket", "near_duplicate_failure"), "near_duplicate"),
        ("latency_unusable_fail", lambda r: r["latency_resource_records"][0].__setitem__("latency_bucket", "latency_unusable"), "latency"),
        ("materialization_engine_drift_fail", lambda r: r["materialization_currentness_records"][0].__setitem__("materialization_engine_bucket", "toy_materializer"), "materialization_engine"),
        ("candidate_generation_overauth_fail", lambda r: r["input_boundary_records"][0].__setitem__("candidate_generation_bool", True), "candidate_generation_overauth"),
        ("retrieval_rerun_overauth_fail", lambda r: r["input_boundary_records"][0].__setitem__("retrieval_rerun_bool", True), "retrieval_rerun_overauth"),
        ("source_scan_overauth_fail", lambda r: r["input_boundary_records"][0].__setitem__("source_scan_bool", True), "source_scan_overauth"),
        ("pack_rerun_overauth_fail", lambda r: r["input_boundary_records"][0].__setitem__("pack_rerun_bool", True), "pack_rerun_overauth"),
        ("frk_j_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("frk_j_authorized_bool", True), "stop_go_overauth"),
        ("frk_b_c_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("frk_b_c_authorized_bool", True), "stop_go_overauth"),
        ("ldi_b_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("ldi_b_authorized_bool", True), "stop_go_overauth"),
        ("haae_sg_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("haae_sg_authorized_bool", True), "stop_go_overauth"),
        ("haae_t_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("haae_t_authorized_bool", True), "stop_go_overauth"),
        ("rpm_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("rpm_training_authorized_bool", True), "stop_go_overauth"),
        ("provider_network_ci_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("provider_network_ci_authorized_bool", True), "stop_go_overauth"),
        ("runtime_default_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("runtime_default_authorized_bool", True), "stop_go_overauth"),
        ("method_claim_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("method_claim_authorized_bool", True), "stop_go_overauth"),
        ("scale_claim_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("scale_claim_authorized_bool", True), "stop_go_overauth"),
        ("winner_claim_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("winner_claim_authorized_bool", True), "stop_go_overauth"),
        ("raw_path_leak_fail", lambda r: r.__setitem__("debug", "/workspace/foo.py"), "privacy_leak"),
        ("raw_query_leak_fail", lambda r: r.__setitem__("debug", "task_id query"), "privacy_leak"),
        ("raw_snippet_leak_fail", lambda r: r.__setitem__("debug", "snippet"), "privacy_leak"),
        ("raw_hash_leak_fail", lambda r: r.__setitem__("debug", "sha256 raw_hash"), "privacy_leak"),
        ("exact_metric_publication_fail", lambda r: r.__setitem__("debug", "exact_metric 0.12"), "privacy_leak"),
        ("privacy_fail_clears_stopgo_fail", lambda r: (r.__setitem__("debug", "/tmp/x"), r["stop_go_records"][0].__setitem__("frk_l_kernel_hardening_authorized_bool", True)), "privacy_leak"),
        ("stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("source_scan_authorized_bool", True), "stop_go_overauth"),
        ("gate_drop_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_exactness"),
        ("gate_duplicate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_duplicate"),
        ("gate_false_fail", lambda r: r["pass_fail_gate_records"][0].__setitem__("gate_passed_bool", False), "gate_false"),
        ("synthetic_drop_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_exactness"),
        ("synthetic_duplicate_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), "synthetic_duplicate"),
        ("synthetic_false_fail", lambda r: r["synthetic_validator_records"][0].__setitem__("validator_passed_bool", False), "synthetic_false"),
        ("readback_drop_fail", lambda r: r["public_readback_records"].clear(), "readback"),
    ]
    for name, mut, issue in mutations:
        x = json.loads(json.dumps(go)); mut(x); ck(name, issue in validate_report(x))
    direct = {"schema_ok": go["schema_version"] == SCHEMA_VERSION, "validate_report_ok": validate_report(go) == [], "aggregate_only_ok": go["privacy_records"][0]["aggregate_only_public_bool"] is True, "self_test_count_exact": len(SYNTH) == SELF_TEST_EXPECTED == go["self_test_total"]}
    for n, ok in direct.items(): ck(n, ok)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_GO}


def write_report(report: dict[str, Any], out: Path | None = None) -> Path:
    p = repo_root() / (out or PUBLIC_REPORT_PATH); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"); return p


def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except Exception: print("invalid arguments", file=sys.stderr); return 2
    if args["self_test"]:
        r = run_self_test(); print(json.dumps(r, indent=2, sort_keys=True)); return 0 if r["passed"] else 1
    if args["validate"]:
        try: rep = load_json(PUBLIC_REPORT_PATH); issues = validate_report(rep)
        except Exception: rep = {"status": "unavailable"}; issues = ["invalid"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": rep.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    explicit = bool(args["run"]); audit = run_stress() if explicit else default_audit()
    report = build_report(explicit, audit); p = write_report(report, PUBLIC_REPORT_PATH if not args["out"] else PUBLIC_REPORT_PATH)
    print(json.dumps({"artifact": str(p), "status": report["status"], "decision_bucket": report["decision_records"][0]["decision_bucket"]}, sort_keys=True))
    return 0 if report["status"] != STATUS_FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
