#!/usr/bin/env python3
"""R4 Derived Level0 Safety — verify safety gates on derived index views.

Runs build/validate/inspect/purge and writes report_kind="derived_level0_safety"
with metrics: remote_calls, candidate_edge_enabled, data_level, stale detection,
policy exclusion, parse errors, etc.
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


def test_stale_mutation(ol: str, cwd: str) -> dict[str, Any]:
    """Build views in a temp repo, modify a source file, validate, assert stale>0."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        # Create a small repo
        (tmppath / ".git").mkdir()
        (tmppath / "lib.rs").write_text("fn original() {}\n")

        # Build derived views
        build = run_cmd(
            [ol, "derived", "build", "--experimental", "--write-files", "--json"],
            str(tmppath),
        )

        if not build.get("success"):
            return {"stale_mutation_test": "skipped", "reason": "build failed"}

        # Mutate source file
        (tmppath / "lib.rs").write_text("fn modified() {}\n")

        # Validate — should detect stale
        validate = run_cmd([ol, "derived", "validate", "--json"], str(tmppath))

        return {
            "stale_mutation_test": "ran",
            "stale_detected": validate.get("stale", 0) > 0,
            "stale_count": validate.get("stale", 0),
            "total": validate.get("total", 0),
        }


def test_policy_excluded(ol: str, cwd: str) -> dict[str, Any]:
    """Create .env, private.pem, secrets/token.txt plus normal file, build derived,
    inspect views, assert default-excluded paths (.env, *.pem) absent, while
    secrets/ may appear (not in default exclude list)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        (tmppath / ".git").mkdir()

        # Create files that should be excluded by default policy
        (tmppath / ".env").write_text("SECRET=abc\n")
        (tmppath / ".env.production").write_text("SECRET=prod\n")
        (tmppath / "private.pem").write_text("-----BEGIN PRIVATE KEY-----\n")
        # secrets/ dir is NOT in default exclude list
        (tmppath / "secrets").mkdir()
        (tmppath / "secrets" / "token.txt").write_text("ghp_abc123\n")
        # Normal file
        (tmppath / "lib.rs").write_text("fn normal_fn() {}\n")

        # Build derived views (default policy excludes .env*, **/*.pem)
        build = run_cmd(
            [ol, "derived", "build", "--experimental", "--write-files", "--json"],
            str(tmppath),
        )

        if not build.get("success") or build.get("generated", 0) == 0:
            return {"policy_excluded_test": "skipped", "reason": "no views generated"}

        # Inspect to check paths
        inspect = run_cmd(
            [ol, "derived", "inspect", "--json", "--limit", "100"], str(tmppath)
        )

        views = inspect.get("views", [])
        paths = [v.get("source", {}).get("path", "") for v in views]

        # .env and *.pem should be excluded by default policy
        env_present = any(p == ".env" or p == ".env.production" for p in paths)
        pem_present = any(p.endswith(".pem") for p in paths)

        return {
            "policy_excluded_test": "ran",
            "env_files_excluded": not env_present,
            "pem_files_excluded": not pem_present,
            "paths_found": paths,
        }


def test_corrupt_jsonl(ol: str, cwd: str) -> dict[str, Any]:
    """Write corrupt JSONL, validate, assert parse_errors>0."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        (tmppath / ".git").mkdir()
        (tmppath / "lib.rs").write_text("fn test() {}\n")

        # Build normally
        build = run_cmd(
            [ol, "derived", "build", "--experimental", "--write-files", "--json"],
            str(tmppath),
        )

        if not build.get("success"):
            return {"corrupt_jsonl_test": "skipped", "reason": "build failed"}

        # Corrupt the JSONL file
        views_path = tmppath / ".openlocus" / "derived" / "views.jsonl"
        if views_path.exists():
            with open(views_path, "a") as f:
                f.write("CORRUPT LINE NOT JSON\n")

        # Validate
        validate = run_cmd([ol, "derived", "validate", "--json"], str(tmppath))

        return {
            "corrupt_jsonl_test": "ran",
            "parse_errors_detected": validate.get("parse_errors", 0) > 0,
            "parse_errors_count": validate.get("parse_errors", 0),
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--openlocus", default="target/debug/openlocus", help="Path to openlocus binary"
    )
    parser.add_argument("--cwd", default=".", help="Working directory")
    parser.add_argument(
        "--out",
        default="runs/derived-safety-report.json",
        help="Output JSON file",
    )
    args = parser.parse_args()

    ol = os.path.abspath(args.openlocus)

    report: dict[str, Any] = {
        "report_kind": "derived_level0_safety",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }

    # 1. Build without --experimental should fail
    build_no_exp = run_cmd([ol, "derived", "build", "--json"], args.cwd)
    report["build_without_experimental"] = build_no_exp
    report["no_experimental_blocks"] = build_no_exp.get("success") is False

    # 2. Build with --experimental
    build_exp = run_cmd(
        [ol, "derived", "build", "--experimental", "--write-files", "--json"], args.cwd
    )
    report["build_with_experimental"] = build_exp
    report["remote_calls"] = build_exp.get("remote_calls", -1)
    report["generated"] = build_exp.get("generated", 0)
    report["valid"] = build_exp.get("valid", 0)
    report["blocked_kind"] = build_exp.get("blocked_kind", 0)
    report["data_level"] = build_exp.get("data_level", -1)
    report["policy_mode"] = build_exp.get("policy_mode", "")

    # 3. Build with --max-data-level 2 should be blocked
    build_dl2 = run_cmd(
        [ol, "derived", "build", "--experimental", "--max-data-level", "2", "--json"],
        args.cwd,
    )
    report["build_data_level_2"] = build_dl2
    report["data_level_2_blocked"] = build_dl2.get("success") is False

    # 4. Validate
    validate = run_cmd([ol, "derived", "validate", "--json"], args.cwd)
    report["validate"] = validate
    report["stale_views_blocked"] = validate.get("stale", 0)
    report["blocked_kind_views"] = validate.get("blocked_kind", 0)
    report["parse_errors"] = validate.get("parse_errors", 0)

    # 5. Build candidate-edge (should be blocked)
    build_edge = run_cmd(
        [ol, "derived", "build", "candidate-edge", "--experimental", "--json"], args.cwd
    )
    report["candidate_edge_build"] = build_edge
    report["candidate_edge_blocked"] = (
        build_edge.get("blocked_kind", 0) > 0
        and build_edge.get("generated", 0) == 0
    )

    # 6. Build bug-symptom-hint (should be blocked)
    build_bsh = run_cmd(
        [ol, "derived", "build", "bug-symptom-hint", "--experimental", "--json"],
        args.cwd,
    )
    report["bug_symptom_hint_build"] = build_bsh
    report["bug_symptom_hint_blocked"] = (
        build_bsh.get("blocked_kind", 0) > 0
        and build_bsh.get("generated", 0) == 0
    )

    # 7. Inspect
    inspect = run_cmd([ol, "derived", "inspect", "--json", "--limit", "5"], args.cwd)
    report["inspect"] = inspect

    # 8. Purge
    purge = run_cmd([ol, "derived", "purge", "--json"], args.cwd)
    report["purge"] = purge
    report["purge_removes_files"] = purge.get("purged") is True

    # 9. Stale mutation test
    report["stale_mutation"] = test_stale_mutation(ol, args.cwd)

    # 10. Policy excluded test
    report["policy_excluded"] = test_policy_excluded(ol, args.cwd)

    # 11. Corrupt JSONL test
    report["corrupt_jsonl"] = test_corrupt_jsonl(ol, args.cwd)

    # Summary checks
    report["safety_checks"] = {
        "no_experimental_blocks": report["no_experimental_blocks"],
        "remote_calls_zero": report["remote_calls"] == 0,
        "candidate_edge_blocked": report["candidate_edge_blocked"],
        "bug_symptom_hint_blocked": report["bug_symptom_hint_blocked"],
        "data_level_le_1": report["data_level"] <= 1,
        "data_level_2_blocked": report["data_level_2_blocked"],
        "policy_mode_local_only": report["policy_mode"] == "local_only",
        "parse_errors_zero": report["parse_errors"] == 0,
        "purge_removes_files": report["purge_removes_files"],
        "stale_mutation_detected": report["stale_mutation"].get("stale_detected", False),
        "policy_excluded_env": report["policy_excluded"].get("env_files_excluded", False),
        "policy_excluded_pem": report["policy_excluded"].get("pem_files_excluded", False),
        "corrupt_jsonl_detected": report["corrupt_jsonl"].get("parse_errors_detected", False),
    }

    all_safe = all(report["safety_checks"].values())
    report["all_safety_checks_passed"] = all_safe

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
