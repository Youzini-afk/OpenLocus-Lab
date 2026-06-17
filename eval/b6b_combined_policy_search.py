#!/usr/bin/env python3
"""B6B combined-matrix interpretable policy search.

B6B is a live diagnostic stage that merges paired P21 ephemeral records from
multiple repos and performs a true leave-one-repo-out interpretable policy
search:

* For every repo, train the pre-registered rule grammar on all *other* repos,
  select the Pareto-frontier policies on that training set, freeze them, and
  evaluate them on the held-out repo.
* Fixed P25 bucket-routed and fixed RMC baselines are also evaluated on every
  held-out repo.
* Only aggregate held-out metrics are reported; per-task / per-repo identities
  stay inside the private ``$RUNNER_TEMP`` paired-records manifest.

The public artifact is aggregate-only.  It never publishes repo IDs, task IDs,
candidate IDs, paths, line ranges, digests, snippets, prompts, responses, labels,
or gold spans.

Routing uses only public RUN-phase fields: ``task_bucket``, ``task_risk_tags``,
and allowlisted ``route_features`` booleans.  SCORE-phase fields such as
``has_gold`` and ``score_group`` are used only after policies are frozen.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_FILE_DIR = Path(__file__).resolve().parent
if str(_FILE_DIR) not in sys.path:
    sys.path.insert(0, str(_FILE_DIR))

import b6_lite_interpretable_policy_search as b6lite
import p25_bucket_policy as p25

SCHEMA_VERSION = "b6b-combined-policy-search-v0"
GENERATED_BY = "b6b_combined_policy_search"
DEFAULT_OUT = Path(
    "artifacts/b6b_combined_policy_search/b6b_combined_policy_search_report.json"
)
DEFAULT_DOC = Path("docs/real-provider-ci/b6b-combined-policy-search.md")

REQUIRED_REPO_COUNT = 4
ALLOWED_MODEL = "[mk]Kimi-K2.7-Code"
ALLOWED_OUTPUT_MODE = "tool_call"
ALLOWED_PLAIN_PACK_LAYOUT = "topk_plain_v0"
ALLOWED_HARD_PACK_LAYOUT = "hard_distractor_contrast_v0"

FORBIDDEN_PUBLIC_KEYS = b6lite.FORBIDDEN_PUBLIC_KEYS
FORBIDDEN_VALUE_PATTERNS = b6lite.FORBIDDEN_VALUE_PATTERNS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _avg(vals: list[float]) -> float | None:
    return sum(vals) / len(vals) if vals else None


def _safe_div(num: float, den: float) -> float | None:
    return num / den if den else None


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Manifest handling
# ---------------------------------------------------------------------------


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"manifest not found: {path}")
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("manifest must be a JSON object")
    if obj.get("schema_version") != "b6b-paired-records-manifest-v0":
        raise ValueError("manifest schema_version must be b6b-paired-records-manifest-v0")
    records = obj.get("records")
    if not isinstance(records, list):
        raise ValueError("manifest.records must be a list")
    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            raise ValueError(f"manifest.records[{i}] must be an object")
        for key in (
            "repo_id",
            "model",
            "output_mode",
            "plain_pack_layout",
            "hard_pack_layout",
            "plain_records_path",
            "hard_records_path",
        ):
            if key not in rec:
                raise ValueError(f"manifest.records[{i}] missing {key}")
    return obj


def _load_repo_records(
    rec: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    plain_path = Path(rec["plain_records_path"])
    hard_path = Path(rec["hard_records_path"])
    if not plain_path.exists():
        raise FileNotFoundError(f"plain records not found: {plain_path}")
    if not hard_path.exists():
        raise FileNotFoundError(f"hard records not found: {hard_path}")
    plain = b6lite._load_records(plain_path)
    hard = b6lite._load_records(hard_path)
    return plain, hard


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _same_task_set(
    plain_tasks: list[dict[str, Any]], hard_tasks: list[dict[str, Any]]
) -> bool:
    plain_ids = [str(t["task_id"]) for t in plain_tasks]
    hard_ids = [str(t["task_id"]) for t in hard_tasks]
    return (
        sorted(plain_ids) == sorted(hard_ids)
        and len(set(plain_ids)) == len(plain_ids)
        and len(set(hard_ids)) == len(hard_ids)
    )


def _validate_manifest_records(
    records: list[dict[str, Any]],
) -> tuple[str | None, list[tuple[str, list[dict[str, Any]], list[dict[str, Any]]]]]:
    """Return (status_block_reason_or_None, loaded_repo_plain_hard_pairs)."""
    if len(records) < REQUIRED_REPO_COUNT:
        return (
            "blocked_insufficient_repos",
            [],
        )

    # All repos must declare the same model, output_mode, and pack layouts.
    # First B6B is Kimi/tool_call only; fail closed unless explicitly same.
    def _first(key: str) -> str:
        return str(records[0].get(key, ""))

    for key in ("model", "output_mode", "plain_pack_layout", "hard_pack_layout"):
        expected = _first(key)
        for rec in records[1:]:
            if str(rec.get(key, "")) != expected:
                return ("blocked_mixed_model_mode_pack", [])
    if _first("model") != ALLOWED_MODEL:
        return ("blocked_mixed_model_mode_pack", [])
    if _first("output_mode") != ALLOWED_OUTPUT_MODE:
        return ("blocked_mixed_model_mode_pack", [])
    if _first("plain_pack_layout") != ALLOWED_PLAIN_PACK_LAYOUT:
        return ("blocked_mixed_model_mode_pack", [])
    if _first("hard_pack_layout") != ALLOWED_HARD_PACK_LAYOUT:
        return ("blocked_mixed_model_mode_pack", [])

    loaded: list[tuple[str, list[dict[str, Any]], list[dict[str, Any]]]] = []
    for rec in records:
        plain, hard = _load_repo_records(rec)
        if not _same_task_set(plain, hard):
            return ("blocked_task_set_mismatch", [])
        # P21 task IDs are only guaranteed unique within a repo/run. Namespace
        # them before merging repos so hard-pack counterfactual outcomes cannot
        # overwrite another repo's task with the same local task_id. The public
        # B6B report never emits task IDs, namespaced or otherwise.
        repo_id = str(rec["repo_id"])
        for row in plain:
            row["task_id"] = f"{repo_id}::{row['task_id']}"
        for row in hard:
            row["task_id"] = f"{repo_id}::{row['task_id']}"
        loaded.append((repo_id, plain, hard))

    # Also require every repo pair to have non-empty tasks.
    for rid, plain, hard in loaded:
        if not plain or not hard:
            return ("blocked_task_set_mismatch", [])

    return (None, loaded)


# ---------------------------------------------------------------------------
# Leave-one-repo-out policy search / evaluation
# ---------------------------------------------------------------------------


def _evaluate_policies_on_tasks(
    policies: list[b6lite.Policy],
    plain_tasks: list[dict[str, Any]],
    hard_by_task: dict[str, dict[str, Any]],
    p25_action_list: list[str],
) -> dict[str, dict[str, Any]]:
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


def _select_train_policies(
    train_plain: list[dict[str, Any]],
    train_hard_by_task: dict[str, dict[str, Any]],
) -> tuple[list[b6lite.Policy], dict[str, Any]]:
    """Return selected policies (frontier + fixed baselines) and search accounting."""
    fixed = b6lite._fixed_policies()
    searched, rules_considered, rules_pruned = b6lite._generate_candidate_rules(
        train_plain
    )
    policies = fixed + searched

    metrics_by_name = _evaluate_policies_on_tasks(
        policies, train_plain, train_hard_by_task, ["use_p25_action"] * len(train_plain)
    )

    # Dedupe by action signature, preferring baseline source first.
    ordered_names = list(metrics_by_name.keys())
    seen_sigs: dict[tuple[str, ...], str] = {}
    deduped: dict[str, dict[str, Any]] = {}
    fixed_names = {p.name for p in fixed}
    for name in ordered_names:
        policy_obj = next(p for p in policies if p.name == name)
        sig = tuple(policy_obj.action_list)
        if name in fixed_names:
            # Fixed baselines are controls, not search candidates. Keep them even
            # if two controls collapse to the same action signature on a small
            # train split; only dedupe searched hypotheses against known sigs.
            deduped[name] = metrics_by_name[name]
            seen_sigs.setdefault(sig, name)
            continue
        if sig in seen_sigs:
            continue
        seen_sigs[sig] = name
        deduped[name] = metrics_by_name[name]

    frontier_info = b6lite._compute_frontier(deduped)
    frontier_set = set(frontier_info["frontier"])

    # Select fixed baselines + non-dominated frontier policies.
    selected_names = {
        name
        for name in deduped
        if name in frontier_set or name in fixed_names
    }

    # Preserve evaluation order and action lists on the *train* set.
    selected_policies = [p for p in policies if p.name in selected_names]

    searched_names = {p.name for p in searched}
    candidate_policy_count = sum(
        1 for name in deduped if name in searched_names
    )

    accounting = {
        "candidate_policy_count": candidate_policy_count,
        "selected_policy_count": len(selected_policies),
        "rules_considered": rules_considered,
        "rules_pruned_by_min_support": rules_pruned,
        "frontier_size": frontier_info["frontier_size"],
        "policies_dominated_by_p25": frontier_info["policies_dominated_by_p25"],
    }
    return selected_policies, accounting


def _evaluate_on_heldout(
    policies: list[b6lite.Policy],
    heldout_plain: list[dict[str, Any]],
    heldout_hard_by_task: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    p25_action_list = ["use_p25_action"] * len(heldout_plain)
    return _evaluate_policies_on_tasks(
        policies, heldout_plain, heldout_hard_by_task, p25_action_list
    )


def _leave_one_repo_out_evaluation(
    repo_pairs: list[tuple[str, list[dict[str, Any]], list[dict[str, Any]]]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Return per-fold accounting and per-family aggregated metrics."""
    fold_accounting: list[dict[str, Any]] = []
    family_values: dict[
        str, dict[str, list[float]]
    ] = defaultdict(lambda: defaultdict(list))
    family_meta: dict[str, dict[str, Any]] = {}

    for rid, plain, hard in repo_pairs:
        hard_by_task = {str(t["task_id"]): t for t in hard}
        train_plain = [
            t
            for orid, op, _oh in repo_pairs
            if orid != rid
            for t in op
        ]
        train_hard_by_task = {
            str(t["task_id"]): t
            for orid, _op, oh in repo_pairs
            if orid != rid
            for t in oh
        }

        selected, accounting = _select_train_policies(
            train_plain, train_hard_by_task
        )
        heldout_metrics = _evaluate_on_heldout(
            selected, plain, hard_by_task
        )

        p25_metrics = heldout_metrics.get("p25_bucket_routed_v0_plain")

        fold_entry = {
            "repo_id_private_only": rid,
            "train_task_count": len(train_plain),
            "heldout_task_count": len(plain),
        }
        fold_entry.update(accounting)
        fold_accounting.append(fold_entry)

        for name, metrics in heldout_metrics.items():
            if name not in family_meta:
                family_meta[name] = {
                    "source": metrics.get("source", "unknown"),
                    "policy_rules": metrics.get("policy_rules", []),
                }
            d = family_values[name]
            for key in (
                "added_gold_span",
                "added_false_span",
                "net_span_value_2x",
                "effective_llm_action_count",
            ):
                d[key].append(float(metrics.get(key) or 0))
            for key in (
                "mean_span_f05",
                "mean_primary_false_positive_rate",
                "no_gold_false_primary_rate",
                "false_per_gold",
            ):
                v = metrics.get(key)
                if v is not None:
                    d[key].append(float(v))
            if p25_metrics is not None:
                d["delta_added_gold_span_vs_p25"].append(
                    float(metrics.get("added_gold_span") or 0)
                    - float(p25_metrics.get("added_gold_span") or 0)
                )
                d["delta_added_false_span_vs_p25"].append(
                    float(metrics.get("added_false_span") or 0)
                    - float(p25_metrics.get("added_false_span") or 0)
                )
                d["delta_net_span_value_2x_vs_p25"].append(
                    float(metrics.get("net_span_value_2x") or 0)
                    - float(p25_metrics.get("net_span_value_2x") or 0)
                )
                d["delta_mean_span_f05_vs_p25"].append(
                    _as_float_delta(metrics.get("mean_span_f05"), p25_metrics.get("mean_span_f05"))
                )
                d["delta_mean_pfp_vs_p25"].append(
                    _as_float_delta(
                        metrics.get("mean_primary_false_positive_rate"),
                        p25_metrics.get("mean_primary_false_positive_rate"),
                    )
                )

    return fold_accounting, _aggregate_family_metrics(family_values, family_meta)


