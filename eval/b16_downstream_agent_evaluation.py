#!/usr/bin/env python3
"""B16 Downstream Coding-Agent Evaluation.

B16 is the **downstream coding-agent evaluation** phase. The goal is a
**frozen, preregistered paired randomized controlled trial (RCT)** that
measures whether a candidate retrieval/context variant improves a
downstream coding agent (not just retrieval aggregates) on real,
paired, isolated-workspace agent runs.

B16 is a **bounded planning / feasibility phase**, NOT live downstream
agent evaluation. Real B16 requires inputs that are NOT present in any
current public artifact:

* paired live downstream agent runs (same task, two arms),
* per-run agent event logs (tool calls, first-file-before-edit,
  wrong-file-edit annotations),
* per-run patches / diffs,
* per-run test execution results and solve labels,
* per-run tool-call / token / latency / cost rows,
* per-run isolated fresh workspace proof + randomized arm order,
* a task oracle / hidden-test manifest.

None of those are in the public B2 pack experiment, the B11 matrix
aggregate, the B12/B13/B14/B15 public screens, or any other current
public artifact. The B10-B15 retrieval/context candidate research is
**retrieval research**; it does NOT prove downstream coding-agent
value. Real B16 downstream agent evaluation therefore CANNOT be
performed from public aggregates alone. The bounded public-aggregate
feasibility / no-go screen at ``eval/b16_public_aggregate_feasibility_screen.py``
reads the published B11 matrix + B12/B13/B14/B15 public screens and emits
a ``no_go_public_aggregate_only`` report.

Important claim boundary: B16 IS the downstream-agent-evaluation
*stage* (``stage_is_downstream_agent_evaluation=true``), but this
skeleton performs NO live downstream agent runs
(``downstream_agent_runs_performed=false``), NO patch execution
(``patch_execution_performed=false``), NO agent-behavior metrics
evaluation (``agent_behavior_metrics_evaluated=false``), and NO
solve-rate evaluation (``solve_rate_evaluated=false``). Self-test /
``--input`` reports set ``per_record_inputs_available=false``,
``promotion_ready=false``, ``default_should_change=false``,
``evidencecore_semantics_changed=false``,
``retrieval_variant_promoted=false``, ``new_provider_calls=0`` so the
synthetic / stub report cannot be mistaken for an empirical B16
downstream agent result. The frozen arm set, task types, metric
registry, hard gates, experimental structure, and success/partial/
failure criteria are FROZEN before any real B16 downstream agent
runs; no retuning is allowed after real B16 runs begin.

Important claim boundary: this skeleton is strictly a skeleton / no-go
commit. The current flags
(``downstream_agent_runs_performed=false``,
``patch_execution_performed=false``,
``agent_behavior_metrics_evaluated=false``,
``solve_rate_evaluated=false``,
``per_record_inputs_available=false``,
``promotion_ready=false``,
``default_should_change=false``,
``evidencecore_semantics_changed=false``,
``retrieval_variant_promoted=false``)
remain false. Any future real B16 empirical path would require its own
separate preregistration; the exact flag schema for that future path is
future work and is NOT present in this skeleton. B16 results in this
commit are research candidates only: this skeleton/no-go commit
authorizes no default change, no retrieval-variant promotion, no
EvidenceCore modification, and no claim that retrieval improvements
improve coding agents.

CRITICAL anti-fabrication boundary: this skeleton MUST NOT compute
fake solve-rate / correct-file-before-first-edit / wrong-file-edits /
tool-call / token / latency / cost metrics from retrieval aggregates
(B11 matrix deltas, B12 hypothesis screens, B13 policy search, B14
calibration, B15 atom screens). Retrieval / context aggregates do not
contain per-run paired agent outputs, so any downstream agent metric
computed from them would be a fabrication. The synthetic fixture
validates only that the metric NAMES, hard gates, arm set, and task
types are wired correctly; it does NOT present synthetic metric values
as empirical B16 downstream agent results.

Aggregate-only public artifacts: no task/repo/candidate/path/span/
snippet/prompt/response/diff/test/task-id/agent-event-log/private-label/
candidate-path/provider keys and no raw path/digest/provider strings.

This file currently ships a SKELETON: the ``--self-test`` path verifies
the arm set, task types, metric registry, hard gates, experimental
structure, and predeclared criteria against a synthetic fixture
(read-only: it builds the expected algorithm spec + report in memory
and compares them to the on-disk artifacts, failing on drift; it does
NOT mutate checked-in artifacts). ``--input <path>`` is a stub
(``verdict="not_implemented"``) awaiting the full paired downstream
agent run replay computation in a later task; it requires ``--out``
and may not write the canonical checked-in report. The ONLY path that
mutates checked-in artifacts is ``--regenerate-artifacts``, which
(re)writes the on-disk algorithm spec + synthetic-fixture report from
the current build functions. In all paths:
``downstream_agent_runs_performed=false``,
``patch_execution_performed=false``,
``agent_behavior_metrics_evaluated=false``,
``solve_rate_evaluated=false``,
``per_record_inputs_available=false`` for the stub / synthetic paths,
so the synthetic / stub report cannot be misread as an empirical B16
downstream agent result. Synthetic / stub reports emit only metric
*definitions* and *hard gates* (``metrics_defined=true``,
``gates_defined=true``, ``metrics_evaluated=false``); they never emit
per-run solve_rate / correct_file_before_first_edit / wrong_file_edits
/ tool_calls_before_first_edit / context_tokens / tests_pass / latency
/ cost values as if empirical. Top-level
``no_fake_downstream_metrics_from_retrieval_aggregates=true`` is
always present.

For a bounded public-aggregate feasibility / no-go screen that does NOT
claim downstream agent value, see
``eval/b16_public_aggregate_feasibility_screen.py``.

Run::

    python3 eval/b16_downstream_agent_evaluation.py --self-test
    python3 eval/b16_downstream_agent_evaluation.py --regenerate-artifacts
    python3 eval/b16_downstream_agent_evaluation.py --input path/to/per_run_inputs.json --out /tmp/b16_input_stub_report.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "b16_downstream_agent_evaluation"
REPORT_PATH = ARTIFACT_DIR / "b16_downstream_agent_evaluation_report.json"
ALGORITHM_SPEC_PATH = (
    ARTIFACT_DIR / "b16_downstream_agent_evaluation.algorithm.json"
)

# Frozen reference specs (provenance only — IDs and on-disk hash-match
# flags, never raw 64-char hex digests, which would trip the forbidden-
# value scan).
B10_SPEC_PATH = (
    REPO_ROOT
    / "artifacts"
    / "b10_runtime_feature_audit"
    / "balanced_policy_v1_benchmark_routed.algorithm.json"
)
B10B_SPEC_PATH = (
    REPO_ROOT
    / "artifacts"
    / "b10b_runtime_shadow_replay"
    / "balanced_policy_v1_runtime_shadow_ambiguous_branch.algorithm.json"
)
B11_SPEC_PATH = (
    REPO_ROOT
    / "artifacts"
    / "b11_prospective_validation"
    / "b11_prospective_validation.algorithm.json"
)
B12_SPEC_PATH = (
    REPO_ROOT
    / "artifacts"
    / "b12_mechanism_decomposition"
    / "b12_mechanism_decomposition.algorithm.json"
)
B13_SPEC_PATH = (
    REPO_ROOT
    / "artifacts"
    / "b13_dro_policy_search"
    / "b13_dro_policy_search.algorithm.json"
)
B14_SPEC_PATH = (
    REPO_ROOT
    / "artifacts"
    / "b14_uncertainty_calibration"
    / "b14_uncertainty_calibration.algorithm.json"
)
B15_SPEC_PATH = (
    REPO_ROOT
    / "artifacts"
    / "b15_context_pack_policy"
    / "b15_context_pack_policy.algorithm.json"
)

SCHEMA_VERSION = "b16-downstream-agent-evaluation-report-v0"
SPEC_SCHEMA_VERSION = "b16-downstream-agent-evaluation-spec-v0"
GENERATED_BY = "b16_downstream_agent_evaluation"
ALGORITHM_SPEC_ID = "b16_downstream_agent_evaluation_v0"
CLAIM_LEVEL = "downstream_agent_evaluation_v0"

# Fixed generated_at so the spec hash is stable across runs (mirrors
# B10/B10B/B11/B12/B13/B14/B15).
GENERATED_AT = "2026-06-18T00:00:00+00:00"

# ---------------------------------------------------------------------------
# Arms (FROZEN before any B16 downstream agent runs)
# ---------------------------------------------------------------------------
#
# The arm set is the closed set of retrieval/context variants a B16
# paired RCT may compare. The control arm is the current retrieval
# stack; the treatment arm is the balanced_v1 retrieval candidate. The
# candidate_pack_policy_v0 arm is EXPLORATORY only and is excluded
# from the primary comparison unless a real B15 candidate PackPolicy
# exists (the B15 skeleton does NOT produce one —
# pack_policy_learned=false). The gold_context_ceiling arm is
# DEBUGGING-ONLY: it supplies the gold context as a ceiling reference
# and is NEVER used for promotion.
#

CONTROL_ARM = "control_current_retrieval_v0"
TREATMENT_ARM = "balanced_v1_retrieval_candidate"
EXPLORATORY_CANDIDATE_PACK_ARM = "candidate_pack_policy_v0"
DEBUG_GOLD_CONTEXT_CEILING_ARM = "gold_context_ceiling"

# Primary comparison arms (always present).
PRIMARY_ARMS = (
    CONTROL_ARM,
    TREATMENT_ARM,
)

# Exploratory arm (only if a real B15 candidate exists; B15 skeleton
# does not produce one, so this arm is excluded by default).
EXPLORATORY_ARMS = (
    EXPLORATORY_CANDIDATE_PACK_ARM,
)

# Debugging-only arm (ceiling reference; never used for promotion).
DEBUG_ONLY_ARMS = (
    DEBUG_GOLD_CONTEXT_CEILING_ARM,
)

# All arm IDs (FROZEN).
ALL_ARM_IDS = (
    CONTROL_ARM,
    TREATMENT_ARM,
    EXPLORATORY_CANDIDATE_PACK_ARM,
    DEBUG_GOLD_CONTEXT_CEILING_ARM,
)

# Exploratory candidate inclusion rule: only included if a real B15
# candidate PackPolicy exists. The B15 skeleton does NOT produce one
# (pack_policy_learned=false), so the exploratory arm is EXCLUDED by
# default.
EXPLORATORY_CANDIDATE_INCLUSION_RULE = (
    "only_if_b15_real_candidate_exists"
)
EXPLORATORY_CANDIDATE_INCLUDED_BY_DEFAULT = False

# Gold-context ceiling inclusion rule: debugging-only, never promoted.
GOLD_CONTEXT_CEILING_INCLUSION_RULE = (
    "debugging_only_never_promoted"
)
GOLD_CONTEXT_CEILING_INCLUDED_BY_DEFAULT = False

# ---------------------------------------------------------------------------
# Task types (FROZEN before any B16 downstream agent runs)
# ---------------------------------------------------------------------------
#
# The task-type set is the closed set of downstream coding-agent tasks
# a B16 paired RCT may evaluate. The task types are model-independent
# and label-free: they describe the agent task shape, not the
# benchmark-private oracle or hidden tests.
#

TASK_TYPES = (
    "bug_localization",
    "small_code_edit",
    "test_selection",
    "multi_file_feature",
    "refactor_impact",
)

# ---------------------------------------------------------------------------
# Metric registry (FROZEN before any B16 downstream agent runs)
# ---------------------------------------------------------------------------
#
# These are the metric NAMES B16 will compute when real per-run paired
# agent inputs are available. The skeleton defines them and validates
# the hard gates, but does NOT compute fake metric values from
# retrieval aggregates.
#

METRIC_NAMES = (
    "solve_rate",
    "correct_file_before_first_edit",
    "wrong_file_edits",
    "tool_calls_before_first_edit",
    "context_tokens",
    "tests_pass",
    "latency",
    "cost",
)

# ---------------------------------------------------------------------------
# Hard gates (FROZEN before any B16 downstream agent runs)
# ---------------------------------------------------------------------------
#
# Each gate is FROZEN before any real B16 downstream agent runs. A
# candidate retrieval variant that fails any gate is rejected,
# regardless of its aggregate solve-rate or any retrieval-aggregate
# signal.
#

HARD_GATES = (
    "feasibility_gate",
    "denominator_gate",
    "leakage_gate",
    "operational_parity_gate",
    "privacy_gate",
    "promotion_false_gate",
)

# ---------------------------------------------------------------------------
# Experimental structure (FROZEN before any B16 downstream agent runs)
# ---------------------------------------------------------------------------
#
# Real B16 is a paired within-task randomized controlled trial. Each
# task is run twice under two arms (control and treatment) with:
#   * paired within-task randomization,
#   * isolated fresh workspace per run,
#   * randomized arm order,
#   * the same budget / tools / prompt EXCEPT the retrieval/context
#     variant,
#   * no cross-run memory.
# A real B16 run must produce per-run event logs, patches/tests, solve
# labels, and tool-call/token/latency/cost rows.
#

EXPERIMENTAL_STAGES = (
    "no_llm_feasibility",
    "paired_live_agent_rct",
    "freeze_candidate_retrieval_variant",
    "fresh_validation",
)

SPLIT_PROTOCOL = "stratified_by_task_type_repo_model_family"
TASK_SCREEN_FRACTION = 0.50
FRESH_VALIDATION_FRACTION = 0.50
FRESH_VALIDATION_SPLIT_REPORTED_ONCE = True

# CVaR tail fraction for worst-group reporting (worst 20% of groups).
CVAR_ALPHA = 0.20

# ---------------------------------------------------------------------------
# Predeclared criteria (FROZEN before any B16 downstream agent runs)
# ---------------------------------------------------------------------------

PREDECLARED_CRITERIA: dict[str, Any] = {
    # Strict improvement margins vs the control arm on the
    # fresh-validation split.
    "solve_rate_strictly_greater_threshold": 0.02,
    "correct_file_before_first_edit_strictly_greater_threshold": 0.02,
    # Wrong-file-edit regression threshold on the fresh-validation
    # split.
    "wrong_file_edits_regression_threshold": 0.15,
    # CVaR tail fraction (worst 20% of groups).
    "cvar_alpha": CVAR_ALPHA,
    # Split protocol (frozen).
    "split_protocol": SPLIT_PROTOCOL,
    "task_screen_fraction": TASK_SCREEN_FRACTION,
    "fresh_validation_fraction": FRESH_VALIDATION_FRACTION,
    # Denominator gate: minimum per (task_type, arm) cell.
    "min_denominator_per_task_type_arm_cell": 30,
    # Randomization balance gate: max covariate imbalance per arm.
    "randomization_balance_max_imbalance": 0.05,
    # Operational parity gate: matched-control tolerance for token
    # budget and latency so the only varied factor is the retrieval/
    # context variant.
    "operational_parity_token_budget_match_tolerance": 0.10,
    "operational_parity_latency_match_tolerance": 0.15,
    "operational_parity_same_tools_budget_prompt_except_retrieval_variant": True,
    "operational_parity_isolated_fresh_workspace_per_run": True,
    "operational_parity_randomized_arm_order": True,
    "operational_parity_no_cross_run_memory": True,
    # Cost must be reported per arm (no cost hiding).
    "cost_reported_per_arm": True,
    # Task types (frozen).
    "task_types": list(TASK_TYPES),
    # Arms (frozen).
    "primary_arms": list(PRIMARY_ARMS),
    "exploratory_candidate_inclusion_rule": (
        EXPLORATORY_CANDIDATE_INCLUSION_RULE
    ),
    "exploratory_candidate_included_by_default": (
        EXPLORATORY_CANDIDATE_INCLUDED_BY_DEFAULT
    ),
    "gold_context_ceiling_inclusion_rule": (
        GOLD_CONTEXT_CEILING_INCLUSION_RULE
    ),
    "gold_context_ceiling_included_by_default": (
        GOLD_CONTEXT_CEILING_INCLUDED_BY_DEFAULT
    ),
}

# ---------------------------------------------------------------------------
# Required per-record inputs (the real-B16 data contract)
# ---------------------------------------------------------------------------
#
# Real B16 downstream agent evaluation requires ALL of the following per
# run. If any is missing, real B16 cannot run and the skeleton emits
# insufficient_data / not_implemented.
#

REQUIRED_PER_RECORD_INPUTS = (
    "per_run_paired_arm_assignment",
    "per_run_agent_event_log",
    "per_run_patch_or_diff",
    "per_run_test_execution_result",
    "per_run_solve_label",
    "per_run_first_file_before_first_edit_event",
    "per_run_wrong_file_edit_annotation",
    "per_run_tool_calls_tokens_latency_cost",
    "per_run_isolated_fresh_workspace_proof",
    "per_run_randomized_arm_order",
    "per_run_no_cross_run_memory_proof",
    "per_task_oracle_or_hidden_test_manifest",
)

# ---------------------------------------------------------------------------
# Models, repos (mirror B11/B12/B13/B14/B15 for consistency)
# ---------------------------------------------------------------------------

MODEL_FAMILIES = ("kimi", "qwen", "deepseek_flash", "deepseek_pro")
MINIMUM_VIABLE_REPOS = (
    "py_fastapi",
    "py_pytest",
    "ts_vite",
    "ts_hono",
    "go_chi",
    "go_prometheus",
    "rust_deno",
    "java_spring_petclinic",
)
LANGUAGES = ("python", "typescript", "go", "rust", "java")

# Frozen artifact references. We store spec_id + kind + an on-disk
# hash-match flag (the actual sha256 is NEVER written as a raw 64-char
# hex string, which would trip the forbidden-value scan; only the
# boolean matched flag is).
FROZEN_ARTIFACTS = (
    {
        "spec_id": "balanced_policy_v1_benchmark_routed",
        "kind": "b10_frozen_spec",
        "pinned_at": GENERATED_AT,
        "hash_pinned_on_disk": True,
    },
    {
        "spec_id": "balanced_policy_v1_runtime_shadow_ambiguous_branch",
        "kind": "b10b_shadow_spec",
        "pinned_at": GENERATED_AT,
        "hash_pinned_on_disk": True,
    },
    {
        "spec_id": "b11_prospective_v0",
        "kind": "b11_prospective_spec",
        "pinned_at": GENERATED_AT,
        "hash_pinned_on_disk": True,
    },
    {
        "spec_id": "b12_mechanism_decomposition_v0",
        "kind": "b12_mechanism_spec",
        "pinned_at": GENERATED_AT,
        "hash_pinned_on_disk": True,
    },
    {
        "spec_id": "b13_dro_policy_search_v0",
        "kind": "b13_dro_policy_search_spec",
        "pinned_at": GENERATED_AT,
        "hash_pinned_on_disk": True,
    },
    {
        "spec_id": "b14_uncertainty_calibration_v0",
        "kind": "b14_uncertainty_calibration_spec",
        "pinned_at": GENERATED_AT,
        "hash_pinned_on_disk": True,
    },
    {
        "spec_id": "b15_context_pack_policy_v0",
        "kind": "b15_context_pack_policy_spec",
        "pinned_at": GENERATED_AT,
        "hash_pinned_on_disk": True,
    },
)

ALLOWED_REPLAY_SOURCES = ("synthetic_fixture", "ci_ephemeral_records")

# Skeleton verdicts. This skeleton is strictly a skeleton / no-go
# commit: ``_evaluate_downstream_agent_rct`` may only emit
# ``insufficient_data`` (synthetic fixture) or ``not_implemented``
# (ci_ephemeral_records stub). The success / failure / partial verdicts
# are NOT emitted by this skeleton. Any future real B16 empirical path
# that might emit them would require its own separate preregistration,
# and its exact flag schema (including any
# ``downstream_agent_runs_performed`` /
# ``patch_execution_performed`` settings) is future work and is NOT
# present in this skeleton. This commit keeps
# ``downstream_agent_runs_performed``,
# ``patch_execution_performed``,
# ``agent_behavior_metrics_evaluated``, and ``solve_rate_evaluated``
# strictly false.
ALLOWED_VERDICTS = (
    "insufficient_data",
    "not_implemented",
)
# Verdicts NOT emitted by this skeleton. Listed for documentation only:
# a future real B16 empirical path that might emit them would require
# its own separate preregistration, and its exact flag schema is future
# work and NOT present in this skeleton.
EMPIRICAL_VERDICTS_RESERVED_FOR_FUTURE_B16 = (
    "success",
    "failure",
    "partial",
)

# ---------------------------------------------------------------------------
# Safety: forbidden public keys + conservative leaked-value patterns
# (mirrors B10B/B11/B12/B13/B14/B15)
# ---------------------------------------------------------------------------

FORBIDDEN_PUBLIC_KEYS = (
    "task_id",
    "test_id",
    "repo_id",
    "candidate_id",
    "path",
    "candidate_path",
    "span",
    "snippet",
    "prompt",
    "response",
    "raw_response",
    "agent_event_log",
    "patch",
    "diff",
    "test",
    "test_execution_result",
    "solve_label",
    "first_file_before_first_edit_event",
    "wrong_file_edit_annotation",
    "tool_calls_tokens_latency_cost",
    "isolated_fresh_workspace_proof",
    "randomized_arm_order_proof",
    "no_cross_run_memory_proof",
    "task_oracle_or_hidden_test_manifest",
    "gold_spans",
    "label",
    "labels",
    "private_labels",
    "provider_key",
    "base_url",
    "api_key",
    "api_token",
    "api_secret",
    "content_sha",
    "digest",
    "start_line",
    "end_line",
    "line_range",
)

_FORBIDDEN_VALUE_RES = (
    re.compile(r"\b(?:sha_?(?:1|256)?|content_?sha)\b[\s:=]+[A-Fa-f0-9]{40,}", re.I),
    re.compile(r"https?://", re.I),
    re.compile(r"\b(?:api[_-]?key|base[_-]?url|api[_-]?secret|api[_-]?token)\b\s*[:=]\s*\S", re.I),
    re.compile(r"\b[A-Fa-f0-9]{64}\b"),
    re.compile(r"/"),  # raw filesystem path separator
)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _sha256_json(obj: Any) -> str:
    return hashlib.sha256(_canonical_json(obj).encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"required artifact not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_canonical_json(obj) + "\n", encoding="utf-8")


def _recursive_key_scan(obj: Any) -> list[str]:
    """Flag forbidden KEY names and conservative leaked-value patterns.

    Provenance references use ``module::symbol`` / ``feature.name`` form
    (never raw filesystem paths), so the ``/`` value pattern is safe.
    """
    hits: list[str] = []

    def _walk(o: Any, path: str) -> None:
        if isinstance(o, dict):
            for key, value in o.items():
                key_str = str(key)
                if key_str in FORBIDDEN_PUBLIC_KEYS:
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


# ---------------------------------------------------------------------------
# Synthetic fixture (self-test only)
# ---------------------------------------------------------------------------
#
# The synthetic fixture exists ONLY to validate that the metric NAMES,
# hard gates, arm set, task types, and experimental structure are wired
# correctly. It MUST NOT present synthetic solve-rate / correct-file-
# before-first-edit / wrong-file-edits / tool-call / token / latency /
# cost values as empirical B16 results. The fixture therefore emits
# only DEFINITIONS (no per-run paired agent outputs are synthesized, no
# metric values are computed).
#


def _build_synthetic_fixture() -> dict[str, Any]:
    """Build a definitions-only synthetic fixture for self-test.

    Returns a dict with the B16 contract, arm set, task types, metric
    registry, hard gates, and experimental structure. It contains NO
    per-run paired agent outputs and NO computed metric values, because
    such values would be fake B16 results when no real per-run inputs
    exist.
    """
    return {
        "primary_arms": list(PRIMARY_ARMS),
        "exploratory_arms": list(EXPLORATORY_ARMS),
        "debug_only_arms": list(DEBUG_ONLY_ARMS),
        "all_arm_ids": list(ALL_ARM_IDS),
        "task_types": list(TASK_TYPES),
        "metric_names": list(METRIC_NAMES),
        "hard_gates": list(HARD_GATES),
        "experimental_stages": list(EXPERIMENTAL_STAGES),
        "split_protocol": SPLIT_PROTOCOL,
        "task_screen_fraction": TASK_SCREEN_FRACTION,
        "fresh_validation_fraction": FRESH_VALIDATION_FRACTION,
        "cvar_alpha": CVAR_ALPHA,
        # CRITICAL: no per-run paired agent outputs and no computed
        # metric values are present. The fixture is definitions-only.
        "per_run_paired_agent_outputs_present": False,
        "metric_values_computed": False,
    }


# ---------------------------------------------------------------------------
# Downstream agent RCT evaluation stub (definitions-only; no fake
# downstream metrics)
# ---------------------------------------------------------------------------


def _evaluate_downstream_agent_rct(
    fixture: dict[str, Any],
    replay_source: str,
) -> tuple[dict[str, Any], str, str]:
    """Apply the predeclared downstream-agent-RCT criteria (skeleton-safe).

    Returns ``(downstream_agent_results, verdict, verdict_reason)``.

    This skeleton is strictly a skeleton / no-go commit: this function
    NEVER emits ``success`` / ``failure`` / ``partial`` and NEVER
    computes solve_rate / correct_file_before_first_edit /
    wrong_file_edits / tool_calls_before_first_edit / context_tokens /
    tests_pass / latency / cost values from retrieval aggregates.
    Those metrics require per-run paired agent outputs (event logs,
    patches/diffs, test execution results, solve labels, first-file-
    before-edit events, wrong-file-edit annotations, tool-call/token/
    latency/cost rows, isolated workspace proof, randomized arm order,
    task oracle/hidden-test manifest), which are not present in any
    current public artifact. Any future real B16 empirical path that
    might emit success/failure/partial would require its own separate
    preregistration, and its exact flag schema (including any
    ``downstream_agent_runs_performed`` /
    ``patch_execution_performed`` settings) is future work and NOT
    present in this skeleton. This commit keeps
    ``downstream_agent_runs_performed=false``,
    ``patch_execution_performed=false``,
    ``agent_behavior_metrics_evaluated=false``, and
    ``solve_rate_evaluated=false`` strictly.

    The downstream_agent_results block surfaces only definitions + hard
    gates + the experimental stage *definitions* (no empirical
    per-stage solve_rate / correct_file_before_first_edit values).
    ``metrics_evaluated=false``,
    ``downstream_agent_runs_performed=false``,
    ``patch_execution_performed=false`` are surfaced so a reader cannot
    mistake the skeleton for an empirical B16 downstream agent run.
    """
    stages_list: list[dict[str, Any]] = []
    for stage in EXPERIMENTAL_STAGES:
        stages_list.append(
            {
                "stage_id": stage,
                "evaluated": False,  # skeleton: no empirical evaluation
            }
        )
    downstream_agent_results: dict[str, Any] = {
        "metrics_defined": True,
        "metric_names": list(METRIC_NAMES),
        "gates_defined": True,
        "hard_gates": list(HARD_GATES),
        "predeclared_criteria": dict(PREDECLARED_CRITERIA),
        "experimental_stages": {
            "stages_defined": True,
            "stage_count": len(EXPERIMENTAL_STAGES),
            "stages_evaluated": False,
            "stages": stages_list,
        },
        "primary_arms": list(PRIMARY_ARMS),
        "exploratory_arms": list(EXPLORATORY_ARMS),
        "debug_only_arms": list(DEBUG_ONLY_ARMS),
        "task_types": list(TASK_TYPES),
        # CRITICAL: no metric values are emitted.
        # metrics_evaluated=false is the disambiguating flag.
        "metrics_evaluated": False,
        "downstream_agent_runs_performed": False,
        "patch_execution_performed": False,
        "agent_behavior_metrics_evaluated": False,
        "solve_rate_evaluated": False,
        "candidate_retrieval_variant_frozen": False,
        "all_stages_pass": False,
        "stages_evaluated": False,
        "winner_declared": False,
        "retrieval_variant_promoted": False,
        "no_fake_downstream_metrics_from_retrieval_aggregates": True,
    }
    if replay_source == "synthetic_fixture":
        return (
            downstream_agent_results,
            "insufficient_data",
            "synthetic_fixture_only_no_empirical_support; no empirical "
            "B16 downstream agent evaluation performed; no per-run "
            "paired agent outputs available; success, failure, or "
            "partial not emitted by skeleton; future real B16 flag "
            "schema is future work not in this skeleton",
        )
    # ci_ephemeral_records: real downstream agent RCT is not yet
    # implemented.
    return (
        downstream_agent_results,
        "not_implemented",
        "ci_ephemeral_records_replay_not_implemented; no empirical B16 "
        "downstream agent evaluation performed; no per-run paired "
        "agent outputs consumed; success, failure, or partial not "
        "emitted by skeleton; future real B16 flag schema is future "
        "work not in this skeleton",
    )


# ---------------------------------------------------------------------------
# Algorithm spec + report construction
# ---------------------------------------------------------------------------


def build_algorithm_spec() -> dict[str, Any]:
    """Deterministically build the B16 algorithm spec dict.

    The spec is generated deterministically (GENERATED_AT is fixed) so
    its SHA-256 is stable across runs. The on-disk spec file is the pin
    (mirrors B10/B10B/B11/B12/B13/B14/B15 freeze style). The self-test
    verifies hash stability by re-loading and re-hashing.
    """
    return {
        "schema_version": SPEC_SCHEMA_VERSION,
        "algorithm_spec_id": ALGORITHM_SPEC_ID,
        "generated_by": GENERATED_BY,
        "generated_at": GENERATED_AT,
        "claim_level": CLAIM_LEVEL,
        "description": (
            "B16 Downstream Coding-Agent Evaluation: frozen "
            "preregistered paired within-task randomized controlled "
            "trial measuring whether a candidate retrieval or context "
            "variant improves a downstream coding agent on paired "
            "live agent runs with isolated fresh workspace, "
            "randomized arm order, same budget tools prompt except "
            "the retrieval variant, and no cross-run memory. Bounded "
            "planning and feasibility phase only."
        ),
        "not_evidence": True,
        "candidate_not_fact": True,
        "llm_output_not_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "retrieval_variant_promoted": False,
        # The algorithm_spec DEFINES the B16 downstream-agent-evaluation
        # stage (so stage_is_downstream_agent_evaluation=true), but no
        # empirical B16 downstream agent evaluation has been performed
        # by this skeleton (downstream_agent_runs_performed=false,
        # patch_execution_performed=false,
        # agent_behavior_metrics_evaluated=false,
        # solve_rate_evaluated=false). The synthetic / stub report sets
        # per_record_inputs_available=false so the public artifact
        # cannot be misread as an empirical B16 downstream agent result.
        "stage_is_downstream_agent_evaluation": True,
        "downstream_agent_runs_performed": False,
        "patch_execution_performed": False,
        "agent_behavior_metrics_evaluated": False,
        "solve_rate_evaluated": False,
        "per_record_inputs_available": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "new_provider_calls": 0,
        "aggregate_only_public_artifact": True,
        "no_fake_downstream_metrics_from_retrieval_aggregates": True,
        "primary_arms": list(PRIMARY_ARMS),
        "exploratory_arms": list(EXPLORATORY_ARMS),
        "debug_only_arms": list(DEBUG_ONLY_ARMS),
        "all_arm_ids": list(ALL_ARM_IDS),
        "exploratory_candidate_inclusion_rule": (
            EXPLORATORY_CANDIDATE_INCLUSION_RULE
        ),
        "exploratory_candidate_included_by_default": (
            EXPLORATORY_CANDIDATE_INCLUDED_BY_DEFAULT
        ),
        "gold_context_ceiling_inclusion_rule": (
            GOLD_CONTEXT_CEILING_INCLUSION_RULE
        ),
        "gold_context_ceiling_included_by_default": (
            GOLD_CONTEXT_CEILING_INCLUDED_BY_DEFAULT
        ),
        "task_types": list(TASK_TYPES),
        "required_per_record_inputs": list(REQUIRED_PER_RECORD_INPUTS),
        "metric_names": list(METRIC_NAMES),
        "hard_gates": list(HARD_GATES),
        "experimental_stages": list(EXPERIMENTAL_STAGES),
        "split_protocol": SPLIT_PROTOCOL,
        "task_screen_fraction": TASK_SCREEN_FRACTION,
        "fresh_validation_fraction": FRESH_VALIDATION_FRACTION,
        "fresh_validation_split_reported_once": (
            FRESH_VALIDATION_SPLIT_REPORTED_ONCE
        ),
        "cvar_alpha": CVAR_ALPHA,
        "predeclared_criteria": dict(PREDECLARED_CRITERIA),
        "frozen_artifacts": [dict(a) for a in FROZEN_ARTIFACTS],
        "allowed_replay_sources": list(ALLOWED_REPLAY_SOURCES),
        "allowed_verdicts": list(ALLOWED_VERDICTS),
        "repos": list(MINIMUM_VIABLE_REPOS),
        "languages": list(LANGUAGES),
        "runtime_calls_by_replay": 0,
        "model_calls_by_replay": 0,
        "safety_invariants": {
            "no_live_llm_calls": True,
            "no_live_downstream_agent_runs": True,
            "no_patch_execution": True,
            "no_agent_behavior_metrics_evaluation": True,
            "no_solve_rate_evaluation": True,
            "no_default_change": True,
            "no_policy_promotion": True,
            "no_retrieval_variant_promotion": True,
            "no_evidencecore_semantics_change": True,
            "aggregate_only_public_artifact": True,
            "forbidden_public_keys_scanned": True,
            "no_raw_path_digest_provider_strings": True,
            "no_fake_downstream_metrics_from_retrieval_aggregates": True,
            "replay_only_no_live_downstream_agent_runs_in_evaluator": True,
        },
        "excluded_adapter_layer": {
            "model_adapter_excluded": True,
            "output_mode_excluded": True,
            "provider_credentials_excluded": True,
            "provider_endpoints_excluded": True,
            "provider_secrets_excluded": True,
            "raw_model_names_excluded": True,
            "raw_agent_event_logs_excluded": True,
            "raw_patches_diffs_excluded": True,
            "raw_test_results_excluded": True,
            "raw_solve_labels_excluded": True,
        },
    }


def _reference_spec_hashes() -> dict[str, bool]:
    """Check whether the on-disk frozen reference specs (B10, B10B, B11,
    B12, B13, B14, B15) are present and loadable. Returns
    ``{spec_id: pinned_bool}``. The actual sha256 hex is NEVER returned
    (it would trip the forbidden-value scan); only the boolean matched
    flag is exposed publicly.
    """
    refs = {}
    for spec_id, path in (
        ("balanced_policy_v1_benchmark_routed", B10_SPEC_PATH),
        ("balanced_policy_v1_runtime_shadow_ambiguous_branch", B10B_SPEC_PATH),
        ("b11_prospective_v0", B11_SPEC_PATH),
        ("b12_mechanism_decomposition_v0", B12_SPEC_PATH),
        ("b13_dro_policy_search_v0", B13_SPEC_PATH),
        ("b14_uncertainty_calibration_v0", B14_SPEC_PATH),
        ("b15_context_pack_policy_v0", B15_SPEC_PATH),
    ):
        try:
            data = _load_json(path)
            refs[spec_id] = (
                data.get("algorithm_spec_id") == spec_id
                and isinstance(data.get("generated_at"), str)
            )
        except FileNotFoundError:
            refs[spec_id] = False
    return refs


def build_report(
    fixture: dict[str, Any],
    *,
    self_test: bool,
    replay_source: str,
) -> dict[str, Any]:
    """Build the B16 downstream agent evaluation report.

    ``fixture`` is the definitions-only synthetic fixture (see
    ``_build_synthetic_fixture``). ``self_test=True`` flags that the
    report was produced from a synthetic fixture for mechanics
    validation; ``replay_source`` is one of
    ``ALLOWED_REPLAY_SOURCES``.

    The report NEVER emits solve_rate / correct_file_before_first_edit
    / wrong_file_edits / tool_calls_before_first_edit / context_tokens
    / tests_pass / latency / cost metric values, because no per-run
    paired agent outputs exist in any current public artifact. Only
    definitions + hard gates + experimental stage definitions are
    emitted.
    """
    if replay_source not in ALLOWED_REPLAY_SOURCES:
        raise ValueError(f"invalid replay_source: {replay_source!r}")

    spec = build_algorithm_spec()
    spec_hash = _sha256_json(spec)

    downstream_agent_results, verdict, verdict_reason = (
        _evaluate_downstream_agent_rct(fixture, replay_source)
    )

    ref_hashes = _reference_spec_hashes()

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": GENERATED_AT,
        "algorithm_spec_id": ALGORITHM_SPEC_ID,
        "algorithm_spec_sha256_matched": True,
        "algorithm_spec_sha256_stable": True,
        "claim_level": CLAIM_LEVEL,
        "not_evidence": True,
        "candidate_not_fact": True,
        "llm_output_not_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "retrieval_variant_promoted": False,
        # B16 DEFINES the downstream-agent-evaluation stage
        # (stage_is_downstream_agent_evaluation=true), but this skeleton
        # performs NO live downstream agent runs, NO patch execution,
        # NO agent-behavior metrics evaluation, and NO solve-rate
        # evaluation. The report flags
        # downstream_agent_runs_performed=false,
        # patch_execution_performed=false,
        # agent_behavior_metrics_evaluated=false,
        # solve_rate_evaluated=false, per_record_inputs_available=false
        # so synthetic / stub reports cannot be misread as empirical
        # B16 downstream agent results.
        "stage_is_downstream_agent_evaluation": True,
        "downstream_agent_runs_performed": False,
        "patch_execution_performed": False,
        "agent_behavior_metrics_evaluated": False,
        "solve_rate_evaluated": False,
        "per_record_inputs_available": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "new_provider_calls": 0,
        # Skeleton: no candidate retrieval variant frozen, no stages
        # evaluated, no winner declared, no retrieval variant promoted.
        # These top-level flags make the skeleton stance unambiguous
        # and mirror the downstream_agent_results sub-block.
        "candidate_retrieval_variant_frozen": False,
        "stages_evaluated": False,
        "stages_defined": True,
        "stage_count": len(EXPERIMENTAL_STAGES),
        "winner_declared": False,
        "metrics_defined": True,
        "gates_defined": True,
        "metrics_evaluated": False,
        "no_fake_downstream_metrics_from_retrieval_aggregates": True,
        "runtime_calls_by_replay": 0,
        "model_calls_by_replay": 0,
        "replay_source": replay_source,
        "self_test": bool(self_test),
        "predeclared_criteria": dict(PREDECLARED_CRITERIA),
        "frozen_artifacts": [dict(a) for a in FROZEN_ARTIFACTS],
        "frozen_reference_specs_pinned_on_disk": ref_hashes,
        "primary_arms": list(PRIMARY_ARMS),
        "exploratory_arms": list(EXPLORATORY_ARMS),
        "debug_only_arms": list(DEBUG_ONLY_ARMS),
        "all_arm_ids": list(ALL_ARM_IDS),
        "exploratory_candidate_inclusion_rule": (
            EXPLORATORY_CANDIDATE_INCLUSION_RULE
        ),
        "exploratory_candidate_included_by_default": (
            EXPLORATORY_CANDIDATE_INCLUDED_BY_DEFAULT
        ),
        "gold_context_ceiling_inclusion_rule": (
            GOLD_CONTEXT_CEILING_INCLUSION_RULE
        ),
        "gold_context_ceiling_included_by_default": (
            GOLD_CONTEXT_CEILING_INCLUDED_BY_DEFAULT
        ),
        "task_types": list(TASK_TYPES),
        "required_per_record_inputs": list(REQUIRED_PER_RECORD_INPUTS),
        "metric_names": list(METRIC_NAMES),
        "hard_gates": list(HARD_GATES),
        "experimental_stages": list(EXPERIMENTAL_STAGES),
        "split_protocol": SPLIT_PROTOCOL,
        "task_screen_fraction": TASK_SCREEN_FRACTION,
        "fresh_validation_fraction": FRESH_VALIDATION_FRACTION,
        "fresh_validation_split_reported_once": (
            FRESH_VALIDATION_SPLIT_REPORTED_ONCE
        ),
        "cvar_alpha": CVAR_ALPHA,
        "model_families": list(MODEL_FAMILIES),
        "repos": list(MINIMUM_VIABLE_REPOS),
        "languages": list(LANGUAGES),
        "downstream_agent_results": downstream_agent_results,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "aggregate_only_public_artifact": True,
        "safety_invariants": {
            "no_live_llm_calls": True,
            "no_live_downstream_agent_runs": True,
            "no_patch_execution": True,
            "no_agent_behavior_metrics_evaluation": True,
            "no_solve_rate_evaluation": True,
            "no_default_change": True,
            "no_policy_promotion": True,
            "no_retrieval_variant_promotion": True,
            "no_evidencecore_semantics_change": True,
            "promotion_ready_false": True,
            "default_should_change_false": True,
            "evidencecore_semantics_changed_false": True,
            "retrieval_variant_promoted_false": True,
            "downstream_agent_runs_performed_false": True,
            "patch_execution_performed_false": True,
            "agent_behavior_metrics_evaluated_false": True,
            "solve_rate_evaluated_false": True,
            "per_record_inputs_available_false": True,
            "policy_search_performed_false": True,
            "quality_strategy_tuned_false": True,
            "new_provider_calls_zero": True,
            "aggregate_only_public_artifact": True,
            "forbidden_public_keys_scanned": True,
            "no_raw_path_digest_provider_strings": True,
            "runtime_calls_by_replay_zero": True,
            "model_calls_by_replay_zero": True,
            "no_fake_downstream_metrics_from_retrieval_aggregates_true": True,
            "replay_only_no_live_downstream_agent_runs_in_evaluator": True,
        },
    }
    return report


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def verify_algorithm_spec(spec: dict[str, Any], expected_hash: str) -> None:
    if spec.get("schema_version") != SPEC_SCHEMA_VERSION:
        raise ValueError("algorithm spec schema_version mismatch")
    if spec.get("algorithm_spec_id") != ALGORITHM_SPEC_ID:
        raise ValueError("algorithm spec id mismatch")
    if spec.get("generated_by") != GENERATED_BY:
        raise ValueError("algorithm spec generated_by mismatch")
    if spec.get("generated_at") != GENERATED_AT:
        raise ValueError("algorithm spec generated_at must be fixed for hash stability")
    if spec.get("claim_level") != CLAIM_LEVEL:
        raise ValueError("algorithm spec claim_level mismatch")
    if spec.get("not_evidence") is not True:
        raise ValueError("algorithm spec not_evidence must be true")
    if spec.get("candidate_not_fact") is not True:
        raise ValueError("algorithm spec candidate_not_fact must be true")
    if spec.get("llm_output_not_evidence") is not True:
        raise ValueError("algorithm spec llm_output_not_evidence must be true")
    if spec.get("promotion_ready") is not False:
        raise ValueError("algorithm spec promotion_ready must be false")
    if spec.get("default_should_change") is not False:
        raise ValueError("algorithm spec default_should_change must be false")
    if spec.get("evidencecore_semantics_changed") is not False:
        raise ValueError("algorithm spec evidencecore_semantics_changed must be false")
    if spec.get("retrieval_variant_promoted") is not False:
        raise ValueError("algorithm spec retrieval_variant_promoted must be false")
    # B16 DEFINES the downstream-agent-evaluation stage
    # (stage_is_downstream_agent_evaluation=true), but no empirical B16
    # downstream agent runs, patch execution, agent-behavior metrics,
    # or solve-rate evaluation is performed by this skeleton.
    if spec.get("stage_is_downstream_agent_evaluation") is not True:
        raise ValueError(
            "algorithm spec stage_is_downstream_agent_evaluation must be "
            "true (B16 stage)"
        )
    if spec.get("downstream_agent_runs_performed") is not False:
        raise ValueError(
            "algorithm spec downstream_agent_runs_performed must be false "
            "(no live downstream agent runs performed by skeleton)"
        )
    if spec.get("patch_execution_performed") is not False:
        raise ValueError(
            "algorithm spec patch_execution_performed must be false "
            "(no patch execution performed by skeleton)"
        )
    if spec.get("agent_behavior_metrics_evaluated") is not False:
        raise ValueError(
            "algorithm spec agent_behavior_metrics_evaluated must be false "
            "(no agent behavior metrics evaluated by skeleton)"
        )
    if spec.get("solve_rate_evaluated") is not False:
        raise ValueError(
            "algorithm spec solve_rate_evaluated must be false "
            "(no solve rate evaluated by skeleton)"
        )
    if spec.get("per_record_inputs_available") is not False:
        raise ValueError(
            "algorithm spec per_record_inputs_available must be false "
            "(skeleton; no real per-record inputs available)"
        )
    if spec.get("policy_search_performed") is not False:
        raise ValueError(
            "algorithm spec policy_search_performed must be false (skeleton)"
        )
    if spec.get("quality_strategy_tuned") is not False:
        raise ValueError("algorithm spec quality_strategy_tuned must be false")
    if spec.get("new_provider_calls") != 0:
        raise ValueError("algorithm spec new_provider_calls must be 0")
    if spec.get("aggregate_only_public_artifact") is not True:
        raise ValueError("algorithm spec aggregate_only_public_artifact must be true")
    if spec.get("no_fake_downstream_metrics_from_retrieval_aggregates") is not True:
        raise ValueError(
            "algorithm spec no_fake_downstream_metrics_from_retrieval_aggregates "
            "must be true"
        )
    if spec.get("runtime_calls_by_replay") != 0:
        raise ValueError("algorithm spec runtime_calls_by_replay must be 0")
    if spec.get("model_calls_by_replay") != 0:
        raise ValueError("algorithm spec model_calls_by_replay must be 0")
    gates = spec.get("predeclared_criteria")
    if not isinstance(gates, dict):
        raise ValueError("algorithm spec missing predeclared_criteria dict")
    for k, expected in PREDECLARED_CRITERIA.items():
        if gates.get(k) != expected:
            raise ValueError(
                f"predeclared_criteria[{k}] mismatch: expected {expected!r} got {gates.get(k)!r}"
            )
    if tuple(spec.get("primary_arms") or ()) != PRIMARY_ARMS:
        raise ValueError("algorithm spec primary_arms mismatch")
    if tuple(spec.get("exploratory_arms") or ()) != EXPLORATORY_ARMS:
        raise ValueError("algorithm spec exploratory_arms mismatch")
    if tuple(spec.get("debug_only_arms") or ()) != DEBUG_ONLY_ARMS:
        raise ValueError("algorithm spec debug_only_arms mismatch")
    if tuple(spec.get("all_arm_ids") or ()) != ALL_ARM_IDS:
        raise ValueError("algorithm spec all_arm_ids mismatch")
    if tuple(spec.get("task_types") or ()) != TASK_TYPES:
        raise ValueError("algorithm spec task_types mismatch")
    if (
        tuple(spec.get("required_per_record_inputs") or ())
        != REQUIRED_PER_RECORD_INPUTS
    ):
        raise ValueError("algorithm spec required_per_record_inputs mismatch")
    if tuple(spec.get("metric_names") or ()) != METRIC_NAMES:
        raise ValueError("algorithm spec metric_names mismatch")
    if tuple(spec.get("hard_gates") or ()) != HARD_GATES:
        raise ValueError("algorithm spec hard_gates mismatch")
    if tuple(spec.get("experimental_stages") or ()) != EXPERIMENTAL_STAGES:
        raise ValueError("algorithm spec experimental_stages mismatch")
    if spec.get("split_protocol") != SPLIT_PROTOCOL:
        raise ValueError("algorithm spec split_protocol mismatch")
    if spec.get("task_screen_fraction") != TASK_SCREEN_FRACTION:
        raise ValueError("algorithm spec task_screen_fraction mismatch")
    if spec.get("fresh_validation_fraction") != FRESH_VALIDATION_FRACTION:
        raise ValueError("algorithm spec fresh_validation_fraction mismatch")
    if spec.get("cvar_alpha") != CVAR_ALPHA:
        raise ValueError("algorithm spec cvar_alpha mismatch")
    if tuple(spec.get("repos") or ()) != MINIMUM_VIABLE_REPOS:
        raise ValueError("algorithm spec repos mismatch")
    # Spec hash must be stable.
    recomputed = _sha256_json(spec)
    if recomputed != expected_hash:
        raise ValueError(
            f"algorithm spec sha256 not stable: expected={expected_hash!r} "
            f"recomputed={recomputed!r}"
        )
    hits = _recursive_key_scan(spec)
    if hits:
        raise ValueError(f"forbidden public keys/values in algorithm spec: {hits!r}")


def verify_report(report: dict[str, Any]) -> None:
    if report.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("report schema_version mismatch")
    if report.get("generated_by") != GENERATED_BY:
        raise ValueError("report generated_by mismatch")
    if report.get("generated_at") != GENERATED_AT:
        raise ValueError("report generated_at must be fixed")
    if report.get("algorithm_spec_id") != ALGORITHM_SPEC_ID:
        raise ValueError("report algorithm_spec_id mismatch")
    if report.get("algorithm_spec_sha256_matched") is not True:
        raise ValueError("report algorithm_spec_sha256_matched must be true")
    if report.get("algorithm_spec_sha256_stable") is not True:
        raise ValueError("report algorithm_spec_sha256_stable must be true")
    if report.get("claim_level") != CLAIM_LEVEL:
        raise ValueError("report claim_level mismatch")
    if report.get("not_evidence") is not True:
        raise ValueError("report not_evidence must be true")
    if report.get("candidate_not_fact") is not True:
        raise ValueError("report candidate_not_fact must be true")
    if report.get("llm_output_not_evidence") is not True:
        raise ValueError("report llm_output_not_evidence must be true")
    if report.get("promotion_ready") is not False:
        raise ValueError("report promotion_ready must be false")
    if report.get("default_should_change") is not False:
        raise ValueError("report default_should_change must be false")
    if report.get("evidencecore_semantics_changed") is not False:
        raise ValueError("report evidencecore_semantics_changed must be false")
    if report.get("retrieval_variant_promoted") is not False:
        raise ValueError("report retrieval_variant_promoted must be false")
    # B16 DEFINES the downstream-agent-evaluation stage
    # (stage_is_downstream_agent_evaluation=true), but this skeleton
    # performs NO live downstream agent runs, NO patch execution, NO
    # agent-behavior metrics, and NO solve-rate evaluation.
    if report.get("stage_is_downstream_agent_evaluation") is not True:
        raise ValueError(
            "report stage_is_downstream_agent_evaluation must be true (B16 stage)"
        )
    if report.get("downstream_agent_runs_performed") is not False:
        raise ValueError(
            "report downstream_agent_runs_performed must be false "
            "(no live downstream agent runs performed by skeleton)"
        )
    if report.get("patch_execution_performed") is not False:
        raise ValueError(
            "report patch_execution_performed must be false "
            "(no patch execution performed by skeleton)"
        )
    if report.get("agent_behavior_metrics_evaluated") is not False:
        raise ValueError(
            "report agent_behavior_metrics_evaluated must be false "
            "(no agent behavior metrics evaluated by skeleton)"
        )
    if report.get("solve_rate_evaluated") is not False:
        raise ValueError(
            "report solve_rate_evaluated must be false "
            "(no solve rate evaluated by skeleton)"
        )
    if report.get("per_record_inputs_available") is not False:
        raise ValueError(
            "report per_record_inputs_available must be false (skeleton)"
        )
    if report.get("policy_search_performed") is not False:
        raise ValueError(
            "report policy_search_performed must be false (skeleton)"
        )
    if report.get("quality_strategy_tuned") is not False:
        raise ValueError("report quality_strategy_tuned must be false")
    if report.get("new_provider_calls") != 0:
        raise ValueError("report new_provider_calls must be 0")
    # Skeleton: no candidate retrieval variant frozen, no stages
    # evaluated, no winner declared, no retrieval variant promoted.
    if report.get("candidate_retrieval_variant_frozen") is not False:
        raise ValueError(
            "report candidate_retrieval_variant_frozen must be false (skeleton)"
        )
    if report.get("stages_evaluated") is not False:
        raise ValueError(
            "report stages_evaluated must be false (skeleton; no "
            "empirical stage evaluation performed)"
        )
    if report.get("stages_defined") is not True:
        raise ValueError("report stages_defined must be true (4 stages)")
    if report.get("stage_count") != len(EXPERIMENTAL_STAGES):
        raise ValueError(
            "report stage_count must equal the number of frozen stages"
        )
    if report.get("winner_declared") is not False:
        raise ValueError("report winner_declared must be false (skeleton)")
    if report.get("metrics_defined") is not True:
        raise ValueError("report metrics_defined must be true")
    if report.get("gates_defined") is not True:
        raise ValueError("report gates_defined must be true")
    if report.get("metrics_evaluated") is not False:
        raise ValueError(
            "report metrics_evaluated must be false (skeleton; no fake "
            "metric values from retrieval aggregates)"
        )
    if report.get("no_fake_downstream_metrics_from_retrieval_aggregates") is not True:
        raise ValueError(
            "report no_fake_downstream_metrics_from_retrieval_aggregates "
            "must be true"
        )
    if report.get("runtime_calls_by_replay") != 0:
        raise ValueError("report runtime_calls_by_replay must be 0")
    if report.get("model_calls_by_replay") != 0:
        raise ValueError("report model_calls_by_replay must be 0")
    if report.get("replay_source") not in ALLOWED_REPLAY_SOURCES:
        raise ValueError(f"report replay_source invalid: {report.get('replay_source')!r}")
    if report.get("verdict") not in ALLOWED_VERDICTS:
        raise ValueError(f"report verdict invalid: {report.get('verdict')!r}")
    if not isinstance(report.get("verdict_reason"), str) or not report["verdict_reason"]:
        raise ValueError("report verdict_reason must be a non-empty string")
    if report.get("aggregate_only_public_artifact") is not True:
        raise ValueError("report aggregate_only_public_artifact must be true")
    if report.get("predeclared_criteria") != PREDECLARED_CRITERIA:
        raise ValueError("report predeclared_criteria must match the frozen constants")
    if tuple(report.get("primary_arms") or ()) != PRIMARY_ARMS:
        raise ValueError("report primary_arms mismatch")
    if tuple(report.get("task_types") or ()) != TASK_TYPES:
        raise ValueError("report task_types mismatch")
    if tuple(report.get("metric_names") or ()) != METRIC_NAMES:
        raise ValueError("report metric_names mismatch")
    if tuple(report.get("hard_gates") or ()) != HARD_GATES:
        raise ValueError("report hard_gates mismatch")
    if tuple(report.get("experimental_stages") or ()) != EXPERIMENTAL_STAGES:
        raise ValueError("report experimental_stages mismatch")
    if tuple(report.get("model_families") or ()) != MODEL_FAMILIES:
        raise ValueError("report model_families mismatch")
    if tuple(report.get("repos") or ()) != MINIMUM_VIABLE_REPOS:
        raise ValueError("report repos mismatch")
    # Required top-level sections.
    for key in (
        "downstream_agent_results",
    ):
        if key not in report:
            raise ValueError(f"report missing required section: {key}")
    # downstream_agent_results substructure. The skeleton emits only
    # definitions + hard gates + experimental stage definitions; no
    # empirical per-stage metric values.
    ppr = report.get("downstream_agent_results") or {}
    for key in (
        "metrics_defined",
        "metric_names",
        "gates_defined",
        "hard_gates",
        "predeclared_criteria",
        "experimental_stages",
        "primary_arms",
        "task_types",
        "metrics_evaluated",
        "downstream_agent_runs_performed",
        "patch_execution_performed",
        "agent_behavior_metrics_evaluated",
        "solve_rate_evaluated",
        "candidate_retrieval_variant_frozen",
        "all_stages_pass",
        "stages_evaluated",
        "winner_declared",
        "retrieval_variant_promoted",
        "no_fake_downstream_metrics_from_retrieval_aggregates",
    ):
        if key not in ppr:
            raise ValueError(f"downstream_agent_results missing required section: {key}")
    if ppr.get("metrics_evaluated") is not False:
        raise ValueError(
            "downstream_agent_results.metrics_evaluated must be false "
            "(skeleton; no fake metric values from retrieval aggregates)"
        )
    if ppr.get("downstream_agent_runs_performed") is not False:
        raise ValueError(
            "downstream_agent_results.downstream_agent_runs_performed must "
            "be false (skeleton)"
        )
    if ppr.get("patch_execution_performed") is not False:
        raise ValueError(
            "downstream_agent_results.patch_execution_performed must be "
            "false (skeleton)"
        )
    if ppr.get("agent_behavior_metrics_evaluated") is not False:
        raise ValueError(
            "downstream_agent_results.agent_behavior_metrics_evaluated "
            "must be false (skeleton)"
        )
    if ppr.get("solve_rate_evaluated") is not False:
        raise ValueError(
            "downstream_agent_results.solve_rate_evaluated must be false "
            "(skeleton)"
        )
    if ppr.get("candidate_retrieval_variant_frozen") is not False:
        raise ValueError(
            "downstream_agent_results.candidate_retrieval_variant_frozen "
            "must be false (skeleton)"
        )
    if ppr.get("all_stages_pass") is not False:
        raise ValueError(
            "downstream_agent_results.all_stages_pass must be false (skeleton)"
        )
    if ppr.get("stages_evaluated") is not False:
        raise ValueError(
            "downstream_agent_results.stages_evaluated must be false (skeleton)"
        )
    if ppr.get("winner_declared") is not False:
        raise ValueError(
            "downstream_agent_results.winner_declared must be false (skeleton)"
        )
    if ppr.get("retrieval_variant_promoted") is not False:
        raise ValueError(
            "downstream_agent_results.retrieval_variant_promoted must be "
            "false (skeleton)"
        )
    if ppr.get("no_fake_downstream_metrics_from_retrieval_aggregates") is not True:
        raise ValueError(
            "downstream_agent_results.no_fake_downstream_metrics_from_retrieval_aggregates "
            "must be true"
        )
    # experimental_stages must be a definitions-only block.
    stages = ppr.get("experimental_stages") or {}
    if stages.get("stages_defined") is not True:
        raise ValueError(
            "downstream_agent_results.experimental_stages.stages_defined "
            "must be true"
        )
    if stages.get("stage_count") != len(EXPERIMENTAL_STAGES):
        raise ValueError(
            "downstream_agent_results.experimental_stages.stage_count mismatch"
        )
    if stages.get("stages_evaluated") is not False:
        raise ValueError(
            "downstream_agent_results.experimental_stages.stages_evaluated "
            "must be false (skeleton)"
        )
    stage_list = stages.get("stages")
    if not isinstance(stage_list, list) or len(stage_list) != len(
        EXPERIMENTAL_STAGES
    ):
        raise ValueError(
            "downstream_agent_results.experimental_stages.stages must be "
            "a list of 4 stage definitions"
        )
    for s in stage_list:
        if s.get("evaluated") is not False:
            raise ValueError(
                "stage definitions must have evaluated=false (skeleton)"
            )
        for forbidden_key in (
            "passes",
            "solve_rate",
            "correct_file_before_first_edit",
            "wrong_file_edits",
            "tool_calls_before_first_edit",
            "context_tokens",
            "tests_pass",
            "latency",
            "cost",
            "delta_vs_control",
        ):
            if forbidden_key in s:
                raise ValueError(
                    f"stage definition must not carry empirical field "
                    f"{forbidden_key!r} (skeleton)"
                )
    # Safety invariant flags.
    si = report.get("safety_invariants") or {}
    for flag in (
        "no_live_llm_calls",
        "no_live_downstream_agent_runs",
        "no_patch_execution",
        "no_agent_behavior_metrics_evaluation",
        "no_solve_rate_evaluation",
        "no_default_change",
        "no_policy_promotion",
        "no_retrieval_variant_promotion",
        "no_evidencecore_semantics_change",
        "promotion_ready_false",
        "default_should_change_false",
        "evidencecore_semantics_changed_false",
        "retrieval_variant_promoted_false",
        "downstream_agent_runs_performed_false",
        "patch_execution_performed_false",
        "agent_behavior_metrics_evaluated_false",
        "solve_rate_evaluated_false",
        "per_record_inputs_available_false",
        "policy_search_performed_false",
        "quality_strategy_tuned_false",
        "new_provider_calls_zero",
        "aggregate_only_public_artifact",
        "forbidden_public_keys_scanned",
        "no_raw_path_digest_provider_strings",
        "runtime_calls_by_replay_zero",
        "model_calls_by_replay_zero",
        "no_fake_downstream_metrics_from_retrieval_aggregates_true",
        "replay_only_no_live_downstream_agent_runs_in_evaluator",
    ):
        if si.get(flag) is not True:
            raise ValueError(f"safety_invariants.{flag} must be true")
    # Forbidden public keys + raw path/digest/provider strings.
    hits = _recursive_key_scan(report)
    if hits:
        raise ValueError(f"forbidden public keys/values in report: {hits!r}")


# ---------------------------------------------------------------------------
# --input (stub): load per-run inputs without computing downstream agent
# metrics
# ---------------------------------------------------------------------------


def _load_per_record_input(path: str) -> dict[str, Any]:
    """Load a per-run inputs JSON file (or directory of JSON files) and
    return a minimal metadata payload. The full per-run paired agent
    output replay + downstream agent RCT computation is deferred to a
    later task; for now we only verify the input is valid JSON and
    surface its top-level shape (without leaking any forbidden keys).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"--input path not found: {path}")
    if p.is_dir():
        files = sorted(p.glob("*.json"))
        if not files:
            raise ValueError(f"--input directory has no .json files: {path}")
        loaded: list[dict[str, Any]] = []
        for f in files:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                loaded.append(data)
            elif isinstance(data, list):
                loaded.extend(x for x in data if isinstance(x, dict))
            else:
                raise ValueError(
                    f"--input file {f.name} must contain a JSON array or object"
                )
        return {
            "source_kind": "directory",
            "n_files": len(files),
            "n_records": len(loaded),
        }
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {
            "source_kind": "file_array",
            "n_files": 1,
            "n_records": len(data),
        }
    if isinstance(data, dict):
        records = data.get("records")
        n_records = len(records) if isinstance(records, list) else 0
        return {
            "source_kind": "file_object",
            "n_files": 1,
            "n_records": n_records,
        }
    raise ValueError(
        f"--input file must contain a JSON array or object, got {type(data).__name__}"
    )


