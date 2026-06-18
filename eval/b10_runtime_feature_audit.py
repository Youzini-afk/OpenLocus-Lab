#!/usr/bin/env python3
"""B10 Runtime Feature Audit + Balanced Policy v1 Freeze.

B10 does NOT run any model, does NOT search, and does NOT change the frozen
policy. It freezes the B6C main balanced candidate
``ambiguous_query_weak_only_default_use_p25_action`` as the algorithm spec
``balanced_policy_v1_benchmark_routed`` and audits the provenance of every
routing feature that the spec actually reads.

This is a **benchmark-routed research algorithm spec only**. It is NOT a
runtime-feature-only policy, NOT a default change, NOT a promotion candidate,
and does NOT change ``EvidenceCore``.

The public artifacts are aggregate-only and never emit task IDs, repo IDs,
candidate IDs, paths, spans, digests, snippets, prompts, responses, gold spans,
provider keys, base URLs, or API keys.

Run::

    python3 eval/b10_runtime_feature_audit.py --self-test
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

_FILE_DIR = Path(__file__).resolve().parent
if str(_FILE_DIR) not in sys.path:
    sys.path.insert(0, str(_FILE_DIR))

import b6_lite_interpretable_policy_search as b6lite  # noqa: E402
import p25_bucket_policy as p25  # noqa: E402

SCHEMA_VERSION = "b10-runtime-feature-audit-report-v0"
GENERATED_BY = "b10_runtime_feature_audit"

REPO_ROOT = _FILE_DIR.parent
ALGORITHM_SPEC_PATH = REPO_ROOT / "artifacts" / "b10_runtime_feature_audit" / "balanced_policy_v1_benchmark_routed.algorithm.json"
AUDIT_REPORT_PATH = REPO_ROOT / "artifacts" / "b10_runtime_feature_audit" / "b10_runtime_feature_audit_report.json"
FROZEN_CANDIDATES_PATH = _FILE_DIR / "b6c_frozen_candidates.json"

EXPECTED_FROZEN_SPEC_SHA256 = "51f0efd837759c96d4849c8e6023633a2595c4ba376231ea6edb08dc2cb8176e"
EXPECTED_ALGORITHM_SPEC_ID = "balanced_policy_v1_benchmark_routed"
EXPECTED_FROZEN_CANDIDATE = "ambiguous_query_weak_only_default_use_p25_action"

EXPECTED_RULES = [
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
]

ALLOWED_PREDICATES = {"ambiguous_or_query_noise", "always_true"}
ALLOWED_ACTIONS = {
    "use_p25_action",
    "candidate_baseline",
    "plain_span_narrow",
    "hard_distractor_filter",
    "abstain_filter",
    "weak_only",
}

FORBIDDEN_PUBLIC_KEYS = (
    "task_id",
    "repo_id",
    "candidate_id",
    "path",
    "span",
    "snippet",
    "prompt",
    "response",
    "gold_spans",
    "provider_key",
    "base_url",
    "api_key",
    "content_sha",
)

# Deterministic runtime route_features that the P25 ``use_p25_action`` default
# reads via ``p25.route_bucket_routed_v0``. These are inherited by the frozen
# spec because the default action delegates to P25.
P25_INHERITED_ROUTE_FEATURES = (
    "candidate_count",
    "candidate_support_exists",
)

BENCHMARK_PUBLIC_LABELS = ("task_bucket", "task_risk_tags")


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _sha256_json(obj: Any) -> str:
    return hashlib.sha256(_canonical_json(obj).encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"required artifact not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


import re

# Forbidden KEY names (exact match) per the B10 task spec. These must never
# appear as object keys in the public artifact because they would carry
# per-task / per-repo / per-candidate / per-path / per-span identity or secrets.
FORBIDDEN_KEY_NAMES = frozenset(FORBIDDEN_PUBLIC_KEYS)

# Conservative value patterns that flag genuine leaked values, NOT provenance
# source-file references (``eval/b6_lite_interpretable_policy_search.py`` is
# provenance, not a leaked repo content path). We flag: SHA-1/SHA-256 content
# hashes, http(s) URLs, and literal ``api_key=...`` / ``base_url=...`` style
# credential assignments.
_FORBIDDEN_VALUE_RES = (
    re.compile(r"\b(?:sha_?(?:1|256)?|content_?sha)\b[\s:=]+[A-Fa-f0-9]{40,}", re.I),
    re.compile(r"https?://", re.I),
    re.compile(r"\b(?:api[_-]?key|base[_-]?url|api[_-]?secret|api[_-]?token)\b\s*[:=]\s*\S", re.I),
    re.compile(r"\b[A-Fa-f0-9]{64}\b"),
)


def _recursive_key_scan(obj: Any) -> list[str]:
    """B10 forbidden-key scan.

    Flags exact forbidden KEY names from the B10 task spec and conservative
    value patterns for genuine leaked content hashes, URLs, and credential
    assignments. Provenance source-file references (e.g.
    ``eval/b6_lite_interpretable_policy_search.py``) are intentionally allowed
    because they document where a predicate/action is implemented, not leaked
    repo content.
    """
    hits: list[str] = []

    def _walk(o: Any, path: str) -> None:
        if isinstance(o, dict):
            for key, value in o.items():
                key_str = str(key)
                if key_str in FORBIDDEN_KEY_NAMES:
                    hits.append(f"{path}.{key_str}")
                _walk(value, f"{path}.{key_str}")
        elif isinstance(o, list):
            for idx, value in enumerate(o):
                _walk(value, f"{path}[{idx}]")
        elif isinstance(o, str):
            if len(o) > 512:
                hits.append(f"{path}:long_string")
            for p in _FORBIDDEN_VALUE_RES:
                if p.search(o):
                    hits.append(f"{path}:forbidden_value")

    _walk(obj, "$")
    return hits


def verify_frozen_spec_hash(frozen_candidates: dict[str, Any]) -> str:
    """Reconstruct the canonical spec dict from the frozen candidates file and
    recompute its SHA-256, exactly mirroring ``b6c_frozen_policy_validation``.
    """
    candidates = frozen_candidates.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("frozen candidates file has no candidates list")
    spec: dict[str, list[dict[str, Any]]] = {}
    for cand in candidates:
        name = cand.get("name")
        rules = cand.get("rules")
        if not isinstance(name, str) or not isinstance(rules, list):
            raise ValueError(f"malformed frozen candidate: {cand!r}")
        spec[name] = rules
    recomputed = _sha256_json(spec)
    declared = frozen_candidates.get("frozen_spec_sha256")
    if declared != recomputed:
        raise ValueError(
            f"frozen_spec_sha256 mismatch: declared={declared!r} recomputed={recomputed!r}"
        )
    if recomputed != EXPECTED_FROZEN_SPEC_SHA256:
        raise ValueError(
            f"frozen_spec_sha256 changed from expected: expected={EXPECTED_FROZEN_SPEC_SHA256!r} got={recomputed!r}"
        )
    return recomputed


def verify_candidate_rules(frozen_candidates: dict[str, Any]) -> dict[str, Any]:
    """Verify the chosen candidate has the exact rule order/predicates/actions."""
    candidates = frozen_candidates["candidates"]
    by_name = {c["name"]: c for c in candidates}
    if EXPECTED_FROZEN_CANDIDATE not in by_name:
        raise ValueError(
            f"expected frozen candidate {EXPECTED_FROZEN_CANDIDATE!r} not found"
        )
    cand = by_name[EXPECTED_FROZEN_CANDIDATE]
    rules = cand.get("rules")
    if rules != EXPECTED_RULES:
        raise ValueError(
            f"rule order/predicates/actions mismatch for {EXPECTED_FROZEN_CANDIDATE!r}:\n"
            f"  expected={EXPECTED_RULES!r}\n  got={rules!r}"
        )
    for rule in rules:
        for pred in rule.get("predicates", []):
            if pred not in ALLOWED_PREDICATES:
                raise ValueError(f"unexpected predicate {pred!r}")
        if rule.get("action") not in ALLOWED_ACTIONS:
            raise ValueError(f"unexpected action {rule.get('action')!r}")
    return cand


def verify_predicate_provenance() -> dict[str, Any]:
    """Reuse the b6_lite predicate implementations to assert the exact
    dependency class (benchmark public label vs deterministic runtime feature)
    of every predicate in the frozen spec."""
    # Sanity-check that the b6_lite predicate symbols still exist and are
    # callable, so we are auditing the real implementation rather than a copy.
    if not callable(b6lite._noisy_or_ambiguous):
        raise ValueError("b6lite._noisy_or_ambiguous is not callable")
    if not callable(b6lite._ambiguous_like):
        raise ValueError("b6lite._ambiguous_like is not callable")
    if not callable(b6lite._query_noise):
        raise ValueError("b6lite._query_noise is not callable")

    # ``_ambiguous_like`` reads bucket labels (task_bucket / task_risk_tags).
    ambiguous_like_probe = {
        "task_bucket": "ambiguous",
        "task_risk_tags": [],
        "route_features": {"query_noise": 0},
    }
    if not b6lite._ambiguous_like(ambiguous_like_probe):
        raise ValueError("_ambiguous_like did not fire on task_bucket=ambiguous")
    # ``_query_noise`` reads route_features.query_noise and ignores buckets.
    query_noise_probe = {
        "task_bucket": "",
        "task_risk_tags": [],
        "route_features": {"query_noise": 1.0},
    }
    if not b6lite._query_noise(query_noise_probe):
        raise ValueError("_query_noise did not fire on route_features.query_noise=1.0")
    # ``_noisy_or_ambiguous`` is the OR of the two components.
    if not b6lite._noisy_or_ambiguous(query_noise_probe):
        raise ValueError("_noisy_or_ambiguous did not fire on query_noise-only probe")

    return {
        "ambiguous_or_query_noise": {
            "resolved_to": "_noisy_or_ambiguous = _ambiguous_like or _query_noise",
            "ambiguous_like_depends_on": list(BENCHMARK_PUBLIC_LABELS),
            "query_noise_depends_on": ["route_features.query_noise"],
            "uses_score_private_fields": False,
            "uses_benchmark_public_labels": True,
            "uses_runtime_features_only": False,
        },
        "always_true": {
            "resolved_to": "lambda _t: True",
            "depends_on": [],
            "uses_score_private_fields": False,
            "uses_benchmark_public_labels": False,
            "uses_runtime_features_only": True,
        },
    }


def verify_action_provenance() -> dict[str, Any]:
    """Verify ``use_p25_action`` delegates to P25 and that P25 route_features
    are inherited as deterministic runtime dependencies."""
    if not callable(p25.route_bucket_routed_v0):
        raise ValueError("p25.route_bucket_routed_v0 is not callable")
    if not callable(p25.bucket_labels):
        raise ValueError("p25.bucket_labels is not callable")
    # P25 reads bucket labels and route_features only.
    exact_unique_probe = {
        "task_bucket": "exact_symbol_unique",
        "task_risk_tags": ["unique_symbol"],
        "route_features": {
            "candidate_count": 1,
            "candidate_support_exists": True,
        },
    }
    # This should short-circuit to candidate_baseline (skip LLM). P25 obtains
    # the exact/unique anchor signal from bucket labels, not from a
    # ``route_features.unique_symbol_anchor`` key.
    action = p25.route_bucket_routed_v0(exact_unique_probe, "llm_abstain_filter")
    if action != "candidate_baseline":
        raise ValueError(
            f"P25 exact-symbol+unique-anchor probe did not short-circuit: got {action!r}"
        )
    # Probe that bucket_labels reads task_bucket and task_risk_tags.
    labels = p25.bucket_labels(
        {"task_bucket": "ambiguous", "task_risk_tags": ["hallucination_risk"]}
    )
    if "ambiguous" not in labels or "hallucination_risk" not in labels:
        raise ValueError(f"p25.bucket_labels did not read bucket/tags: {labels!r}")
    return {
        "use_p25_action": {
            "delegates_to": "eval/p25_bucket_policy.py::route_bucket_routed_v0",
            "provider_call_required": "conditional",
            "inherited_route_features": [f"route_features.{f}" for f in P25_INHERITED_ROUTE_FEATURES],
            "inherited_benchmark_labels": list(BENCHMARK_PUBLIC_LABELS),
            "uses_score_private_fields_for_routing": False,
        },
        "weak_only": {
            "provider_call_required": False,
            "uses_score_private_fields_for_routing": False,
        },
    }


def verify_runtime_feature_only_mode_would_fail(
    predicate_provenance: dict[str, Any]
) -> dict[str, Any]:
    """A runtime-feature-only policy would have no task_bucket / task_risk_tags
    labels. The ``ambiguous_or_query_noise`` predicate cannot be evaluated
    without those labels because its ``_ambiguous_like`` branch reads them.
    Therefore runtime_clean MUST be false and runtime_feature_only_mode MUST
    fail. This is asserted, not assumed.
    """
    ambiguous_branch = predicate_provenance["ambiguous_or_query_noise"]
    uses_labels = ambiguous_branch["uses_benchmark_public_labels"]
    if not uses_labels:
        raise ValueError(
            "ambiguous_or_query_noise must use benchmark public labels; "
            "if it does not, runtime_feature_only_mode_would_fail cannot hold"
        )
    label_deps = set(ambiguous_branch["ambiguous_like_depends_on"])
    if label_deps != set(BENCHMARK_PUBLIC_LABELS):
        raise ValueError(
            f"_ambiguous_like dependency set changed: {label_deps!r}"
        )
    # Build a runtime-feature-only task (no task_bucket / task_risk_tags) and
    # show the predicate cannot be evaluated to True purely from route_features
    # when the query_noise feature is zero. This is the failure mode.
    runtime_only_probe = {
        "task_bucket": None,
        "task_risk_tags": [],
        "route_features": {"query_noise": 0},
    }
    # With labels missing AND query_noise=0, the predicate must be False. That
    # is exactly why a runtime-feature-only policy would route every task to
    # the default action and never match the ambiguous_query_weak_only rule.
    if b6lite._noisy_or_ambiguous(runtime_only_probe):
        raise ValueError(
            "runtime-only probe (no labels, query_noise=0) fired the predicate; "
            "runtime_feature_only_mode_would_fail assertion is invalid"
        )
    return {
        "runtime_feature_only_mode_would_fail": True,
        "runtime_clean": False,
        "reason": "ambiguous_or_query_noise depends on task_bucket/task_risk_tags via _ambiguous_like; runtime-feature-only mode cannot evaluate the predicate",
    }


def _verify_spec_semantics(spec: dict[str, Any]) -> None:
    computed_predicates = verify_predicate_provenance()
    computed_actions = verify_action_provenance()

    semantics = spec.get("predicate_semantics") or {}
    ambiguous = semantics.get("ambiguous_or_query_noise") or {}
    components = ambiguous.get("components") or {}
    ambiguous_like = components.get("_ambiguous_like") or {}
    query_noise = components.get("_query_noise") or {}
    always_true = semantics.get("always_true") or {}

    computed_ambiguous = computed_predicates["ambiguous_or_query_noise"]
    if set(ambiguous_like.get("depends_on") or []) != set(computed_ambiguous["ambiguous_like_depends_on"]):
        raise ValueError("algorithm spec _ambiguous_like dependencies do not match computed provenance")
    if set(query_noise.get("depends_on") or []) != set(computed_ambiguous["query_noise_depends_on"]):
        raise ValueError("algorithm spec _query_noise dependencies do not match computed provenance")
    if ambiguous_like.get("dependency_class") != "benchmark_public":
        raise ValueError("algorithm spec _ambiguous_like must be benchmark_public")
    if query_noise.get("dependency_class") != "deterministic_runtime":
        raise ValueError("algorithm spec _query_noise must be deterministic_runtime")
    if always_true.get("depends_on") != computed_predicates["always_true"]["depends_on"]:
        raise ValueError("algorithm spec always_true dependencies do not match computed provenance")

    action_semantics = spec.get("action_semantics") or {}
    p25_action = action_semantics.get("use_p25_action") or {}
    computed_p25 = computed_actions["use_p25_action"]
    if p25_action.get("source") != computed_p25["delegates_to"]:
        raise ValueError("algorithm spec use_p25_action source does not match computed provenance")
    if set(p25_action.get("inherited_runtime_dependencies") or []) != set(computed_p25["inherited_route_features"]):
        raise ValueError("algorithm spec inherited runtime dependencies do not match computed provenance")
    if set(p25_action.get("inherited_benchmark_dependencies") or []) != set(computed_p25["inherited_benchmark_labels"]):
        raise ValueError("algorithm spec inherited benchmark dependencies do not match computed provenance")
    weak_action = action_semantics.get("weak_only") or {}
    if weak_action.get("provider_call_required") != computed_actions["weak_only"]["provider_call_required"]:
        raise ValueError("algorithm spec weak_only provider_call_required mismatch")


def _verify_report_provenance(report: dict[str, Any]) -> None:
    computed_predicates = verify_predicate_provenance()
    computed_actions = verify_action_provenance()
    if report.get("predicate_verification") != computed_predicates:
        raise ValueError("audit report predicate_verification does not match computed provenance")
    if report.get("action_verification") != computed_actions:
        raise ValueError("audit report action_verification does not match computed provenance")


def verify_algorithm_spec(spec: dict[str, Any], frozen_hash: str) -> None:
    if spec.get("algorithm_spec_id") != EXPECTED_ALGORITHM_SPEC_ID:
        raise ValueError(
            f"algorithm_spec_id mismatch: expected={EXPECTED_ALGORITHM_SPEC_ID!r} "
            f"got={spec.get('algorithm_spec_id')!r}"
        )
    # Public artifact must NOT carry the literal SHA-256 hex string (it would
    # trip the forbidden-value hex32+ pattern in ``b6lite._walk_forbidden``).
    # It only carries the boolean matched flag.
    if spec.get("frozen_spec_hash_matched") is not True:
        raise ValueError("algorithm spec frozen_spec_hash_matched must be true")
    if spec.get("rules") != EXPECTED_RULES:
        raise ValueError("algorithm spec rules do not match the frozen candidate rules")
    if spec.get("runtime_clean") is not False:
        raise ValueError("algorithm spec runtime_clean must be false")
    if spec.get("runtime_feature_only_mode_supported") is not False:
        raise ValueError("algorithm spec runtime_feature_only_mode_supported must be false")
    if spec.get("promotion_ready") is not False:
        raise ValueError("algorithm spec promotion_ready must be false")
    if spec.get("default_should_change") is not False:
        raise ValueError("algorithm spec default_should_change must be false")
    if spec.get("evidencecore_semantics_changed") is not False:
        raise ValueError("algorithm spec evidencecore_semantics_changed must be false")
    if spec.get("claim_level") != "benchmark_routed_algorithm_spec_only":
        raise ValueError("algorithm spec claim_level must be benchmark_routed_algorithm_spec_only")
    if spec.get("score_private_dependencies_for_routing") != []:
        raise ValueError("score_private_dependencies_for_routing must be empty")
    if set(spec.get("benchmark_public_dependencies", [])) != set(BENCHMARK_PUBLIC_LABELS):
        raise ValueError("benchmark_public_dependencies must be task_bucket and task_risk_tags")
    expected_runtime = {
        "route_features.query_noise",
        "always_true",
        "route_features.candidate_count",
        "route_features.candidate_support_exists",
    }
    if set(spec.get("deterministic_runtime_dependencies", [])) != expected_runtime:
        raise ValueError("deterministic_runtime_dependencies do not match the audit")
    _verify_spec_semantics(spec)
    score_private_scoring = set(spec.get("score_private_used_for_aggregate_scoring", []))
    if not score_private_scoring.issuperset({"has_gold", "score_group", "outcome_metrics"}):
        raise ValueError("score_private_used_for_aggregate_scoring is missing required safe summary keys")
    # Adapter layer must be excluded from the algorithm spec.
    excluded = spec.get("excluded_adapter_layer", {})
    if not excluded.get("model_adapter_excluded") is True:
        raise ValueError("algorithm spec must exclude model_adapter as an adapter layer")
    if not excluded.get("output_mode_excluded") is True:
        raise ValueError("algorithm spec must exclude output_mode as an adapter layer")
    if not excluded.get("provider_credentials_excluded") is True:
        raise ValueError("algorithm spec must exclude provider credentials as an adapter layer")
    if not excluded.get("provider_endpoints_excluded") is True:
        raise ValueError("algorithm spec must exclude provider endpoints as an adapter layer")
    if not excluded.get("provider_secrets_excluded") is True:
        raise ValueError("algorithm spec must exclude provider secrets as an adapter layer")
    hits = _recursive_key_scan(spec)
    if hits:
        raise ValueError(f"forbidden public keys in algorithm spec: {hits!r}")


def verify_audit_report(report: dict[str, Any], frozen_hash: str) -> None:
    if report.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"audit report schema_version mismatch: {report.get('schema_version')!r}")
    if report.get("generated_by") != GENERATED_BY:
        raise ValueError(f"audit report generated_by mismatch: {report.get('generated_by')!r}")
    if report.get("algorithm_spec_id") != EXPECTED_ALGORITHM_SPEC_ID:
        raise ValueError("audit report algorithm_spec_id mismatch")
    if report.get("claim_level") != "benchmark_routed_algorithm_spec_only":
        raise ValueError("audit report claim_level mismatch")
    if report.get("frozen_spec_hash_matched") is not True:
        raise ValueError("audit report frozen_spec_hash_matched must be true")
    if report.get("runtime_clean") is not False:
        raise ValueError("audit report runtime_clean must be false")
    if report.get("runtime_feature_only_mode_supported") is not False:
        raise ValueError("audit report runtime_feature_only_mode_supported must be false")
    if report.get("promotion_ready") is not False:
        raise ValueError("audit report promotion_ready must be false")
    if report.get("default_should_change") is not False:
        raise ValueError("audit report default_should_change must be false")
    if report.get("evidencecore_semantics_changed") is not False:
        raise ValueError("audit report evidencecore_semantics_changed must be false")
    if report.get("score_private_dependencies_for_routing") != []:
        raise ValueError("audit report score_private_dependencies_for_routing must be empty")
    if set(report.get("benchmark_public_dependencies", [])) != set(BENCHMARK_PUBLIC_LABELS):
        raise ValueError("audit report benchmark_public_dependencies mismatch")
    _verify_report_provenance(report)
    hits = _recursive_key_scan(report)
    if hits:
        raise ValueError(f"forbidden public keys in audit report: {hits!r}")


def run_self_test() -> dict[str, Any]:
    frozen_candidates = _load_json(FROZEN_CANDIDATES_PATH)
    frozen_hash = verify_frozen_spec_hash(frozen_candidates)
    candidate = verify_candidate_rules(frozen_candidates)
    predicate_provenance = verify_predicate_provenance()
    action_provenance = verify_action_provenance()
    runtime_only_failure = verify_runtime_feature_only_mode_would_fail(predicate_provenance)

    spec = _load_json(ALGORITHM_SPEC_PATH)
    verify_algorithm_spec(spec, frozen_hash)
    report = _load_json(AUDIT_REPORT_PATH)
    verify_audit_report(report, frozen_hash)

    return {
        "frozen_spec_sha256": frozen_hash,
        "frozen_candidate": candidate["name"],
        "algorithm_spec_id": spec["algorithm_spec_id"],
        "runtime_clean": False,
        "runtime_feature_only_mode_would_fail": True,
        "no_forbidden_public_keys": True,
        "score_private_not_used_for_routing": True,
        "predicate_provenance": predicate_provenance,
        "action_provenance": action_provenance,
        "runtime_only_failure": runtime_only_failure,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run the B10 self-test")
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.error("B10 only supports --self-test in this freeze")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.self_test:
        print("B10 requires --self-test", file=sys.stderr)
        return 2
    result = run_self_test()
    print(json.dumps(result, indent=2, sort_keys=True))
    print("B10 self-test: PASS", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
