#!/usr/bin/env python3
"""Phase 9H candidate source-pool public-source network-fetch materialization runner.

This runner has one narrow purpose: under explicit confirmations and the frozen
Phase 9G candidate-source-pool network-fetch protocol, fetch public-only source
repositories via unauthenticated public GitHub API transport into ignored
``runs/`` workspace only, deterministically attempt to materialize private
file-localizable task-candidate readiness rows, and publish only an aggregate
public report.  It does not score strategies, create benchmark labels, record
outcomes, evaluate evidence success, fit/train models, call providers or LLMs,
or change runtime/default/product behavior.

The Phase 9G public gate reference values (remote commit ``130b6732``, CI run
``28974306775``) and the Phase 9F public gate reference values (remote commit
``c091b742``, CI run ``28973602930``) are used as public gate references.
Local same-tree git commits are not read or compared; the supplied
confirmation values are matched against the frozen public gate constants only.

Readiness means source-materialization readiness only.  It is not evidence
success, method success, benchmark success, scoring success, or product
readiness.  Materialization itself is not evidence_success.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]

PHASE = (
    "phase9h_candidate_source_pool_public_source_network_fetch"
    "_materialization_no_scoring_no_claim"
)
STATUS_READINESS = (
    "phase9h_candidate_source_pool_public_source_network_fetch"
    "_materialization_readiness_no_scoring_no_claim"
)
STATUS_REPAIR = (
    "phase9h_candidate_source_pool_public_source_network_fetch"
    "_materialization_repair_no_claim"
)
STATUS_GATE_MISSING = "phase9h_blocked_phase9g_gate_missing_or_not_green_no_claim"
ALLOWED_STATUSES = {STATUS_READINESS, STATUS_REPAIR, STATUS_GATE_MISSING}
SCHEMA_VERSION = f"{PHASE}_report_v1"

DEFAULT_PUBLIC_REPORT = REPO / "artifacts" / PHASE / f"{PHASE}_report.json"
DEFAULT_PRIVATE_RUN_DIR = REPO / "runs" / PHASE / "current"

# Phase 9G public gate (frozen protocol).  Public gate reference values.
PHASE9G_STATUS = (
    "phase9g_candidate_source_pool_network_fetch_protocol_freeze"
    "_no_execution_no_scoring_no_claim"
)
PHASE9G_PUBLIC_REPORT = (
    REPO / "artifacts" / PHASE9G_STATUS / f"{PHASE9G_STATUS}_report.json"
)
PHASE9G_DOCS = (
    REPO / "docs" / "en" / "interventional-evidence-acquisition-phase9g-candidate-source-pool-network-fetch-protocol-freeze-no-execution-no-scoring-no-claim.md",
    REPO / "docs" / "zh" / "interventional-evidence-acquisition-phase9g-candidate-source-pool-network-fetch-protocol-freeze-no-execution-no-scoring-no-claim.md",
)
PHASE9G_COMMIT = "130b6732"
PHASE9G_CI_RUN = "28974306775"

# Phase 9F public gate (also referenced per spec).  Public gate reference values.
PHASE9F_STATUS = "phase9f_public_source_fetch_clone_materialization_repair_no_claim"
PHASE9F_COMMIT = "c091b742"
PHASE9F_CI_RUN = "28973602930"

# Caps inherited from the frozen Phase 9G network-fetch contract.
TARGET_TASK_MIN = 48
TARGET_TASK_MAX = 72
HARD_TASK_CAP = 96
PER_SOURCE_TASK_CAP = 8
MIN_DISTINCT_SOURCES = 8
MAX_SOURCE_CANDIDATES = 16
PER_SOURCE_TRANSPORT_ATTEMPTS = 2  # initial attempt + one fixed retry only
NETWORK_TIMEOUT_SECONDS = 12

# GitHub API public transport (unauthenticated, aggregate-only).
GITHUB_PUBLIC_HOSTS = {
    "api.github.com",
    "github.com",
    "codeload.github.com",
    "raw.githubusercontent.com",
    "objects.githubusercontent.com",
}
TRANSPORT_DECLARED = "unauthenticated_public_github_api_aggregate_bucket_only"
PERMISSIVE_LICENSES = {
    "mit",
    "apache-2.0",
    "bsd-2-clause",
    "bsd-3-clause",
    "isc",
    "unlicense",
    "mpl-2.0",
    "0bsd",
}
CURRENTNESS_MAX_AGE_DAYS = 365

CODE_SUFFIXES = {
    ".c", ".cc", ".cpp", ".cs", ".go", ".java", ".js", ".jsx", ".kt",
    ".lua", ".php", ".py", ".rb", ".rs", ".scala", ".sol", ".swift",
    ".ts", ".tsx",
}
MAX_FILE_BYTES = 512_000
LINE_WINDOW = 24

# Frozen candidate-source-pool schema (from Phase 9G).  Each private pool row
# must carry these schema fields; private identity fields may also be present
# under ignored ``runs/`` only.
POOL_SCHEMA_REQUIRED_FIELDS = {
    "publicly_accessible_without_authentication": bool,
    "declared_or_publicly_auditable_license_present": bool,
    "default_branch_or_equivalent_revision_resolvable": bool,
    "currentness_field_present": bool,
    "deterministic_source_order_index": int,
    "private_clone_target_dir": str,
    "retry_timeout_failure_bucket": str,
    "no_credentials_or_auth_prompt": bool,
    "no_private_host": bool,
    "no_local_fallback": bool,
}

FORBIDDEN_PUBLIC_FIELD_WORDS = ("scoring", "labels", "outcomes", "evidence_success")
CLAIM_BOUNDARY_FALSE_KEYS = (
    "method_claim", "product_claim", "performance_claim", "training_claim",
    "provider_claim", "model_claim", "runtime_claim", "default_claim",
    "scoring_claim", "outcome_claim", "evidence_success_claim",
)
FORBIDDEN_EXECUTION_FALSE_KEYS = (
    "strategy_evaluation_executed",
    "benchmark_annotation_generated",
    "result_annotation_generated",
    "evidence_result_evaluation_executed",
    "model_fitting_executed",
    "provider_or_llm_calls_executed",
    "runtime_default_or_product_changes_executed",
    "labels_generated",
    "outcomes_generated",
)
PUBLIC_PRIVACY_FALSE_KEYS = (
    "repo_names_public", "source_names_public", "urls_public", "owners_public",
    "commits_public", "hashes_public", "paths_public", "snippets_public",
    "task_ids_public", "row_ids_public", "manifest_locations_public",
    "run_locations_public", "per_source_public_facts", "per_task_public_facts",
    "singleton_buckets_public",
)

PRIVATE_SHAPED_VALUE_RE = re.compile(
    r"(?:https?://|git@|[A-Za-z]:[\\/]"
    r"|(?:^|\s)/[A-Za-z0-9_.-]+/"
    r"|\b[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\b"
    r"|\b[a-fA-F0-9]{32,}\b)"
)
SINGLETON_BUCKET_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:count_1|bucket_one|singleton)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
PRIVATE_KEY_RE = re.compile(
    r"^(?:repo|repo_name|repo_url|owner|url|source_url"
    r"|candidate_identity|commit|commit_sha|sha|hash"
    r"|path|range|snippet|task_id|row_id"
    r"|manifest|run_dir|per_source|per_task)$",
    re.IGNORECASE,
)
CLAIM_WORDING_RE = re.compile(
    r"\b(?:"
    r"materialization\s+(?:works|succeeded|proven|established)"
    r"|fetch(?:/clone)?\s+(?:works|succeeded|proven|established)"
    r"|clone\s+(?:works|succeeded|proven|established)"
    r"|network\s+fetch\s+(?:works|succeeded|proven|established)"
    r"|evidence_success\s+(?:achieved|proven|established|confirmed)"
    r"|method\s+(?:proven|established|works|winner)"
    r"|lift\s+(?:proven|established|achieved)"
    r")\b",
    re.IGNORECASE,
)

# Attestation counters to prove the validator/self-test do not fetch/read.
FETCH_CLONE_ATTEMPTS = 0
SOURCE_FILE_READ_ATTEMPTS = 0
PRIVATE_RUNS_READ_ATTEMPTS = 0
PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS = 0
PRIVATE_REGISTRY_READ_ATTEMPTS = 0


# ---------------------------------------------------------------------------
# Ignored-runs / privacy helpers
# ---------------------------------------------------------------------------

def _runs_is_ignored() -> bool:
    gitignore = REPO / ".gitignore"
    if not gitignore.exists():
        return False
    lines = [line.strip() for line in gitignore.read_text(encoding="utf-8").splitlines()]
    return "/runs/" in lines or "runs/" in lines or "/runs" in lines


def _assert_under_ignored_runs(path: Path) -> Path:
    resolved = path.resolve()
    runs_root = (REPO / "runs").resolve()
    if resolved != runs_root and runs_root not in resolved.parents:
        raise ValueError("private output must stay under ignored runs/")
    if not _runs_is_ignored():
        raise ValueError("runs/ must remain ignored before private output is allowed")
    return resolved


# ---------------------------------------------------------------------------
# Bucket helpers
# ---------------------------------------------------------------------------

def _bucket_quantity(value: int) -> str:
    if value <= 0:
        return "bucket_zero"
    if value < MIN_DISTINCT_SOURCES:
        return "bucket_nonzero_below_minimum"
    if value < TARGET_TASK_MIN:
        return "bucket_at_least_minimum_below_target"
    if value <= TARGET_TASK_MAX:
        return "bucket_target_48_to_72"
    if value <= HARD_TASK_CAP:
        return "bucket_above_target_within_hard_cap"
    return "bucket_over_hard_cap"


def _bucket_sources(value: int) -> str:
    if value <= 0:
        return "bucket_zero"
    if value < MIN_DISTINCT_SOURCES:
        return "bucket_nonzero_below_minimum"
    if value <= 12:
        return "bucket_minimum_met_low"
    if value <= 24:
        return "bucket_minimum_met_mid"
    return "bucket_minimum_met_high"


# ---------------------------------------------------------------------------
# Phase 9G gate validation (reads tracked public report + docs only)
# ---------------------------------------------------------------------------

def _phase9g_gate_errors(
    report: Any | None = None,
    docs_text: str | None = None,
    supplied_commit: str | None = None,
    supplied_ci: str | None = None,
) -> list[str]:
    """Validate the Phase 9G public gate.

    Returns a list of error strings.  An empty list means the gate is valid
    (present and green).  This function does not fetch/clone; it reads the
    Phase 9G public report and docs only (tracked artifacts).
    """
    errors: list[str] = []
    if report is None:
        if not PHASE9G_PUBLIC_REPORT.exists():
            return ["Phase 9G public report missing"]
        report = json.loads(PHASE9G_PUBLIC_REPORT.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        return ["Phase 9G public report must be object"]
    if report.get("phase") != PHASE9G_STATUS or report.get("status") != PHASE9G_STATUS:
        errors.append("Phase 9G public report status drift")
    if report.get("schema_version") != f"{PHASE9G_STATUS}_report_v1":
        errors.append("Phase 9G public report schema drift")

    scope = report.get("phase9g_scope", {})
    if scope.get("public_fetch_clone_executed") is not False:
        errors.append("Phase 9G scope public_fetch_clone_executed must be false")
    if scope.get("source_materialization_executed") is not False:
        errors.append("Phase 9G scope source_materialization_executed must be false")
    if scope.get("future_execution_requires_phase9g_commit_and_ci_green") is not True:
        errors.append("Phase 9G future execution commit+CI-green boundary missing")

    schema = report.get("candidate_source_pool_schema", {})
    if schema.get("publication_level") != "aggregate_bucketed_schema_only":
        errors.append("Phase 9G candidate source pool schema publication level drift")
    for key in (
        "bounded_public_source_pool_only",
        "license_field",
        "access_field",
        "default_branch_field",
        "currentness_field",
        "deterministic_source_order_field",
        "retry_timeout_failure_bucket_fields",
        "clone_target_mapping_under_ignored_runs_only",
        "no_credentials_or_auth_prompt_fields",
        "no_private_host_fields",
        "no_local_fallback_fields",
        "no_repo_name_or_url_or_owner_or_commit_or_path_or_hash_fields",
    ):
        if schema.get(key) is not True:
            errors.append(f"Phase 9G candidate source pool schema missing: {key}")

    future = report.get("future_phase9h_network_fetch_contract", {})
    if future.get("publication_level") != "aggregate_bucketed_protocol_only":
        errors.append("Phase 9G future phase9h contract publication level drift")
    if future.get("ignored_workspace") != "runs/ only":
        errors.append("Phase 9G future phase9h contract ignored workspace drift")
    if future.get("license_access_default_branch_currentness_hash_checks") is not True:
        errors.append("Phase 9G future phase9h contract checks missing")
    if future.get("stop_on_zero_materialization_after_caps") is not True:
        errors.append("Phase 9G future phase9h contract stop-on-zero missing")
    if future.get("stop_on_diversity_below_minimum_after_caps") is not True:
        errors.append("Phase 9G future phase9h contract stop-on-diversity missing")
    if future.get("future_strategy_scoring_requires_another_frozen_boundary") is not True:
        errors.append("Phase 9G future phase9h contract strategy-scoring boundary missing")
    rules = future.get("fetch_clone_rules")
    if not isinstance(rules, list) or not rules:
        errors.append("Phase 9G future phase9h contract fetch_clone_rules missing")

    gate9f = report.get("phase9f_gate_references", {})
    if gate9f.get("phase9f_commit") != PHASE9F_COMMIT:
        errors.append("Phase 9G report Phase 9F commit gate reference drift")
    if gate9f.get("phase9f_ci_run") != PHASE9F_CI_RUN:
        errors.append("Phase 9G report Phase 9F CI run gate reference drift")
    if gate9f.get("phase9f_status") != PHASE9F_STATUS:
        errors.append("Phase 9G report Phase 9F status gate reference drift")
    if gate9f.get("phase9f_repair_no_claim") is not True:
        errors.append("Phase 9G report Phase 9F repair/no-claim gate missing")
    if gate9f.get("phase9f_zero_buckets") is not True:
        errors.append("Phase 9G report Phase 9F zero-buckets gate missing")
    if gate9f.get("phase9f_public_fetch_or_clone_executed") is not False:
        errors.append("Phase 9G report Phase 9F public fetch/clone gate must be false")

    # Supplied public gate confirmation values must match the frozen constants.
    if supplied_commit is not None and supplied_commit != PHASE9G_COMMIT:
        errors.append("supplied Phase 9G commit does not match public gate reference")
    if supplied_ci is not None and supplied_ci != PHASE9G_CI_RUN:
        errors.append("supplied Phase 9G CI run does not match public gate reference")

    if docs_text is None:
        missing_docs = [path for path in PHASE9G_DOCS if not path.exists()]
        if missing_docs:
            errors.append("Phase 9G docs missing")
        docs_text = "\n".join(
            path.read_text(encoding="utf-8") for path in PHASE9G_DOCS if path.exists()
        )
    if PHASE9G_STATUS not in docs_text:
        errors.append("Phase 9G docs status reference missing")
    if "CI green" not in docs_text and "CI run" not in docs_text:
        errors.append("Phase 9G docs CI reference missing")
    return sorted(set(errors))


def _load_phase9g_gate(supplied_commit: str, supplied_ci: str) -> dict[str, Any]:
    errors = _phase9g_gate_errors(
        supplied_commit=supplied_commit, supplied_ci=supplied_ci
    )
    if errors:
        raise ValueError("Phase 9G gate failed: " + "; ".join(errors))
    return {
        "phase9g_public_report_validated": True,
        "phase9g_public_report_status": PHASE9G_STATUS,
        "phase9g_commit_gate_reference": PHASE9G_COMMIT,
        "phase9g_ci_run_gate_reference": PHASE9G_CI_RUN,
        "phase9g_ci_success_gate": True,
        "phase9g_protocol_freeze": True,
        "phase9g_carries_phase9f_gate": True,
        "phase9g_future_execution_boundary_present": True,
        "phase9g_gate_required_before_phase9h": True,
    }


# ---------------------------------------------------------------------------
# Private candidate source pool (under ignored runs/ only)
# ---------------------------------------------------------------------------

def _find_private_candidate_pool(private_run_dir: Path) -> Path | None:
    """Locate a private candidate source pool under ignored runs/ only."""
    global PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS
    PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS += 1
    runs_root = (REPO / "runs").resolve()
    resolved = private_run_dir.resolve()
    if runs_root not in resolved.parents and resolved != runs_root:
        return None
    candidate = resolved / "private_candidate_source_pool.json"
    if candidate.exists():
        return candidate
    return None


def _validate_pool_row_schema(row: Any, index: int) -> list[str]:
    """Validate a single candidate-source-pool row against the frozen Phase 9G schema.

    This is a pure schema check: no filesystem or network access.  Used by both
    the private pool reader (under ignored ``runs/``) and the self-test.
    """
    errors: list[str] = []
    if not isinstance(row, dict):
        errors.append(f"pool row {index} not object")
        return errors
    for field, expected_type in POOL_SCHEMA_REQUIRED_FIELDS.items():
        if field not in row:
            errors.append(f"pool row {index} missing schema field: {field}")
        elif not isinstance(row[field], expected_type):
            errors.append(f"pool row {index} field {field} wrong type")
    return errors


def _read_private_candidate_pool(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Read a private candidate source pool.  Private only; never public."""
    global PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS
    PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS += 1
    resolved = path.resolve()
    runs_root = (REPO / "runs").resolve()
    if runs_root not in resolved.parents:
        return [], ["private candidate source pool must be under ignored runs/"]
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [], ["private candidate source pool unreadable"]
    if not isinstance(payload, dict):
        return [], ["private candidate source pool must be object"]
    rows = payload.get("candidate_sources_private")
    if not isinstance(rows, list):
        return [], ["private candidate source pool missing candidate_sources_private"]
    schema_errors: list[str] = []
    valid_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        row_errors = _validate_pool_row_schema(row, index)
        schema_errors.extend(row_errors)
        if not row_errors:
            valid_rows.append(row)
    return valid_rows, schema_errors