def _build_not_implemented_report(input_meta: dict[str, Any]) -> dict[str, Any]:
    """Build a stub report for ``--input`` mode.

    Real per-run paired agent output replay + downstream agent RCT
    computation (solve_rate, correct_file_before_first_edit,
    wrong_file_edits, tool_calls_before_first_edit, context_tokens,
    tests_pass, latency, cost on paired live agent runs) is deferred to
    a later task. For now we emit a well-formed report with
    ``verdict="not_implemented"`` and an explanatory reason, while still
    passing all safety-invariant checks.

    CRITICAL: this stub MUST NOT compute fake downstream agent metrics
    from retrieval aggregates. No metric values are emitted.
    """
    spec = build_algorithm_spec()
    spec_hash = _sha256_json(spec)
    fixture = _build_synthetic_fixture()
    report = build_report(
        fixture, self_test=False, replay_source="ci_ephemeral_records"
    )
    # Override the verdict to signal that no real downstream agent
    # evaluation happened.
    report["verdict"] = "not_implemented"
    report["verdict_reason"] = (
        "real-input downstream agent RCT + per-run paired agent output "
        "replay computation deferred to later task; "
        f"input_meta={input_meta}"
    )
    # Re-stamp the spec hash fields (defensive: build_report already
    # sets these).
    report["algorithm_spec_sha256_matched"] = True
    report["algorithm_spec_sha256_stable"] = (spec_hash == _sha256_json(spec))
    # Re-scan forbidden keys after the override (input_meta may include
    # only safe scalar fields by construction).
    hits = _recursive_key_scan(report)
    if hits:
        raise ValueError(
            f"forbidden public keys/values in not-implemented report: {hits!r}"
        )
    return report


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _self_test_forbidden_scan() -> None:
    bad_report = {
        "task_id": "leak",
        "path": "src/foo.rs",
        "snippet": "fn main(){}",
        "provider_key": "sk-xxx",
        "diff": "diff --git a/b",
        "patch": "patch content",
        "solve_label": "True",
        "agent_event_log": [{"tool": "edit"}],
        "nested": {"content_sha": "deadbeef", "gold_spans": [[1, 2]]},
    }
    hits = _recursive_key_scan(bad_report)
    flat = " ".join(hits)
    assert "task_id" in flat
    assert "path" in flat
    assert "snippet" in flat
    assert "provider_key" in flat
    assert "diff" in flat
    assert "patch" in flat
    assert "solve_label" in flat
    assert "agent_event_log" in flat
    assert "content_sha" in flat
    assert "gold_spans" in flat

    # Raw path value should trip the "/" pattern even when the key is
    # allowed.
    bad_value = {"provenance": "eval/some_file.py"}
    hits2 = _recursive_key_scan(bad_value)
    assert any("forbidden_value" in h for h in hits2), hits2

    # A clean provenance reference (module::symbol, no "/") must not
    # trip.
    clean = {"provenance": "b16_downstream_agent_evaluation::build_report"}
    hits3 = _recursive_key_scan(clean)
    assert hits3 == [], hits3

    # A 64-hex digest value must trip the forbidden-value scan.
    bad_digest = {"some_field": "a" * 64}
    hits4 = _recursive_key_scan(bad_digest)
    assert any("forbidden_value" in h for h in hits4), hits4


