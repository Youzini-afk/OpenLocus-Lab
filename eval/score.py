#!/usr/bin/env python3
"""Placeholder scorer for R0 smoke runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pred", required=True)
    args = parser.parse_args()

    total = 0
    ok = 0
    for line in Path(args.pred).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        total += 1
        if json.loads(line).get("returncode") == 0:
            ok += 1
    print(json.dumps({"total": total, "ok": ok, "success_rate": ok / total if total else 0.0}, indent=2))


if __name__ == "__main__":
    main()