def _as_float_delta(v: Any, baseline: Any) -> float:
    if v is None or baseline is None:
        return 0.0
    try:
        return float(v) - float(baseline)
    except (TypeError, ValueError):
        return 0.0


def _aggregate_family_metrics(
    family_values: dict[str, dict[str, list[float]]],
    family_meta: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    families: dict[str, dict[str, Any]] = {}
    for name, values in family_values.items():
        agg: dict[str, Any] = {
            "source": family_meta[name]["source"],
            "policy_rules": family_meta[name]["policy_rules"],
            "fold_appearances": len(values.get("added_gold_span", [])),
        }
        for key, vals in values.items():
            if not vals:
                agg[f"mean_{key}"] = None
                agg[f"worst_{key}"] = None
                continue
            mean = sum(vals) / len(vals)
            agg[f"mean_{key}"] = mean
            if "false" in key or "pfp" in key.lower():
                agg[f"worst_{key}"] = max(vals)
            else:
                agg[f"worst_{key}"] = min(vals)
        # Integer sums for count-valued fields (more useful than means).
        for key in ("added_gold_span", "added_false_span", "net_span_value_2x", "effective_llm_action_count"):
            vals = values.get(key, [])
            if vals:
                agg[f"total_{key}"] = int(sum(vals))
        families[name] = agg
    return families


# ---------------------------------------------------------------------------
# Report assembly and safety
# ---------------------------------------------------------------------------


def _base_report(status: str, self_test: bool) -> dict[str, Any]:
    report = b6lite._base_report(status, self_test)
    report["schema_version"] = SCHEMA_VERSION
    report["generated_by"] = GENERATED_BY
    report["claim_level"] = "leave_one_repo_diagnostic_only"
    report["public_per_repo_rows"] = False
    report["evidencecore_semantics_changed"] = False
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
    }:
        raise ValueError("bad status")

    must_be_true = [
        "not_evidence",
        "llm_output_not_evidence",
        "aggregate_only_public_artifact",
        "candidate_not_fact",
        "policy_search_not_admission",
        "diagnostic_policy_search",
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
    ]
    for key in must_be_false:
        if report.get(key) is not False:
            raise ValueError(f"{key} must be false")

    if report.get("remote_calls_by_policy_search") != 0:
        raise ValueError("remote_calls_by_policy_search must be 0")
    if report.get("claim_level") != "leave_one_repo_diagnostic_only":
        raise ValueError("claim_level must be leave_one_repo_diagnostic_only")

    violations = b6lite._walk_forbidden(report)
    if violations:
        raise ValueError(
            "public report contains forbidden fields: " + ", ".join(violations[:5])
        )

    if report.get("status") == "ok":
        families = report.get("policy_families") or {}
        if "p25_bucket_routed_v0_plain" not in families:
            raise ValueError("P25 baseline missing from policy_families")
        search = report.get("search_accounting") or {}
        for key in (
            "mean_candidate_policy_count",
            "rules_considered_per_fold",
            "total_rules_considered_across_folds",
            "mean_rules_pruned_by_min_support",
            "frontier_appearances_total",
        ):
            if key not in search:
                raise ValueError(f"missing search_accounting.{key}")
        if report.get("fold_count", 0) < 1:
            raise ValueError("fold_count must be positive")
        if report.get("included_repo_count", 0) < 1:
            raise ValueError("included_repo_count must be positive")
        inv = report.get("routing_invariance") or {}
        if inv.get("selected_actions_invariant") is not True:
            raise ValueError("routing changed when SCORE/gold fields were mutated")
        if "winner" in report or "default_recommendation" in report:
            raise ValueError("report must not declare a winner or default recommendation")