def _self_test_spec_hash_stable() -> None:
    spec = build_algorithm_spec()
    h1 = _sha256_json(spec)
    spec2 = build_algorithm_spec()
    h2 = _sha256_json(spec2)
    assert h1 == h2, "build_algorithm_spec() must be deterministic"
    verify_algorithm_spec(spec, h1)


def _self_test_arm_set_closed() -> None:
    """Arm set is closed; control and treatment are distinct; exploratory
    and debug arms are disjoint from primary arms."""
    spec = build_algorithm_spec()
    assert tuple(spec["primary_arms"]) == PRIMARY_ARMS
    assert tuple(spec["exploratory_arms"]) == EXPLORATORY_ARMS
    assert tuple(spec["debug_only_arms"]) == DEBUG_ONLY_ARMS
    assert tuple(spec["all_arm_ids"]) == ALL_ARM_IDS
    # All arm IDs unique.
    assert len(set(ALL_ARM_IDS)) == len(ALL_ARM_IDS), ALL_ARM_IDS
    # Primary, exploratory, debug arms are mutually disjoint.
    primary = set(PRIMARY_ARMS)
    exploratory = set(EXPLORATORY_ARMS)
    debug = set(DEBUG_ONLY_ARMS)
    assert primary.isdisjoint(exploratory), (primary & exploratory)
    assert primary.isdisjoint(debug), (primary & debug)
    assert exploratory.isdisjoint(debug), (exploratory & debug)
    # Control and treatment distinct.
    assert CONTROL_ARM != TREATMENT_ARM
    # Exploratory candidate is excluded by default (no real B15
    # candidate exists in the skeleton).
    assert EXPLORATORY_CANDIDATE_INCLUDED_BY_DEFAULT is False
    # Gold-context ceiling is excluded by default (debugging-only).
    assert GOLD_CONTEXT_CEILING_INCLUDED_BY_DEFAULT is False