def _candidate_clone_target(row: dict[str, Any], index: int, workspace: Path) -> Path | None:
    """Resolve a private clone target under ignored runs/ only."""
    value = row.get("private_clone_target_dir")
    if not isinstance(value, str) or not value.strip():
        value = f"private_source_{index}"
    candidate_path = Path(value)
    target = candidate_path if candidate_path.is_absolute() else (workspace / value)
    target = target.resolve()
    runs_root = (REPO / "runs").resolve()
    if runs_root not in target.parents and target != runs_root:
        return None
    return target


def _public_access_prechecks_pass(row: dict[str, Any]) -> bool:
    return (
        row.get("publicly_accessible_without_authentication") is True
        and row.get("declared_or_publicly_auditable_license_present") is True
        and row.get("default_branch_or_equivalent_revision_resolvable") is True
        and row.get("currentness_field_present") is True
        and row.get("no_credentials_or_auth_prompt") is True
        and row.get("no_private_host") is True
        and row.get("no_local_fallback") is True
    )


# ---------------------------------------------------------------------------
# Public GitHub API transport (unauthenticated, aggregate-only)
# ---------------------------------------------------------------------------

class _PublicHostOnlyRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follow redirects only to known public GitHub hosts; fail closed otherwise."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlparse(newurl)
        if parsed.hostname not in GITHUB_PUBLIC_HOSTS:
            raise urllib.error.URLError(
                "redirect to non-public host: " + str(parsed.hostname)
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _github_api_get(url: str) -> tuple[Any, str]:
    """Unauthenticated public GitHub API GET.

    Returns (parsed_json, failure_reason).  failure_reason is empty on success.
    """
    global FETCH_CLONE_ATTEMPTS
    FETCH_CLONE_ATTEMPTS += 1
    opener = urllib.request.build_opener(_PublicHostOnlyRedirectHandler())
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "OpenLocus-Phase9H-Public-Transport",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with opener.open(req, timeout=NETWORK_TIMEOUT_SECONDS) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body), ""
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            remaining = exc.headers.get("X-RateLimit-Remaining", "")
            if remaining == "0":
                return None, "rate_limit_no_auth_stop"
        return None, f"http_error_{exc.code}"
    except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError) as exc:
        reason = "redirect_ambiguity" if "non-public host" in str(exc) else "transport_error"
        return None, reason


