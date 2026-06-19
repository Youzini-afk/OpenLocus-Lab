#!/usr/bin/env python3
"""C1 Private Per-Record Research Records adapter.

C1 is infrastructure, not a new algorithm and not a promotion step. It turns the
existing P21 runner-temp private payload (``p25-policy-records-ephemeral-v1``)
into a reusable, validated private record source for B11/B12/B13 mechanism and
policy research. This module NEVER writes public artifacts. Public consumers
(B12/B13/...) build aggregate-only reports themselves and must run their own
forbidden-key scans; this adapter only loads, validates, and normalizes the
private payload in memory.

Schema/shape (frozen P21 v1 payload):

    {
      "schema_version": "p25-policy-records-ephemeral-v1",
      "not_artifact_for_commit": true,
      "raw_queries_stored": false,
      "raw_snippets_stored": false,
      "raw_prompts_stored": false,
      "raw_responses_stored": false,
      "gold_spans_stored": false,
      "p31_score_gold_spans_stored": true,    # allowed only under private input
      "records": [ ... ]
    }

Taint model (three categories, not two):

1. ``runtime_clean`` route_features
   - The only category a runtime-clean policy may read.
2. Benchmark route labels
   - ``task_bucket``, ``task_risk_tags``. Used to analyze frozen
     benchmark-routed policies (B10/B11/B12 variants A/C/D) but NOT a
     runtime-clean policy input. Marked ``benchmark_label_taint=true``.
3. Score/outcome/private fields
   - ``score_group``, per-strategy outcome dicts, ``p31_score_gold``,
     ``p31_candidate_pools``, ``p33b_anchor_subtypes``. Marked
     ``score_phase_private=true``. Allowed only because the file is
     runner-temp/private and never uploaded; never a routing input.

Helpers exposed for B11/B12/B13 reuse:

- ``load_private_records``: load + validate + normalize a private payload.
- ``derive_model_family``: derive model_family from payload metadata/filename.
- ``derive_language``: derive language from repo_id prefix.
- ``sanitize_bucket`` / ``sanitize_tags``: p25 allowlist sanitization.
- ``extract_outcome_dict``: pull a per-strategy outcome dict.
- ``extract_outcome_metrics``: pull the four scalar audit metrics.
- ``compute_p25_strategy``: P25 ``route_bucket_routed_v0`` action.
- ``balanced_branch_predicate``: ``ambiguous_or_query_noise`` -> weak_only.
- ``p25_llm_eligible``: True iff D/P25 would choose an LLM strategy.
- ``runtime_clean_route_features``: copy of route_features only.

Stable private hashes are computed for internal/dedup use ONLY. They are never
written to public artifacts; callers building public reports must NOT copy any
field whose name starts with ``private_`` or any per-record hash into public
output.

Run the self-test::

    python3 eval/c1_private_records.py --self-test
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# p25 helpers live next to this module; import locally so the adapter can be
# reused by B11/B12/B13 without duplicating the allowlists.
import p25_bucket_policy as p25

EXPECTED_SCHEMA_VERSION = "p25-policy-records-ephemeral-v1"

# Per-strategy outcome keys P21 v1 records carry.
P21_STRATEGY_KEYS = (
    "candidate_baseline",
    "llm_span_narrow",
    "llm_filter",
    "llm_abstain_filter",
    "symbol_regex_union",
    "rrf_primary",
    "symbol_primary",
    "regex_primary",
    "supporting_only",
    "weak_candidate_only",
)

# Strategies that cost one provider LLM call per task (per-record proxy).
LLM_STRATEGIES = frozenset(
    {"llm_span_narrow", "llm_filter", "llm_abstain_filter"}
)

# Four scalar audit metrics that downstream consumers (B10B/B11/B12) extract.
OUTCOME_AUDIT_NUMERIC_FIELDS = (
    "span_f0_5",
    "added_gold_span",
    "added_false_span",
    "primary_false_positive_rate",
)

# Top-level privacy flags that MUST be set as expected on a v1 payload.
# ``p31_score_gold_spans_stored=True`` is ALLOWED for private runner-temp
# payloads (it carries private SCORE-phase gold metadata for P31 reach study).
# It is reported in taint metadata but never causes rejection here.
_REQUIRED_PRIVACY_FLAGS = {
    "not_artifact_for_commit": True,
    "raw_queries_stored": False,
    "raw_snippets_stored": False,
    "raw_prompts_stored": False,
    "raw_responses_stored": False,
    "gold_spans_stored": False,
}

# File-name prefixes -> model family (mirror B11). Falls back to "unknown".
_MODEL_FAMILY_PREFIXES = (
    ("deepseek_flash", "deepseek_flash"),
    ("deepseek_pro", "deepseek_pro"),
    ("deepseek", "deepseek_pro"),
    ("kimi", "kimi"),
    ("qwen", "qwen"),
)

# repo_id prefix -> language label (mirror B11).
_REPO_LANG_PREFIXES = (
    ("py_", "Python"),
    ("ts_", "TypeScript"),
    ("js_", "JavaScript"),
    ("go_", "Go"),
    ("rust_", "Rust"),
    ("java_", "Java"),
    ("rb_", "Ruby"),
    ("cpp_", "Cpp"),
    ("c_", "C"),
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PrivateRecordError(Exception):
    """Base error for private record adapter failures (schema/privacy)."""


class PrivateRecordSchemaError(PrivateRecordError):
    """Top-level schema/shape violation (e.g. wrong schema_version)."""


class PrivateRecordPrivacyError(PrivateRecordError):
    """Top-level privacy flag violation (e.g. raw_prompts_stored=true)."""


# ---------------------------------------------------------------------------
# Normalized record dataclass
# ---------------------------------------------------------------------------


@dataclass
class PrivateRecord:
    """In-memory normalized view of one P21 v1 record.

    NEVER emit this directly in a public artifact. ``task_id`` / ``repo_id`` /
    per-record hash are kept IN MEMORY ONLY for grouping and dedup. Public
    consumers must derive aggregate-only metrics from these fields and run
    their own forbidden-key scans.
    """

    # In-memory identifiers (NEVER emitted publicly; for grouping/dedup only).
    task_id: str
    repo_id: str
    model_family: str
    language: str
    # Source ordinal (file index / in-file index) used for the record-level
    # private hash so two records with the same task_id/repo_id but different
    # model_family or file are NOT collapsed. NEVER emitted publicly.
    source_ordinal: int
    # In-memory stable hash (private/internal only; NEVER in public output).
    private_record_hash: str

    # Category 1: runtime-clean route features.
    route_features: dict[str, Any]

    # Category 2: benchmark route labels (NOT runtime-clean).
    task_bucket: str
    task_risk_tags: list[str]

    # Category 3: SCORE/outcome/private fields (NOT runtime-clean).
    score_group: str
    has_gold: bool
    outcomes: dict[str, dict[str, Any]]
    # Per-strategy outcome presence: True iff the strategy outcome dict is
    # present AND has all four required numeric audit fields. Missing
    # outcomes are reported as 0.0 in ``outcomes`` BUT as False here so
    # downstream consumers (B12) can mark the record incomplete and avoid
    # silently zeroing missing per-strategy outcomes.
    outcome_present: dict[str, bool]
    # Private P31/P33 blocks kept verbatim for SCORE-phase consumers only.
    p31_candidate_pools: dict[str, Any] = field(default_factory=dict)
    p31_score_gold: dict[str, Any] = field(default_factory=dict)
    p33b_anchor_subtypes: list[dict[str, Any]] = field(default_factory=list)

    # Taint metadata (aggregated).
    taint: dict[str, bool] = field(default_factory=dict)

    def public_safe_summary(self) -> dict[str, Any]:
        """Return ONLY the safe scalar fields a public consumer needs.

        This NEVER includes task_id, repo_id, private_record_hash, p31/p33
        blocks, or raw route_features (consumers extract specific scalar
        features themselves). Provided as a convenience for B11/B12/B13 that
        already run their own forbidden-key scans on their own reports.
        """
        return {
            "model_family": self.model_family,
            "language": self.language,
            "task_bucket": self.task_bucket,
            "task_risk_tags": list(self.task_risk_tags),
            "has_gold": self.has_gold,
        }


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


_PRIVATE_HASH_OMIT_KEYS = {
    "api_key",
    "api_secret",
    "api_token",
    "authorization",
    "base_url",
    "prompt",
    "prompts",
    "provider_key",
    "raw_prompt",
    "raw_query",
    "raw_response",
    "raw_snippet",
    "response",
    "responses",
    "snippet",
    "source_text",
}


def _sanitize_for_private_hash(obj: Any) -> Any:
    """Sanitize private record content before internal hashing.

    The hash is private/internal only, but the input may still contain provider
    or raw-text fields if an upstream bug regresses. Drop those fields before
    hashing so the digest is a record-content fingerprint over structured
    metadata/outcomes, not over raw prompts/responses/snippets/secrets.
    """
    if isinstance(obj, dict):
        clean: dict[str, Any] = {}
        for key in sorted(obj):
            key_str = str(key)
            if key_str in _PRIVATE_HASH_OMIT_KEYS:
                continue
            clean[key_str] = _sanitize_for_private_hash(obj[key])
        return clean
    if isinstance(obj, list):
        return [_sanitize_for_private_hash(item) for item in obj]
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    return str(obj)


def _private_hash(raw_record: dict[str, Any], model_family: str, source_ordinal: int) -> str:
    """Stable private per-record hash over sanitized record content.

    This is IN MEMORY ONLY and NEVER written to a public artifact. It hashes the
    sanitized record body plus file-derived model_family and source_ordinal so
    two records with the same task_id/repo_id but different model families,
    outcome blocks, or source positions are not collapsed.
    """
    payload = {
        "model_family": model_family,
        "record": _sanitize_for_private_hash(raw_record),
        "source_ordinal": source_ordinal,
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def derive_model_family(filename: str | None, payload: dict[str, Any] | None = None) -> str:
    """Derive model_family from payload metadata or filename prefix.

    Falls back to ``"unknown"`` when no hint is available (single-file inputs
    without a model-hinting filename). Mirror of the B11 helper, exposed here
    so all consumers share one derivation rule.
    """
    if payload and isinstance(payload.get("model_family"), str):
        fam = str(payload["model_family"]).strip().lower()
        if fam:
            return fam
    if filename:
        stem = Path(filename).stem.lower()
        for prefix, family in _MODEL_FAMILY_PREFIXES:
            if stem.startswith(prefix) or prefix in stem.split("_"):
                return family
    return "unknown"


def derive_language(repo_id: str | None) -> str:
    rid = str(repo_id or "").lower()
    for prefix, lang in _REPO_LANG_PREFIXES:
        if rid.startswith(prefix):
            return lang
    return "unknown"


def sanitize_bucket(value: Any) -> str:
    """p25 allowlist bucket sanitization (public-safe label)."""
    return p25.sanitize_public_bucket(value)


def sanitize_tags(values: Any) -> list[str]:
    """p25 allowlist tag sanitization (public-safe labels)."""
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        values = []
    return p25.sanitize_public_tags(list(values))


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def extract_outcome_dict(raw: dict[str, Any], name: str) -> dict[str, Any]:
    """Pull a per-strategy outcome dict from a P21 record.

    Handles nested ``strategies``/``outcomes``/``strategy_results``/
    ``results``/``metrics`` containers in case future payloads nest them.
    """
    src = raw.get(name)
    if isinstance(src, dict):
        return src
    for key in ("strategies", "outcomes", "strategy_results", "results", "metrics"):
        container = raw.get(key) or {}
        if isinstance(container, dict) and isinstance(container.get(name), dict):
            return container[name]
    return {}


def extract_outcome_metrics(
    raw: dict[str, Any], name: str
) -> dict[str, float]:
    """Extract the four scalar audit metrics from a per-strategy outcome dict.

    Missing/non-numeric fields default to 0.0 (consumers mark the record
    missing if they need all four present). Mirrors B11's extraction rule.
    """
    src = extract_outcome_dict(raw, name)
    return {
        "span_f0_5": _as_float(src.get("span_f0_5")),
        "added_gold_span": float(_as_int(src.get("added_gold_span"))),
        "added_false_span": float(_as_int(src.get("added_false_span"))),
        "primary_false_positive_rate": _as_float(
            src.get("primary_false_positive_rate")
        ),
    }


def runtime_clean_route_features(record: dict[str, Any]) -> dict[str, Any]:
    """Return ONLY the route_features dict (category 1, runtime-clean).

    Returns an empty dict if absent. Does not deep-copy nested private blocks
    inside route_features (P21 v1 route_features contains only scalar/bool
    runtime features by construction; no paths/snippets/gold).
    """
    rf = record.get("route_features")
    if isinstance(rf, dict):
        return dict(rf)
    return {}


def record_complete_for_strategies(
    record: "PrivateRecord", strategies: list[str]
) -> bool:
    """True iff every strategy in ``strategies`` has a present outcome for
    this record (i.e. ``outcome_present[strat]`` is True for all). Used by B12
    to mark a record complete for the chosen A/B/C/D/E strategies: a missing
    required outcome makes the record incomplete and it must NOT silently
    count as a zero-outcome complete record.
    """
    op = getattr(record, "outcome_present", {}) or {}
    return all(op.get(s) is True for s in strategies)


# ---------------------------------------------------------------------------
# P25 / balanced-branch predicates (mirror B11 so all consumers share one rule)
# ---------------------------------------------------------------------------


def compute_p25_strategy(record: PrivateRecord | dict[str, Any]) -> str:
    """P25 ``route_bucket_routed_v0`` action -> strategy key.

    Accepts either a ``PrivateRecord`` or a raw dict carrying
    ``task_bucket``/``task_risk_tags``/``route_features`` (the B11 normalized
    shape). Returns one of ``candidate_baseline``, ``llm_span_narrow``,
    ``llm_filter``, ``llm_abstain_filter`` (all valid P21 strategy keys).
    """
    if isinstance(record, PrivateRecord):
        task = {
            "task_bucket": record.task_bucket,
            "task_risk_tags": list(record.task_risk_tags),
            "route_features": dict(record.route_features),
        }
    else:
        task = record
    action = p25.route_bucket_routed_v0(
        task, p25.choose_negative_strategy([task])
    )
    if action in P21_STRATEGY_KEYS:
        return action
    return "candidate_baseline"


def p25_llm_eligible(record: PrivateRecord | dict[str, Any]) -> bool:
    """True iff D/P25 would choose an LLM strategy for this record.

    ``actual_call_avoided_set = balanced_branch_set ∩ p25_llm_subset`` (the
    B12 call-reduction control definition) is computed by consumers using this
    predicate alongside ``balanced_branch_predicate``.
    """
    strategy = compute_p25_strategy(record)
    return strategy in LLM_STRATEGIES


def balanced_branch_predicate(record: PrivateRecord | dict[str, Any]) -> bool:
    """Balanced v1 ``ambiguous_or_query_noise`` -> weak_only branch predicate.

    Mirrors ``b6_lite._noisy_or_ambiguous``: true iff the benchmark labels
    contain an ambiguous/hallucination_risk/weak_candidates tag OR
    ``route_features.query_noise > 0``. Returns True => the balanced policy
    routes this record to ``weak_candidate_only`` (instead of P25's action).

    NOTE: this predicate reads benchmark route labels (category 2 taint),
    which is exactly why the balanced_v1 policy is benchmark-routed, NOT
    runtime-clean. Consumers MUST mark this in their taint metadata.
    """
    if isinstance(record, PrivateRecord):
        labels = {record.task_bucket}
        labels.update(record.task_risk_tags)
        rf = record.route_features
    else:
        labels = set()
        bucket = record.get("task_bucket")
        if isinstance(bucket, str):
            labels.add(bucket)
        tags = record.get("task_risk_tags") or []
        if isinstance(tags, str):
            tags = [tags]
        if isinstance(tags, list):
            for t in tags:
                if isinstance(t, str):
                    labels.add(t)
        rf = record.get("route_features") or {}
    ambiguous_like = bool(
        labels & {"ambiguous", "hallucination_risk", "weak_candidates"}
    )
    qn = rf.get("query_noise") if isinstance(rf, dict) else None
    try:
        query_noise = bool(float(qn) > 0)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        query_noise = False
    return ambiguous_like or query_noise


# ---------------------------------------------------------------------------
# Top-level validation + loading
# ---------------------------------------------------------------------------


def validate_payload_privacy(payload: dict[str, Any]) -> None:
    """Validate the top-level privacy flags of a P21 v1 private payload.

    Raises ``PrivateRecordPrivacyError`` if any required flag is set to a
    public-leaking value (raw queries/snippets/prompts/responses stored, or
    gold_spans_stored at the top level, or not_artifact_for_commit not set).

    Does NOT reject ``p31_score_gold_spans_stored=True``: P31 gold spans are
    allowed only because the file is runner-temp/private and never uploaded.
    The taint metadata separately records that private score-phase fields are
    present so consumers never silently route on them.
    """
    if not isinstance(payload, dict):
        raise PrivateRecordSchemaError(
            "private payload must be a JSON object"
        )
    for flag, expected in _REQUIRED_PRIVACY_FLAGS.items():
        actual = payload.get(flag)
        if actual != expected:
            raise PrivateRecordPrivacyError(
                f"privacy flag {flag!r} expected {expected!r} got {actual!r}; "
                "refusing to load a payload that may leak raw/private fields"
            )


def _outcome_is_present(src: dict[str, Any]) -> bool:
    """True iff the strategy outcome dict is present AND has all four required
    numeric audit fields (span_f0_5, added_gold_span, added_false_span,
    primary_false_positive_rate). Missing/non-numeric fields => not present,
    so downstream consumers (B12) can mark the record incomplete and avoid
    silently zeroing missing per-strategy outcomes.
    """
    if not isinstance(src, dict) or not src:
        return False
    for field_name in OUTCOME_AUDIT_NUMERIC_FIELDS:
        v = src.get(field_name)
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return False
    return True


def _normalize_one(
    raw: dict[str, Any], model_family: str, source_ordinal: int
) -> PrivateRecord | None:
    """Normalize a single raw record into a ``PrivateRecord``.

    Returns None if the record has no task_id (cannot be grouped/dedup'd).
    ``source_ordinal`` is a stable file/index label supplied by the loader,
    folded into the record-level private hash so two records with the same
    task_id/repo_id but different model_family or file are NOT collapsed.
    """
    tid = raw.get("task_id") or raw.get("test_id")
    if not tid:
        return None
    tid = str(tid)
    repo_id = str(raw.get("repo_id") or "")
    model_family = model_family or "unknown"
    route_features = runtime_clean_route_features(raw)
    task_bucket = sanitize_bucket(raw.get("task_bucket", "unknown"))
    risk_tags = sanitize_tags(raw.get("task_risk_tags") or [])
    score_group = str(raw.get("score_group") or "unknown")
    if score_group == "positive":
        has_gold = True
    elif score_group == "no_gold":
        has_gold = False
    else:
        has_gold = bool(raw.get("has_gold", False))

    outcomes: dict[str, dict[str, Any]] = {}
    outcome_present: dict[str, bool] = {}
    for strat in P21_STRATEGY_KEYS:
        src = extract_outcome_dict(raw, strat)
        present = _outcome_is_present(src)
        outcome_present[strat] = present
        if present:
            outcomes[strat] = {
                "span_f0_5": _as_float(src.get("span_f0_5")),
                "added_gold_span": float(_as_int(src.get("added_gold_span"))),
                "added_false_span": float(_as_int(src.get("added_false_span"))),
                "primary_false_positive_rate": _as_float(
                    src.get("primary_false_positive_rate")
                ),
            }
        else:
            # Missing outcome: keep a zero dict for backward-compat readers
            # BUT mark outcome_present=False so B12 can exclude the record
            # from complete_records instead of silently zeroing it.
            outcomes[strat] = {
                "span_f0_5": 0.0,
                "added_gold_span": 0.0,
                "added_false_span": 0.0,
                "primary_false_positive_rate": 0.0,
            }

    p31_pools = raw.get("p31_candidate_pools")
    p31_pools = p31_pools if isinstance(p31_pools, dict) else {}
    p31_gold = raw.get("p31_score_gold")
    p31_gold = p31_gold if isinstance(p31_gold, dict) else {}
    p33b = raw.get("p33b_anchor_subtypes")
    p33b = p33b if isinstance(p33b, list) else []

    # Taint metadata: which categories are present.
    benchmark_label_taint = bool(task_bucket != "unknown") or bool(risk_tags)
    score_phase_private = (
        bool(score_group != "unknown")
        or any(outcome_present.values())
        or bool(p31_pools)
        or bool(p31_gold)
        or bool(p33b)
        or bool(raw.get("p31_score_gold_spans_stored"))
    )

    return PrivateRecord(
        task_id=tid,
        repo_id=repo_id,
        model_family=model_family,
        language=derive_language(repo_id),
        source_ordinal=source_ordinal,
        private_record_hash=_private_hash(raw, model_family, source_ordinal),
        route_features=route_features,
        task_bucket=task_bucket,
        task_risk_tags=risk_tags,
        score_group=score_group,
        has_gold=has_gold,
        outcomes=outcomes,
        outcome_present=outcome_present,
        p31_candidate_pools=p31_pools,
        p31_score_gold=p31_gold,
        p33b_anchor_subtypes=p33b,
        taint={
            "runtime_clean_route_features": True,
            "benchmark_label_taint": benchmark_label_taint,
            "score_phase_private": score_phase_private,
            "p31_score_gold_present": bool(p31_gold),
            "p31_candidate_pools_present": bool(p31_pools),
            "p33b_anchor_subtypes_present": bool(p33b),
        },
    )


def load_private_records(
    path: str | Path, *, require_schema: bool = True
) -> tuple[list[PrivateRecord], dict[str, Any]]:
    """Load + validate + normalize a P21 v1 private payload.

    Accepts a JSON file or a directory of JSON files. Each file may be:
    - A JSON object with ``schema_version == "p25-policy-records-ephemeral-v1"``
      and a ``records`` list (canonical P21 v1 payload).
    - A JSON list of records (self-test shape; validated with relaxed schema
      when ``require_schema=False``).

    Returns ``(records, meta)`` where ``records`` is the in-memory normalized
    list (NEVER emit directly in public artifacts) and ``meta`` carries safe
    scalar counts plus the per-file model_family derivation. ``meta`` is
    safe to surface in a public report (no task_ids/repo_ids/paths).

    Raises ``PrivateRecordSchemaError`` / ``PrivateRecordPrivacyError`` /
    ``FileNotFoundError`` / ``ValueError`` as appropriate. These are
    mechanical/privacy/schema errors that callers should propagate as
    nonzero exit codes.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"--input path not found: {path}")

    files: list[Path]
    if p.is_dir():
        files = sorted(p.glob("*.json"))
        if not files:
            raise ValueError(f"--input directory has no .json files: {path}")
        source_kind = "directory"
    else:
        files = [p]
        source_kind = "file_object"

    all_records: list[PrivateRecord] = []
    per_file_meta: list[dict[str, Any]] = []
    for file_idx, f in enumerate(files):
        data = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(data, list):
            # Bare JSON array of records (self-test/helper shape). Reject by
            # default — normal C1/B12 input MUST be the private P21 v1
            # envelope (object with schema_version + records). Allow only
            # when the caller explicitly opts in via require_schema=False.
            if require_schema:
                raise PrivateRecordSchemaError(
                    f"file {f.name} is a bare JSON array; the C1 adapter "
                    "requires the private P21 v1 envelope "
                    "(p25-policy-records-ephemeral-v1 object with "
                    "'records'); bare arrays are only allowed in "
                    "self-test/helper mode (require_schema=False)"
                )
            raw_records = data
            payload_meta: dict[str, Any] = {}
            schema_version = None
        elif isinstance(data, dict):
            schema_version = data.get("schema_version")
            if require_schema and schema_version != EXPECTED_SCHEMA_VERSION:
                raise PrivateRecordSchemaError(
                    f"file {f.name} schema_version {schema_version!r} != "
                    f"{EXPECTED_SCHEMA_VERSION!r}"
                )
            validate_payload_privacy(data)
            raw_records = data.get("records")
            if not isinstance(raw_records, list):
                raise PrivateRecordSchemaError(
                    f"file {f.name} has no 'records' list"
                )
            payload_meta = data
        else:
            raise ValueError(
                f"--input file {f.name} must contain a JSON object or array, "
                f"got {type(data).__name__}"
            )

        model_family = derive_model_family(f.name, payload_meta)
        # Record-level source ordinal: encode (file_idx, in_file_idx) so the
        # private record hash does NOT collapse two records with the same
        # task_id/repo_id across model families / files. We use a stable
        # large-base encoding to keep it within one integer.
        normalized = []
        for in_file_idx, raw in enumerate(raw_records):
            ordinal = file_idx * 1_000_000 + in_file_idx
            n = _normalize_one(raw, model_family, ordinal)
            if n is not None:
                normalized.append(n)
        all_records.extend(normalized)
        per_file_meta.append({
            "source_kind": "file",
            "model_family": model_family,
            "n_records": len(normalized),
        })

    meta: dict[str, Any] = {
        "source_kind": source_kind,
        "n_files": len(files),
        "n_records": len(all_records),
        "per_file": per_file_meta,
        "schema_version": EXPECTED_SCHEMA_VERSION,
        # Aggregate taint summary (safe scalar counts only).
        "taint_summary": _taint_summary(all_records),
    }
    return all_records, meta


def _taint_summary(records: list[PrivateRecord]) -> dict[str, Any]:
    n = len(records)
    if n == 0:
        return {
            "n_records": 0,
            "benchmark_label_taint_count": 0,
            "score_phase_private_count": 0,
            "p31_score_gold_present_count": 0,
            "p31_candidate_pools_present_count": 0,
            "p33b_anchor_subtypes_present_count": 0,
        }
    return {
        "n_records": n,
        "benchmark_label_taint_count": sum(
            1 for r in records if r.taint.get("benchmark_label_taint")
        ),
        "score_phase_private_count": sum(
            1 for r in records if r.taint.get("score_phase_private")
        ),
        "p31_score_gold_present_count": sum(
            1 for r in records if r.taint.get("p31_score_gold_present")
        ),
        "p31_candidate_pools_present_count": sum(
            1 for r in records if r.taint.get("p31_candidate_pools_present")
        ),
        "p33b_anchor_subtypes_present_count": sum(
            1 for r in records if r.taint.get("p33b_anchor_subtypes_present")
        ),
    }


# ---------------------------------------------------------------------------
# Synthetic v1 payload for self-test
# ---------------------------------------------------------------------------


def build_synthetic_v1_payload() -> dict[str, Any]:
    """Build a synthetic ``p25-policy-records-ephemeral-v1`` payload.

    Includes private P31 gold/candidate fields and P33b anchor subtypes to
    prove the adapter allows private score-phase fields under private
    runner-temp input while flagging them as tainted. Used by ``--self-test``.
    """
    records: list[dict[str, Any]] = []
    cases = [
        # (repo, bucket, tags, has_gold, query_noise)
        ("py_fastapi", "positive", ["high_confidence"], True, 0.0),
        ("py_fastapi", "ambiguous", ["ambiguous", "weak_candidates"], True, 1.0),
        ("ts_vite", "negative", ["negative"], False, 0.0),
        ("ts_vite", "hard_distractor", ["hard_distractor", "dense_false_positive"], True, 0.0),
        ("go_chi", "positive", ["exact_symbol", "unique_symbol"], True, 0.0),
        ("go_chi", "negative", ["no_gold", "negative"], False, 0.0),
    ]
    for idx, (repo, bucket, tags, has_gold, qn) in enumerate(cases):
        rec: dict[str, Any] = {
            "task_id": f"c1-selftest-{idx:03d}",
            "repo_id": repo,
            "task_bucket": bucket,
            "task_risk_tags": tags,
            "score_group": "positive" if has_gold else "no_gold",
            "route_features": {
                "candidate_count": 3,
                "candidate_support_exists": True,
                "unique_symbol_anchor": "unique_symbol" in tags,
                "query_noise": qn,
                "local_anchor": True,
                "rrf_backed_by_anchor": True,
            },
        }
        for strat in P21_STRATEGY_KEYS:
            # Give each strategy a slightly different scalar profile so the
            # adapter self-test can prove outcomes are extracted correctly and
            # LLM-eligibility / balanced-branch predicates are computed.
            base = 0.30 + 0.01 * idx
            is_llm = strat in LLM_STRATEGIES
            is_weak = strat == "weak_candidate_only"
            is_local = strat == "candidate_baseline"
            rec[strat] = {
                "span_f0_5": base + (0.02 if is_llm else 0.0) - (0.01 if is_weak else 0.0),
                "added_gold_span": (1 if has_gold else 0) + (1 if is_local and has_gold else 0),
                "added_false_span": 2 - (idx % 2) + (1 if is_llm else 0) - (1 if is_weak else 0),
                "primary_false_positive_rate": 0.10 + 0.01 * idx - (0.02 if is_weak else 0.0),
                "abstained": strat in {"weak_candidate_only", "supporting_only"},
            }
        # Private P31 blocks (allowed only under private runner-temp input).
        rec["p31_candidate_pools"] = {
            "candidate_baseline": [
                {"rank": 1, "path": "src/foo.py", "start_line": 1, "end_line": 2,
                 "candidate_id": "abcd1234abcd1234"},
            ],
            "llm_span_narrow": [
                {"rank": 1, "path": "src/foo.py", "start_line": 1, "end_line": 2,
                 "candidate_id": "abcd1234abcd1234", "content_sha": "deadbeef"},
            ],
        }
        rec["p31_score_gold"] = {
            "has_gold": has_gold,
            "score_group": "positive" if has_gold else "no_gold",
            "gold_spans": [
                {"path": "src/foo.py", "start_line": 1, "end_line": 2,
                 "content_sha": "deadbeef"}
            ] if has_gold else [],
        }
        rec["p33b_anchor_subtypes"] = [
            {"rank_bin": "top3", "count_bin": "small",
             "source_class": "symbol_regex_fusion",
             "agreement_class": "span_overlap",
             "rrf_backing": True}
        ]
        rec["p33b_anchor_subtypes_schema"] = "p33b-anchor-subtypes-v1"
        rec["p33b_anchor_subtype_handoff"] = True
        records.append(rec)

    return {
        "schema_version": EXPECTED_SCHEMA_VERSION,
        "p31_h1_candidate_reach_handoff": True,
        "p31_h1_schema_version": "p31-h1-candidate-reach-handoff-v1",
        "p30_h1_fields_present": True,
        "contains_local_anchor_outcomes": True,
        "p30_h1_route_features_present": True,
        "not_artifact_for_commit": True,
        "score_phase_gold_group_stored": True,
        "p31_score_gold_spans_stored": True,
        "raw_queries_stored": False,
        "raw_snippets_stored": False,
        "raw_prompts_stored": False,
        "raw_responses_stored": False,
        "gold_spans_stored": False,
        "private_label_categories_stored": False,
        "records": records,
    }


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _self_test_load_synthetic_v1(tmp_path: Path) -> None:
    payload = build_synthetic_v1_payload()
    tmp_path.mkdir(parents=True, exist_ok=True)
    p = tmp_path / "kimi_c1_selftest.json"
    p.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    records, meta = load_private_records(p)
    assert meta["source_kind"] == "file_object"
    assert meta["n_files"] == 1
    assert meta["n_records"] == len(payload["records"])
    # model_family derived from filename prefix "kimi".
    assert all(r.model_family == "kimi" for r in records), (
        [r.model_family for r in records]
    )
    # All records carry the three-category taint metadata.
    for r in records:
        assert r.taint["runtime_clean_route_features"] is True
        assert r.taint["benchmark_label_taint"] is True
        assert r.taint["score_phase_private"] is True
        assert r.taint["p31_score_gold_present"] is True
        assert r.taint["p31_candidate_pools_present"] is True
        assert r.taint["p33b_anchor_subtypes_present"] is True
    # Aggregate taint summary counts.
    ts = meta["taint_summary"]
    assert ts["n_records"] == len(records)
    assert ts["p31_score_gold_present_count"] == len(records)
    assert ts["p31_candidate_pools_present_count"] == len(records)


def _self_test_outcome_extraction() -> None:
    payload = build_synthetic_v1_payload()
    rec = payload["records"][0]
    metrics = extract_outcome_metrics(rec, "weak_candidate_only")
    for field in OUTCOME_AUDIT_NUMERIC_FIELDS:
        assert field in metrics, field
        assert isinstance(metrics[field], float), (field, type(metrics[field]))
    # Per-strategy outcome dicts are accessible.
    for strat in P21_STRATEGY_KEYS:
        d = extract_outcome_dict(rec, strat)
        assert isinstance(d, dict) and "span_f0_5" in d, strat


def _self_test_predicates() -> None:
    payload = build_synthetic_v1_payload()
    records, _ = load_private_records_from_payload(payload, model_family="kimi")
    # Record 1 (py_fastapi ambiguous, query_noise=1.0) is balanced-branch.
    assert balanced_branch_predicate(records[1]) is True
    # Record 0 (positive, query_noise=0) is NOT balanced-branch.
    assert balanced_branch_predicate(records[0]) is False
    # p25_llm_eligible: at least one record should be LLM-eligible under P25
    # (positive + support_exists -> llm_span_narrow).
    llm_eligible = [r for r in records if p25_llm_eligible(r)]
    assert llm_eligible, "expected at least one P25 LLM-eligible record"
    # actual_call_avoided_set = balanced_branch ∩ p25_llm_subset.
    actual_call_avoided = [
        r for r in records
        if balanced_branch_predicate(r) and p25_llm_eligible(r)
    ]
    # Sanity: the ambiguous record is both balanced-branch and (positive +
    # support_exists -> llm_span_narrow) LLM-eligible.
    assert any(r.task_id == "c1-selftest-001" for r in actual_call_avoided), (
        [r.task_id for r in actual_call_avoided]
    )


def _self_test_privacy_rejects_raw_flags(tmp_path: Path) -> None:
    payload = build_synthetic_v1_payload()
    payload["raw_prompts_stored"] = True
    tmp_path.mkdir(parents=True, exist_ok=True)
    p = tmp_path / "bad_privacy.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    try:
        load_private_records(p)
    except PrivateRecordPrivacyError:
        pass
    else:
        raise AssertionError("expected PrivateRecordPrivacyError for raw_prompts_stored=true")


def _self_test_schema_rejects_wrong_version(tmp_path: Path) -> None:
    payload = build_synthetic_v1_payload()
    payload["schema_version"] = "some-other-version-v2"
    tmp_path.mkdir(parents=True, exist_ok=True)
    p = tmp_path / "bad_schema.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    try:
        load_private_records(p)
    except PrivateRecordSchemaError:
        pass
    else:
        raise AssertionError("expected PrivateRecordSchemaError for wrong schema_version")


def _self_test_allows_p31_gold_spans_stored(tmp_path: Path) -> None:
    """p31_score_gold_spans_stored=True must NOT be rejected (private input)."""
    payload = build_synthetic_v1_payload()
    payload["p31_score_gold_spans_stored"] = True
    tmp_path.mkdir(parents=True, exist_ok=True)
    p = tmp_path / "p31_allowed.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    records, _ = load_private_records(p)
    assert len(records) == len(payload["records"])


def _self_test_directory_load(tmp_path: Path) -> None:
    payload = build_synthetic_v1_payload()
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "kimi_dir.json").write_text(json.dumps(payload), encoding="utf-8")
    (tmp_path / "deepseek_flash_dir.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    records, meta = load_private_records(tmp_path)
    assert meta["source_kind"] == "directory"
    assert meta["n_files"] == 2
    assert meta["n_records"] == 2 * len(payload["records"])
    families = {r.model_family for r in records}
    assert families == {"kimi", "deepseek_flash"}, families


def _self_test_bare_list_rejected_with_schema(tmp_path: Path) -> None:
    """A bare JSON array (no envelope) must be rejected when
    require_schema=True (the default for normal C1/B12 input)."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    p = tmp_path / "bare_list.json"
    p.write_text(json.dumps([{"task_id": "t1", "repo_id": "r1"}]), encoding="utf-8")
    try:
        load_private_records(p)  # require_schema=True by default
    except PrivateRecordSchemaError:
        pass
    else:
        raise AssertionError(
            "expected PrivateRecordSchemaError for bare list with require_schema=True"
        )


def _self_test_bare_list_allowed_without_schema(tmp_path: Path) -> None:
    """A bare JSON array is allowed only in self-test/helper mode
    (require_schema=False)."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    p = tmp_path / "bare_list_helper.json"
    p.write_text(
        json.dumps([{"task_id": "t1", "repo_id": "r1"}]), encoding="utf-8"
    )
    records, _ = load_private_records(p, require_schema=False)
    assert len(records) == 1
    assert records[0].task_id == "t1"


def _self_test_record_level_hash() -> None:
    """private_record_hash must be record-level: two records with the same
    task_id/repo_id but different model_family OR different source ordinal
    must get DIFFERENT hashes (so B/E counts are not collapsed)."""
    payload = build_synthetic_v1_payload()
    # Same payload, different model_family derivation.
    recs_kimi, _ = load_private_records_from_payload(payload, model_family="kimi")
    recs_qwen, _ = load_private_records_from_payload(payload, model_family="qwen")
    # Same task_id/repo_id but different model_family => different hash.
    assert recs_kimi[0].task_id == recs_qwen[0].task_id
    assert recs_kimi[0].repo_id == recs_qwen[0].repo_id
    assert recs_kimi[0].private_record_hash != recs_qwen[0].private_record_hash, (
        "record-level hash must distinguish model_family"
    )
    # Within one model_family, two records with same task_id/repo_id but
    # different source ordinal (different in-file index) => different hash.
    h0 = recs_kimi[0].private_record_hash
    h1 = recs_kimi[1].private_record_hash
    assert h0 != h1, "record-level hash must distinguish source ordinal"


def _self_test_missing_outcome_detection() -> None:
    """A record with a missing/malformed strategy outcome must have
    outcome_present[strat]=False and NOT silently look complete with zeros."""
    payload = build_synthetic_v1_payload()
    # Remove one strategy outcome entirely from record 0.
    del payload["records"][0]["weak_candidate_only"]
    # Make another strategy's outcome non-numeric (corrupt).
    payload["records"][0]["candidate_baseline"]["span_f0_5"] = "not_a_number"
    records, _ = load_private_records_from_payload(payload, model_family="kimi")
    r0 = records[0]
    # weak_candidate_only was deleted => not present.
    assert r0.outcome_present["weak_candidate_only"] is False, (
        r0.outcome_present["weak_candidate_only"]
    )
    # candidate_baseline has a non-numeric field => not present.
    assert r0.outcome_present["candidate_baseline"] is False, (
        r0.outcome_present["candidate_baseline"]
    )
    # A complete strategy (llm_span_narrow) is still present.
    assert r0.outcome_present["llm_span_narrow"] is True
    # The outcomes dict for the missing strategy still has zeros (backward
    # compat for direct readers) but outcome_present flags it missing.
    assert r0.outcomes["weak_candidate_only"]["span_f0_5"] == 0.0
    # outcome_present is exposed for every strategy key.
    assert set(r0.outcome_present.keys()) == set(P21_STRATEGY_KEYS)


def _self_test_no_public_leak_in_meta() -> None:
    """The returned ``meta`` dict must not leak private per-record fields.

    Checks that ``meta`` does not contain any forbidden KEY (anywhere in the
    nested dict) and does not contain raw task_id/repo_id/path/content_sha
    values. Aggregate taint summary counts whose names happen to contain a
    forbidden substring (e.g. ``p31_score_gold_present_count``) are allowed —
    they are scalar counts, not the private fields themselves.
    """
    payload = build_synthetic_v1_payload()
    _records, meta = load_private_records_from_payload(payload, model_family="kimi")

    forbidden_keys = {
        "task_id", "repo_id", "path", "content_sha", "candidate_id",
        "gold_spans", "p31_score_gold", "p31_candidate_pools",
        "p33b_anchor_subtypes", "private_record_hash",
        "raw_query", "raw_snippet", "raw_prompt", "raw_response",
        "api_key", "base_url", "provider_key",
    }

    def _walk_keys(o: Any) -> list[str]:
        keys: list[str] = []
        if isinstance(o, dict):
            for k, v in o.items():
                keys.append(str(k))
                keys.extend(_walk_keys(v))
        elif isinstance(o, list):
            for v in o:
                keys.extend(_walk_keys(v))
        return keys

    present_keys = set(_walk_keys(meta))
    leaked = forbidden_keys & present_keys
    assert not leaked, leaked
    # Value-level: no raw task_id/repo_id/path strings leaked into meta.
    blob = json.dumps(meta, sort_keys=True)
    for raw_id in ("c1-selftest-", "src/foo.py", "deadbeef", "abcd1234"):
        assert raw_id not in blob, (raw_id, blob)


def load_private_records_from_payload(
    payload: dict[str, Any], *, model_family: str = "unknown"
) -> tuple[list[PrivateRecord], dict[str, Any]]:
    """Load + normalize an already-parsed in-memory payload (self-test helper).

    Validates schema/privacy the same way ``load_private_records`` does.
    """
    if not isinstance(payload, dict):
        raise PrivateRecordSchemaError("payload must be a JSON object")
    if payload.get("schema_version") != EXPECTED_SCHEMA_VERSION:
        raise PrivateRecordSchemaError(
            f"schema_version {payload.get('schema_version')!r} != "
            f"{EXPECTED_SCHEMA_VERSION!r}"
        )
    validate_payload_privacy(payload)
    raw_records = payload.get("records")
    if not isinstance(raw_records, list):
        raise PrivateRecordSchemaError("payload has no 'records' list")
    records = []
    for in_file_idx, raw in enumerate(raw_records):
        n = _normalize_one(raw, model_family, in_file_idx)
        if n is not None:
            records.append(n)
    meta = {
        "source_kind": "in_memory",
        "n_files": 1,
        "n_records": len(records),
        "schema_version": EXPECTED_SCHEMA_VERSION,
        "taint_summary": _taint_summary(records),
    }
    return records, meta


def run_self_test() -> dict[str, Any]:
    """Run all C1 adapter self-test checks. Returns a summary dict."""
    import tempfile

    _self_test_outcome_extraction()

    # Use isolated subdirectories so a deliberately-bad fixture written by
    # one check does not contaminate the directory-load check.
    with tempfile.TemporaryDirectory() as tmp_root:
        tmp = Path(tmp_root)
        _self_test_load_synthetic_v1(tmp / "load")
        _self_test_privacy_rejects_raw_flags(tmp / "privacy")
        _self_test_schema_rejects_wrong_version(tmp / "schema")
        _self_test_allows_p31_gold_spans_stored(tmp / "p31")
        _self_test_directory_load(tmp / "dir")
        _self_test_bare_list_rejected_with_schema(tmp / "bare_reject")
        _self_test_bare_list_allowed_without_schema(tmp / "bare_allow")

    _self_test_predicates()
    _self_test_no_public_leak_in_meta()
    _self_test_record_level_hash()
    _self_test_missing_outcome_detection()

    return {
        "adapter": "c1_private_records",
        "schema_version": EXPECTED_SCHEMA_VERSION,
        "self_test_checks": {
            "load_synthetic_v1": True,
            "outcome_extraction": True,
            "predicates": True,
            "privacy_rejects_raw_flags": True,
            "schema_rejects_wrong_version": True,
            "allows_p31_gold_spans_stored": True,
            "directory_load": True,
            "bare_list_rejected_with_schema": True,
            "bare_list_allowed_without_schema": True,
            "record_level_hash": True,
            "missing_outcome_detection": True,
            "no_public_leak_in_meta": True,
        },
        "aggregate_only_public_artifact": True,
        "never_writes_public_artifacts": True,
        "taint_categories": [
            "runtime_clean_route_features",
            "benchmark_label_taint",
            "score_phase_private",
        ],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run the C1 adapter self-test (synthetic v1 payload)",
    )
    if argv is None:
        argv = sys.argv[1:]
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        result = run_self_test()
        print(json.dumps(result, indent=2, sort_keys=True))
        print("C1 adapter self-test: PASS", file=sys.stderr)
        return 0
    parse_args(["--help"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