def _routing_invariance_all_tasks(
    repo_pairs: list[tuple[str, list[dict[str, Any]], list[dict[str, Any]]]],
    selected_by_fold: list[list[b6lite.Policy]],
) -> dict[str, Any]:
    all_plain = [t for _rid, plain, _hard in repo_pairs for t in plain]
    all_selected: list[b6lite.Policy] = []
    seen: set[str] = set()
    for fold_policies in selected_by_fold:
        for policy in fold_policies:
            if policy.name not in seen:
                seen.add(policy.name)
                all_selected.append(policy)
    return b6lite._routing_invariance_check(all_selected, all_plain)


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    if args.self_test:
        manifest_path, repo_pairs = _write_self_test_manifest()
        self_test = True
    else:
        manifest = _load_manifest(args.paired_records_manifest)
        self_test = bool(getattr(args, "mark_self_test", False))
        records = manifest["records"]
        block_status, repo_pairs = _validate_manifest_records(records)
        if block_status:
            report = _base_report(block_status, self_test)
            report.update(
                {
                    "included_repo_count": len(records),
                    "fold_count": 0,
                    "comparable_task_count": 0,
                    "manifest_record_count": len(records),
                }
            )
            if block_status == "blocked_insufficient_repos":
                report["required_repo_count"] = REQUIRED_REPO_COUNT
            validate_report(report)
            return report

    # At this point we have >= 4 repos with matched records.
    fold_accounting, families = _leave_one_repo_out_evaluation(repo_pairs)

    # Re-derive selected policies list per fold for routing invariance check.
    selected_by_fold: list[list[b6lite.Policy]] = []
    for rid, plain, hard in repo_pairs:
        hard_by_task = {str(t["task_id"]): t for t in hard}
        train_plain = [
            t
            for orid, op, _oh in repo_pairs
            if orid != rid
            for t in op
        ]
        train_hard_by_task = {
            str(t["task_id"]): t
            for orid, _op, oh in repo_pairs
            if orid != rid
            for t in oh
        }
        selected, _ = _select_train_policies(train_plain, train_hard_by_task)
        selected_by_fold.append(selected)

    routing_invariance = _routing_invariance_all_tasks(repo_pairs, selected_by_fold)

    comparable_task_count = sum(
        len(plain) for _rid, plain, _hard in repo_pairs
    )

    # Aggregate search accounting across folds.
    candidate_counts = [fa["candidate_policy_count"] for fa in fold_accounting]
    rules_pruned = [fa["rules_pruned_by_min_support"] for fa in fold_accounting]
    frontier_sizes = [fa["frontier_size"] for fa in fold_accounting]
    dominated_by_p25 = [fa["policies_dominated_by_p25"] for fa in fold_accounting]
    selected_counts = [fa["selected_policy_count"] for fa in fold_accounting]

    search_accounting = {
        "rules_considered_per_fold": fold_accounting[0]["rules_considered"],
        "total_rules_considered_across_folds": sum(
            fa["rules_considered"] for fa in fold_accounting
        ),
        "mean_rules_pruned_by_min_support": (
            sum(rules_pruned) / len(rules_pruned) if rules_pruned else None
        ),
        "mean_candidate_policy_count": (
            sum(candidate_counts) / len(candidate_counts) if candidate_counts else None
        ),
        "min_candidate_policy_count": min(candidate_counts) if candidate_counts else None,
        "max_candidate_policy_count": max(candidate_counts) if candidate_counts else None,
        "mean_selected_policy_count": (
            sum(selected_counts) / len(selected_counts) if selected_counts else None
        ),
        "frontier_size_min": min(frontier_sizes) if frontier_sizes else None,
        "frontier_size_max": max(frontier_sizes) if frontier_sizes else None,
        "frontier_appearances_total": sum(frontier_sizes) if frontier_sizes else None,
        "policies_dominated_by_p25_total": sum(dominated_by_p25) if dominated_by_p25 else None,
    }

    # Build a heldout Pareto frontier across family aggregates.
    heldout_values = {name: fam for name, fam in families.items()}
    frontier_info = b6lite._compute_frontier(
        heldout_values, p25_name="p25_bucket_routed_v0_plain"
    )

    # Count how many families come from searched policies.
    searched_family_count = sum(
        1 for fam in families.values() if fam.get("source") == "searched"
    )

    report = _base_report("self_test_only" if self_test else "ok", self_test)
    report.update(
        {
            "fold_count": len(repo_pairs),
            "included_repo_count": len(repo_pairs),
            "comparable_task_count": comparable_task_count,
            "manifest_record_count": len(repo_pairs),
            "search_accounting": search_accounting,
            "policy_families": families,
            "searched_family_count": searched_family_count,
            "pareto_frontier": {
                "frontier": sorted(frontier_info["frontier"]),
                "frontier_size": frontier_info["frontier_size"],
                "policies_dominated_by_p25": frontier_info["policies_dominated_by_p25"],
                "non_dominated_observed": sorted(frontier_info["non_dominated_observed"]),
            },
            "routing_invariance": routing_invariance,
            "comparability": {
                "model": ALLOWED_MODEL,
                "output_mode": ALLOWED_OUTPUT_MODE,
                "plain_pack_layout": ALLOWED_PLAIN_PACK_LAYOUT,
                "hard_pack_layout": ALLOWED_HARD_PACK_LAYOUT,
                "same_model_required": True,
                "same_output_mode_required": True,
                "same_pack_layout_required": True,
                "same_model_observed": True,
                "same_task_set_within_repo_required": True,
                "same_task_set_within_repo_observed": True,
                "leave_one_repo_out": True,
            },
        }
    )
    # Add convenience fields for downstream validation.
    for fam in families.values():
        fam["task_count"] = comparable_task_count
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
    lines.append("# B6B Combined-Matrix Interpretable Policy Search")
    lines.append("")
    lines.append(f"Status: `{report['status']}`")
    lines.append("")
    lines.append(
        "B6B searches a pre-registered grammar of interpretable routing rules over "
        "paired P21 ephemeral records from multiple repos using a true "
        "leave-one-repo-out protocol.  Policies are selected on a training set of "
        "repos and then evaluated on the held-out repo.  The public artifact is "
        "aggregate-only; per-task / per-repo / per-candidate details stay in "
        "`$RUNNER_TEMP`."
    )
    lines.append("")
    if report.get("status") != "ok" and report.get("status") != "self_test_only":
        lines.append("Evaluation was blocked; no policies were scored.")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    lines.append("## Search accounting")
    search = report.get("search_accounting", {})
    for k, v in sorted(search.items()):
        lines.append(f"- `{k}`: {_fmt(v)}")
    lines.append("")

    lines.append("## Aggregate held-out policy families")
    header = (
        "| Policy family | source | folds | +gold | +false | F/G | SpanF0.5 | PFP | "
        "LLM calls | net 2x | Δ+gold vs P25 | Δ+false vs P25 | Δ net 2x vs P25 |"
    )
    lines.append(header)
    lines.append(
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    )
    for name in sorted(report.get("policy_families", {})):
        m = report["policy_families"][name]
        source = m.get("source", "unknown")
        folds = m.get("fold_appearances", 0)
        lines.append(
            f"| `{name}` | {source} | {folds} | "
            f"{m.get('total_added_gold_span', '')} | "
            f"{m.get('total_added_false_span', '')} | "
            f"{_fmt(m.get('mean_false_per_gold'))} | "
            f"{_fmt(m.get('mean_mean_span_f05'))} | "
            f"{_fmt(m.get('mean_mean_primary_false_positive_rate'))} | "
            f"{m.get('total_effective_llm_action_count', '')} | "
            f"{m.get('total_net_span_value_2x', '')} | "
            f"{_fmt(m.get('mean_delta_added_gold_span_vs_p25'))} | "
            f"{_fmt(m.get('mean_delta_added_false_span_vs_p25'))} | "
            f"{_fmt(m.get('mean_delta_net_span_value_2x_vs_p25'))} |"
        )
    lines.append("")

    lines.append("## Heldout Pareto frontier (aggregated)")
    frontier = report.get("pareto_frontier", {})
    lines.append(f"Frontier size: {frontier.get('frontier_size')}")
    lines.append(f"Families dominated by P25: {frontier.get('policies_dominated_by_p25')}")
    lines.append(
        f"Non-dominated families: {', '.join(frontier.get('non_dominated_observed', []))}"
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
        "`evidencecore_semantics_changed=false`."
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
    lines.append(
        "- Leave-one-repo-out split happens before policy search and selection."
    )
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Self-test inputs
# ---------------------------------------------------------------------------


def _make_hard_variant(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hard_rows = json.loads(json.dumps(rows))
    for row in hard_rows:
        labels = set(row.get("task_risk_tags") or []) | {row.get("task_bucket")}
        if labels & {"negative", "hard_distractor", "ambiguous", "dense_false_positive"}:
            row["llm_filter"] = {
                "file_recall_at_5": 0.0,
                "span_f0_5": 0.0,
                "primary_false_positive_rate": 0.0,
                "no_gold_false_primary_rate": 0.0,
                "added_gold_span": 0,
                "added_false_span": 0,
            }
    return hard_rows


def _build_repo_pair(
    tmp: Path,
    repo_id: str,
    base_tasks: list[dict[str, Any]],
    offset: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Path, Path]:
    repo_dir = tmp / repo_id
    repo_dir.mkdir(parents=True, exist_ok=True)
    plain_path = repo_dir / "plain.private.json"
    hard_path = repo_dir / "hard.private.json"

    plain_rows: list[dict[str, Any]] = []
    hard_rows_base: list[dict[str, Any]] = []
    for i, task in enumerate(base_tasks):
        row = dict(task)
        row["repo_id"] = repo_id
        row["task_id"] = f"{repo_id}-p25-{i + 1 + offset:03d}"
        # Vary outcomes slightly per repo for meaningful aggregation.
        for key in ("candidate_baseline", "llm_span_narrow", "llm_filter", "llm_abstain_filter"):
            outcome = row.get(key)
            if isinstance(outcome, dict):
                for ok in ("added_gold_span", "added_false_span"):
                    if ok in outcome:
                        outcome[ok] = max(0, int(outcome[ok]) + (offset % 2))
        plain_rows.append(row)
        hard_rows_base.append(dict(row))

    hard_rows = _make_hard_variant(hard_rows_base)

    payload = {
        "schema_version": "p25-policy-records-ephemeral-v1",
        "not_artifact_for_commit": True,
    }
    plain_path.write_text(
        json.dumps({**payload, "records": plain_rows}), encoding="utf-8"
    )
    hard_path.write_text(
        json.dumps({**payload, "records": hard_rows}), encoding="utf-8"
    )
    return plain_rows, hard_rows, plain_path, hard_path


def _write_self_test_manifest(
    tmp: Path | None = None,
) -> tuple[Path, list[tuple[str, list[dict[str, Any]], list[dict[str, Any]]]]]:
    if tmp is None:
        tmp = Path("/tmp/opencode/b6b-combined-self-test")
    tmp.mkdir(parents=True, exist_ok=True)
    base_tasks = p25.make_self_test_tasks()
    repos = ["py_flask", "js_express", "go_gin", "rust_ripgrep"]
    repo_pairs: list[tuple[str, list[dict[str, Any]], list[dict[str, Any]]]] = []
    manifest_records: list[dict[str, Any]] = []

    for offset, repo_id in enumerate(repos):
        plain_rows, hard_rows, plain_path, hard_path = _build_repo_pair(
            tmp, repo_id, base_tasks, offset
        )
        plain_norm = b6lite._load_records(plain_path)
        hard_norm = b6lite._load_records(hard_path)
        repo_pairs.append((repo_id, plain_norm, hard_norm))
        manifest_records.append(
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

    manifest = {
        "schema_version": "b6b-paired-records-manifest-v0",
        "not_artifact_for_commit": True,
        "records": manifest_records,
    }
    manifest_path = tmp / "b6b_paired_records_manifest.private.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path, repo_pairs


# ---------------------------------------------------------------------------
# Self-test assertions
# ---------------------------------------------------------------------------


def _self_test_insufficient_repos() -> None:
    tmp = Path("/tmp/opencode/b6b-test-insufficient")
    tmp.mkdir(parents=True, exist_ok=True)
    base_tasks = p25.make_self_test_tasks()
    records: list[dict[str, Any]] = []
    for offset, repo_id in enumerate(["py_flask", "js_express"]):
        _, _, plain_path, hard_path = _build_repo_pair(tmp, repo_id, base_tasks, offset)
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
            {"schema_version": "b6b-paired-records-manifest-v0", "records": records}
        ),
        encoding="utf-8",
    )
    args = argparse.Namespace(
        paired_records_manifest=manifest_path, out=tmp / "out.json", doc=tmp / "out.md", self_test=False
    )
    report = build_report(args)
    assert report["status"] == "blocked_insufficient_repos", report["status"]
    print("self-test insufficient repos: ok")


def _self_test_task_mismatch() -> None:
    tmp = Path("/tmp/opencode/b6b-test-mismatch")
    tmp.mkdir(parents=True, exist_ok=True)
    base_tasks = p25.make_self_test_tasks()
    records: list[dict[str, Any]] = []
    for offset, repo_id in enumerate(["py_flask", "js_express", "go_gin", "rust_ripgrep"]):
        plain_rows, hard_rows, plain_path, hard_path = _build_repo_pair(
            tmp, repo_id, base_tasks, offset
        )
        if offset == 1:
            # Corrupt hard task ids for js_express.
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
            {"schema_version": "b6b-paired-records-manifest-v0", "records": records}
        ),
        encoding="utf-8",
    )
    args = argparse.Namespace(
        paired_records_manifest=manifest_path, out=tmp / "out.json", doc=tmp / "out.md", self_test=False
    )
    report = build_report(args)
    assert report["status"] == "blocked_task_set_mismatch", report["status"]
    print("self-test task mismatch: ok")