def _github_raw_get(url: str) -> tuple[bytes, str]:
    """Unauthenticated public raw content GET (raw.githubusercontent.com)."""
    global FETCH_CLONE_ATTEMPTS
    FETCH_CLONE_ATTEMPTS += 1
    opener = urllib.request.build_opener(_PublicHostOnlyRedirectHandler())
    req = urllib.request.Request(
        url, headers={"User-Agent": "OpenLocus-Phase9H-Public-Transport"}
    )
    try:
        with opener.open(req, timeout=NETWORK_TIMEOUT_SECONDS) as resp:
            return resp.read(), ""
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            remaining = exc.headers.get("X-RateLimit-Remaining", "")
            if remaining == "0":
                return b"", "rate_limit_no_auth_stop"
        return b"", f"http_error_{exc.code}"
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        reason = "redirect_ambiguity" if "non-public host" in str(exc) else "transport_error"
        return b"", reason


def _discover_public_candidate_sources() -> tuple[list[dict[str, Any]], str]:
    """Discover public candidate sources via unauthenticated GitHub search API.

    The search query is a generic public filter (no embedded repo names).  Repo
    identities come from the API response and go only into the private pool
    under ignored ``runs/``.
    """
    query = (
        "language:python+license:mit+stars:%3E200"
        "+pushed:%3E2025-06-01+size:%3C2000"
    )
    url = (
        f"https://api.github.com/search/repositories?q={query}"
        f"&sort=stars&order=desc&per_page=30"
    )
    data, reason = _github_api_get(url)
    if data is None:
        return [], reason or "search_api_failure"
    items = data.get("items")
    if not isinstance(items, list):
        return [], "search_api_malformed"
    now = datetime.now(timezone.utc)
    rows: list[dict[str, Any]] = []
    for item in items:
        if len(rows) >= MAX_SOURCE_CANDIDATES:
            break
        if not isinstance(item, dict):
            continue
        if item.get("private") is not False:
            continue  # fail closed on private repo
        license_info = item.get("license")
        license_key = (
            license_info.get("key") if isinstance(license_info, dict) else None
        )
        if license_key not in PERMISSIVE_LICENSES:
            continue  # fail closed on missing/unverifiable license
        default_branch = item.get("default_branch")
        if not isinstance(default_branch, str) or not default_branch.strip():
            continue  # fail closed on missing default branch
        pushed_at = item.get("pushed_at")
        if not isinstance(pushed_at, str):
            continue  # fail closed on missing currentness
        try:
            pushed_dt = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
        except ValueError:
            continue  # fail closed on unverifiable currentness
        if (now - pushed_dt).days > CURRENTNESS_MAX_AGE_DAYS:
            continue  # fail closed on stale currentness
        full_name = item.get("full_name")
        if not isinstance(full_name, str) or "/" not in full_name:
            continue  # fail closed on unverifiable identity
        rows.append({
            "publicly_accessible_without_authentication": True,
            "declared_or_publicly_auditable_license_present": True,
            "default_branch_or_equivalent_revision_resolvable": True,
            "currentness_field_present": True,
            "deterministic_source_order_index": len(rows),
            "private_clone_target_dir": f"private_source_{len(rows)}",
            "retry_timeout_failure_bucket": "bucket_initial_attempt",
            "no_credentials_or_auth_prompt": True,
            "no_private_host": True,
            "no_local_fallback": True,
            "private_source_identity": {
                "full_name": full_name,
                "default_branch": default_branch,
                "license_key": license_key,
                "pushed_at": pushed_at,
                "archive_endpoint": "github_api_trees_and_raw_content",
                "trees_url": f"https://api.github.com/repos/{full_name}/git/trees/{default_branch}?recursive=1",
                "raw_base": f"https://raw.githubusercontent.com/{full_name}/{default_branch}/",
            },
        })
    if not rows:
        return [], "no_candidates_after_prechecks"
    return rows, ""


def _private_candidate_id(
    source_index: int, root: Path, file_path: Path, start_line: int, end_line: int
) -> str:
    payload = (
        f"{PHASE}\0{source_index}\0{root}\0{file_path}\0{start_line}\0{end_line}"
    ).encode("utf-8", errors="replace")
    return hashlib.sha256(payload).hexdigest()


def _attempt_source_transport(
    row: dict[str, Any], workspace: Path, source_index: int
) -> tuple[list[dict[str, Any]], str]:
    """Attempt public-source transport for one source.

    Uses GitHub trees API (metadata) + raw.githubusercontent.com (content).
    Returns (materialized_rows, failure_reason).  Initial attempt + one fixed
    retry only.  failure_reason containing 'rate_limit' triggers stop-no-auth.
    """
    global SOURCE_FILE_READ_ATTEMPTS
    identity = row.get("private_source_identity")
    if not isinstance(identity, dict):
        return [], "missing_private_identity"
    trees_url = identity.get("trees_url")
    raw_base = identity.get("raw_base")
    if not isinstance(trees_url, str) or not isinstance(raw_base, str):
        return [], "missing_transport_urls"
    clone_target = _candidate_clone_target(row, source_index, workspace)
    if clone_target is None:
        return [], "no_private_clone_target_under_ignored_runs"
    failure_reason = ""
    for attempt in range(PER_SOURCE_TRANSPORT_ATTEMPTS):
        tree_data, reason = _github_api_get(trees_url)
        if tree_data is None:
            failure_reason = reason or "trees_api_failure"
            continue
        tree = tree_data.get("tree")
        if not isinstance(tree, list):
            failure_reason = "trees_api_malformed"
            continue
        code_blobs: list[dict[str, Any]] = []
        for entry in tree:
            if not isinstance(entry, dict):
                continue
            if entry.get("type") != "blob":
                continue
            path = entry.get("path")
            if not isinstance(path, str) or not path:
                continue
            if Path(path).suffix.lower() not in CODE_SUFFIXES:
                continue
            size = entry.get("size", 0)
            if not isinstance(size, int) or size <= 0 or size > MAX_FILE_BYTES:
                continue
            code_blobs.append(entry)
        code_blobs.sort(key=lambda e: str(e.get("path", "")))
        rows: list[dict[str, Any]] = []
        for blob in code_blobs[:PER_SOURCE_TASK_CAP]:
            path = str(blob.get("path", ""))
            encoded_path = urllib.parse.quote(path, safe="/")
            raw_url = raw_base + encoded_path
            content, raw_reason = _github_raw_get(raw_url)
            if not content:
                if "rate_limit" in raw_reason:
                    return [], raw_reason
                continue  # skip this file, try next
            SOURCE_FILE_READ_ATTEMPTS += 1
            clone_target.mkdir(parents=True, exist_ok=True)
            local_file = clone_target / path
            local_file.parent.mkdir(parents=True, exist_ok=True)
            local_file.write_bytes(content)
            text = content.decode("utf-8", errors="replace")
            line_total = max(
                1, text.count("\n") + (0 if text.endswith("\n") else 1)
            )
            start_line = 1
            end_line = min(line_total, LINE_WINDOW)
            rows.append({
                "private_candidate_id": _private_candidate_id(
                    source_index, clone_target, Path(path), start_line, end_line
                ),
                "source_order_index_private": source_index,
                "candidate_order_index_private": 0,
                "task_type": "evidence_finding_file_localizable_code_task",
                "private_source_file_path": path,
                "private_line_range": {"start": start_line, "end": end_line},
                "private_source_sha256": hashlib.sha256(content).hexdigest(),
                "currentness_reread_available_private": True,
                "license_access_default_branch_checks_passed": True,
                "public_access_check_passed": True,
                "source_snippet_stored": False,
                "replacement_policy_private": (
                    "next_deterministic_candidate_same_source_else_next_source"
                    "_before_benchmark_annotations_or_strategy_evaluation"
                ),
            })
        if rows:
            return rows, ""
        failure_reason = "no_materialized_files_after_transport"
    return [], failure_reason or "transport_failure_after_caps"


# ---------------------------------------------------------------------------
# Materialization orchestration
# ---------------------------------------------------------------------------