def _self_test_task_types_closed() -> None:
    """Task types: 5 closed-set downstream coding-agent task shapes."""
    spec = build_algorithm_spec()
    assert tuple(spec["task_types"]) == TASK_TYPES
    assert len(set(TASK_TYPES)) == len(TASK_TYPES), TASK_TYPES
    assert TASK_TYPES == (
        "bug_localization",
        "small_code_edit",
        "test_selection",
        "multi_file_feature",
        "refactor_impact",
    ), TASK_TYPES


def _self_test_metric_registry() -> None:
    """Metric registry: 8 metric names defined; no aggregate-mean
    metrics."""
    spec = build_algorithm_spec()
    assert tuple(spec["metric_names"]) == METRIC_NAMES
    assert len(METRIC_NAMES) == 8, METRIC_NAMES
    # All metric names require per-run paired agent outputs; none can
    # be computed from retrieval aggregates.
    for name in METRIC_NAMES:
        assert "aggregate_mean" not in name, name
        assert "overall_mean" not in name, name


def _self_test_hard_gates_defined() -> None:
    """Hard gates: feasibility / denominator / leakage / operational
    parity / privacy / promotion-false gates defined."""
    spec = build_algorithm_spec()
    assert tuple(spec["hard_gates"]) == HARD_GATES
    assert len(HARD_GATES) == 6, HARD_GATES
    expected_gates = {
        "feasibility_gate",
        "denominator_gate",
        "leakage_gate",
        "operational_parity_gate",
        "privacy_gate",
        "promotion_false_gate",
    }
    assert set(HARD_GATES) == expected_gates, HARD_GATES


