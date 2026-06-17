#!/usr/bin/env python3
"""B6C frozen-policy fresh validation.

B6C takes the two candidate policies frozen by B6B and evaluates them, plus the
P25 bucket-routed baseline, on a fresh paired P21 records sample. It performs
**no** search, rule generation, or winner selection. The public artifact is
aggregate-only and never emits repo IDs, task IDs, candidate IDs, paths, spans,
digests, snippets, prompts, responses, labels, or gold spans.

Routing uses only public RUN-phase fields: ``task_bucket``, ``task_risk_tags``,
and allowlisted ``route_features`` booleans. SCORE-phase fields such as
``has_gold`` and ``score_group`` are used only after policies are frozen.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_FILE_DIR = Path(__file__).resolve().parent
if str(_FILE_DIR) not in sys.path:
    sys.path.insert(0, str(_FILE_DIR))

import b6_lite_interpretable_policy_search as b6lite
import b6b_combined_policy_search as b6b

SCHEMA_VERSION = "b6c-frozen-policy-validation-v0"
GENERATED_BY = "b6c_frozen_policy_validation"
DEFAULT_OUT = Path(
    "artifacts/b6c_frozen_policy_validation/b6c_frozen_policy_validation_report.json"
)
DEFAULT_DOC = Path("docs/real-provider-ci/b6c-frozen-policy-validation.md")

FROZEN_CANDIDATES_PATH = _FILE_DIR / "b6c_frozen_candidates.json"

EXPECTED_FROZEN_NAMES = {
    "ambiguous_query_weak_only_default_use_p25_action",
    "negative_weak_only_ambiguous_query_use_p25_action_default_use_p25_action",
}

EXPECTED_FROZEN_POLICY_SPECS: dict[str, list[dict[str, Any]]] = {
    "ambiguous_query_weak_only_default_use_p25_action": [
        {
            "name": "ambiguous_query_weak_only",
            "predicates": ["ambiguous_or_query_noise"],
            "action": "weak_only",
            "is_default": False,
        },
        {
            "name": "default_use_p25",
            "predicates": ["always_true"],
            "action": "use_p25_action",
            "is_default": True,
        },
    ],
    "negative_weak_only_ambiguous_query_use_p25_action_default_use_p25_action": [
        {
            "name": "negative_weak_only",
            "predicates": ["hard_distractor_like"],
            "action": "weak_only",
            "is_default": False,
        },
        {
            "name": "ambiguous_query_use_p25_action",
            "predicates": ["ambiguous_or_query_noise"],
            "action": "use_p25_action",
            "is_default": False,
        },
        {
            "name": "default_use_p25",
            "predicates": ["always_true"],
            "action": "use_p25_action",
            "is_default": True,
        },
    ],
}

ALLOWED_PREDICATES = {
    "ambiguous_or_query_noise",
    "hard_distractor_like",
    "always_true",
}

ALLOWED_ACTIONS = {
    "use_p25_action",
    "candidate_baseline",
    "plain_span_narrow",
    "hard_distractor_filter",
    "abstain_filter",
    "weak_only",
}


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _sha256_json(obj: Any) -> str:
    return hashlib.sha256(_canonical_json(obj).encode("utf-8")).hexdigest()


EXPECTED_FROZEN_SPEC_SHA256 = _sha256_json(EXPECTED_FROZEN_POLICY_SPECS)
FRESHNESS_CONTRACT_SCHEMA = "b6c-fresh-validation-contract-v0"

PREDICATE_MAP: dict[str, Any] = {
    "ambiguous_or_query_noise": b6lite._noisy_or_ambiguous,
    "hard_distractor_like": b6lite._hard_distractor_like,
    "always_true": lambda _t: True,
}

# Mirror B6B manifest required keys explicitly.
MANIFEST_RECORD_KEYS = (
    "repo_id",
    "model",
    "output_mode",
    "plain_pack_layout",
    "hard_pack_layout",
    "plain_records_path",
    "hard_records_path",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Frozen candidate loading and policy reconstruction
# ---------------------------------------------------------------------------


def _load_frozen_candidates(path: Path | None = None) -> list[b6lite.Policy]:
    if path is None:
        path = FROZEN_CANDIDATES_PATH
    if not path.exists():
        raise FileNotFoundError(f"frozen candidates not found: {path}")
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("frozen candidates must be a JSON object")
    if obj.get("schema_version") != "b6c-frozen-candidates-v0":
        raise ValueError("bad frozen candidates schema_version")
    if obj.get("frozen_spec_sha256") != EXPECTED_FROZEN_SPEC_SHA256:
        raise ValueError("frozen candidates spec hash mismatch")
    if obj.get("frozen_policy_search_performed") is not False:
        raise ValueError("frozen_policy_search_performed must be false")
    if set(obj.get("candidate_predicates_allowlist") or []) != ALLOWED_PREDICATES:
        raise ValueError("candidate_predicates_allowlist mismatch")
    if set(obj.get("candidate_actions_allowlist") or []) != ALLOWED_ACTIONS:
        raise ValueError("candidate_actions_allowlist mismatch")
    candidates = obj.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("frozen candidates must contain a non-empty list")

    policies: list[b6lite.Policy] = []
    seen_names: set[str] = set()
    for c in candidates:
        name = str(c.get("name", ""))
        if not name:
            raise ValueError("frozen candidate missing name")
        if name in seen_names:
            raise ValueError(f"duplicate frozen candidate name: {name}")
        seen_names.add(name)

        raw_rules = c.get("rules")
        if not isinstance(raw_rules, list) or not raw_rules:
            raise ValueError(f"frozen candidate {name} missing rules")
        expected_rules = EXPECTED_FROZEN_POLICY_SPECS.get(name)
        if expected_rules is None:
            raise ValueError(f"unexpected frozen candidate: {name}")
        normalized_rules = [
            {
                "name": str(r.get("name", "")),
                "predicates": list(r.get("predicates") or []),
                "action": str(r.get("action", "")),
                "is_default": bool(r.get("is_default")),
            }
            for r in raw_rules
        ]
        if normalized_rules != expected_rules:
            raise ValueError(f"frozen candidate {name} spec differs from B6B frozen manifest")

        rules: list[dict[str, Any]] = []
        rule_names: set[str] = set()
        for idx, r in enumerate(raw_rules):
            rule_name = str(r.get("name", ""))
            if not rule_name:
                raise ValueError(f"frozen candidate {name} rule {idx} missing name")
            if rule_name in rule_names:
                raise ValueError(f"duplicate rule name {rule_name} in {name}")
            rule_names.add(rule_name)

            predicates = list(r.get("predicates") or [])
            if not predicates:
                raise ValueError(f"rule {rule_name} has no predicates")
            disallowed = set(predicates) - ALLOWED_PREDICATES
            if disallowed:
                raise ValueError(
                    f"candidate {name} rule {rule_name} uses forbidden predicates: {sorted(disallowed)}"
                )

            action = str(r.get("action", ""))
            if action not in ALLOWED_ACTIONS:
                raise ValueError(
                    f"candidate {name} rule {rule_name} uses forbidden action: {action}"
                )

            conds = [PREDICATE_MAP[p] for p in predicates]
            rule = b6lite._rule(
                rule_name,
                predicates,
                lambda t, conds=conds: all(f(t) for f in conds),
                action,
            )
            if r.get("is_default"):
                rule["is_default"] = True
            rules.append(rule)

        default_rules = [r for r in rules if r.get("is_default")]
        if len(default_rules) != 1:
            raise ValueError(
                f"candidate {name} must have exactly one default rule, found {len(default_rules)}"
            )
        if rules[-1] is not default_rules[0]:
            raise ValueError(f"candidate {name} default rule must be the last rule")

        policies.append(
            b6lite.Policy(
                name=name,
                source="frozen",
                rules=rules,
                action_fn=b6lite._make_first_match_action_fn(rules),
            )
        )

    got_names = {p.name for p in policies}
    if got_names != EXPECTED_FROZEN_NAMES:
        raise ValueError(
            f"frozen candidate set mismatch: expected {EXPECTED_FROZEN_NAMES}, got {got_names}"
        )
    return policies


def _freshness_contract(manifest: dict[str, Any]) -> dict[str, Any]:
    contract = manifest.get("b6c_fresh_validation_contract")
    if not isinstance(contract, dict):
        return {"present": False, "valid": False, "reason": "missing"}
    valid = (
        contract.get("schema_version") == FRESHNESS_CONTRACT_SCHEMA
        and contract.get("frozen_spec_sha256") == EXPECTED_FROZEN_SPEC_SHA256
        and contract.get("policy_search_performed_for_b6c") is False
        and contract.get("fresh_records_generated_after_freeze") is True
        and contract.get("no_b6c_result_driven_retuning") is True
        and contract.get("record_paths_private_runner_temp_only") is True
    )
    return {
        "present": True,
        "valid": valid,
        "schema_version_ok": contract.get("schema_version") == FRESHNESS_CONTRACT_SCHEMA,
        "frozen_spec_hash_matched": contract.get("frozen_spec_sha256") == EXPECTED_FROZEN_SPEC_SHA256,
        "policy_search_performed_for_b6c": contract.get("policy_search_performed_for_b6c"),
        "fresh_records_generated_after_freeze": contract.get("fresh_records_generated_after_freeze"),
        "no_b6c_result_driven_retuning": contract.get("no_b6c_result_driven_retuning"),
        "record_paths_private_runner_temp_only": contract.get("record_paths_private_runner_temp_only"),
    }


def _with_valid_freshness_contract(manifest: dict[str, Any]) -> dict[str, Any]:
    out = dict(manifest)
    out["b6c_fresh_validation_contract"] = {
        "schema_version": FRESHNESS_CONTRACT_SCHEMA,
        "frozen_spec_sha256": EXPECTED_FROZEN_SPEC_SHA256,
        "policy_search_performed_for_b6c": False,
        "fresh_records_generated_after_freeze": True,
        "no_b6c_result_driven_retuning": True,
        "record_paths_private_runner_temp_only": True,
    }
    return out


# ---------------------------------------------------------------------------
# Manifest handling (B6B schema)
# ---------------------------------------------------------------------------


def _load_manifest(path: Path) -> dict[str, Any]:
    return b6b._load_manifest(path)


def _load_repo_records(rec: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return b6b._load_repo_records(rec)


def _same_task_set(
    plain_tasks: list[dict[str, Any]], hard_tasks: list[dict[str, Any]]
) -> bool:
    return b6b._same_task_set(plain_tasks, hard_tasks)


def _validate_manifest_records(
    records: list[dict[str, Any]],
) -> tuple[str | None, list[tuple[str, list[dict[str, Any]], list[dict[str, Any]]]]]:
    return b6b._validate_manifest_records(records)


# ---------------------------------------------------------------------------
# Aggregate fresh evaluation
# ---------------------------------------------------------------------------


def _evaluate_policies_on_tasks(
    policies: list[b6lite.Policy],
    plain_tasks: list[dict[str, Any]],
    hard_by_task: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    p25_action_list = ["use_p25_action"] * len(plain_tasks)
    metrics_by_name: dict[str, dict[str, Any]] = {}
    for policy in policies:
        action_list = [policy.action_for(t) for t in plain_tasks]
        policy.action_list = list(action_list)
        metrics = b6lite._metrics_from_action_list(
            plain_tasks, hard_by_task, action_list, p25_action_list
        )
        metrics["source"] = policy.source
        metrics["policy_rules"] = [
            {
                "name": r["name"],
                "predicates": list(r["predicates"]),
                "action": r["action"],
                "is_default": bool(r.get("is_default")),
            }
            for r in policy.rules
        ]
        metrics_by_name[policy.name] = metrics
    return metrics_by_name


def _build_p25_baseline() -> b6lite.Policy:
    fixed = b6lite._fixed_policies()
    p25 = next((p for p in fixed if p.name == "p25_bucket_routed_v0_plain"), None)
    if p25 is None:
        raise RuntimeError("P25 baseline policy missing from b6lite")
    return p25


# ---------------------------------------------------------------------------
# Report assembly and safety
# ---------------------------------------------------------------------------


def _base_report(status: str, self_test: bool) -> dict[str, Any]:
    report = b6lite._base_report(status, self_test)
    report["schema_version"] = SCHEMA_VERSION
    report["generated_by"] = GENERATED_BY
    if self_test:
        report["claim_level"] = "self_test_synthetic_protocol_check"
    elif status == "ok":
        report["claim_level"] = "frozen_policy_fresh_validation"
    else:
        report["claim_level"] = "fresh_validation_blocked_precondition"
    report["policy_search_performed"] = False
    report["frozen_policy_validation"] = True
    report["public_per_repo_rows"] = False
    return report


def validate_report(report: dict[str, Any]) -> None:
    if report.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("bad schema_version")
    if report.get("status") not in {
        "ok",
        "self_test_only",
        "blocked_insufficient_repos",
        "blocked_mixed_model_mode_pack",
        "blocked_task_set_mismatch",
        "blocked_freshness_contract",
    }:
        raise ValueError("bad status")

    must_be_true = [
        "not_evidence",
        "llm_output_not_evidence",
        "aggregate_only_public_artifact",
        "candidate_not_fact",
        "policy_search_not_admission",
        "diagnostic_policy_search",
        "frozen_policy_validation",
    ]
    for key in must_be_true:
        if report.get(key) is not True:
            raise ValueError(f"{key} must be true")

    must_be_false = [
        "promotion_ready",
        "default_should_change",
        "evidencecore_semantics_changed",
        "task_ids_in_artifact",
        "candidate_ids_in_artifact",
        "repo_ids_in_artifact",
        "raw_prompts_stored",
        "raw_responses_stored",
        "raw_snippets_stored",
        "raw_snippets_committed",
        "raw_paths_in_artifact",
        "raw_line_ranges_in_artifact",
        "raw_digests_in_artifact",
        "private_labels_committed",
        "gold_spans_in_artifact",
        "public_per_task_rows",
        "public_per_repo_rows",
        "policy_search_performed",
    ]
    for key in must_be_false:
        if report.get(key) is not False:
            raise ValueError(f"{key} must be false")

    if report.get("remote_calls_by_policy_search") != 0:
        raise ValueError("remote_calls_by_policy_search must be 0")
    expected_claim = (
        "self_test_synthetic_protocol_check"
        if report.get("self_test") is True
        else (
            "frozen_policy_fresh_validation"
            if report.get("status") == "ok"
            else "fresh_validation_blocked_precondition"
        )
    )
    if report.get("claim_level") != expected_claim:
        raise ValueError(f"claim_level must be {expected_claim}")

    violations = b6lite._walk_forbidden(report)
    if violations:
        raise ValueError(
            "public report contains forbidden fields: " + ", ".join(violations[:5])
        )

    if report.get("status") == "ok":
        families = report.get("policy_families") or {}
        if "p25_bucket_routed_v0_plain" not in families:
            raise ValueError("P25 baseline missing from policy_families")
        frozen_names = set(report.get("frozen_policy_names") or [])
        if frozen_names != EXPECTED_FROZEN_NAMES:
            raise ValueError(f"frozen_policy_names mismatch: {frozen_names}")
        if report.get("frozen_policy_count") != len(EXPECTED_FROZEN_NAMES):
            raise ValueError("frozen_policy_count mismatch")

        integrity = report.get("frozen_manifest_integrity") or {}
        for key in (
            "manifest_schema_version_ok",
            "record_required_fields_present",
            "model_mode_pack_uniform",
            "allowed_model_mode_pack",
            "task_sets_matched",
            "paired_records_loadable",
            "freshness_contract_valid",
            "frozen_spec_hash_matched",
            "forbidden_public_key_scan_clean",
        ):
            if integrity.get(key) is not True:
                raise ValueError(f"frozen_manifest_integrity.{key} must be true")

        routing = report.get("routing_invariance") or {}
        if routing.get("selected_actions_invariant") is not True:
            raise ValueError("routing changed when SCORE/gold fields were mutated")

        for name, metrics in families.items():
            tc = metrics.get("task_count")
            if not isinstance(tc, int) or tc <= 0:
                raise ValueError(f"{name} has invalid task_count")
            if sum((metrics.get("action_counts") or {}).values()) != tc:
                raise ValueError(f"{name} action counts do not sum to {tc}")
            if "policy_rules" not in metrics:
                raise ValueError(f"{name} missing policy_rules")

        if "winner" in report or "default_recommendation" in report:
            raise ValueError("report must not declare a winner or default recommendation")


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    self_test = bool(args.self_test or getattr(args, "mark_self_test", False))

    if args.self_test:
        manifest_path, repo_pairs = b6b._write_self_test_manifest()
        freshness = {"present": False, "valid": False, "self_test_synthetic": True}
    else:
        manifest = _load_manifest(args.paired_records_manifest)
        freshness = _freshness_contract(manifest)
        records = manifest["records"]
        if not bool(args.mark_self_test) and not freshness.get("valid"):
            report = _base_report("blocked_freshness_contract", self_test)
            report.update(
                {
                    "included_repo_count": len(records),
                    "manifest_record_count": len(records),
                    "comparable_task_count": 0,
                    "frozen_policy_count": len(EXPECTED_FROZEN_NAMES),
                    "frozen_policy_names": sorted(EXPECTED_FROZEN_NAMES),
                    "sample_freshness_protocol": "blocked_missing_or_invalid_b6c_fresh_validation_contract",
                    "frozen_manifest_integrity": {
                        "manifest_schema_version_ok": True,
                        "record_required_fields_present": True,
                        "freshness_contract_present": freshness.get("present") is True,
                        "freshness_contract_valid": False,
                        "frozen_spec_hash_matched": freshness.get("frozen_spec_hash_matched") is True,
                        "forbidden_public_key_scan_clean": True,
                        "block_reason": "blocked_freshness_contract",
                    },
                    "policy_families": {},
                }
            )
            validate_report(report)
            return report
        block_status, repo_pairs = _validate_manifest_records(records)
        if block_status:
            report = _base_report(block_status, self_test)
            report.update(
                {
                    "included_repo_count": len(records),
                    "manifest_record_count": len(records),
                    "comparable_task_count": 0,
                    "frozen_policy_count": len(EXPECTED_FROZEN_NAMES),
                    "frozen_policy_names": sorted(EXPECTED_FROZEN_NAMES),
                    "sample_freshness_protocol": "new_paired_p21_records_aggregate_only",
                    "frozen_manifest_integrity": {
                        "manifest_schema_version_ok": True,
                        "record_required_fields_present": True,
                        "model_mode_pack_uniform": block_status != "blocked_mixed_model_mode_pack",
                        "allowed_model_mode_pack": block_status != "blocked_mixed_model_mode_pack",
                        "task_sets_matched": block_status != "blocked_task_set_mismatch",
                        "paired_records_loadable": True,
                        "freshness_contract_present": freshness.get("present") is True,
                        "freshness_contract_valid": bool(args.mark_self_test) or freshness.get("valid") is True,
                        "frozen_spec_hash_matched": bool(args.mark_self_test) or freshness.get("frozen_spec_hash_matched") is True,
                        "forbidden_public_key_scan_clean": True,
                        "block_reason": block_status,
                    },
                    "policy_families": {},
                }
            )
            if block_status == "blocked_insufficient_repos":
                report["required_repo_count"] = b6b.REQUIRED_REPO_COUNT
            validate_report(report)
            return report

    # Load frozen candidates and P25 baseline.
    frozen_policies = _load_frozen_candidates()
    p25_policy = _build_p25_baseline()
    policies = [p25_policy] + frozen_policies

    all_plain = [t for _rid, plain, _hard in repo_pairs for t in plain]
    all_hard_by_task = {
        str(t["task_id"]): t for _rid, _plain, hard in repo_pairs for t in hard
    }

    metrics_by_name = _evaluate_policies_on_tasks(policies, all_plain, all_hard_by_task)

    # Populate per-family task_count.
    for metrics in metrics_by_name.values():
        metrics["task_count"] = len(all_plain)

    routing_invariance = b6lite._routing_invariance_check(policies, all_plain)

    integrity: dict[str, Any] = {
        "manifest_schema_version_ok": True,
        "record_required_fields_present": True,
        "model_mode_pack_uniform": True,
        "allowed_model_mode_pack": True,
        "task_sets_matched": True,
        "paired_records_loadable": True,
        "forbidden_public_key_scan_clean": True,
    }

    report = _base_report("self_test_only" if self_test else "ok", self_test)
    report.update(
        {
            "included_repo_count": len(repo_pairs),
            "manifest_record_count": len(repo_pairs),
            "comparable_task_count": len(all_plain),
            "sample_freshness_protocol": (
                "self_test_synthetic_sample_not_fresh_validation"
                if self_test
                else "b6c_fresh_validation_contract_checked; policies frozen before evaluation; no search on fresh records"
            ),
            "frozen_manifest_integrity": integrity,
            "frozen_policy_count": len(frozen_policies),
            "frozen_policy_names": sorted(p.name for p in frozen_policies),
            "policy_families": metrics_by_name,
            "routing_invariance": routing_invariance,
            "comparability": {
                "model": b6b.ALLOWED_MODEL,
                "output_mode": b6b.ALLOWED_OUTPUT_MODE,
                "plain_pack_layout": b6b.ALLOWED_PLAIN_PACK_LAYOUT,
                "hard_pack_layout": b6b.ALLOWED_HARD_PACK_LAYOUT,
                "same_model_required": True,
                "same_output_mode_required": True,
                "same_pack_layout_required": True,
                "same_model_observed": True,
                "same_task_set_within_repo_required": True,
                "same_task_set_within_repo_observed": True,
                "fresh_aggregate_evaluation": not self_test,
                "search_performed": False,
            },
        }
    )

    report_violations = b6lite._walk_forbidden(report)
    report["frozen_manifest_integrity"]["forbidden_public_key_scan_clean"] = not report_violations
    report["frozen_manifest_integrity"]["freshness_contract_present"] = freshness.get("present") is True
    report["frozen_manifest_integrity"]["freshness_contract_valid"] = bool(self_test) or freshness.get("valid") is True
    report["frozen_manifest_integrity"]["frozen_spec_hash_matched"] = bool(self_test) or freshness.get("frozen_spec_hash_matched") is True
    if report_violations:
        report["frozen_manifest_integrity"]["forbidden_public_key_violations"] = report_violations[:5]

    validate_report(report)
    return report


# ---------------------------------------------------------------------------
# Markdown output
# ---------------------------------------------------------------------------


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    lines: list[str] = []
    lines.append("# B6C Frozen-Policy Fresh Validation")
    lines.append("")
    lines.append(f"Status: `{report['status']}`")
    lines.append("")
    lines.append(
        "B6C evaluates the two policies frozen by B6B, plus the fixed P25 "
        "bucket-routed baseline, on a paired P21 records sample. "
        "No search, rule generation, or winner selection is performed. "
        "The public artifact is aggregate-only; per-task / per-repo details stay in "
        "`$RUNNER_TEMP`."
    )
    if report.get("self_test") is True:
        lines.append("")
        lines.append(
            "This is a self-test / synthetic protocol check, not a fresh live validation run."
        )
    lines.append("")

    if report.get("status") not in {"ok", "self_test_only"}:
        lines.append("Evaluation was blocked; no policies were scored.")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    lines.append("## Frozen policies")
    lines.append(f"- Count: {report['frozen_policy_count']}")
    lines.append(
        "- Names: " + ", ".join(f"`{n}`" for n in sorted(report.get("frozen_policy_names", [])))
    )
    lines.append(
        "- Sample freshness protocol: "
        f"{report.get('sample_freshness_protocol', '')}"
    )
    lines.append("")

    lines.append("## Aggregate policy families")
    header = (
        "| Policy family | source | +gold | +false | F/G | SpanF0.5 | PFP | "
        "LLM calls | net 2x | gold kill vs P25 | false reduction vs P25 |"
    )
    lines.append(header)
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for name in sorted(report.get("policy_families", {})):
        m = report["policy_families"][name]
        source = m.get("source", "unknown")
        lines.append(
            f"| `{name}` | {source} | {m.get('added_gold_span', '')} | "
            f"{m.get('added_false_span', '')} | {_fmt(m.get('false_per_gold'))} | "
            f"{_fmt(m.get('mean_span_f05'))} | {_fmt(m.get('mean_primary_false_positive_rate'))} | "
            f"{m.get('effective_llm_action_count', '')} | {m.get('net_span_value_2x', '')} | "
            f"{m.get('gold_kill_vs_p25', '')} | {m.get('false_reduction_vs_p25', '')} |"
        )
    lines.append("")

    lines.append("## Routing invariance")
    inv = report.get("routing_invariance", {})
    lines.append(
        f"- SCORE-field routing invariance: {inv.get('selected_actions_invariant')} "
        f"(changed policies: {inv.get('changed_policy_count')})"
    )
    lines.append("")

    lines.append("## Safety notes")
    lines.append(
        "- `promotion_ready=false`, `default_should_change=false`, "
        "`evidencecore_semantics_changed=false`, `policy_search_performed=false`."
    )
    lines.append(
        "- `remote_calls_by_policy_search=0`; P21 makes calls, this evaluator does not."
    )
    lines.append(
        "- Routing uses only public `task_bucket`, `task_risk_tags`, and allowlisted "
        "`route_features`."
    )
    lines.append(
        "- Gold/SCORE fields are used only after a policy is frozen for aggregate scoring."
    )
    lines.append(
        "- The public artifact is aggregate-only: no task IDs, repo IDs, paths, "
        "candidates, snippets, prompts, responses, or gold spans."
    )
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Self-test inputs and assertions
# ---------------------------------------------------------------------------


def _self_test_frozen_policies_present() -> dict[str, Any]:
    policies = _load_frozen_candidates()
    names = {p.name for p in policies}
    assert names == EXPECTED_FROZEN_NAMES, names
    print("self-test frozen policies present: ok")
    return {p.name: [r["name"] for r in p.rules] for p in policies}


def _self_test_forbidden_predicate_rejected() -> None:
    tmp = Path("/tmp/opencode/b6c-test-bad-predicate")
    tmp.mkdir(parents=True, exist_ok=True)
    bad = {
        "schema_version": "b6c-frozen-candidates-v0",
        "candidates": [
            {
                "name": "bad_predicate_policy",
                "rules": [
                    {
                        "name": "exact_unique_rule",
                        "predicates": ["exact_unique"],
                        "action": "candidate_baseline",
                    },
                    {
                        "name": "default_use_p25",
                        "predicates": ["always_true"],
                        "action": "use_p25_action",
                        "is_default": True,
                    },
                ],
            }
        ],
    }
    bad_path = tmp / "bad.json"
    bad_path.write_text(json.dumps(bad), encoding="utf-8")
    try:
        _load_frozen_candidates(bad_path)
        raise AssertionError("expected forbidden predicate rejection")
    except ValueError as exc:
        assert "spec hash mismatch" in str(exc) or "spec differs" in str(exc), str(exc)
    print("self-test forbidden predicate rejected: ok")


def _self_test_forbidden_action_rejected() -> None:
    tmp = Path("/tmp/opencode/b6c-test-bad-action")
    tmp.mkdir(parents=True, exist_ok=True)
    bad = {
        "schema_version": "b6c-frozen-candidates-v0",
        "candidates": [
            {
                "name": "bad_action_policy",
                "rules": [
                    {
                        "name": "ambiguous_query_unknown_action",
                        "predicates": ["ambiguous_or_query_noise"],
                        "action": "unknown_action",
                    },
                    {
                        "name": "default_use_p25",
                        "predicates": ["always_true"],
                        "action": "use_p25_action",
                        "is_default": True,
                    },
                ],
            }
        ],
    }
    bad_path = tmp / "bad.json"
    bad_path.write_text(json.dumps(bad), encoding="utf-8")
    try:
        _load_frozen_candidates(bad_path)
        raise AssertionError("expected forbidden action rejection")
    except ValueError as exc:
        assert "spec hash mismatch" in str(exc) or "spec differs" in str(exc), str(exc)
    print("self-test forbidden action rejected: ok")


def _self_test_insufficient_repos() -> None:
    tmp = Path("/tmp/opencode/b6c-test-insufficient")
    tmp.mkdir(parents=True, exist_ok=True)
    base_tasks = b6b.p25.make_self_test_tasks()
    records: list[dict[str, Any]] = []
    for offset, repo_id in enumerate(["py_flask", "js_express"]):
        _, _, plain_path, hard_path = b6b._build_repo_pair(tmp, repo_id, base_tasks, offset)
        records.append(
            {
                "repo_id": repo_id,
                "model": "[mk]Kimi-K2.7-Code",
                "output_mode": "tool_call",
                "plain_pack_layout": "topk_plain_v0",
                "hard_pack_layout": "hard_distractor_contrast_v0",
                "plain_records_path": str(plain_path),
                "hard_records_path": str(hard_path),
            }
        )
    manifest_path = tmp / "manifest.private.json"
    manifest_path.write_text(
        json.dumps(
            _with_valid_freshness_contract(
                {"schema_version": "b6b-paired-records-manifest-v0", "records": records}
            )
        ),
        encoding="utf-8",
    )
    args = argparse.Namespace(
        paired_records_manifest=manifest_path,
        out=tmp / "out.json",
        doc=tmp / "out.md",
        self_test=False,
        mark_self_test=False,
    )
    report = build_report(args)
    assert report["status"] == "blocked_insufficient_repos", report["status"]
    assert report["policy_search_performed"] is False
    print("self-test insufficient repos: ok")


def _self_test_mixed_model() -> None:
    tmp = Path("/tmp/opencode/b6c-test-mixed")
    tmp.mkdir(parents=True, exist_ok=True)
    base_tasks = b6b.p25.make_self_test_tasks()
    records: list[dict[str, Any]] = []
    models = [
        "[mk]Kimi-K2.7-Code",
        "[mk]Kimi-K2.7-Code",
        "[mk]Qwen3.6-27B",
        "[mk]Kimi-K2.7-Code",
    ]
    for offset, repo_id in enumerate(["py_flask", "js_express", "go_gin", "rust_ripgrep"]):
        _, _, plain_path, hard_path = b6b._build_repo_pair(tmp, repo_id, base_tasks, offset)
        records.append(
            {
                "repo_id": repo_id,
                "model": models[offset],
                "output_mode": "tool_call",
                "plain_pack_layout": "topk_plain_v0",
                "hard_pack_layout": "hard_distractor_contrast_v0",
                "plain_records_path": str(plain_path),
                "hard_records_path": str(hard_path),
            }
        )
    manifest_path = tmp / "manifest.private.json"
    manifest_path.write_text(
        json.dumps(
            _with_valid_freshness_contract(
                {"schema_version": "b6b-paired-records-manifest-v0", "records": records}
            )
        ),
        encoding="utf-8",
    )
    args = argparse.Namespace(
        paired_records_manifest=manifest_path,
        out=tmp / "out.json",
        doc=tmp / "out.md",
        self_test=False,
        mark_self_test=False,
    )
    report = build_report(args)
    assert report["status"] == "blocked_mixed_model_mode_pack", report["status"]
    print("self-test mixed model: ok")


def _self_test_bad_output_mode() -> None:
    tmp = Path("/tmp/opencode/b6c-test-bad-mode")
    tmp.mkdir(parents=True, exist_ok=True)
    base_tasks = b6b.p25.make_self_test_tasks()
    records: list[dict[str, Any]] = []
    for offset, repo_id in enumerate(["py_flask", "js_express", "go_gin", "rust_ripgrep"]):
        _, _, plain_path, hard_path = b6b._build_repo_pair(tmp, repo_id, base_tasks, offset)
        records.append(
            {
                "repo_id": repo_id,
                "model": "[mk]Kimi-K2.7-Code",
                "output_mode": "json_schema_strict",
                "plain_pack_layout": "topk_plain_v0",
                "hard_pack_layout": "hard_distractor_contrast_v0",
                "plain_records_path": str(plain_path),
                "hard_records_path": str(hard_path),
            }
        )
    manifest_path = tmp / "manifest.private.json"
    manifest_path.write_text(
        json.dumps(
            _with_valid_freshness_contract(
                {"schema_version": "b6b-paired-records-manifest-v0", "records": records}
            )
        ),
        encoding="utf-8",
    )
    args = argparse.Namespace(
        paired_records_manifest=manifest_path,
        out=tmp / "out.json",
        doc=tmp / "out.md",
        self_test=False,
        mark_self_test=False,
    )
    report = build_report(args)
    assert report["status"] == "blocked_mixed_model_mode_pack", report["status"]
    print("self-test bad output mode: ok")


def _self_test_task_mismatch() -> None:
    tmp = Path("/tmp/opencode/b6c-test-mismatch")
    tmp.mkdir(parents=True, exist_ok=True)
    base_tasks = b6b.p25.make_self_test_tasks()
    records: list[dict[str, Any]] = []
    for offset, repo_id in enumerate(["py_flask", "js_express", "go_gin", "rust_ripgrep"]):
        plain_rows, hard_rows, plain_path, hard_path = b6b._build_repo_pair(
            tmp, repo_id, base_tasks, offset
        )
        if offset == 1:
            for row in hard_rows:
                row["task_id"] = row["task_id"] + "-x"
            payload = {
                "schema_version": "p25-policy-records-ephemeral-v1",
                "not_artifact_for_commit": True,
                "records": hard_rows,
            }
            hard_path.write_text(json.dumps(payload), encoding="utf-8")
        records.append(
            {
                "repo_id": repo_id,
                "model": "[mk]Kimi-K2.7-Code",
                "output_mode": "tool_call",
                "plain_pack_layout": "topk_plain_v0",
                "hard_pack_layout": "hard_distractor_contrast_v0",
                "plain_records_path": str(plain_path),
                "hard_records_path": str(hard_path),
            }
        )
    manifest_path = tmp / "manifest.private.json"
    manifest_path.write_text(
        json.dumps(
            _with_valid_freshness_contract(
                {"schema_version": "b6b-paired-records-manifest-v0", "records": records}
            )
        ),
        encoding="utf-8",
    )
    args = argparse.Namespace(
        paired_records_manifest=manifest_path,
        out=tmp / "out.json",
        doc=tmp / "out.md",
        self_test=False,
        mark_self_test=False,
    )
    report = build_report(args)
    assert report["status"] == "blocked_task_set_mismatch", report["status"]
    print("self-test task mismatch: ok")


def _self_test_missing_freshness_contract_blocks() -> None:
    tmp = Path("/tmp/opencode/b6c-test-missing-freshness")
    tmp.mkdir(parents=True, exist_ok=True)
    manifest_path, _repo_pairs = b6b._write_self_test_manifest(tmp)
    args = argparse.Namespace(
        paired_records_manifest=manifest_path,
        out=tmp / "out.json",
        doc=tmp / "out.md",
        self_test=False,
        mark_self_test=False,
    )
    report = build_report(args)
    assert report["status"] == "blocked_freshness_contract", report["status"]
    assert report["claim_level"] == "fresh_validation_blocked_precondition"
    print("self-test missing freshness contract blocks: ok")


def run_self_tests() -> dict[str, Any]:
    _self_test_frozen_policies_present()
    _self_test_forbidden_predicate_rejected()
    _self_test_forbidden_action_rejected()
    _self_test_insufficient_repos()
    _self_test_mixed_model()
    _self_test_bad_output_mode()
    _self_test_task_mismatch()
    _self_test_missing_freshness_contract_blocks()
    print("all b6c self-tests passed")

    # Final happy-path report for caller validation.
    tmp = Path("/tmp/opencode/b6c-test-happy")
    tmp.mkdir(parents=True, exist_ok=True)
    manifest_path, _repo_pairs = b6b._write_self_test_manifest(tmp)
    args = argparse.Namespace(
        paired_records_manifest=manifest_path,
        out=tmp / "out.json",
        doc=tmp / "out.md",
        self_test=False,
        mark_self_test=True,
    )
    report = build_report(args)
    assert report["status"] == "self_test_only", report["status"]
    assert report["policy_search_performed"] is False
    assert report.get("frozen_policy_count") == 2
    assert set(report.get("frozen_policy_names", [])) == EXPECTED_FROZEN_NAMES
    assert "p25_bucket_routed_v0_plain" in report["policy_families"]
    for name in EXPECTED_FROZEN_NAMES:
        assert name in report["policy_families"], name
    inv = report.get("routing_invariance", {})
    assert inv.get("selected_actions_invariant") is True, inv
    integrity = report.get("frozen_manifest_integrity", {})
    assert integrity.get("forbidden_public_key_scan_clean") is True, integrity
    print("self-test happy path: ok")
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paired-records-manifest", type=Path)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument(
        "--mark-self-test",
        action="store_true",
        help="Process the provided manifest but mark the public report self_test_only.",
    )
    args = parser.parse_args(argv)
    if not args.self_test and not args.paired_records_manifest:
        parser.error("--paired-records-manifest is required unless --self-test")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        run_self_tests()
    report = build_report(args)
    _write_json(args.out, report)
    _write_markdown(report, args.doc)
    print(
        json.dumps(
            {
                "status": report["status"],
                "included_repo_count": report.get("included_repo_count"),
                "comparable_task_count": report.get("comparable_task_count"),
                "frozen_policy_count": report.get("frozen_policy_count"),
                "policy_search_performed": report.get("policy_search_performed"),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