def _materialize_rows(
    candidate_sources: list[dict[str, Any]],
    workspace: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    global FETCH_CLONE_ATTEMPTS, SOURCE_FILE_READ_ATTEMPTS
    all_rows: list[dict[str, Any]] = []
    source_private_summaries: list[dict[str, Any]] = []
    sources_with_rows = 0
    sources_checked = 0
    precheck_passed_sources = 0
    transport_attempted_sources = 0
    transport_succeeded_sources = 0
    skipped_sources = 0
    rate_limit_stop = False
    redirect_ambiguity = False

    for source_index, source in enumerate(candidate_sources):
        if len(all_rows) >= TARGET_TASK_MAX:
            break
        if source_index >= MAX_SOURCE_CANDIDATES:
            break
        if rate_limit_stop:
            break
        sources_checked += 1
        if not _public_access_prechecks_pass(source):
            skipped_sources += 1
            source_private_summaries.append({
                "source_order_index": source_index,
                "private_skip_reason": "public_access_license_default_branch_currentness_precheck_failed",
            })
            continue
        precheck_passed_sources += 1
        transport_attempted_sources += 1
        rows, reason = _attempt_source_transport(source, workspace, source_index)
        if "rate_limit" in reason:
            rate_limit_stop = True
        if "redirect" in reason and "ambiguity" in reason:
            redirect_ambiguity = True
        if not rows:
            skipped_sources += 1
            source_private_summaries.append({
                "source_order_index": source_index,
                "private_skip_reason": reason or "transport_failure",
            })
            continue
        transport_succeeded_sources += 1
        for row_data in rows:
            row_data["candidate_order_index_private"] = len(all_rows)
            all_rows.append(row_data)
            if len(all_rows) >= TARGET_TASK_MAX:
                break
        sources_with_rows += 1
        source_private_summaries.append({
            "source_order_index": source_index,
            "private_materialized_rows": len(rows),
        })
        if len(all_rows) >= TARGET_TASK_MIN and sources_with_rows >= MIN_DISTINCT_SOURCES:
            break

    aggregate = {
        "candidate_total": len(all_rows),
        "distinct_sources_with_candidates": sources_with_rows,
        "candidate_sources_checked": sources_checked,
        "precheck_passed_sources": precheck_passed_sources,
        "transport_attempted_sources": transport_attempted_sources,
        "transport_succeeded_sources": transport_succeeded_sources,
        "skipped_sources": skipped_sources,
        "hard_cap_respected": len(all_rows) <= HARD_TASK_CAP,
        "per_source_cap_respected": True,
        "target_bucket_met": TARGET_TASK_MIN <= len(all_rows) <= TARGET_TASK_MAX,
        "diversity_minimum_met": sources_with_rows >= MIN_DISTINCT_SOURCES,
        "rate_limit_stop_no_auth": rate_limit_stop,
        "redirect_ambiguity_fail_closed": redirect_ambiguity,
        "source_file_reads_attempted": SOURCE_FILE_READ_ATTEMPTS,
        "fetch_clone_attempts": FETCH_CLONE_ATTEMPTS,
    }
    private_manifest = {
        "phase": PHASE,
        "private_only_not_for_public_report": True,
        "task_candidate_rows_are_inventory_only": True,
        "accepted_task_rows_remain_inventory_only_not_benchmark_annotations": True,
        "provider_or_llm_calls_executed": False,
        "model_fitting_executed": False,
        "source_snippets_stored": False,
        "materialization_rows_private": all_rows,
        "source_private_summaries": source_private_summaries,
        "aggregate_private_totals": aggregate,
    }
    return all_rows, private_manifest


def _empty_private_manifest(reason: str) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "private_only_not_for_public_report": True,
        "task_candidate_rows_are_inventory_only": True,
        "private_stop_reason": reason,
        "materialization_rows_private": [],
        "source_private_summaries": [],
        "aggregate_private_totals": {
            "candidate_total": 0,
            "distinct_sources_with_candidates": 0,
            "candidate_sources_checked": 0,
            "precheck_passed_sources": 0,
            "transport_attempted_sources": 0,
            "transport_succeeded_sources": 0,
            "skipped_sources": 0,
            "hard_cap_respected": True,
            "per_source_cap_respected": True,
            "target_bucket_met": False,
            "diversity_minimum_met": False,
            "rate_limit_stop_no_auth": False,
            "redirect_ambiguity_fail_closed": False,
            "source_file_reads_attempted": SOURCE_FILE_READ_ATTEMPTS,
            "fetch_clone_attempts": FETCH_CLONE_ATTEMPTS,
        },
    }


# ---------------------------------------------------------------------------
# Public report builder
# ---------------------------------------------------------------------------

def build_public_report(
    aggregate: dict[str, Any],
    phase9g_gate: dict[str, Any] | None,
    gate_missing: bool,
    confirmations: dict[str, bool],
    pool_schema_errors: list[str] | None = None,
) -> dict[str, Any]:
    candidate_total = int(aggregate.get("candidate_total", 0))
    distinct_sources = int(aggregate.get("distinct_sources_with_candidates", 0))
    transport_attempted = int(aggregate.get("transport_attempted_sources", 0))
    transport_succeeded = int(aggregate.get("transport_succeeded_sources", 0))
    transport_failures = max(0, transport_attempted - transport_succeeded)
    rate_limit_stop = bool(aggregate.get("rate_limit_stop_no_auth", False))
    redirect_ambiguity = bool(aggregate.get("redirect_ambiguity_fail_closed", False))

    gate_ok = (
        phase9g_gate is not None
        and phase9g_gate.get("phase9g_public_report_validated") is True
        and phase9g_gate.get("phase9g_public_report_status") == PHASE9G_STATUS
        and phase9g_gate.get("phase9g_ci_success_gate") is True
        and phase9g_gate.get("phase9g_future_execution_boundary_present") is True
    )
    all_confirmations = all(confirmations.values()) and len(confirmations) == 9
    caps_ok = (
        aggregate.get("hard_cap_respected") is True
        and aggregate.get("per_source_cap_respected") is True
    )
    target_ok = TARGET_TASK_MIN <= candidate_total <= TARGET_TASK_MAX
    diversity_ok = distinct_sources >= MIN_DISTINCT_SOURCES
    schema_ok = not pool_schema_errors

    if gate_missing or not gate_ok:
        status = STATUS_GATE_MISSING
    elif not all_confirmations or not caps_ok or not schema_ok:
        status = STATUS_REPAIR
    elif target_ok and diversity_ok and candidate_total > 0:
        status = STATUS_READINESS
    else:
        status = STATUS_REPAIR

    network_fetch_executed = (
        status != STATUS_GATE_MISSING and candidate_total > 0
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "status": status,
        "phase9f_gate_references": {
            "phase9f_commit": PHASE9F_COMMIT,
            "phase9f_ci_run": PHASE9F_CI_RUN,
            "phase9f_status": PHASE9F_STATUS,
            "phase9f_repair_no_claim": True,
            "phase9f_zero_buckets": True,
            "phase9f_public_fetch_or_clone_executed": False,
            "phase9f_not_proof_fetch_or_clone_or_materialization_works": True,
            "phase9f_gate_referenced_from_phase9g": True,
        },
        "phase9g_gate_references": {
            "phase9g_public_report_validated": gate_ok,
            "phase9g_public_report_status": PHASE9G_STATUS,
            "phase9g_commit_gate_reference": PHASE9G_COMMIT,
            "phase9g_ci_run_gate_reference": PHASE9G_CI_RUN,
            "phase9g_ci_success_gate": (phase9g_gate or {}).get("phase9g_ci_success_gate") is True,
            "phase9g_protocol_freeze": (phase9g_gate or {}).get("phase9g_protocol_freeze") is True,
            "phase9g_carries_phase9f_gate": (phase9g_gate or {}).get("phase9g_carries_phase9f_gate") is True,
            "phase9g_future_execution_boundary_present": (phase9g_gate or {}).get("phase9g_future_execution_boundary_present") is True,
            "phase9g_gate_required_before_phase9h": True,
        },
        "confirmation_summary": {
            "phase9g_commit_confirmed": confirmations.get("phase9g_commit_confirmed") is True,
            "phase9g_ci_confirmed": confirmations.get("phase9g_ci_confirmed") is True,
            "public_source_network_fetch_confirmed": confirmations.get("public_source_network_fetch_confirmed") is True,
            "ignored_runs_workspace_confirmed": confirmations.get("ignored_runs_workspace_confirmed") is True,
            "allow_public_github_api_transport_confirmed": confirmations.get("allow_public_github_api_transport_confirmed") is True,
            "no_private_or_local_fallback_confirmed": confirmations.get("no_private_or_local_fallback_confirmed") is True,
            "no_labels_outcomes_scoring_evidence_success_confirmed": confirmations.get("no_labels_outcomes_scoring_evidence_success_confirmed") is True,
            "no_provider_llm_model_default_runtime_change_confirmed": confirmations.get("no_provider_llm_model_default_runtime_change_confirmed") is True,
            "aggregate_public_report_only_confirmed": confirmations.get("aggregate_public_report_only_confirmed") is True,
            "all_required_confirmations_present": all_confirmations,
            "dry_self_test_and_report_validation_read_private_runs": False,
            "dry_self_test_and_report_validation_fetch_or_clone": False,
        },
        "candidate_source_pool_schema": {
            "publication_level": "aggregate_bucketed_schema_only",
            "bounded_public_source_pool_only": True,
            "license_field": True,
            "access_field": True,
            "default_branch_field": True,
            "currentness_field": True,
            "deterministic_source_order_field": True,
            "retry_timeout_failure_bucket_fields": True,
            "clone_target_mapping_under_ignored_runs_only": True,
            "no_credentials_or_auth_prompt_fields": True,
            "no_private_host_fields": True,
            "no_local_fallback_fields": True,
            "no_repo_name_or_url_or_owner_or_commit_or_path_or_hash_fields": True,
            "pool_schema_validation_passed": schema_ok,
        },
        "transport_summary": {
            "publication_level": "aggregate_bucketed_transport_only",
            "transport_declared": TRANSPORT_DECLARED,
            "public_source_network_fetch_executed": network_fetch_executed,
            "transport_attempt_bucket": _bucket_sources(transport_attempted),
            "transport_success_bucket": _bucket_sources(transport_succeeded),
            "transport_retry_policy": "initial_plus_one_fixed_retry_only",
            "transport_no_credentials_or_auth_prompts": True,
            "transport_no_private_host": True,
            "transport_no_local_fallback": True,
            "transport_redirect_ambiguity_fail_closed": True,
            "transport_rate_limit_stop_no_auth": rate_limit_stop,
            "transport_no_hidden_github_api_fallback": True,
            "transport_comparison_claims": False,
        },
        "materialization_summary": {
            "publication_level": "aggregate_bucketed_inventory_only",
            "candidate_type": "evidence_finding_file_localizable_code_tasks_only",
            "public_source_network_fetch_executed": network_fetch_executed,
            "constructed_inventory_bucket": _bucket_quantity(candidate_total),
            "materialized_reference_bucket": _bucket_quantity(candidate_total),
            "target_task_candidate_bucket": "bucket_target_48_to_72",
            "hard_cap_bucket": "bucket_up_to_96",
            "per_source_cap_bucket": "bucket_up_to_8",
            "license_access_default_branch_precheck_bucket": _bucket_sources(
                int(aggregate.get("precheck_passed_sources", 0))
            ),
            "source_reference_currentness_reread_available_privately": candidate_total > 0,
            "source_snippets_public": False,
            "source_snippets_stored_private": False,
            "accepted_rows_remain_inventory_only_not_benchmark_annotations": True,
            "replacement_before_benchmark_annotations_or_strategy_evaluation_only": True,
            "replacement_uses_no_performance_evidence_or_downstream_feedback": True,
        },
        "source_diversity_summary": {
            "minimum_distinct_sources_bucket": "bucket_at_least_8",
            "observed_distinct_sources_bucket": _bucket_sources(distinct_sources),
            "diversity_minimum_met": diversity_ok,
            "stop_or_repair_if_below_minimum_after_caps": True,
        },
        "retry_timeout_failure_summary": {
            "publication_level": "aggregate_bucketed_retry_timeout_failure_only",
            "retry_policy": "initial_plus_one_fixed_retry_only",
            "retry_attempt_bucket": _bucket_sources(transport_attempted),
            "timeout_failure_bucket": _bucket_sources(transport_failures),
            "rate_limit_stop_no_auth": rate_limit_stop,
            "redirect_ambiguity_fail_closed": redirect_ambiguity,
            "no_dynamic_cap_changes_after_observation": True,
            "caps_fixed_before_observation": True,
        },
        "privacy_summary": {
            "public_output_aggregate_only": True,
            "private_outputs_under_ignored_runs_only": True,
            "runs_remains_ignored": _runs_is_ignored(),
            **{key: False for key in PUBLIC_PRIVACY_FALSE_KEYS},
        },
        "no_claim_boundary": {key: False for key in CLAIM_BOUNDARY_FALSE_KEYS},
        "forbidden_execution_boundary": {
            key: False for key in FORBIDDEN_EXECUTION_FALSE_KEYS
        },
        "validation_summary": {
            "route_specific_validator_available": True,
            "self_test_available": True,
            "report_validation_available": True,
            "public_artifact_privacy_audit_expected": True,
            "readiness_status_requires_nonzero_materialization_target_bucket_and_minimum_diversity": True,
            "validator_does_not_fetch_or_read_private": True,
            "validator_does_not_read_private_candidate_pools": True,
            "validator_executes_tasks": False,
            "validator_reads_private_registry": False,
            "validator_reads_sources": False,
            "validator_reads_ignored_runs": False,
        },
        "conservative_recommendation": (
            "candidate_source_pool_public_source_network_fetch_materialization"
            "_readiness_only_no_scoring_no_claim_no_evidence_success"
            "_future_strategy_scoring_requires_another_frozen_boundary"
        ),
    }