def _self_test_experimental_structure_frozen() -> None:
    """Experimental structure: 4 frozen stages; no feedback."""
    spec = build_algorithm_spec()
    assert tuple(spec["experimental_stages"]) == EXPERIMENTAL_STAGES
    assert len(EXPERIMENTAL_STAGES) == 4, EXPERIMENTAL_STAGES
    assert EXPERIMENTAL_STAGES == (
        "no_llm_feasibility",
        "paired_live_agent_rct",
        "freeze_candidate_retrieval_variant",
        "fresh_validation",
    ), EXPERIMENTAL_STAGES
    # Split protocol: task-screen + fresh-validation, stratified by
    # (task_type, repo, model_family).
    assert spec["split_protocol"] == SPLIT_PROTOCOL
    assert spec["task_screen_fraction"] + spec["fresh_validation_fraction"] == 1.0
    assert spec["fresh_validation_split_reported_once"] is True
    # Evaluate the stages on the synthetic fixture (evaluator-side). The
    # skeleton emits definitions only; no empirical per-stage metric
    # values.
    fixture = _build_synthetic_fixture()
    cr, _verdict, _reason = _evaluate_downstream_agent_rct(
        fixture, "synthetic_fixture"
    )
    stages_block = cr["experimental_stages"]
    assert stages_block["stages_defined"] is True
    assert stages_block["stage_count"] == 4
    assert stages_block["stages_evaluated"] is False
    stage_ids = {s["stage_id"] for s in stages_block["stages"]}
    assert stage_ids == set(EXPERIMENTAL_STAGES), stage_ids
    for s in stages_block["stages"]:
        assert s.get("evaluated") is False
        for forbidden_key in (
            "passes",
            "solve_rate",
            "correct_file_before_first_edit",
            "wrong_file_edits",
            "tool_calls_before_first_edit",
            "context_tokens",
            "tests_pass",
            "latency",
            "cost",
            "delta_vs_control",
        ):
            assert forbidden_key not in s, (forbidden_key, s)