def _self_test_mixed_model() -> None:
    tmp = Path("/tmp/opencode/b6b-test-mixed")
    tmp.mkdir(parents=True, exist_ok=True)
    base_tasks = p25.make_self_test_tasks()
    records: list[dict[str, Any]] = []
    models = [
        "[mk]Kimi-K2.7-Code",
        "[mk]Kimi-K2.7-Code",
        "[mk]Qwen3.6-27B",
        "[mk]Kimi-K2.7-Code",
    ]
    for offset, repo_id in enumerate(["py_flask", "js_express", "go_gin", "rust_ripgrep"]):
        _, _, plain_path, hard_path = _build_repo_pair(tmp, repo_id, base_tasks, offset)
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
            {"schema_version": "b6b-paired-records-manifest-v0", "records": records}
        ),
        encoding="utf-8",
    )
    args = argparse.Namespace(
        paired_records_manifest=manifest_path, out=tmp / "out.json", doc=tmp / "out.md", self_test=False
    )
    report = build_report(args)
    assert report["status"] == "blocked_mixed_model_mode_pack", report["status"]
    print("self-test mixed model: ok")


def _self_test_bad_output_mode() -> None:
    tmp = Path("/tmp/opencode/b6b-test-bad-mode")
    tmp.mkdir(parents=True, exist_ok=True)
    base_tasks = p25.make_self_test_tasks()
    records: list[dict[str, Any]] = []
    for offset, repo_id in enumerate(["py_flask", "js_express", "go_gin", "rust_ripgrep"]):
        _, _, plain_path, hard_path = _build_repo_pair(tmp, repo_id, base_tasks, offset)
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
            {"schema_version": "b6b-paired-records-manifest-v0", "records": records}
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