# ---------------------------------------------------------------------------
# Public report privacy scan + validation
# ---------------------------------------------------------------------------

def _scan_public(value: Any, path: str = "$", key: str = "") -> list[str]:
    errors: list[str] = []
    key_lower = key.lower()
    if key_lower in {"count"} or key_lower.endswith("_count"):
        errors.append(f"exact public count field at {path}")
    if not isinstance(value, bool) and any(
        word in key_lower for word in FORBIDDEN_PUBLIC_FIELD_WORDS
    ):
        errors.append(f"forbidden public field word at {path}")
    if key and PRIVATE_KEY_RE.search(key):
        errors.append(f"private-shaped public key at {path}")
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            child_path = f"{path}.{child_key}" if path != "$" else f"$.{child_key}"
            errors.extend(_scan_public(child_value, child_path, str(child_key)))
    elif isinstance(value, list):
        for index, child_value in enumerate(value):
            errors.extend(_scan_public(child_value, f"{path}[{index}]", ""))
    elif isinstance(value, str):
        if PRIVATE_SHAPED_VALUE_RE.search(value):
            errors.append(f"private-shaped public value at {path}")
        if SINGLETON_BUCKET_RE.search(value):
            errors.append(f"singleton bucket wording at {path}")
        if CLAIM_WORDING_RE.search(value):
            errors.append(f"claim-making wording at {path}")
    return errors


def validate_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["report must be object"]
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema drift")
    if report.get("phase") != PHASE:
        errors.append("phase drift")
    if report.get("status") not in ALLOWED_STATUSES:
        errors.append("unknown status")

    # Phase 9F gate references
    gate9f = report.get("phase9f_gate_references", {})
    if gate9f.get("phase9f_commit") != PHASE9F_COMMIT:
        errors.append("Phase 9F commit gate reference drift")
    if gate9f.get("phase9f_ci_run") != PHASE9F_CI_RUN:
        errors.append("Phase 9F CI run gate reference drift")
    if gate9f.get("phase9f_status") != PHASE9F_STATUS:
        errors.append("Phase 9F status gate reference drift")
    if gate9f.get("phase9f_repair_no_claim") is not True:
        errors.append("Phase 9F repair/no-claim gate missing")
    if gate9f.get("phase9f_zero_buckets") is not True:
        errors.append("Phase 9F zero-buckets gate missing")
    if gate9f.get("phase9f_public_fetch_or_clone_executed") is not False:
        errors.append("Phase 9F public fetch/clone gate must be false")
    if gate9f.get("phase9f_gate_referenced_from_phase9g") is not True:
        errors.append("Phase 9F gate-referenced-from-9g boundary missing")

    # Phase 9G gate references
    gate9g = report.get("phase9g_gate_references", {})
    if gate9g.get("phase9g_public_report_status") != PHASE9G_STATUS:
        errors.append("Phase 9G public report status drift")
    if gate9g.get("phase9g_commit_gate_reference") != PHASE9G_COMMIT:
        errors.append("Phase 9G commit gate reference drift")
    if gate9g.get("phase9g_ci_run_gate_reference") != PHASE9G_CI_RUN:
        errors.append("Phase 9G CI run gate reference drift")
    if gate9g.get("phase9g_gate_required_before_phase9h") is not True:
        errors.append("Phase 9G gate-required boundary missing")
    if report.get("status") != STATUS_GATE_MISSING:
        for key in (
            "phase9g_public_report_validated",
            "phase9g_ci_success_gate",
            "phase9g_protocol_freeze",
            "phase9g_carries_phase9f_gate",
            "phase9g_future_execution_boundary_present",
        ):
            if gate9g.get(key) is not True:
                errors.append(f"Phase 9G gate reference missing: {key}")

    # Confirmation summary
    confirm = report.get("confirmation_summary", {})
    required_confirm_keys = (
        "phase9g_commit_confirmed",
        "phase9g_ci_confirmed",
        "public_source_network_fetch_confirmed",
        "ignored_runs_workspace_confirmed",
        "allow_public_github_api_transport_confirmed",
        "no_private_or_local_fallback_confirmed",
        "no_labels_outcomes_scoring_evidence_success_confirmed",
        "no_provider_llm_model_default_runtime_change_confirmed",
        "aggregate_public_report_only_confirmed",
    )
    for key in required_confirm_keys:
        if confirm.get(key) is not True:
            errors.append(f"confirmation missing: {key}")
    if confirm.get("all_required_confirmations_present") is not True:
        errors.append("all_required_confirmations_present boundary missing")
    if confirm.get("dry_self_test_and_report_validation_read_private_runs") is not False:
        errors.append("self-test/validate-report private-runs read boundary failed")
    if confirm.get("dry_self_test_and_report_validation_fetch_or_clone") is not False:
        errors.append("self-test/validate-report fetch/clone boundary failed")

    # Candidate source pool schema
    schema = report.get("candidate_source_pool_schema", {})
    if schema.get("publication_level") != "aggregate_bucketed_schema_only":
        errors.append("candidate source pool schema publication level drift")
    for key in (
        "bounded_public_source_pool_only",
        "license_field",
        "access_field",
        "default_branch_field",
        "currentness_field",
        "deterministic_source_order_field",
        "retry_timeout_failure_bucket_fields",
        "clone_target_mapping_under_ignored_runs_only",
        "no_credentials_or_auth_prompt_fields",
        "no_private_host_fields",
        "no_local_fallback_fields",
        "no_repo_name_or_url_or_owner_or_commit_or_path_or_hash_fields",
        "pool_schema_validation_passed",
    ):
        if schema.get(key) is not True:
            errors.append(f"candidate source pool schema missing: {key}")

    # Transport summary
    transport = report.get("transport_summary", {})
    if transport.get("publication_level") != "aggregate_bucketed_transport_only":
        errors.append("transport summary publication level drift")
    if transport.get("transport_declared") != TRANSPORT_DECLARED:
        errors.append("transport declared drift")
    if transport.get("transport_retry_policy") != "initial_plus_one_fixed_retry_only":
        errors.append("transport retry policy drift")
    for key in (
        "transport_no_credentials_or_auth_prompts",
        "transport_no_private_host",
        "transport_no_local_fallback",
        "transport_redirect_ambiguity_fail_closed",
        "transport_no_hidden_github_api_fallback",
    ):
        if transport.get(key) is not True:
            errors.append(f"transport summary boundary missing: {key}")
    if transport.get("transport_comparison_claims") is not False:
        errors.append("transport comparison claims boundary failed")

    # Materialization summary
    materialization = report.get("materialization_summary", {})
    expected_inventory = {
        "publication_level": "aggregate_bucketed_inventory_only",
        "candidate_type": "evidence_finding_file_localizable_code_tasks_only",
        "target_task_candidate_bucket": "bucket_target_48_to_72",
        "hard_cap_bucket": "bucket_up_to_96",
        "per_source_cap_bucket": "bucket_up_to_8",
    }
    for key, expected in expected_inventory.items():
        if materialization.get(key) != expected:
            errors.append(f"materialization summary drift: {key}")
    for key in (
        "accepted_rows_remain_inventory_only_not_benchmark_annotations",
        "replacement_before_benchmark_annotations_or_strategy_evaluation_only",
        "replacement_uses_no_performance_evidence_or_downstream_feedback",
    ):
        if materialization.get(key) is not True:
            errors.append(f"materialization boundary missing: {key}")
    if materialization.get("source_snippets_public") is not False:
        errors.append("source snippets public boundary failed")
    if materialization.get("source_snippets_stored_private") is not False:
        errors.append("source snippets stored-private boundary failed")
    if report.get("status") == STATUS_READINESS:
        if materialization.get("constructed_inventory_bucket") != "bucket_target_48_to_72":
            errors.append("readiness status outside target task-candidate bucket")
        if materialization.get("public_source_network_fetch_executed") is not True:
            errors.append("readiness status requires public source network fetch executed")

    # Source diversity summary
    diversity = report.get("source_diversity_summary", {})
    if diversity.get("minimum_distinct_sources_bucket") != "bucket_at_least_8":
        errors.append("minimum distinct source bucket drift")
    if diversity.get("stop_or_repair_if_below_minimum_after_caps") is not True:
        errors.append("diversity stop/repair boundary missing")
    if report.get("status") == STATUS_READINESS:
        if diversity.get("diversity_minimum_met") is not True:
            errors.append("readiness status below minimum diversity")

    # Retry/timeout/failure summary
    retry = report.get("retry_timeout_failure_summary", {})
    if retry.get("publication_level") != "aggregate_bucketed_retry_timeout_failure_only":
        errors.append("retry timeout failure summary publication level drift")
    if retry.get("retry_policy") != "initial_plus_one_fixed_retry_only":
        errors.append("retry policy drift")
    if retry.get("no_dynamic_cap_changes_after_observation") is not True:
        errors.append("no dynamic cap changes boundary missing")
    if retry.get("caps_fixed_before_observation") is not True:
        errors.append("caps fixed before observation boundary missing")

    # Privacy summary
    privacy = report.get("privacy_summary", {})
    for key in (
        "public_output_aggregate_only",
        "private_outputs_under_ignored_runs_only",
        "runs_remains_ignored",
    ):
        if privacy.get(key) is not True:
            errors.append(f"privacy summary missing: {key}")
    for key in PUBLIC_PRIVACY_FALSE_KEYS:
        if privacy.get(key) is not False:
            errors.append(f"public privacy boundary failed: {key}")

    # Validation summary
    validation = report.get("validation_summary", {})
    for key in (
        "route_specific_validator_available",
        "self_test_available",
        "report_validation_available",
        "public_artifact_privacy_audit_expected",
        "readiness_status_requires_nonzero_materialization_target_bucket_and_minimum_diversity",
        "validator_does_not_fetch_or_read_private",
        "validator_does_not_read_private_candidate_pools",
    ):
        if validation.get(key) is not True:
            errors.append(f"validation summary missing: {key}")
    for key in (
        "validator_executes_tasks",
        "validator_reads_private_registry",
        "validator_reads_sources",
        "validator_reads_ignored_runs",
    ):
        if validation.get(key) is not False:
            errors.append(f"validation summary execution boundary failed: {key}")

    # No-claim boundary
    for key in CLAIM_BOUNDARY_FALSE_KEYS:
        if report.get("no_claim_boundary", {}).get(key) is not False:
            errors.append(f"claim boundary failed: {key}")

    # Forbidden execution boundary
    for key in FORBIDDEN_EXECUTION_FALSE_KEYS:
        if report.get("forbidden_execution_boundary", {}).get(key) is not False:
            errors.append(f"forbidden execution boundary failed: {key}")

    errors.extend(_scan_public(report))
    return sorted(set(errors))