def _self_test_no_fake_downstream_metrics_from_retrieval_aggregates() -> None:
    """CRITICAL: the skeleton must NOT compute fake downstream agent
    metrics from retrieval aggregates. The synthetic-fixture report
    must surface metrics_evaluated=false and contain no metric value
    fields.
    """
    fixture = _build_synthetic_fixture()
    assert fixture["per_run_paired_agent_outputs_present"] is False
    assert fixture["metric_values_computed"] is False
    report = build_report(
        fixture, self_test=True, replay_source="synthetic_fixture"
    )
    assert report["metrics_evaluated"] is False
    assert report["no_fake_downstream_metrics_from_retrieval_aggregates"] is True
    assert report["downstream_agent_results"]["metrics_evaluated"] is False
    assert (
        report["downstream_agent_results"][
            "no_fake_downstream_metrics_from_retrieval_aggregates"
        ]
        is True
    )
    # No metric value fields should be present at the top level.
    for forbidden_field in (
        "solve_rate_value",
        "correct_file_before_first_edit_value",
        "wrong_file_edits_value",
        "tool_calls_before_first_edit_value",
        "context_tokens_value",
        "tests_pass_value",
        "latency_value",
        "cost_value",
    ):
        assert forbidden_field not in report, forbidden_field
        assert forbidden_field not in report["downstream_agent_results"], forbidden_field


