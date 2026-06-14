#!/usr/bin/env python3
"""Summarize real-provider P1-P6 findings without secrets."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/real_provider/p7_real_provider_summary.json"
DOC = ROOT / "docs/en/real-provider-p7-summary.md"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main() -> None:
    p1_embed = load("artifacts/real_provider/p1_real_embedding_smoke.json")
    p1_llm = load("artifacts/real_provider/p1_real_llm_smoke.json")
    p2 = load("artifacts/real_provider/p2_real_embedding_view_bakeoff_bounded.json")
    p3 = load("artifacts/real_provider/p3_real_quiver_readiness.json")
    p4 = load("artifacts/real_provider/p4_real_quiver_anchor_proto.json")
    p5 = load("artifacts/real_provider/p5_real_llm_derived_stress.json")
    p6 = load("artifacts/real_provider/p6_real_provider_replay_summary.json")
    best_p4 = p4.get("best_net_strategies", [{}])[0]
    summary = {
        "schema_version": "p7-real-provider-summary-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider_protocols": {
            "embedding": "openai-compatible via local env only",
            "llm": "openai-compatible via local env only",
            "committed_url_or_key": False,
        },
        "p1_provider_smoke": {
            "embedding_status": p1_embed.get("provider_status"),
            "embedding_remote_calls": p1_embed.get("view_build_summaries", {}).get("path_plus_symbol", {}).get("remote_calls"),
            "embedding_citation_validity": p1_embed.get("view_results", {}).get("path_plus_symbol", {}).get("metrics", {}).get("citation_validity"),
            "llm_status": p1_llm.get("llm_status", {}).get("status"),
            "llm_remote_calls": p1_llm.get("remote_calls"),
        },
        "p2_real_embedding_bakeoff": {
            "provider_status": p2.get("provider_status"),
            "view": p2.get("views"),
            "FileRecall@1": p2.get("view_results", {}).get("path_plus_symbol", {}).get("metrics", {}).get("FileRecall@1"),
            "FileRecall@3": p2.get("view_results", {}).get("path_plus_symbol", {}).get("metrics", {}).get("FileRecall@3"),
            "SpanF0.5": p2.get("view_results", {}).get("path_plus_symbol", {}).get("metrics", {}).get("SpanF0.5"),
            "primary_false_positive_rate": p2.get("view_results", {}).get("path_plus_symbol", {}).get("metrics", {}).get("primary_false_positive_rate"),
        },
        "p3_quiver_readiness": {
            "quiver_fit": p3.get("diagnostics", {}).get("quiver_fit"),
            "BQ_overlap@10": p3.get("diagnostics", {}).get("BQ_overlap@10"),
            "sign_entropy_mean": p3.get("diagnostics", {}).get("sign_entropy_mean"),
            "quiver_graph_implemented": p3.get("quiver_graph_implemented"),
        },
        "p4_anchor_seeded": {
            "best_strategy": best_p4.get("strategy"),
            "FileRecall@1": best_p4.get("metrics", {}).get("FileRecall@1"),
            "SpanF0.5": best_p4.get("metrics", {}).get("SpanF0.5"),
            "added_gold_span": best_p4.get("metrics", {}).get("added_gold_span"),
            "added_false_span": best_p4.get("metrics", {}).get("added_false_span"),
            "semantic_trap_nonempty": best_p4.get("metrics", {}).get("semantic_trap_nonempty"),
        },
        "p5_llm_derived_stress": {
            "llm_status": p5.get("llm_status", {}).get("status"),
            "remote_calls": p5.get("remote_calls"),
            "derived_view_count": p5.get("derived_view_count"),
            "stress_public_task_count": p5.get("stress_public_task_count"),
            "stress_private_label_count": p5.get("stress_private_label_count"),
            "artifact_secret_scan_clean": p5.get("safety_gates", {}).get("artifact_secret_scan_clean"),
        },
        "p6_replay": {
            "p5_public_fields_ok": p6.get("p5_public_fields_ok"),
            "best_regex_mode": p6.get("r39_r40_replay", {}).get("best_regex_mode"),
            "symbol_FileRecall_delta": p6.get("r39_r40_replay", {}).get("symbol_FileRecall_delta"),
            "graph_expansion_blocked": p6.get("r41_r42_replay", {}).get("graph_expansion_blocked"),
            "selective_risk": p6.get("r41_r42_replay", {}).get("selective_risk"),
        },
        "decision": {
            "promotion_ready": False,
            "default_should_change": False,
            "dense_recommendation": "supporting_only_and_anchor_seeded_only_for_now",
            "quiver_recommendation": "continue_diagnostics_no_global_default",
            "llm_derived_recommendation": "derived_stress_only_not_evidence",
            "graph_recommendation": "supporting_or_explainer_only",
        },
        "next_required_tests": [
            "run P2/P3/P4 on CI smoke public corpus with repo/file caps",
            "add remote-safe repo/file cap before running R26/R38 large locks",
            "compare Qwen3-Embedding-8B/4B/0.6B and bge-m3 on the same capped corpus",
            "validate anchored dense/quiver against P5 stress traps",
            "run admission_v2_rules with real dense support features",
        ],
        "safety_gates": {
            "no_url_or_key_committed": True,
            "env_file_ignored": True,
            "raw_prompt_stored": False,
            "raw_response_stored": False,
            "llm_outputs_are_evidence": False,
            "dense_outputs_are_evidence": False,
            "quiver_graph_quality_claimed": False,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    DOC.write_text(
        "# Real Provider P7 Summary\n\n"
        "P7 summarizes P1-P6 real-provider tests. No provider URL or key is committed.\n\n"
        "## Main Findings\n\n"
        f"- Embedding smoke status: `{summary['p1_provider_smoke']['embedding_status']}`\n"
        f"- LLM smoke status: `{summary['p1_provider_smoke']['llm_status']}`\n"
        f"- P2 dense FileRecall@3: `{summary['p2_real_embedding_bakeoff']['FileRecall@3']}` with primary_false_positive_rate `{summary['p2_real_embedding_bakeoff']['primary_false_positive_rate']}`\n"
        f"- P3 QuIVer fit: `{summary['p3_quiver_readiness']['quiver_fit']}`; graph implemented: `{summary['p3_quiver_readiness']['quiver_graph_implemented']}`\n"
        f"- P4 best anchored strategy: `{summary['p4_anchor_seeded']['best_strategy']}` with added_gold `{summary['p4_anchor_seeded']['added_gold_span']}` and added_false `{summary['p4_anchor_seeded']['added_false_span']}`\n"
        f"- P5 stress tasks: `{summary['p5_llm_derived_stress']['stress_public_task_count']}` public / `{summary['p5_llm_derived_stress']['stress_private_label_count']}` private labels\n"
        f"- P6 best regex mode: `{summary['p6_replay']['best_regex_mode']}`; graph expansion blocked: `{summary['p6_replay']['graph_expansion_blocked']}`\n\n"
        "## Decision\n\n"
        "- `promotion_ready=false`\n"
        "- `default_should_change=false`\n"
        "- dense remains supporting-only and preferably anchor-seeded\n"
        "- QuIVer remains diagnostic-only; no global default\n"
        "- LLM-derived/stress remains not Evidence and not promotion evidence\n"
        "- graph remains supporting/explainer-only\n\n"
        "## Next Required Tests\n\n"
        + "\n".join(f"- {item}" for item in summary["next_required_tests"])
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUT.relative_to(ROOT)}")
    print(f"Wrote {DOC.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
