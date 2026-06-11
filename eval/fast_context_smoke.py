#!/usr/bin/env python3
"""R6 Fast Context Level0 Smoke — verify 4-turn deterministic loop.

Checks: pack exists, trace_id exists, turns/actions replayable,
unknown channel blocked, tokens_estimated meaningful/budget respected,
citation validate true, no raw derived/graph edges.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


def run_cmd(args: list[str], cwd: str) -> dict[str, Any]:
    """Run an openlocus command and return parsed JSON + latency."""
    t0 = time.perf_counter()
    proc = subprocess.run(args, check=False, text=True, capture_output=True, cwd=cwd)
    latency_ms = int((time.perf_counter() - t0) * 1000)

    try:
        result: dict[str, Any] = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        result = {"raw_stdout": proc.stdout[:500]}

    result["latency_ms"] = latency_ms
    result["returncode"] = proc.returncode
    result["stderr"] = proc.stderr[:500] if proc.stderr else ""
    return result


def create_fixture_repo(base: Path) -> Path:
    """Create a synthetic repo with import/test/config examples."""
    repo = base / "test_repo"
    repo.mkdir(parents=True, exist_ok=True)

    src = repo / "src"
    src.mkdir(exist_ok=True)
    (src / "lib.rs").write_text("pub mod evidence;\npub mod policy;\n")
    (src / "evidence.rs").write_text(
        "pub struct EvidenceCore {\n"
        "    pub path: String,\n"
        "    pub start_line: u64,\n"
        "    pub end_line: u64,\n"
        "    pub content_sha: String,\n"
        "    pub score: f64,\n"
        "    pub why: Vec<String>,\n"
        "    pub channels: Vec<String>,\n"
        "}\n"
    )
    (src / "policy.rs").write_text(
        "pub struct Policy {\n"
        "    pub data_level: u8,\n"
        "}\n"
        "\n"
        "impl Default for Policy {\n"
        "    fn default() -> Self {\n"
        "        Self { data_level: 1 }\n"
        "    }\n"
        "}\n"
    )

    tests = repo / "tests"
    tests.mkdir(exist_ok=True)
    (tests / "evidence_test.rs").write_text("use super::*;\n#[test]\nfn test_evidence() {}\n")

    (repo / "Cargo.toml").write_text('[package]\nname = "test"\nversion = "0.1.0"\n')
    (repo / ".git").mkdir(exist_ok=True)

    return repo


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--openlocus", default="target/debug/openlocus", help="Path to openlocus binary"
    )
    parser.add_argument(
        "--out",
        default="runs/fast-context-level0-smoke-report.json",
        help="Output JSON file",
    )
    args = parser.parse_args()

    ol = os.path.abspath(args.openlocus)

    # Create synthetic fixture repo
    tmpdir = tempfile.mkdtemp(prefix="openlocus_fc_smoke_")
    repo = create_fixture_repo(Path(tmpdir))
    cwd = str(repo)

    report: dict[str, Any] = {
        "report_kind": "fast_context_level0_smoke",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "fixture_repo": str(repo),
    }

    # 1. Basic fast-context query
    fc = run_cmd(
        [ol, "fast-context", "EvidenceCore", "--channels", "regex,bm25,symbol,graph", "--json"],
        cwd,
    )
    report["fast_context"] = fc
    report["success"] = fc.get("success") is True
    report["evidence_count"] = len(fc.get("evidence", []))
    report["turns_count"] = len(fc.get("turns", []))
    report["remote_calls"] = fc.get("remote_calls", -1)
    report["confidence"] = fc.get("confidence", 0.0)

    # 2. Pack shape validation
    pack = fc.get("pack", {})
    report["pack_exists"] = isinstance(pack, dict) and "evidence" in pack
    report["pack_trace_id"] = pack.get("trace_id", "")
    report["trace_id_matches"] = (
        fc.get("trace_id", "") != ""
        and fc.get("trace_id") == pack.get("trace_id")
    )
    report["trace_id_nonempty"] = fc.get("trace_id", "") != ""

    # 3. Actions replayable
    actions = fc.get("actions", [])
    report["actions_nonempty"] = len(actions) > 0
    report["actions_have_channel"] = all(a.get("channel", "") != "" for a in actions)
    report["actions_have_query"] = all(a.get("query", "") != "" for a in actions)

    # 4. Citation validation of evidence
    evidence = fc.get("evidence", [])
    citation_valid = False
    if evidence:
        cite_file = os.path.join(tmpdir, "fc_cite.json")
        with open(cite_file, "w") as f:
            json.dump(evidence, f)
        validate = run_cmd([ol, "citations", "validate", cite_file, "--json"], cwd)
        report["citation_validation"] = validate
        citation_valid = (
            validate.get("valid_count", 0) == len(evidence)
            and validate.get("invalid_count", 0) == 0
        )
    else:
        citation_valid = True
    report["citation_valid"] = citation_valid

    # 5. Token budget respected
    fc_budget = run_cmd(
        [ol, "fast-context", "EvidenceCore", "--budget", "50", "--json"],
        cwd,
    )
    budget_evidence_count = len(fc_budget.get("evidence", []))
    budget_tokens = fc_budget.get("budget_used", {}).get("tokens_estimated", 0)
    report["budget_respected"] = budget_tokens <= 50
    report["tokens_estimated_meaningful"] = budget_tokens > 0

    # 6. Turns <= 4
    report["turns_le_4"] = report["turns_count"] <= 4

    # 7. Unknown channel blocked
    fc_unknown = run_cmd(
        [ol, "fast-context", "test", "--channels", "unknown", "--json"],
        cwd,
    )
    report["unknown_channel_blocked"] = fc_unknown.get("success") is not True and "unknown" in fc_unknown.get("error", "").lower()

    # 8. No raw derived/graph edges in output
    fc_str = json.dumps(fc)
    report["no_derived_edges_in_output"] = "candidate_edge" not in fc_str
    report["no_raw_graph_edges"] = "source_content_sha" not in fc_str or "evidence" in fc_str

    # 9. Diagnostics present
    diagnostics = fc.get("diagnostics", {})
    report["diagnostics_present"] = isinstance(diagnostics, dict) and "invalid_citations_dropped" in diagnostics

    # 10. Remote calls = 0
    report["remote_calls_zero"] = report["remote_calls"] == 0

    # Summary checks
    report["safety_checks"] = {
        "success": report["success"],
        "evidence_non_empty": report["evidence_count"] > 0,
        "citation_valid": report["citation_valid"],
        "remote_calls_zero": report["remote_calls_zero"],
        "pack_exists": report["pack_exists"],
        "trace_id_nonempty": report["trace_id_nonempty"],
        "trace_id_matches": report["trace_id_matches"],
        "actions_replayable": report["actions_nonempty"] and report["actions_have_channel"] and report["actions_have_query"],
        "unknown_channel_blocked": report["unknown_channel_blocked"],
        "budget_respected": report["budget_respected"],
        "tokens_estimated_meaningful": report["tokens_estimated_meaningful"],
        "turns_le_4": report["turns_le_4"],
        "diagnostics_present": report["diagnostics_present"],
        "no_derived_edges_in_output": report["no_derived_edges_in_output"],
    }

    all_safe = all(report["safety_checks"].values())
    report["all_safety_checks_passed"] = all_safe

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))

    # Cleanup
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
