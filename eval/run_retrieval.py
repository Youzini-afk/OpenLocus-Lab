#!/usr/bin/env python3
"""OpenLocus retrieval harness — R2 multi-method.

This script intentionally shells out to the CLI so eval stays decoupled from
the Rust implementation.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path


def run_query(openlocus: str, method: str, query: str, cwd: str, channels: str = "") -> dict:
    """Run a single retrieval query and return structured result."""
    if method == "regex":
        cmd = [openlocus, "search", "regex", query, "--json"]
    elif method == "text":
        cmd = [openlocus, "search", "text", query, "--json"]
    elif method == "bm25":
        cmd = [openlocus, "search", "bm25", query, "--json"]
    elif method == "symbol":
        cmd = [openlocus, "search", "symbol", query, "--json"]
    elif method == "rrf":
        cmd = [openlocus, "retrieve", query, "--json"]
        if channels:
            cmd.extend(["--channels", channels])
    else:
        return {
            "evidence": [],
            "latency_ms": 0,
            "returncode": -1,
            "stderr": f"unknown method: {method}",
        }

    t0 = time.perf_counter()
    proc = subprocess.run(cmd, check=False, text=True, capture_output=True, cwd=cwd)
    latency_ms = int((time.perf_counter() - t0) * 1000)

    evidence = []
    try:
        raw = json.loads(proc.stdout) if proc.stdout.strip() else []
        # For `retrieve`, the evidence is inside an EvidencePack
        if method == "rrf" and isinstance(raw, dict) and "evidence" in raw:
            evidence = raw["evidence"]
        elif isinstance(raw, list):
            evidence = raw
    except json.JSONDecodeError:
        pass

    return {
        "evidence": evidence,
        "latency_ms": latency_ms,
        "returncode": proc.returncode,
        "stderr": proc.stderr[:500] if proc.stderr else "",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--openlocus", default="target/debug/openlocus")
    parser.add_argument(
        "--method",
        default=None,
        help="Override method for all tasks (regex|text|bm25|symbol|rrf). "
        "If omitted, uses per-task method field.",
    )
    parser.add_argument(
        "--channels",
        default="",
        help="Channels for RRF retrieve (e.g. regex,bm25,symbol)",
    )
    parser.add_argument("--cwd", default=None, help="Working directory for CLI")
    args = parser.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cwd = args.cwd or "."

    with Path(args.dataset).open("r", encoding="utf-8") as src, out.open(
        "w", encoding="utf-8"
    ) as dst:
        for line in src:
            if not line.strip():
                continue
            item = json.loads(line)
            query = item["query"]
            task_id = item.get("task_id", "")
            method = args.method or item.get("method", "regex")

            result = run_query(args.openlocus, method, query, cwd, args.channels)

            dst.write(
                json.dumps(
                    {
                        "task_id": task_id,
                        "query": query,
                        "method": method,
                        "evidence": result["evidence"],
                        "latency_ms": result["latency_ms"],
                        "returncode": result["returncode"],
                        "stderr": result["stderr"],
                    }
                )
                + "\n"
            )


if __name__ == "__main__":
    main()
