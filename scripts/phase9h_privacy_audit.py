#!/usr/bin/env python3
"""Privacy audit for the Phase 9H public report and ignored-runs guard.

The committed public report must contain no private-shaped source identity. The
runner itself intentionally contains generic GitHub API URL templates, MIME
strings, and self-test rejection fixtures, so runner source privacy is guarded by
the route-specific validator and normal code review instead of this artifact
audit.
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REPORT = REPO / "artifacts" / "phase9h_candidate_source_pool_public_source_network_fetch_materialization_no_scoring_no_claim" / "phase9h_candidate_source_pool_public_source_network_fetch_materialization_no_scoring_no_claim_report.json"

PATTERNS = {
    "github_url": r"https?://github\.com/[^\s\"']+",
    "api_github_repos_url": r"https?://api\.github\.com/repos/[^\s\"']+",
    "raw_githubusercontent_url": r"https?://raw\.githubusercontent\.com/[^\s\"']+",
    "codeload_url": r"https?://codeload\.github\.com/[^\s\"']+",
    "owner_repo_pair": r"\b[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\b",
    "sha40": r"\b[a-fA-F0-9]{40}\b",
    "sha32": r"\b[a-fA-F0-9]{32}\b",
    "windows_abs_path": r"[A-Za-z]:[\\/][^\s\"']+",
    "singleton_bucket": r"(?<![A-Za-z0-9_])(?:count_1|bucket_one|singleton)(?![A-Za-z0-9_])",
    "claim_wording": r"\b(?:materialization\s+(?:works|succeeded|proven|established)|fetch(?:/clone)?\s+(?:works|succeeded|proven|established)|network\s+fetch\s+(?:works|succeeded|proven|established)|evidence_success\s+(?:achieved|proven|established|confirmed))\b",
}


def audit_file(path, label, allowed_patterns=None):
    allowed = allowed_patterns or set()
    text = path.read_text(encoding="utf-8")
    leaks = []
    for name, pat in PATTERNS.items():
        if name in allowed:
            continue
        matches = re.findall(pat, text, re.IGNORECASE)
        if matches:
            leaks.append((name, matches[:8]))
    if leaks:
        print(f"LEAKS in {label}:")
        for name, matches in leaks:
            print(f"  {name}: {matches}")
    else:
        print(f"OK: {label} clean")
    return not leaks


def main():
    ok = True
    # Public report: NO private patterns allowed at all.
    ok = audit_file(REPORT, "public_report") and ok
    # Verify runs/ is gitignored
    gitignore = (REPO / ".gitignore").read_text(encoding="utf-8")
    runs_ignored = "/runs/" in gitignore or "runs/" in gitignore
    print(f"{'OK' if runs_ignored else 'FAIL'}: runs/ ignored in .gitignore")
    ok = runs_ignored and ok
    # Verify runs/ phase9h content is NOT tracked by git
    import subprocess
    result = subprocess.run(
        ["git", "status", "--short", "runs/"],
        capture_output=True, text=True, cwd=str(REPO),
    )
    phase9h_tracked = "phase9h" in result.stdout
    print(f"{'OK' if not phase9h_tracked else 'FAIL'}: runs/phase9h not tracked by git")
    ok = (not phase9h_tracked) and ok
    print("OVERALL:", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
