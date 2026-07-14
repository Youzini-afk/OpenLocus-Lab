#!/usr/bin/env python3
"""B2 real-repository wrappers for the frozen S0-S5 product stacks.

The production components, descriptors, lifecycle, parser, receipts, and
resource isolation remain the B1-closed implementation.  B2 changes only the
source of the frozen visible-file declaration and the multi-target binding
needed by the predeclared ambiguous-task scoring rule.
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from product_bakeoff_contract import (
    AdapterHooks,
    AdapterRequest,
    AdapterResult,
    BindingProposal,
    ContractError,
)
from product_bakeoff_b1_spec import (
    B1_ADAPTER_VERSION,
    B1_INDEX_SEAL_REL,
    B1_LINEAGE_RECEIPT_REL,
    B1_MAX_CANDIDATES,
    B1_ONE_SHOT_MAX_TARGETS,
    B1_TWO_STEP_MAX_SUPPORT,
    S0_ADAPTER_ID,
    S0_OUTPUT_CHANNELS,
    S1_ADAPTER_ID,
    S1_OUTPUT_CHANNELS,
    S2_ADAPTER_ID,
    S2_OUTPUT_CHANNELS,
    S3_ADAPTER_ID,
    S3_OUTPUT_CHANNELS,
    S4_ADAPTER_ID,
    S4_OUTPUT_CHANNELS,
    S5_ADAPTER_ID,
    S5_OUTPUT_CHANNELS,
    adapter_context_components,
    adapter_support_components,
    adapter_supports_support,
)
from product_bakeoff_b1_adapters import (
    RustReceiptError,
    _b1_prepare,
    _build_ledger,
    _context_binding,
    _evidence_to_candidates,
    _find_cli,
    _is_reparse_or_link,
    _no_evidence_binding,
    _ordered_components,
    _run_transcribed_command,
    _support_binding,
    _write_local_transcript,
    load_invocation_transcript,
    parse_bakeoff_query,
    s0_descriptor,
    s1_descriptor,
    s2_descriptor,
    s3_descriptor,
    s4_descriptor,
    s5_descriptor,
    verify_index_seal,
)
from product_bakeoff_b2_corpus import (
    B2CorpusError,
    load_json,
    validate_external_visible_manifest,
)


B2_VISIBLE_MANIFEST_ENV = "OPENLOCUS_B2_VISIBLE_MANIFEST"
B2_ADAPTER_VERSION = B1_ADAPTER_VERSION


def _visible_manifest_path() -> Path:
    raw = os.environ.get(B2_VISIBLE_MANIFEST_ENV)
    if not raw or len(raw) > 4096:
        raise ContractError("B2 visible manifest environment binding is missing")
    path = Path(raw)
    if not path.is_absolute() or not path.is_file() or _is_reparse_or_link(path):
        raise ContractError("B2 visible manifest path is missing or unsafe")
    try:
        if path.stat().st_size > 16 * 1024 * 1024:
            raise ContractError("B2 visible manifest exceeds 16 MiB")
    except OSError as exc:
        raise ContractError("cannot stat B2 visible manifest") from exc
    return path


def get_b2_visible_files(request: AdapterRequest) -> tuple[str, ...]:
    try:
        raw = load_json(_visible_manifest_path())
        return validate_external_visible_manifest(
            raw,
            snapshot_manifest_digest=request.run_spec.snapshot_manifest_digest,
            source_visibility_digest=request.run_spec.source_visibility_digest,
            visible_tree_digest=request.run_spec.visible_tree_digest,
        )
    except B2CorpusError as exc:
        raise ContractError(f"B2 visible manifest rejected: {exc}") from exc


def _b2_context_binding(
    request: AdapterRequest, candidates: tuple[Any, ...]
) -> BindingProposal:
    if request.run_spec.interaction_mode == "two_step":
        return _context_binding(candidates, 1, check_tie=False)
    if request.run_spec.task.task_family != "ambiguous_target":
        return _context_binding(candidates, B1_ONE_SHOT_MAX_TARGETS)
    if not candidates:
        return _no_evidence_binding("all executed components returned zero")
    indices: list[int] = []
    paths: set[str] = set()
    for index, candidate in enumerate(candidates):
        if candidate.path in paths:
            continue
        indices.append(index)
        paths.add(candidate.path)
        if len(indices) == B1_ONE_SHOT_MAX_TARGETS:
            break
    if len(indices) >= 2:
        return BindingProposal(
            proposed_status="uncertain",
            target_evidence_indices=tuple(indices),
            support_bindings=(),
            status_reason="multiple distinct source locations for ambiguous task",
        )
    return BindingProposal(
        proposed_status="ready",
        target_evidence_indices=(0,),
        support_bindings=(),
    )


def _run_b2_bakeoff_query(
    request: AdapterRequest,
    isolated_root: Path,
    args: list[str],
    *,
    expected_components: frozenset[str],
    expected_mode: str,
    expected_parent: tuple[str, int, int] | None = None,
):
    cli = _find_cli()
    stdout = _run_transcribed_command(
        request,
        isolated_root,
        phase="query",
        command_kind="rust_bakeoff_query",
        command=[cli, "bakeoff-query", *args],
        cwd=str(isolated_root.resolve()),
        timeout=request.run_spec.timeout_seconds,
    )
    return parse_bakeoff_query(
        stdout,
        expected_components,
        get_b2_visible_files(request),
        expected_mode,
        request.run_spec.request_id,
        expected_source_root=isolated_root,
        expected_state_root=isolated_root,
        expected_query=(
            request.run_spec.task.query if expected_mode == "context" else None
        ),
        expected_task_family=(
            request.run_spec.task.task_family if expected_mode == "context" else None
        ),
        expected_max_results=(
            B1_MAX_CANDIDATES
            if expected_mode == "context"
            else B1_TWO_STEP_MAX_SUPPORT
        ),
    )


def _b2_context_query(
    request: AdapterRequest,
    isolated_root: Path,
    adapter_id: str,
    descriptor_channels: frozenset[str],
) -> AdapterResult:
    query = request.run_spec.task.query
    components = adapter_context_components(adapter_id)
    sealed = (isolated_root / B1_INDEX_SEAL_REL).is_file()
    if sealed:
        verify_index_seal(isolated_root)
    args = [
        "context",
        "--source-root", str(isolated_root.resolve()),
        "--state-root", str(isolated_root.resolve()),
        "--query", query,
        "--components", ",".join(_ordered_components(components)),
        "--task-family", request.run_spec.task.task_family,
        "--max-results", str(B1_MAX_CANDIDATES),
        "--json",
    ]
    try:
        parsed = _run_b2_bakeoff_query(
            request,
            isolated_root,
            args,
            expected_components=components,
            expected_mode="context",
        )
    except (RuntimeError, RustReceiptError, ContractError) as exc:
        return AdapterResult(
            status="failed",
            failure_category=f"adapter_exception:{type(exc).__name__}",
            candidates=(),
            capability_ledger=_build_ledger(
                adapter_id,
                False,
                False,
                False,
                False,
                request.run_spec.cache_state != "warm",
            ),
            fallback_provenance=(),
        )
    finally:
        if sealed:
            verify_index_seal(isolated_root)
    for receipt in parsed.receipts:
        if receipt.status == "error":
            return AdapterResult(
                status="failed",
                failure_category="adapter_exception:FailedResult",
                candidates=(),
                capability_ledger=_build_ledger(
                    adapter_id,
                    False,
                    False,
                    False,
                    False,
                    request.run_spec.cache_state != "warm",
                ),
                fallback_provenance=(),
            )
    candidates = _evidence_to_candidates(
        parsed.evidence,
        adapter_id,
        descriptor_channels,
        B1_MAX_CANDIDATES,
        mode="context",
    )
    binding = _b2_context_binding(request, candidates)
    ledger = _build_ledger(
        adapter_id,
        False,
        bool(candidates),
        bool(binding.target_evidence_indices),
        False,
        request.run_spec.cache_state != "warm",
    )
    return AdapterResult(
        status="ok",
        failure_category=None,
        candidates=candidates,
        capability_ledger=ledger,
        fallback_provenance=(),
        binding_proposal=binding,
    )


def _read_parent_receipt(
    request: AdapterRequest, isolated_root: Path
) -> dict[str, Any] | None:
    receipt_path = isolated_root / B1_LINEAGE_RECEIPT_REL
    if not receipt_path.is_file() or _is_reparse_or_link(receipt_path):
        return None
    try:
        data = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or set(data) != {
        "schema_version", "request_id", "parent_result_id", "bound_target_id",
        "target_path", "target_start_line", "target_end_line",
        "snapshot_manifest_digest", "parent_canonical_result_hash",
        "parent_canonical_pack_hash",
    }:
        return None
    expected = {
        "schema_version": "product_bakeoff_b1_lineage.v1",
        "request_id": request.run_spec.request_id,
        "parent_result_id": request.run_spec.parent_result_id,
        "bound_target_id": request.run_spec.bound_target_id,
        "snapshot_manifest_digest": request.run_spec.snapshot_manifest_digest,
    }
    if any(data.get(key) != value for key, value in expected.items()):
        return None
    for key, prefix in (
        ("parent_canonical_result_hash", "crh_"),
        ("parent_canonical_pack_hash", "cph_"),
    ):
        if not isinstance(data.get(key), str) or not re.fullmatch(
            rf"{prefix}[0-9a-f]{{16}}", data[key]
        ):
            return None
    path = data.get("target_path")
    start = data.get("target_start_line")
    end = data.get("target_end_line")
    if path not in set(get_b2_visible_files(request)):
        return None
    if not isinstance(start, int) or isinstance(start, bool) or start < 1:
        return None
    if not isinstance(end, int) or isinstance(end, bool) or end < start:
        return None
    return {"path": path, "start_line": start, "end_line": end}


def _b2_support_query(
    request: AdapterRequest,
    isolated_root: Path,
    adapter_id: str,
    descriptor_channels: frozenset[str],
    parent_path: str,
    parent_start: int,
    parent_end: int,
    bound_target_id: str,
) -> AdapterResult:
    if not adapter_supports_support(adapter_id):
        _write_local_transcript(
            request,
            isolated_root,
            phase="query",
            command_kind="local_support_predicate_skip",
            local_receipt={
                "component": "support",
                "status": "legitimate_skip",
                "reason": "adapter_support_predicate_false",
                "evidence_count": 0,
            },
        )
        return AdapterResult(
            status="ok",
            failure_category=None,
            candidates=(),
            capability_ledger=_build_ledger(
                adapter_id,
                True,
                False,
                False,
                False,
                request.run_spec.cache_state != "warm",
            ),
            fallback_provenance=(),
            binding_proposal=_no_evidence_binding(
                "adapter does not support support expansion"
            ),
        )
    components = adapter_support_components(adapter_id)
    verify_index_seal(isolated_root)
    args = [
        "support",
        "--source-root", str(isolated_root.resolve()),
        "--state-root", str(isolated_root.resolve()),
        "--parent-path", parent_path,
        "--parent-range", f"{parent_start}-{parent_end}",
        "--max-results", str(B1_TWO_STEP_MAX_SUPPORT),
        "--json",
    ]
    try:
        parsed = _run_b2_bakeoff_query(
            request,
            isolated_root,
            args,
            expected_components=components,
            expected_mode="support",
            expected_parent=(parent_path, parent_start, parent_end),
        )
    except (RuntimeError, RustReceiptError, ContractError) as exc:
        return AdapterResult(
            status="failed",
            failure_category=f"adapter_exception:{type(exc).__name__}",
            candidates=(),
            capability_ledger=_build_ledger(
                adapter_id,
                True,
                False,
                False,
                False,
                request.run_spec.cache_state != "warm",
            ),
            fallback_provenance=(),
        )
    finally:
        verify_index_seal(isolated_root)
    if any(receipt.status == "error" for receipt in parsed.receipts):
        return AdapterResult(
            status="failed",
            failure_category="adapter_exception:FailedResult",
            candidates=(),
            capability_ledger=_build_ledger(
                adapter_id,
                True,
                False,
                False,
                False,
                request.run_spec.cache_state != "warm",
            ),
            fallback_provenance=(),
        )
    if (
        parsed.parent_path != parent_path
        or parsed.parent_start_line != parent_start
        or parsed.parent_end_line != parent_end
    ):
        raise RustReceiptError("B2 support parent echo mismatch")
    candidates = _evidence_to_candidates(
        parsed.evidence,
        adapter_id,
        descriptor_channels,
        B1_TWO_STEP_MAX_SUPPORT,
        mode="support",
    )
    binding = _support_binding(
        candidates,
        parsed.support_relations,
        B1_TWO_STEP_MAX_SUPPORT,
        bound_target_id,
    )
    ledger = _build_ledger(
        adapter_id,
        True,
        bool(candidates),
        False,
        bool(binding.support_bindings),
        request.run_spec.cache_state != "warm",
    )
    return AdapterResult(
        status="ok",
        failure_category=None,
        candidates=candidates,
        capability_ledger=ledger,
        fallback_provenance=(),
        binding_proposal=binding,
    )


def _dispatch(
    request: AdapterRequest,
    isolated_root: Path,
    adapter_id: str,
    descriptor_channels: frozenset[str],
) -> AdapterResult:
    if request.run_spec.operation == "context":
        return _b2_context_query(
            request, isolated_root, adapter_id, descriptor_channels
        )
    parent = _read_parent_receipt(request, isolated_root)
    if parent is None:
        return AdapterResult(
            status="failed",
            failure_category="lineage:unknown_parent_target",
            candidates=(),
            capability_ledger=_build_ledger(
                adapter_id,
                True,
                False,
                False,
                False,
                request.run_spec.cache_state != "warm",
            ),
            fallback_provenance=(),
        )
    return _b2_support_query(
        request,
        isolated_root,
        adapter_id,
        descriptor_channels,
        parent["path"],
        parent["start_line"],
        parent["end_line"],
        request.run_spec.bound_target_id or "",
    )


def s0_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    return _dispatch(request, isolated_root, S0_ADAPTER_ID, S0_OUTPUT_CHANNELS)


def s1_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    return _dispatch(request, isolated_root, S1_ADAPTER_ID, S1_OUTPUT_CHANNELS)


def s2_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    return _dispatch(request, isolated_root, S2_ADAPTER_ID, S2_OUTPUT_CHANNELS)


def s3_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    return _dispatch(request, isolated_root, S3_ADAPTER_ID, S3_OUTPUT_CHANNELS)


def s4_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    return _dispatch(request, isolated_root, S4_ADAPTER_ID, S4_OUTPUT_CHANNELS)


def s5_query(request: AdapterRequest, isolated_root: Path) -> AdapterResult:
    return _dispatch(request, isolated_root, S5_ADAPTER_ID, S5_OUTPUT_CHANNELS)


def s0_hooks() -> AdapterHooks:
    return AdapterHooks(prepare=_b1_prepare, index=None, query=s0_query).validate()


def s1_hooks() -> AdapterHooks:
    return AdapterHooks(prepare=_b1_prepare, index=None, query=s1_query).validate()


def s2_hooks() -> AdapterHooks:
    return AdapterHooks(prepare=_b1_prepare, index=None, query=s2_query).validate()


def s3_hooks() -> AdapterHooks:
    return AdapterHooks(prepare=_b1_prepare, index=None, query=s3_query).validate()


def s4_hooks() -> AdapterHooks:
    return AdapterHooks(prepare=_b1_prepare, index=None, query=s4_query).validate()


def s5_hooks() -> AdapterHooks:
    return AdapterHooks(prepare=_b1_prepare, index=None, query=s5_query).validate()


_B2_SUPPORTED_LANGUAGES = frozenset({"rust", "python", "typescript"})


def _b2_descriptor(factory):
    return dataclasses.replace(
        factory(), supported_languages=_B2_SUPPORTED_LANGUAGES
    ).validate()


def b2_s0_descriptor():
    return _b2_descriptor(s0_descriptor)


def b2_s1_descriptor():
    return _b2_descriptor(s1_descriptor)


def b2_s2_descriptor():
    return _b2_descriptor(s2_descriptor)


def b2_s3_descriptor():
    return _b2_descriptor(s3_descriptor)


def b2_s4_descriptor():
    return _b2_descriptor(s4_descriptor)


def b2_s5_descriptor():
    return _b2_descriptor(s5_descriptor)


B2_ADAPTERS: tuple[tuple[str, Any, Any], ...] = (
    (S0_ADAPTER_ID, b2_s0_descriptor, s0_hooks),
    (S1_ADAPTER_ID, b2_s1_descriptor, s1_hooks),
    (S2_ADAPTER_ID, b2_s2_descriptor, s2_hooks),
    (S3_ADAPTER_ID, b2_s3_descriptor, s3_hooks),
    (S4_ADAPTER_ID, b2_s4_descriptor, s4_hooks),
    (S5_ADAPTER_ID, b2_s5_descriptor, s5_hooks),
)


def parse_b2_query_transcript(
    request: AdapterRequest, isolated_root: Path
):
    transcript = load_invocation_transcript(request, isolated_root, "query")
    if transcript["command_kind"] == "local_support_predicate_skip":
        expected = {
            "component": "support",
            "status": "legitimate_skip",
            "reason": "adapter_support_predicate_false",
            "evidence_count": 0,
        }
        if transcript["local_receipt"] != expected:
            raise ContractError("B2 local support skip receipt mismatch")
        if adapter_supports_support(request.adapter_id):
            raise ContractError("support-capable B2 adapter used local skip")
        return transcript, None
    if transcript["command_kind"] != "rust_bakeoff_query":
        raise ContractError("B2 query transcript command mismatch")
    mode = request.run_spec.operation
    components = (
        adapter_context_components(request.adapter_id)
        if mode == "context"
        else adapter_support_components(request.adapter_id)
    )
    parsed = parse_bakeoff_query(
        transcript["_stdout_bytes"],
        components,
        get_b2_visible_files(request),
        mode,
        request.run_spec.request_id,
        expected_source_root=isolated_root,
        expected_state_root=isolated_root,
        expected_query=(request.run_spec.task.query if mode == "context" else None),
        expected_task_family=(
            request.run_spec.task.task_family if mode == "context" else None
        ),
        expected_max_results=(
            B1_MAX_CANDIDATES if mode == "context" else B1_TWO_STEP_MAX_SUPPORT
        ),
    )
    root_text = str(isolated_root.resolve())
    if mode == "context":
        expected_argv = [
            _find_cli(), "bakeoff-query", "context",
            "--source-root", root_text,
            "--state-root", root_text,
            "--query", request.run_spec.task.query,
            "--components", ",".join(_ordered_components(components)),
            "--task-family", request.run_spec.task.task_family,
            "--max-results", str(B1_MAX_CANDIDATES),
            "--json",
        ]
    else:
        expected_argv = [
            _find_cli(), "bakeoff-query", "support",
            "--source-root", root_text,
            "--state-root", root_text,
            "--parent-path", parsed.parent_path or "",
            "--parent-range", f"{parsed.parent_start_line}-{parsed.parent_end_line}",
            "--max-results", str(B1_TWO_STEP_MAX_SUPPORT),
            "--json",
        ]
    if transcript["argv"] != expected_argv:
        raise ContractError("B2 query transcript argv mismatch")
    return transcript, parsed


def run_self_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    class CandidateStub:
        def __init__(self, path: str):
            self.path = path

    class TaskStub:
        task_family = "ambiguous_target"

    class RunSpecStub:
        interaction_mode = "one_shot"
        task = TaskStub()

    class RequestStub:
        run_spec = RunSpecStub()

    binding = _b2_context_binding(
        RequestStub(), (CandidateStub("a.rs"), CandidateStub("b.rs"))
    )
    checks.append(("ambiguous_multi_target", binding.proposed_status == "uncertain"))
    checks.append(("ambiguous_two_targets", binding.target_evidence_indices == (0, 1)))
    checks.append((
        "python_declared_supported",
        all("python" in descriptor_factory().supported_languages
            for _, descriptor_factory, _ in B2_ADAPTERS),
    ))
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def run_fault_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    old = os.environ.pop(B2_VISIBLE_MANIFEST_ENV, None)
    try:
        class RunSpecStub:
            snapshot_manifest_digest = "snap_" + "a" * 24
            source_visibility_digest = "vis_" + "b" * 24
            visible_tree_digest = "tree_" + "c" * 24

        class RequestStub:
            run_spec = RunSpecStub()

        try:
            get_b2_visible_files(RequestStub())
            missing_rejected = False
        except ContractError:
            missing_rejected = True
        checks.append(("missing_manifest_env_rejected", missing_rejected))
    finally:
        if old is not None:
            os.environ[B2_VISIBLE_MANIFEST_ENV] = old
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


__all__ = [
    "B2_VISIBLE_MANIFEST_ENV", "B2_ADAPTER_VERSION", "B2_ADAPTERS",
    "get_b2_visible_files", "parse_b2_query_transcript",
    "run_self_test", "run_fault_test",
]