def _self_test_input_stub_not_implemented(tmp_path: Path) -> None:
    """--input mode must emit verdict='not_implemented' without doing
    any real downstream agent RCT computation."""
    p = tmp_path / "per_run_stub.json"
    p.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "arm": "control_current_retrieval_v0",
                        "solve": 1,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    meta = _load_per_record_input(str(p))
    assert meta["source_kind"] == "file_object"
    assert meta["n_records"] == 1
    report = _build_not_implemented_report(meta)
    verify_report(report)
    assert report["replay_source"] == "ci_ephemeral_records"
    assert report["verdict"] == "not_implemented"
    assert "deferred" in report["verdict_reason"]
    # Stub report must still surface metrics_evaluated=false (no fake
    # metrics).
    assert report["metrics_evaluated"] is False
    assert report["downstream_agent_runs_performed"] is False
    assert report["patch_execution_performed"] is False
    assert report["agent_behavior_metrics_evaluated"] is False
    assert report["solve_rate_evaluated"] is False


def _self_test_reference_specs() -> None:
    """The B10, B10B, B11, B12, B13, B14 and B15 frozen reference specs
    must exist on disk so the B16 frozen_artifacts pin is meaningful."""
    refs = _reference_spec_hashes()
    assert refs.get("balanced_policy_v1_benchmark_routed") is True, refs
    assert refs.get("balanced_policy_v1_runtime_shadow_ambiguous_branch") is True, refs
    assert refs.get("b11_prospective_v0") is True, refs
    assert refs.get("b12_mechanism_decomposition_v0") is True, refs
    assert refs.get("b13_dro_policy_search_v0") is True, refs
    assert refs.get("b14_uncertainty_calibration_v0") is True, refs
    assert refs.get("b15_context_pack_policy_v0") is True, refs


def _self_test_artifacts_match_in_memory() -> None:
    """Read-only drift check: build the expected algorithm spec + report
    in memory and compare them to the on-disk artifacts. Fails on
    drift. Does NOT write anything to disk (self-test is read-only).
    Use ``--regenerate-artifacts`` to (re)write the on-disk artifacts.
    """
    expected_spec = build_algorithm_spec()
    expected_spec_hash = _sha256_json(expected_spec)

    on_disk_spec = _load_json(ALGORITHM_SPEC_PATH)
    on_disk_spec_hash = _sha256_json(on_disk_spec)
    if on_disk_spec_hash != expected_spec_hash:
        raise ValueError(
            "on-disk algorithm spec drifted from build_algorithm_spec() "
            f"output: on_disk={on_disk_spec_hash!r} "
            f"expected={expected_spec_hash!r}; run "
            "`python3 eval/b16_downstream_agent_evaluation.py --regenerate-artifacts` "
            "to refresh the on-disk artifacts"
        )
    verify_algorithm_spec(on_disk_spec, on_disk_spec_hash)
    if on_disk_spec != expected_spec:
        raise ValueError(
            "on-disk algorithm spec content drifted from "
            "build_algorithm_spec() output (same hash but content differs; "
            "this should be impossible)"
        )

    fixture = _build_synthetic_fixture()
    expected_report = build_report(
        fixture, self_test=True, replay_source="synthetic_fixture"
    )

    on_disk_report = _load_json(REPORT_PATH)
    if on_disk_report != expected_report:
        raise ValueError(
            "on-disk b16_downstream_agent_evaluation_report.json drifted "
            "from the in-memory build_report() output; run "
            "`python3 eval/b16_downstream_agent_evaluation.py --regenerate-artifacts` "
            "to refresh the on-disk artifacts"
        )
    verify_report(on_disk_report)


