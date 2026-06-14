#!/usr/bin/env python3
"""P6 summary for repair/admission replay on P5 generated stress artifacts."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "artifacts/real_provider/p5_real_llm_stress_public.jsonl"
LABELS = ROOT / "artifacts/real_provider/p5_real_llm_stress_labels.jsonl"
R39 = ROOT / "artifacts/real_provider/p6_symbol_regex_repair.json"
R41 = ROOT / "artifacts/real_provider/p6_graph_admission.json"
OUT = ROOT / "artifacts/real_provider/p6_real_provider_replay_summary.json"
DOC = ROOT / "docs/en/real-provider-p6-replay-summary.md"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    public = load_jsonl(PUBLIC)
    labels = load_jsonl(LABELS)
    r39 = load_json(R39)
    r41 = load_json(R41)
    public_fields_ok = all(set(row) <= {"test_id", "repo_id", "query", "public_version", "source"} for row in public)
    labels_by_id = {row["test_id"]: row for row in labels}
    paired = all(row["test_id"] in labels_by_id for row in public)
    category_counts = Counter(row.get("source_category") for row in labels)
    label_quality = sorted({str(row.get("label_quality")) for row in labels})
    summary = {
        "schema_version": "p6-real-provider-replay-summary-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "p5_stress_public_tasks": len(public),
        "p5_stress_private_labels": len(labels),
        "p5_public_fields_ok": public_fields_ok,
        "p5_public_private_pairing_ok": paired,
        "p5_stress_by_category": dict(sorted(category_counts.items())),
        "p5_label_quality": label_quality,
        "r39_r40_replay": {
            "task_count": r39.get("task_count"),
            "best_regex_mode": r39.get("regex_repair", {}).get("best_regex_mode"),
            "symbol_FileRecall_delta": r39.get("symbol_repair", {}).get("symbol_FileRecall_delta"),
            "symbol_false_primary_delta": r39.get("symbol_repair", {}).get("symbol_false_primary_delta"),
            "promotion_ready": r39.get("promotion_ready"),
        },
        "r41_r42_replay": {
            "task_count": r41.get("task_count"),
            "graph_expansion_blocked": r41.get("metrics", {}).get("graph_expansion_blocked"),
            "graph_pollution_ratio": r41.get("metrics", {}).get("graph_pollution_ratio"),
            "selective_risk": r41.get("metrics", {}).get("selective_risk"),
            "coverage": r41.get("metrics", {}).get("coverage"),
            "promotion_ready": r41.get("promotion_ready"),
        },
        "not_promotion_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "core_changes": False,
        "evidencecore_semantics_changed": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    DOC.write_text(
        "# Real Provider P6 Replay Summary\n\n"
        "P6 replays repair/admission harnesses and validates the P5 generated stress corpus remains failure-discovery only.\n\n"
        f"- P5 public tasks: `{summary['p5_stress_public_tasks']}`\n"
        f"- P5 private labels: `{summary['p5_stress_private_labels']}`\n"
        f"- public fields ok: `{summary['p5_public_fields_ok']}`\n"
        f"- label quality: `{', '.join(label_quality)}`\n"
        f"- best regex mode: `{summary['r39_r40_replay']['best_regex_mode']}`\n"
        f"- symbol FileRecall delta: `{summary['r39_r40_replay']['symbol_FileRecall_delta']}`\n"
        f"- graph expansion blocked: `{summary['r41_r42_replay']['graph_expansion_blocked']}`\n"
        f"- admission selective risk: `{summary['r41_r42_replay']['selective_risk']}`\n"
        "\nNo promotion/default change is allowed from this replay.\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUT.relative_to(ROOT)}")
    print(f"Wrote {DOC.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