def _self_test_routing_invariance() -> None:
    tmp = Path("/tmp/opencode/b6b-test-invariance")
    tmp.mkdir(parents=True, exist_ok=True)
    manifest_path, repo_pairs = _write_self_test_manifest(tmp)
    args = argparse.Namespace(
        paired_records_manifest=manifest_path, out=tmp / "out.json", doc=tmp / "out.md", self_test=False
    )
    report = build_report(args)
    assert report["status"] == "ok", report["status"]
    inv = report.get("routing_invariance", {})
    assert inv.get("selected_actions_invariant") is True, inv
    print("self-test routing invariance: ok")


def _self_test_happy_path() -> None:
    tmp = Path("/tmp/opencode/b6b-test-happy")
    tmp.mkdir(parents=True, exist_ok=True)
    manifest_path, repo_pairs = _write_self_test_manifest(tmp)
    args = argparse.Namespace(
        paired_records_manifest=manifest_path, out=tmp / "out.json", doc=tmp / "out.md", self_test=False
    )
    report = build_report(args)
    assert report["status"] == "ok", report["status"]
    assert report["fold_count"] == REQUIRED_REPO_COUNT, report["fold_count"]
    assert report["included_repo_count"] == REQUIRED_REPO_COUNT
    assert "p25_bucket_routed_v0_plain" in report["policy_families"]
    for required in (
        "rmc_local_conservative_v0",
        "rmc_llm_pack_routed_v0",
        "rmc_hybrid_v0",
    ):
        assert required in report["policy_families"], required
    assert report.get("searched_family_count", 0) > 0, report.get("searched_family_count")
    families = report["policy_families"]
    for name, fam in families.items():
        assert "fold_appearances" in fam, name
        assert fam["fold_appearances"] > 0, name
    print("self-test happy path: ok")


def run_self_tests() -> None:
    _self_test_insufficient_repos()
    _self_test_task_mismatch()
    _self_test_mixed_model()
    _self_test_bad_output_mode()
    _self_test_routing_invariance()
    _self_test_happy_path()
    print("all b6b self-tests passed")


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
                "fold_count": report.get("fold_count"),
                "included_repo_count": report.get("included_repo_count"),
                "searched_family_count": report.get("searched_family_count"),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