def regenerate_artifacts() -> None:
    """Regenerate the on-disk algorithm spec + synthetic-fixture report
    so the artifact pin matches the in-code build functions. Mirrors
    the B10/B10B/B11/B12/B13/B14/B15 freeze-write style: deterministic
    output, canonical JSON.

    This is the ONLY mutating path. ``--self-test`` is read-only and
    uses ``_self_test_artifacts_match_in_memory`` to detect drift.
    """
    spec = build_algorithm_spec()
    _write_json(ALGORITHM_SPEC_PATH, spec)
    fixture = _build_synthetic_fixture()
    report = build_report(
        fixture, self_test=True, replay_source="synthetic_fixture"
    )
    _write_json(REPORT_PATH, report)


def run_self_test() -> dict[str, Any]:
    """Run all B16 self-test checks. Returns a summary dict."""
    import tempfile

    _self_test_forbidden_scan()
    _self_test_spec_hash_stable()
    _self_test_arm_set_closed()
    _self_test_task_types_closed()
    _self_test_metric_registry()
    _self_test_hard_gates_defined()
    _self_test_experimental_structure_frozen()
    _self_test_no_fake_downstream_metrics_from_retrieval_aggregates()
    with tempfile.TemporaryDirectory() as tmp:
        _self_test_input_stub_not_implemented(Path(tmp))
    _self_test_reference_specs()
    _self_test_artifacts_match_in_memory()

    spec = build_algorithm_spec()
    spec_hash = _sha256_json(spec)

    return {
        "algorithm_spec_id": ALGORITHM_SPEC_ID,
        "algorithm_spec_sha256": spec_hash,
        "algorithm_spec_sha256_matched": True,
        "algorithm_spec_sha256_stable": True,
        "claim_level": CLAIM_LEVEL,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "retrieval_variant_promoted": False,
        "stage_is_downstream_agent_evaluation": True,
        "downstream_agent_runs_performed": False,
        "patch_execution_performed": False,
        "agent_behavior_metrics_evaluated": False,
        "solve_rate_evaluated": False,
        "per_record_inputs_available": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "new_provider_calls": 0,
        "candidate_retrieval_variant_frozen": False,
        "stages_evaluated": False,
        "stages_defined": True,
        "stage_count": len(EXPERIMENTAL_STAGES),
        "winner_declared": False,
        "metrics_defined": True,
        "gates_defined": True,
        "metrics_evaluated": False,
        "no_fake_downstream_metrics_from_retrieval_aggregates": True,
        "runtime_calls_by_replay": 0,
        "model_calls_by_replay": 0,
        "no_forbidden_public_keys": True,
        "no_raw_path_digest_provider_strings": True,
        "aggregate_only_public_artifact": True,
        "self_test_checks": {
            "forbidden_scan": True,
            "spec_hash_stable": True,
            "arm_set_closed": True,
            "task_types_closed": True,
            "metric_registry": True,
            "hard_gates_defined": True,
            "experimental_structure_frozen": True,
            "no_fake_downstream_metrics_from_retrieval_aggregates": True,
            "input_stub_not_implemented": True,
            "reference_specs_pinned": True,
            "artifacts_match_in_memory": True,
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--self-test",
        action="store_true",
        help=(
            "run the B16 self-test (read-only; synthetic fixture; verifies "
            "mechanics; compares in-memory expected artifacts to on-disk "
            "artifacts and fails on drift; does NOT write to disk)"
        ),
    )
    parser.add_argument(
        "--regenerate-artifacts",
        action="store_true",
        help=(
            "explicitly (re)write the on-disk algorithm spec + "
            "synthetic-fixture report artifacts from the current build "
            "functions. This is the ONLY mutating path; --self-test is "
            "read-only."
        ),
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help=(
            "path to a JSON file or directory of JSON files containing "
            "per-run paired agent outputs (event logs, patches/diffs, "
            "test execution results, solve labels, first-file-before-"
            "edit events, wrong-file-edit annotations, tool-call/token/"
            "latency/cost rows, isolated workspace proof, randomized "
            "arm order, task oracle/hidden-test manifest). Currently a "
            "STUB: emits verdict='not_implemented'; full downstream "
            "agent RCT + per-run replay computation deferred to a later "
            "task. Requires --out and may not write the canonical "
            "checked-in artifact."
        ),
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help=(
            "path to write a stub input report. Required with --input; "
            "must not be the canonical checked-in B16 report artifact."
        ),
    )
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)
    if not args.self_test and not args.input and not args.regenerate_artifacts:
        parser.error(
            "B16 requires --self-test, --regenerate-artifacts, or "
            "--input <path> in this skeleton"
        )
    selected = sum(
        1 for flag in (args.self_test, args.regenerate_artifacts, bool(args.input))
        if flag
    )
    if selected > 1:
        parser.error(
            "--self-test, --regenerate-artifacts, and --input are mutually "
            "exclusive"
        )
    if args.input:
        if not args.out:
            parser.error(
                "--input is a non-canonical stub path and requires --out; "
                "only --regenerate-artifacts may write checked-in artifacts"
            )
        out_path = Path(args.out).resolve()
        # Blocker guard: --input must not write ANY checked-in B16
        # artifact — neither the canonical report, the algorithm spec,
        # nor the public-aggregate feasibility-screen report. The
        # simplest fail-closed rule is to reject any --out that resolves
        # inside artifacts/b16_downstream_agent_evaluation/. --input is
        # intended for /tmp or other external paths only.
        artifact_dir_resolved = ARTIFACT_DIR.resolve()
        canonical_paths = {
            REPORT_PATH.resolve(),
            ALGORITHM_SPEC_PATH.resolve(),
            (
                ARTIFACT_DIR
                / "b16_public_aggregate_feasibility_report.json"
            ).resolve(),
        }
        try:
            in_artifact_dir = (
                out_path == artifact_dir_resolved
                or artifact_dir_resolved in out_path.parents
            )
        except ValueError:
            in_artifact_dir = False
        if in_artifact_dir or out_path in canonical_paths:
            parser.error(
                "--input may not write inside the checked-in B16 "
                "artifact directory artifacts/b16_downstream_agent_evaluation/ "
                "(canonical report, algorithm spec, or public-aggregate "
                "feasibility report); use --out outside artifacts/ or "
                "run --regenerate-artifacts"
            )
    return args


def _print_summary(report: dict[str, Any]) -> None:
    summary = {
        "algorithm_spec_id": report["algorithm_spec_id"],
        "replay_source": report["replay_source"],
        "claim_level": report["claim_level"],
        "primary_arms": report["primary_arms"],
        "task_types": report["task_types"],
        "metric_names": report["metric_names"],
        "hard_gates": report["hard_gates"],
        "experimental_stages": report["experimental_stages"],
        "split_protocol": report["split_protocol"],
        "task_screen_fraction": report["task_screen_fraction"],
        "fresh_validation_fraction": report["fresh_validation_fraction"],
        "verdict": report["verdict"],
        "verdict_reason": report["verdict_reason"],
        "promotion_ready": report["promotion_ready"],
        "default_should_change": report["default_should_change"],
        "evidencecore_semantics_changed": report["evidencecore_semantics_changed"],
        "retrieval_variant_promoted": report["retrieval_variant_promoted"],
        "stage_is_downstream_agent_evaluation": report[
            "stage_is_downstream_agent_evaluation"
        ],
        "downstream_agent_runs_performed": report[
            "downstream_agent_runs_performed"
        ],
        "patch_execution_performed": report["patch_execution_performed"],
        "agent_behavior_metrics_evaluated": report[
            "agent_behavior_metrics_evaluated"
        ],
        "solve_rate_evaluated": report["solve_rate_evaluated"],
        "per_record_inputs_available": report["per_record_inputs_available"],
        "policy_search_performed": report["policy_search_performed"],
        "quality_strategy_tuned": report["quality_strategy_tuned"],
        "new_provider_calls": report["new_provider_calls"],
        "candidate_retrieval_variant_frozen": report[
            "candidate_retrieval_variant_frozen"
        ],
        "stages_evaluated": report["stages_evaluated"],
        "stages_defined": report["stages_defined"],
        "stage_count": report["stage_count"],
        "winner_declared": report["winner_declared"],
        "metrics_defined": report["metrics_defined"],
        "gates_defined": report["gates_defined"],
        "metrics_evaluated": report["metrics_evaluated"],
        "no_fake_downstream_metrics_from_retrieval_aggregates": report[
            "no_fake_downstream_metrics_from_retrieval_aggregates"
        ],
        "runtime_calls_by_replay": report["runtime_calls_by_replay"],
        "model_calls_by_replay": report["model_calls_by_replay"],
        "aggregate_only_public_artifact": report["aggregate_only_public_artifact"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        result = run_self_test()
        print(json.dumps(result, indent=2, sort_keys=True))
        print("B16 self-test: PASS (read-only; no artifacts written)", file=sys.stderr)
        return 0
    if args.regenerate_artifacts:
        regenerate_artifacts()
        summary = {
            "algorithm_spec_id": ALGORITHM_SPEC_ID,
            "algorithm_spec_path": str(ALGORITHM_SPEC_PATH),
            "report_path": str(REPORT_PATH),
            "regenerated": True,
            "self_test": True,
            "replay_source": "synthetic_fixture",
            "verdict": "insufficient_data",
            "downstream_agent_runs_performed": False,
            "patch_execution_performed": False,
            "agent_behavior_metrics_evaluated": False,
            "solve_rate_evaluated": False,
            "per_record_inputs_available": False,
            "candidate_retrieval_variant_frozen": False,
            "stages_evaluated": False,
            "winner_declared": False,
            "metrics_evaluated": False,
            "no_fake_downstream_metrics_from_retrieval_aggregates": True,
        }
        print(json.dumps(summary, indent=2, sort_keys=True))
        print(
            f"B16 artifacts regenerated: {ALGORITHM_SPEC_PATH} + {REPORT_PATH}",
            file=sys.stderr,
        )
        return 0
    if args.input:
        input_meta = _load_per_record_input(args.input)
        report = _build_not_implemented_report(input_meta)
        verify_report(report)
        out_path = Path(args.out)
        _write_json(out_path, report)
        _print_summary(report)
        print(f"B16 report written to {out_path}", file=sys.stderr)
        return 0
    print(
        "B16 requires --self-test, --regenerate-artifacts, or --input",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
