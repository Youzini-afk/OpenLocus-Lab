#!/usr/bin/env python3
"""Minimal OpenLocus retrieval harness.

This script intentionally shells out to the CLI so eval stays decoupled from
the Rust implementation.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--openlocus", default="target/debug/openlocus")
    args = parser.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with Path(args.dataset).open("r", encoding="utf-8") as src, out.open("w", encoding="utf-8") as dst:
        for line in src:
            if not line.strip():
                continue
            item = json.loads(line)
            query = item["query"]
            proc = subprocess.run(
                [args.openlocus, "search", "regex", query, "--json"],
                check=False,
                text=True,
                capture_output=True,
            )
            dst.write(json.dumps({"task_id": item.get("task_id"), "query": query, "stdout": proc.stdout, "returncode": proc.returncode}) + "\n")


if __name__ == "__main__":
    main()