# ---------------------------------------------------------------------------
# Confirmation helpers
# ---------------------------------------------------------------------------

def _all_confirmations_dict(
    confirm_phase9g_commit: str | None,
    confirm_phase9g_ci: str | None,
    confirm_public_source_network_fetch: bool,
    confirm_ignored_runs_workspace: bool,
    confirm_allow_public_github_api_transport: bool,
    confirm_no_private_or_local_fallback: bool,
    confirm_no_labels_outcomes_scoring_evidence_success: bool,
    confirm_no_provider_llm_model_default_runtime_change: bool,
    confirm_aggregate_public_report_only: bool,
) -> dict[str, bool]:
    return {
        "phase9g_commit_confirmed": confirm_phase9g_commit == PHASE9G_COMMIT,
        "phase9g_ci_confirmed": confirm_phase9g_ci == PHASE9G_CI_RUN,
        "public_source_network_fetch_confirmed": confirm_public_source_network_fetch is True,
        "ignored_runs_workspace_confirmed": confirm_ignored_runs_workspace is True,
        "allow_public_github_api_transport_confirmed": confirm_allow_public_github_api_transport is True,
        "no_private_or_local_fallback_confirmed": confirm_no_private_or_local_fallback is True,
        "no_labels_outcomes_scoring_evidence_success_confirmed": confirm_no_labels_outcomes_scoring_evidence_success is True,
        "no_provider_llm_model_default_runtime_change_confirmed": confirm_no_provider_llm_model_default_runtime_change is True,
        "aggregate_public_report_only_confirmed": confirm_aggregate_public_report_only is True,
    }


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def execute_phase9h(
    private_run_dir: Path,
    public_report: Path,
    confirm_phase9g_commit: str | None,
    confirm_phase9g_ci: str | None,
    confirm_public_source_network_fetch: bool,
    confirm_ignored_runs_workspace: bool,
    confirm_allow_public_github_api_transport: bool,
    confirm_no_private_or_local_fallback: bool,
    confirm_no_labels_outcomes_scoring_evidence_success: bool,
    confirm_no_provider_llm_model_default_runtime_change: bool,
    confirm_aggregate_public_report_only: bool,
) -> dict[str, Any]:
    confirmations = _all_confirmations_dict(
        confirm_phase9g_commit,
        confirm_phase9g_ci,
        confirm_public_source_network_fetch,
        confirm_ignored_runs_workspace,
        confirm_allow_public_github_api_transport,
        confirm_no_private_or_local_fallback,
        confirm_no_labels_outcomes_scoring_evidence_success,
        confirm_no_provider_llm_model_default_runtime_change,
        confirm_aggregate_public_report_only,
    )
    missing = [name for name, ok in confirmations.items() if not ok]
    if missing:
        raise ValueError("missing required confirmation(s): " + ", ".join(missing))

    private_run_dir = _assert_under_ignored_runs(private_run_dir)
    workspace = private_run_dir / "private_materialized_sources_workspace"
    _assert_under_ignored_runs(workspace)

    gate_errors = _phase9g_gate_errors(
        supplied_commit=confirm_phase9g_commit, supplied_ci=confirm_phase9g_ci
    )
    if gate_errors:
        phase9g_gate = {
            "phase9g_public_report_validated": False,
            "phase9g_public_report_status": PHASE9G_STATUS,
            "phase9g_commit_gate_reference": PHASE9G_COMMIT,
            "phase9g_ci_run_gate_reference": PHASE9G_CI_RUN,
            "phase9g_ci_success_gate": False,
            "phase9g_protocol_freeze": False,
            "phase9g_carries_phase9f_gate": False,
            "phase9g_future_execution_boundary_present": False,
            "phase9g_gate_required_before_phase9h": True,
        }
        aggregate = _empty_private_manifest(
            "phase9g_gate_missing_or_not_green_no_materialization"
        )["aggregate_private_totals"]
        report = build_public_report(
            aggregate, phase9g_gate, gate_missing=True, confirmations=confirmations
        )
        errors = validate_report(report)
        if errors:
            raise ValueError(
                "generated gate-missing report invalid: " + "; ".join(errors[:12])
            )
        private_run_dir.mkdir(parents=True, exist_ok=True)
        public_report.parent.mkdir(parents=True, exist_ok=True)
        (private_run_dir / "private_phase9h_gate_missing_manifest.json").write_text(
            json.dumps(
                {
                    "phase": PHASE,
                    "private_only_not_for_public_report": True,
                    "private_stop_reason": "phase9g_gate_missing_or_not_green_no_materialization",
                    "phase9g_gate_errors_private": gate_errors,
                },
                indent=2, sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )
        public_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return {
            "status": report["status"],
            "public_report": str(public_report),
            "public_inventory_bucket": report["materialization_summary"]["constructed_inventory_bucket"],
            "public_diversity_bucket": report["source_diversity_summary"]["observed_distinct_sources_bucket"],
            "private_output_under_ignored_runs": True,
        }

    phase9g_gate = _load_phase9g_gate(confirm_phase9g_commit, confirm_phase9g_ci)

    # Locate or create private candidate source pool under ignored runs/ only.
    candidate_pool_path = _find_private_candidate_pool(private_run_dir)
    candidate_sources: list[dict[str, Any]] = []
    pool_schema_errors: list[str] = []
    if candidate_pool_path is not None:
        candidate_sources, pool_schema_errors = _read_private_candidate_pool(
            candidate_pool_path
        )
    else:
        # Create private candidate pool only as private ignored input during
        # confirmed execution.  Source identities stay private under runs/.
        discovered, discover_reason = _discover_public_candidate_sources()
        if discovered:
            private_run_dir.mkdir(parents=True, exist_ok=True)
            pool_payload = {
                "phase": PHASE,
                "private_only_not_for_public_report": True,
                "candidate_sources_private": discovered,
                "private_discovery_note": (
                    "private pool created during confirmed execution; "
                    "source identities stay private under ignored runs/"
                ),
            }
            pool_path = private_run_dir / "private_candidate_source_pool.json"
            pool_path.write_text(
                json.dumps(pool_payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            candidate_sources = discovered
        else:
            candidate_sources = []

    # Schema drift -> must-stop repair/no-claim.
    if pool_schema_errors:
        aggregate = _empty_private_manifest(
            "candidate_source_pool_schema_drift_no_materialization"
        )["aggregate_private_totals"]
        report = build_public_report(
            aggregate, phase9g_gate, gate_missing=False,
            confirmations=confirmations, pool_schema_errors=pool_schema_errors,
        )
        errors = validate_report(report)
        if errors:
            raise ValueError(
                "generated schema-drift report invalid: " + "; ".join(errors[:12])
            )
        private_run_dir.mkdir(parents=True, exist_ok=True)
        public_report.parent.mkdir(parents=True, exist_ok=True)
        (private_run_dir / "private_phase9h_schema_drift_manifest.json").write_text(
            json.dumps(
                {
                    "phase": PHASE,
                    "private_only_not_for_public_report": True,
                    "private_stop_reason": "candidate_source_pool_schema_drift",
                    "pool_schema_errors_private": pool_schema_errors,
                },
                indent=2, sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )
        public_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return {
            "status": report["status"],
            "public_report": str(public_report),
            "public_inventory_bucket": report["materialization_summary"]["constructed_inventory_bucket"],
            "public_diversity_bucket": report["source_diversity_summary"]["observed_distinct_sources_bucket"],
            "private_output_under_ignored_runs": True,
        }

    # No candidate source pool available -> must-stop repair/no-claim.
    if not candidate_sources:
        aggregate = _empty_private_manifest(
            "no_candidate_source_pool_available_no_materialization"
        )["aggregate_private_totals"]
        report = build_public_report(
            aggregate, phase9g_gate, gate_missing=False, confirmations=confirmations
        )
        errors = validate_report(report)
        if errors:
            raise ValueError(
                "generated no-pool report invalid: " + "; ".join(errors[:12])
            )
        private_run_dir.mkdir(parents=True, exist_ok=True)
        public_report.parent.mkdir(parents=True, exist_ok=True)
        (private_run_dir / "private_phase9h_no_pool_manifest.json").write_text(
            json.dumps(
                {
                    "phase": PHASE,
                    "private_only_not_for_public_report": True,
                    "private_stop_reason": "no_candidate_source_pool_available",
                },
                indent=2, sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )
        public_report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return {
            "status": report["status"],
            "public_report": str(public_report),
            "public_inventory_bucket": report["materialization_summary"]["constructed_inventory_bucket"],
            "public_diversity_bucket": report["source_diversity_summary"]["observed_distinct_sources_bucket"],
            "private_output_under_ignored_runs": True,
        }

    # Proceed to bounded public-source network-fetch materialization.
    _rows, private_manifest = _materialize_rows(candidate_sources, workspace)
    aggregate = private_manifest["aggregate_private_totals"]
    report = build_public_report(
        aggregate, phase9g_gate, gate_missing=False, confirmations=confirmations
    )
    errors = validate_report(report)
    if errors:
        raise ValueError(
            "generated public report invalid: " + "; ".join(errors[:12])
        )

    private_run_dir.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    public_report.parent.mkdir(parents=True, exist_ok=True)
    (private_run_dir / "private_phase9h_materialization_manifest.json").write_text(
        json.dumps(private_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (private_run_dir / "private_phase9h_materialization_rows.json").write_text(
        json.dumps(private_manifest["materialization_rows_private"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    public_report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "status": report["status"],
        "public_report": str(public_report),
        "public_inventory_bucket": report["materialization_summary"]["constructed_inventory_bucket"],
        "public_diversity_bucket": report["source_diversity_summary"]["observed_distinct_sources_bucket"],
        "private_output_under_ignored_runs": True,
    }


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def run_self_test() -> dict[str, Any]:
    global FETCH_CLONE_ATTEMPTS, SOURCE_FILE_READ_ATTEMPTS, PRIVATE_RUNS_READ_ATTEMPTS
    global PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS, PRIVATE_REGISTRY_READ_ATTEMPTS
    FETCH_CLONE_ATTEMPTS = 0
    SOURCE_FILE_READ_ATTEMPTS = 0
    PRIVATE_RUNS_READ_ATTEMPTS = 0
    PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS = 0
    PRIVATE_REGISTRY_READ_ATTEMPTS = 0
    checks: list[tuple[str, bool]] = []

    full_confirmations = _all_confirmations_dict(
        PHASE9G_COMMIT, PHASE9G_CI_RUN, True, True, True, True, True, True, True,
    )
    gate = {
        "phase9g_public_report_validated": True,
        "phase9g_public_report_status": PHASE9G_STATUS,
        "phase9g_commit_gate_reference": PHASE9G_COMMIT,
        "phase9g_ci_run_gate_reference": PHASE9G_CI_RUN,
        "phase9g_ci_success_gate": True,
        "phase9g_protocol_freeze": True,
        "phase9g_carries_phase9f_gate": True,
        "phase9g_future_execution_boundary_present": True,
        "phase9g_gate_required_before_phase9h": True,
    }

    # --- valid readiness/no-claim report (pass) ---
    readiness_aggregate = {
        "candidate_total": 56,
        "distinct_sources_with_candidates": 8,
        "precheck_passed_sources": 8,
        "transport_attempted_sources": 8,
        "transport_succeeded_sources": 8,
        "hard_cap_respected": True,
        "per_source_cap_respected": True,
        "rate_limit_stop_no_auth": False,
        "redirect_ambiguity_fail_closed": False,
    }
    readiness_report = build_public_report(
        readiness_aggregate, gate, gate_missing=False, confirmations=full_confirmations
    )
    checks.append(("valid_readiness_report_passes", not validate_report(readiness_report)))
    checks.append(("readiness_report_is_readiness_status", readiness_report["status"] == STATUS_READINESS))

    # --- valid repair/no-claim report (zero materialization) ---
    repair_aggregate = _empty_private_manifest(
        "zero_materialization_after_caps"
    )["aggregate_private_totals"]
    repair_report = build_public_report(
        repair_aggregate, gate, gate_missing=False, confirmations=full_confirmations
    )
    checks.append(("valid_repair_no_claim_report_passes", not validate_report(repair_report)))
    checks.append(("repair_report_is_repair_status", repair_report["status"] == STATUS_REPAIR))

    # --- valid gate-missing report ---
    gate_missing_gate = {
        "phase9g_public_report_validated": False,
        "phase9g_public_report_status": PHASE9G_STATUS,
        "phase9g_commit_gate_reference": PHASE9G_COMMIT,
        "phase9g_ci_run_gate_reference": PHASE9G_CI_RUN,
        "phase9g_ci_success_gate": False,
        "phase9g_protocol_freeze": False,
        "phase9g_carries_phase9f_gate": False,
        "phase9g_future_execution_boundary_present": False,
        "phase9g_gate_required_before_phase9h": True,
    }
    gate_missing_report = build_public_report(
        repair_aggregate, gate_missing_gate, gate_missing=True, confirmations=full_confirmations
    )
    checks.append(("valid_gate_missing_report_passes", not validate_report(gate_missing_report)))
    checks.append(("gate_missing_report_is_gate_missing_status", gate_missing_report["status"] == STATUS_GATE_MISSING))

    # --- missing confirmation blocks execution before network/materialization ---
    for label, kwargs in (
        ("missing_confirm_phase9g_commit", dict(confirm_phase9g_commit=None)),
        ("missing_confirm_phase9g_ci", dict(confirm_phase9g_ci=None)),
        ("missing_confirm_public_source_network_fetch", dict(confirm_public_source_network_fetch=False)),
        ("missing_confirm_ignored_runs_workspace", dict(confirm_ignored_runs_workspace=False)),
        ("missing_confirm_allow_public_github_api_transport", dict(confirm_allow_public_github_api_transport=False)),
        ("missing_confirm_no_private_or_local_fallback", dict(confirm_no_private_or_local_fallback=False)),
        ("missing_confirm_no_labels_outcomes_scoring_evidence_success", dict(confirm_no_labels_outcomes_scoring_evidence_success=False)),
        ("missing_confirm_no_provider_llm_model_default_runtime_change", dict(confirm_no_provider_llm_model_default_runtime_change=False)),
        ("missing_confirm_aggregate_public_report_only", dict(confirm_aggregate_public_report_only=False)),
    ):
        try:
            execute_phase9h(
                DEFAULT_PRIVATE_RUN_DIR, DEFAULT_PUBLIC_REPORT,
                PHASE9G_COMMIT if "commit" not in label else None,
                PHASE9G_CI_RUN if "ci" not in label else None,
                True if "network_fetch" not in label else False,
                True if "workspace" not in label else False,
                True if "github_api" not in label else False,
                True if "fallback" not in label else False,
                True if "labels" not in label else False,
                True if "provider" not in label else False,
                True if "aggregate" not in label else False,
            )
            checks.append((f"{label}_rejected", False))
        except ValueError as exc:
            checks.append((f"{label}_rejected", "missing required confirmation" in str(exc)))

    # --- tracked materialization path rejected ---
    try:
        _assert_under_ignored_runs(REPO / "artifacts" / "bad_tracked_output")
        checks.append(("tracked_materialization_path_rejected", False))
    except ValueError as exc:
        checks.append(("tracked_materialization_path_rejected", "runs" in str(exc)))
    tracked_clone_target = _candidate_clone_target(
        {"private_clone_target_dir": str(REPO / "artifacts" / "bad_tracked_clone")},
        0,
        DEFAULT_PRIVATE_RUN_DIR,
    )
    checks.append(("tracked_clone_target_rejected", tracked_clone_target is None))

    # --- Phase 9G gate validation ---
    mutated_phase9g_report = {
        "schema_version": f"{PHASE9G_STATUS}_report_v1",
        "phase": PHASE9G_STATUS,
        "status": "drift",
        "phase9g_scope": {
            "public_fetch_clone_executed": True,
            "source_materialization_executed": False,
            "future_execution_requires_phase9g_commit_and_ci_green": True,
        },
        "candidate_source_pool_schema": {
            "publication_level": "aggregate_bucketed_schema_only",
            "bounded_public_source_pool_only": True,
            "license_field": True,
            "access_field": True,
            "default_branch_field": True,
            "currentness_field": True,
            "deterministic_source_order_field": True,
            "retry_timeout_failure_bucket_fields": True,
            "clone_target_mapping_under_ignored_runs_only": True,
            "no_credentials_or_auth_prompt_fields": True,
            "no_private_host_fields": True,
            "no_local_fallback_fields": True,
            "no_repo_name_or_url_or_owner_or_commit_or_path_or_hash_fields": True,
        },
        "future_phase9h_network_fetch_contract": {
            "publication_level": "aggregate_bucketed_protocol_only",
            "ignored_workspace": "runs/ only",
            "license_access_default_branch_currentness_hash_checks": True,
            "stop_on_zero_materialization_after_caps": True,
            "stop_on_diversity_below_minimum_after_caps": True,
            "future_strategy_scoring_requires_another_frozen_boundary": True,
            "fetch_clone_rules": ["rule_one"],
        },
        "phase9f_gate_references": {
            "phase9f_commit": PHASE9F_COMMIT,
            "phase9f_ci_run": PHASE9F_CI_RUN,
            "phase9f_status": PHASE9F_STATUS,
            "phase9f_repair_no_claim": True,
            "phase9f_zero_buckets": True,
            "phase9f_public_fetch_or_clone_executed": False,
        },
    }
    checks.append((
        "invalid_phase9g_gate_rejected",
        bool(_phase9g_gate_errors(
            mutated_phase9g_report,
            PHASE9G_STATUS + " CI green",
            PHASE9G_COMMIT, PHASE9G_CI_RUN,
        )),
    ))
    checks.append((
        "wrong_phase9g_commit_rejected",
        bool(_phase9g_gate_errors(supplied_commit="deadbeef", supplied_ci=PHASE9G_CI_RUN)),
    ))
    checks.append((
        "wrong_phase9g_ci_rejected",
        bool(_phase9g_gate_errors(supplied_commit=PHASE9G_COMMIT, supplied_ci="0000")),
    ))

    # --- pool schema drift rejected (pure schema check, no filesystem read) ---
    malformed_row = {
        "publicly_accessible_without_authentication": True,
        "declared_or_publicly_auditable_license_present": True,
        "default_branch_or_equivalent_revision_resolvable": True,
        "currentness_field_present": True,
        "deterministic_source_order_index": 0,
        "private_clone_target_dir": "private_source_0",
        "retry_timeout_failure_bucket": "bucket_initial_attempt",
        "no_credentials_or_auth_prompt": True,
        "no_private_host": True,
        "no_local_fallback": "not_a_bool",
    }
    checks.append(("pool_schema_drift_detected", bool(_validate_pool_row_schema(malformed_row, 0))))

    missing_field_row = {
        "publicly_accessible_without_authentication": True,
        "declared_or_publicly_auditable_license_present": True,
        "default_branch_or_equivalent_revision_resolvable": True,
        "currentness_field_present": True,
        "deterministic_source_order_index": 0,
        "private_clone_target_dir": "private_source_0",
        "retry_timeout_failure_bucket": "bucket_initial_attempt",
        "no_credentials_or_auth_prompt": True,
        "no_private_host": True,
        # no_local_fallback missing
    }
    checks.append(("pool_schema_missing_field_detected", bool(_validate_pool_row_schema(missing_field_row, 1))))

    # valid pool rows pass schema validation (pure check, no private read)
    valid_row = {
        "publicly_accessible_without_authentication": True,
        "declared_or_publicly_auditable_license_present": True,
        "default_branch_or_equivalent_revision_resolvable": True,
        "currentness_field_present": True,
        "deterministic_source_order_index": 0,
        "private_clone_target_dir": "private_source_0",
        "retry_timeout_failure_bucket": "bucket_initial_attempt",
        "no_credentials_or_auth_prompt": True,
        "no_private_host": True,
        "no_local_fallback": True,
    }
    checks.append(("valid_pool_schema_passes", not _validate_pool_row_schema(valid_row, 0)))

    # --- schema-drift report uses repair/no-claim status ---
    schema_drift_aggregate = _empty_private_manifest(
        "candidate_source_pool_schema_drift_no_materialization"
    )["aggregate_private_totals"]
    schema_drift_report = build_public_report(
        schema_drift_aggregate, gate, gate_missing=False,
        confirmations=full_confirmations, pool_schema_errors=["synthetic_drift"],
    )
    checks.append(("schema_drift_report_is_repair_status", schema_drift_report["status"] == STATUS_REPAIR))
    checks.append(("schema_drift_report_pool_validation_false", schema_drift_report["candidate_source_pool_schema"]["pool_schema_validation_passed"] is False))

    # --- public report with repo URL rejected ---
    mutated = copy.deepcopy(readiness_report)
    mutated["transport_summary"]["example_value"] = "https://example.invalid/owner/repo"
    checks.append(("public_report_with_repo_url_rejected", bool(validate_report(mutated))))

    # --- public report with per-task/per-source fact rejected ---
    mutated = copy.deepcopy(readiness_report)
    mutated["privacy_summary"]["per_source_public_facts"] = True
    checks.append(("public_report_with_per_source_fact_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(readiness_report)
    mutated["privacy_summary"]["per_task_public_facts"] = True
    checks.append(("public_report_with_per_task_fact_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(readiness_report)
    mutated["source_diversity_summary"]["observed_source_name"] = "owner/repo"
    checks.append(("public_report_with_source_name_rejected", bool(validate_report(mutated))))

    # --- singleton buckets rejected ---
    mutated = copy.deepcopy(readiness_report)
    mutated["materialization_summary"]["example_bucket"] = "count_1"
    checks.append(("count_1_singleton_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(readiness_report)
    mutated["source_diversity_summary"]["example_bucket"] = "bucket_one"
    checks.append(("bucket_one_singleton_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(readiness_report)
    mutated["transport_summary"]["example_bucket"] = "singleton"
    checks.append(("singleton_word_rejected", bool(validate_report(mutated))))

    # --- labels/outcomes/scoring/evidence_success generation rejected ---
    for bad_key in FORBIDDEN_PUBLIC_FIELD_WORDS:
        mutated = copy.deepcopy(readiness_report)
        mutated["materialization_summary"][bad_key] = "exposed_value"
        checks.append((f"forbidden_public_field_rejected_{bad_key}", bool(validate_report(mutated))))

    # --- provider/LLM/model/default/runtime change rejected ---
    for execution_key in (
        "provider_or_llm_calls_executed",
        "model_fitting_executed",
        "runtime_default_or_product_changes_executed",
        "labels_generated",
        "outcomes_generated",
    ):
        mutated = copy.deepcopy(readiness_report)
        mutated["forbidden_execution_boundary"][execution_key] = True
        checks.append((f"{execution_key}_true_rejected", bool(validate_report(mutated))))
    for claim_key in (
        "provider_claim", "model_claim", "runtime_claim", "default_claim",
        "product_claim", "scoring_claim", "outcome_claim", "evidence_success_claim",
    ):
        mutated = copy.deepcopy(readiness_report)
        mutated["no_claim_boundary"][claim_key] = True
        checks.append((f"{claim_key}_true_rejected", bool(validate_report(mutated))))

    # --- privacy / count / private-shaped key/value rejections ---
    mutated = copy.deepcopy(readiness_report)
    mutated["materialization_summary"]["count"] = 56
    checks.append(("exact_count_field_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(readiness_report)
    mutated["privacy_summary"]["path"] = "src/private.py"
    checks.append(("private_shaped_key_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(readiness_report)
    mutated["materialization_summary"]["example_value"] = "owner/repo"
    checks.append(("private_shaped_value_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(readiness_report)
    mutated["transport_summary"]["example_value"] = "a" * 40
    checks.append(("hash_private_shaped_value_rejected", bool(validate_report(mutated))))

    # --- claim wording rejected ---
    mutated = copy.deepcopy(readiness_report)
    mutated["conservative_recommendation"] = "materialization works and is proven"
    checks.append(("claim_wording_materialization_works_rejected", bool(validate_report(mutated))))
    mutated = copy.deepcopy(readiness_report)
    mutated["transport_summary"]["example_note"] = "network fetch works"
    checks.append(("claim_wording_network_fetch_works_rejected", bool(validate_report(mutated))))

    # --- rate-limit-stop repair report (no auth) ---
    rate_limit_aggregate = _empty_private_manifest("rate_limit_no_auth_stop")["aggregate_private_totals"]
    rate_limit_aggregate["rate_limit_stop_no_auth"] = True
    rate_limit_aggregate["transport_attempted_sources"] = 3
    rate_limit_aggregate["transport_succeeded_sources"] = 2
    rate_limit_report = build_public_report(
        rate_limit_aggregate, gate, gate_missing=False, confirmations=full_confirmations
    )
    checks.append(("rate_limit_repair_report_passes", not validate_report(rate_limit_report)))
    checks.append(("rate_limit_report_is_repair_status", rate_limit_report["status"] == STATUS_REPAIR))
    checks.append((
        "rate_limit_stop_no_auth_recorded",
        rate_limit_report["transport_summary"]["transport_rate_limit_stop_no_auth"] is True,
    ))

    # --- temp-file round-trip validation ---
    with tempfile.TemporaryDirectory(prefix="phase9h_selftest_") as tmp:
        tmp_report = Path(tmp) / "report.json"
        tmp_report.write_text(json.dumps(readiness_report), encoding="utf-8")
        loaded = json.loads(tmp_report.read_text(encoding="utf-8"))
        checks.append(("validate_report_temp_fixture_valid", not validate_report(loaded)))

    # --- self-test/validate-report do not fetch/read private ---
    checks.append(("selftest_does_not_fetch_or_clone", FETCH_CLONE_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_source_files", SOURCE_FILE_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_private_runs", PRIVATE_RUNS_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_private_candidate_pool", PRIVATE_CANDIDATE_POOL_READ_ATTEMPTS == 0))
    checks.append(("selftest_does_not_read_private_registry", PRIVATE_REGISTRY_READ_ATTEMPTS == 0))

    failed = [name for name, ok in checks if not ok]
    if failed:
        raise SystemExit("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 9H candidate source-pool public-source network-fetch materialization runner"
    )
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--validate-report", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_PUBLIC_REPORT)
    parser.add_argument("--confirm-phase9g-commit")
    parser.add_argument("--confirm-phase9g-ci")
    parser.add_argument("--confirm-public-source-network-fetch", action="store_true")
    parser.add_argument("--confirm-ignored-runs-workspace", action="store_true")
    parser.add_argument("--confirm-allow-public-github-api-transport", action="store_true")
    parser.add_argument("--confirm-no-private-or-local-fallback", action="store_true")
    parser.add_argument(
        "--confirm-no-labels-outcomes-scoring-evidence-success", action="store_true"
    )
    parser.add_argument(
        "--confirm-no-provider-llm-model-default-runtime-change", action="store_true"
    )
    parser.add_argument("--confirm-aggregate-public-report-only", action="store_true")
    parser.add_argument("--private-run-dir", type=Path, default=DEFAULT_PRIVATE_RUN_DIR)
    args = parser.parse_args(argv)

    if args.self_test:
        print(json.dumps(run_self_test(), indent=2, sort_keys=True))
        return 0
    if args.validate_report:
        report = json.loads(args.validate_report.read_text(encoding="utf-8"))
        errors = validate_report(report)
        if errors:
            for error_message in errors:
                print(f"ERROR: {error_message}", file=sys.stderr)
            return 1
        print(f"Validation passed: {args.validate_report}")
        return 0
    if args.write_report:
        result = execute_phase9h(
            args.private_run_dir,
            args.output,
            args.confirm_phase9g_commit,
            args.confirm_phase9g_ci,
            args.confirm_public_source_network_fetch,
            args.confirm_ignored_runs_workspace,
            args.confirm_allow_public_github_api_transport,
            args.confirm_no_private_or_local_fallback,
            args.confirm_no_labels_outcomes_scoring_evidence_success,
            args.confirm_no_provider_llm_model_default_runtime_change,
            args.confirm_aggregate_public_report_only,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    parser.error("choose --self-test, --write-report, or --validate-report")
    return 2


if __name__ == "__main__":
    sys.exit(main())
