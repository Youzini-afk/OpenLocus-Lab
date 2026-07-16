#!/usr/bin/env python3
"""Validate closed product-bakeoff artifacts without rebinding them to HEAD.

The B2 through B2.5 protocols intentionally froze the implementation source
that existed before each formal attempt.  Once an attempt is terminal, later
product fixes are expected to change that implementation.  Re-running an old
``--check-drift`` against the current checkout therefore confuses two distinct
questions:

* did a closed public artifact change; and
* does today's implementation still equal the historical frozen source.

This archive validator answers only the first question.  It locks the exact
canonical JSON of every public parent, checks self-digests where their original
construction is canonical, and verifies the public cross-phase bindings.  It
never reads a private manifest, run directory, repository identity, query,
oracle row, score, rank, or runner receipt.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ArtifactSpec:
    name: str
    relative_path: str
    schema_version: str
    status: str
    canonical_sha256: str
    digest_field: str | None = None
    digest_prefix: str | None = None
    expected_digest: str | None = None
    recompute_digest: bool = True


SPECS: tuple[ArtifactSpec, ...] = (
    ArtifactSpec(
        "b2_protocol",
        "artifacts/product_bakeoff_b2_protocol/product_bakeoff_b2_protocol_report.json",
        "product_bakeoff_b2_protocol_report.v1",
        "product_bakeoff_b2_protocol_frozen_no_execution_no_result",
        "3c921671e2fc0cef73bb8842760a342aeaa516e215f709bf9fa13eff7ea06105",
        "protocol_digest",
        "b2protocol_",
        "b2protocol_9057cbb85bb11f84377424a96ea2de55e7bff80314520b89b3c0c1e35340b679",
    ),
    ArtifactSpec(
        "b2_failure",
        "artifacts/product_bakeoff_b2/product_bakeoff_b2_failed_closed_aggregate.json",
        "product_bakeoff_b2_failed_closed_aggregate.v1",
        "product_bakeoff_b2_execution_failed_closed_no_result",
        "b3ee202547b83b893b0890584ddf4aae7eee0965b6a977a7bc24d9ef1a0f4376",
    ),
    ArtifactSpec(
        "b21_protocol",
        "artifacts/product_bakeoff_b21_protocol/product_bakeoff_b21_protocol_report.json",
        "product_bakeoff_b21_protocol_report.v1",
        "product_bakeoff_b21_implementation_ready_preflight_passed_no_holdout_no_result",
        "1b46cc6b551d6cf4f85921cb3278fffd5417bd29779dfb89409526f7e706af50",
        "protocol_digest",
        "b21protocol_",
        "b21protocol_385333bd86ba0a553229caf0797ceb2ef1acd18f05cae8f9a4edcff16ba5c2e1",
    ),
    ArtifactSpec(
        "b21_failure",
        "artifacts/product_bakeoff_b21/product_bakeoff_b21_failed_closed_aggregate.json",
        "product_bakeoff_b21_failed_closed_aggregate.v1",
        "product_bakeoff_b21_execution_failed_closed_no_result",
        "6309673f7ca0a3725cf7c9fc15eeb267e90a127cbbc234a6ff6d07e8c675354c",
        "failure_aggregate_digest",
        "b21failure_",
        "b21failure_6feabc0f3ffa4efc396a5195417f15ff4e21527f753114f1854951ddc855b68c",
    ),
    ArtifactSpec(
        "b22_protocol",
        "artifacts/product_bakeoff_b22_protocol/product_bakeoff_b22_protocol_report.json",
        "product_bakeoff_b22_protocol_report.v1",
        "product_bakeoff_b22_runner_protocol_ready_no_runner_no_holdout_no_result",
        "11b756801cba0637932b7196099df357caad47762a332d92afaa001a44bb01ae",
        "protocol_digest",
        "b22protocol_",
        "b22protocol_a84b309cf327a81325eb38451682beb8077cd93e2e9a49b3befc65fc4219e425",
    ),
    ArtifactSpec(
        "b23_protocol",
        "artifacts/product_bakeoff_b23_protocol/product_bakeoff_b23_protocol_report.json",
        "product_bakeoff_b23_protocol_report.v1",
        "product_bakeoff_b23_linux_longrun_protocol_ready_no_runner_qualification_no_holdout_no_result",
        "99d3c7ef43f12f5d08736f9569de4638a5fd7c82c8e73249031508e324e4852f",
        "protocol_digest",
        "b23protocol_",
        "b23protocol_4e59c0b0496aeaf3f5adfc88148d22e8edd617f075831b82152a805aa836bf23",
    ),
    ArtifactSpec(
        "b23_qualification",
        "artifacts/product_bakeoff_b23_runner_qualification/product_bakeoff_b23_runner_qualification.json",
        "product_bakeoff_b23_runner_qualification_public.v1",
        "product_bakeoff_b23_runner_qualified_no_private_input_read",
        "aa9b73c64528652215f5fd02fea093614261a309b94a33e27a4771e09b76f236",
        "qualification_digest",
        "b23qual_",
        "b23qual_0ba839c5e02c96a7c8c879532ad354f19a6405cd6dd3f9885baa2ea3c1a499a1",
    ),
    ArtifactSpec(
        "b24_protocol",
        "artifacts/product_bakeoff_b24_protocol/product_bakeoff_b24_protocol_report.json",
        "product_bakeoff_b24_protocol_report.v1",
        "product_bakeoff_b24_preexecution_launcher_correction_ready_no_private_holdout_no_tournament_no_result",
        "613fac66dd316eea02e12cf083738fff5ff80df8d8092d3f6cf19738ed569f2d",
        "protocol_digest",
        "b24protocol_",
        "b24protocol_ec4bc650b509781477fde7cf2c6bf5532221d86e3379364a1df8741570a5c222",
    ),
    ArtifactSpec(
        "b24_readiness",
        "artifacts/product_bakeoff_b24_readiness/product_bakeoff_b24_holdout_readiness.json",
        "product_bakeoff_b24_holdout_readiness.v1",
        "product_bakeoff_b24_private_holdout_frozen_no_treatment_output_no_result",
        "1a7c4c2562373a0358a421306ee3caf1ab01d973100de051ae96c76444bc5626",
        "readiness_digest",
        "b24ready_",
        "b24ready_86eb4cfe65fed9e38af6f2ce3c369afb257a05055747c17446cad89028718fc0",
    ),
    ArtifactSpec(
        "b24_failure",
        "artifacts/product_bakeoff_b24/product_bakeoff_b24_failed_closed_aggregate.json",
        "product_bakeoff_b24_failed_closed_aggregate.v1",
        "product_bakeoff_b24_execution_failed_closed_no_result",
        "a4855074c7e6236d4c62668038aebacb5bc837dbd99bd5c2926fddebf5c0e29f",
        "failure_aggregate_digest",
        expected_digest="b24failure_a41d6e150a5e5c2752cfb455b0ca5dd1df35687b9489d82e5a888362dc4c4b83",
        recompute_digest=False,
    ),
    ArtifactSpec(
        "b24_repair",
        "artifacts/product_bakeoff_b24_repair/product_bakeoff_b24_bm25_tokenizer_repair.json",
        "product_bakeoff_b24_bm25_tokenizer_repair.v1",
        "product_bakeoff_b24_postcloseout_bm25_tokenizer_repair_complete_b25_design_authorized",
        "3259733ba7346418d1b98c9e3a50bb28ba2838755c9c5216d379d17bf319bbd3",
        "repair_digest",
        expected_digest="b24repair_2a4e664f19e8c72de3f6f4b09f4476f5313c01b547bbb141cb5c26a394473136",
        recompute_digest=False,
    ),
    ArtifactSpec(
        "b25_protocol",
        "artifacts/product_bakeoff_b25_protocol/product_bakeoff_b25_protocol_report.json",
        "product_bakeoff_b25_protocol_report.v2",
        "product_bakeoff_b25_protocol_ready_runtime_qualification_pending_no_private_holdout_no_tournament_no_result",
        "deecba85fb83d72512b051472eb1170449f2117a2ee429ac1b5865b5f2c363da",
        "protocol_digest",
        "b25protocol_",
        "b25protocol_cdb3ec1eb55acd1bf5ba1de39a76deccc525b0dbf6f0d7e74d2ee2b2c20e8ba7",
    ),
    ArtifactSpec(
        "b25_qualification",
        "artifacts/product_bakeoff_b25_runtime_qualification/product_bakeoff_b25_runtime_qualification.json",
        "product_bakeoff_b25_runtime_qualification_report.v2",
        "product_bakeoff_b25_repaired_runtime_synthetically_qualified_private_authoring_allowed_tournament_not_authorized",
        "6e1f62acd002ce7589093afdd51fd388b5e7dc7414eeae517268a591b734d96c",
        "qualification_digest",
        "b25qual_",
        "b25qual_c908d1a1598fc44da290c1129b01d054ab2ed2cafe0b99a8b08234daa1ec7230",
    ),
    ArtifactSpec(
        "b25_readiness",
        "artifacts/product_bakeoff_b25_readiness/product_bakeoff_b25_holdout_readiness.json",
        "product_bakeoff_b25_holdout_readiness.v1",
        "product_bakeoff_b25_private_holdout_frozen_query_compatible_no_treatment_output_no_result",
        "9b6b61f6a6ceceb424b507c40a2ec9627a6dfa158f08a74b0630451ee4f213f7",
        "readiness_digest",
        "b25ready_",
        "b25ready_b9c2010e61e804ab3e0499ab60489edfe90ab7300c1e6dff5651da891f468531",
    ),
    ArtifactSpec(
        "b25_failure",
        "artifacts/product_bakeoff_b25/product_bakeoff_b25_failed_closed_aggregate.json",
        "product_bakeoff_b25_failed_closed_aggregate.v1",
        "product_bakeoff_b25_execution_failed_closed_no_result",
        "f1d3d6999e8c3f05cbdd1927b379f97fca7e7a9ca935748dcdecce07b7fd57e7",
        "failure_aggregate_digest",
        "b25failure_",
        "b25failure_012f59fc4d7d717b4f1d4f0da5513430637d4a6cc6eaf8a326a35adc339302fd",
    ),
)

SPEC_BY_NAME = {spec.name: spec for spec in SPECS}

_B2_ARCHIVE = ("b2_protocol", "b2_failure")
_B24_ARCHIVE = (
    *_B2_ARCHIVE,
    "b21_protocol",
    "b21_failure",
    "b22_protocol",
    "b23_protocol",
    "b23_qualification",
    "b24_protocol",
    "b24_readiness",
    "b24_failure",
    "b24_repair",
)
_B25_PARENT_ARCHIVE = (
    *_B24_ARCHIVE,
    "b25_protocol",
    "b25_qualification",
    "b25_readiness",
)
_B25_ARCHIVE = (*_B25_PARENT_ARCHIVE, "b25_failure")

GROUPS = {
    "b2": _B2_ARCHIVE,
    "b24": _B24_ARCHIVE,
    "b25_parents": _B25_PARENT_ARCHIVE,
    "b25": _B25_ARCHIVE,
    "all": _B25_ARCHIVE,
}


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _normalized_file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _artifact_path(spec: ArtifactSpec) -> Path:
    path = REPO_ROOT / spec.relative_path
    try:
        path.resolve(strict=False).relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"{spec.name}: artifact path escapes repository") from exc
    return path


def _load_documents(names: tuple[str, ...]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    documents: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for name in names:
        spec = SPEC_BY_NAME[name]
        path = _artifact_path(spec)
        if path.is_symlink() or not path.is_file():
            errors.append(f"{name}: artifact missing or unsafe")
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"{name}: artifact unreadable ({type(exc).__name__})")
            continue
        if not isinstance(value, dict):
            errors.append(f"{name}: artifact must be an object")
            continue
        documents[name] = value
    return documents, errors


def _validate_document(spec: ArtifactSpec, value: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if value.get("schema_version") != spec.schema_version:
        errors.append(f"{spec.name}: schema mismatch")
    if value.get("status") != spec.status:
        errors.append(f"{spec.name}: status mismatch")
    if _canonical_sha256(value) != spec.canonical_sha256:
        errors.append(f"{spec.name}: canonical archive lock mismatch")
    if spec.digest_field is not None:
        observed = value.get(spec.digest_field)
        if observed != spec.expected_digest:
            errors.append(f"{spec.name}: declared digest mismatch")
        if spec.recompute_digest:
            payload = copy.deepcopy(dict(value))
            payload.pop(spec.digest_field, None)
            expected = (spec.digest_prefix or "") + hashlib.sha256(
                _canonical(payload)
            ).hexdigest()
            if observed != expected:
                errors.append(f"{spec.name}: self-digest mismatch")
    return errors


def _get(value: Mapping[str, Any], *keys: str) -> Any:
    current: Any = value
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _expect(
    errors: list[str],
    label: str,
    left: Any,
    right: Any,
) -> None:
    if left != right:
        errors.append(f"cross-link: {label}")


def _validate_cross_links(documents: Mapping[str, Mapping[str, Any]]) -> list[str]:
    required = set(GROUPS["b25_parents"])
    if not required.issubset(documents):
        return ["cross-link: archive chain is incomplete"]

    errors: list[str] = []
    b2 = documents["b2_protocol"]
    b2_failure = documents["b2_failure"]
    b21 = documents["b21_protocol"]
    b21_failure = documents["b21_failure"]
    b22 = documents["b22_protocol"]
    b23 = documents["b23_protocol"]
    b23q = documents["b23_qualification"]
    b24 = documents["b24_protocol"]
    b24r = documents["b24_readiness"]
    b24f = documents["b24_failure"]
    b24repair = documents["b24_repair"]
    b25 = documents["b25_protocol"]
    b25q = documents["b25_qualification"]
    b25r = documents["b25_readiness"]
    b25f = documents.get("b25_failure")

    for label, child_key, parent_key in (
        ("B2 protocol digest", "protocol_report_digest", "protocol_digest"),
        ("B2 source bundle", "source_bundle_digest", "b2_source_bundle_digest"),
        ("B2 spec", "spec_digest", "b2_spec_digest"),
    ):
        _expect(
            errors,
            label,
            _get(b21, "parent_b2_lock", child_key),
            _get(b2, "source_locks", parent_key)
            if parent_key != "protocol_digest"
            else b2.get(parent_key),
        )
        _expect(
            errors,
            f"B2 failure {label}",
            _get(b2_failure, "protocol", child_key),
            _get(b21, "parent_b2_lock", child_key),
        )
    _expect(
        errors,
        "B2 failed aggregate bytes",
        _get(b21, "parent_b2_lock", "failed_closed_aggregate_sha256"),
        _normalized_file_sha256(_artifact_path(SPEC_BY_NAME["b2_failure"])),
    )

    for key in ("protocol_report_digest", "source_bundle_digest", "spec_digest"):
        parent_key = {
            "protocol_report_digest": "protocol_digest",
            "source_bundle_digest": "b21_source_bundle_digest",
            "spec_digest": "b21_spec_digest",
        }[key]
        _expect(
            errors,
            f"B2.2 parent B2.1 {key}",
            _get(b22, "parent_b21_lock", key),
            b21.get(parent_key)
            if parent_key == "protocol_digest"
            else _get(b21, "source_locks", parent_key),
        )
        _expect(
            errors,
            f"B2.1 failure {key}",
            _get(b21_failure, "protocol", key),
            _get(b22, "parent_b21_lock", key),
        )
    _expect(
        errors,
        "B2.1 failed aggregate bytes",
        _get(b22, "parent_b21_lock", "failure_aggregate_sha256"),
        _normalized_file_sha256(_artifact_path(SPEC_BY_NAME["b21_failure"])),
    )

    _expect(
        errors,
        "B2.3 parent B2.2 protocol digest",
        _get(b23, "parent_b22_lock", "protocol_report_digest"),
        b22.get("protocol_digest"),
    )
    _expect(
        errors,
        "B2.3 parent B2.2 protocol bytes",
        _get(b23, "parent_b22_lock", "protocol_report_normalized_sha256"),
        _normalized_file_sha256(_artifact_path(SPEC_BY_NAME["b22_protocol"])),
    )
    _expect(
        errors,
        "B2.3 qualification source bundle",
        b23q.get("b23_source_bundle_digest"),
        _get(b23, "source_locks", "b23_source_bundle_digest"),
    )
    _expect(
        errors,
        "B2.3 qualification spec",
        b23q.get("b23_spec_digest"),
        _get(b23, "source_locks", "b23_spec_digest"),
    )

    _expect(
        errors,
        "B2.4 parent B2.3 qualification digest",
        _get(b24, "parent_b23_qualification", "qualification_digest"),
        b23q.get("qualification_digest"),
    )
    _expect(
        errors,
        "B2.4 parent B2.3 qualification bytes",
        _get(b24, "parent_b23_qualification", "aggregate_sha256"),
        _normalized_file_sha256(_artifact_path(SPEC_BY_NAME["b23_qualification"])),
    )
    for suffix in (
        "spec_digest",
        "source_bundle_digest",
        "holdout_frame_digest",
        "execution_schedule_digest",
    ):
        _expect(
            errors,
            f"B2.4 readiness {suffix}",
            _get(b24r, "protocol_gate", f"b24_{suffix}"),
            _get(b24, "source_locks", f"b24_{suffix}"),
        )
    _expect(
        errors,
        "B2.4 readiness qualification",
        _get(b24r, "runner_qualification_gate", "qualification_digest"),
        b23q.get("qualification_digest"),
    )
    _expect(
        errors,
        "B2.4 failure readiness",
        _get(b24f, "source_gate", "readiness_digest"),
        b24r.get("readiness_digest"),
    )
    _expect(
        errors,
        "B2.4 failure protocol",
        _get(b24f, "protocol", "protocol_report_digest"),
        b24.get("protocol_digest"),
    )
    _expect(
        errors,
        "B2.4 repair failure parent",
        _get(b24repair, "parent_closeout", "failure_aggregate_digest"),
        b24f.get("failure_aggregate_digest"),
    )

    _expect(
        errors,
        "B2.5 parent B2.3 qualification",
        _get(b25, "parent_b23_qualification", "qualification_digest"),
        b23q.get("qualification_digest"),
    )
    _expect(
        errors,
        "B2.5 parent B2.4 failure",
        _get(b25, "parent_b24_failure", "failure_digest"),
        b24f.get("failure_aggregate_digest"),
    )
    _expect(
        errors,
        "B2.5 parent B2.4 repair",
        _get(b25, "parent_b24_repair", "repair_digest"),
        b24repair.get("repair_digest"),
    )
    _expect(
        errors,
        "B2.5 qualification source bundle",
        _get(b25q, "protocol_gate", "b25_source_bundle_digest"),
        _get(b25, "source_locks", "b25_source_bundle_digest"),
    )
    _expect(
        errors,
        "B2.5 qualification spec",
        _get(b25q, "protocol_gate", "b25_spec_digest"),
        _get(b25, "source_locks", "b25_spec_digest"),
    )
    _expect(
        errors,
        "B2.5 qualification repair",
        _get(b25q, "repair_gate", "repair_digest"),
        b24repair.get("repair_digest"),
    )
    for suffix in (
        "spec_digest",
        "source_bundle_digest",
        "holdout_frame_digest",
        "execution_schedule_digest",
    ):
        _expect(
            errors,
            f"B2.5 readiness {suffix}",
            _get(b25r, "preauthoring_publication_gate", f"b25_{suffix}"),
            _get(b25, "source_locks", f"b25_{suffix}"),
        )
    _expect(
        errors,
        "B2.5 readiness runtime qualification",
        _get(b25r, "runner_qualification_gate", "runtime_qualification_digest"),
        b25q.get("qualification_digest"),
    )
    _expect(
        errors,
        "B2.5 readiness B2.4 failure",
        _get(b25r, "historical_closeout_gate", "b24_failure_digest"),
        b24f.get("failure_aggregate_digest"),
    )
    _expect(
        errors,
        "B2.5 readiness B2.4 repair",
        _get(b25r, "historical_closeout_gate", "b24_repair_digest"),
        b24repair.get("repair_digest"),
    )
    if b25f is not None:
        _expect(
            errors,
            "B2.5 failure readiness",
            _get(b25f, "source_gate", "readiness_digest"),
            b25r.get("readiness_digest"),
        )
        _expect(
            errors,
            "B2.5 failure protocol",
            _get(b25f, "protocol", "protocol_report_digest"),
            b25.get("protocol_digest"),
        )
    return errors


def _validate_documents(
    names: tuple[str, ...], documents: Mapping[str, Mapping[str, Any]]
) -> list[str]:
    errors: list[str] = []
    for name in names:
        value = documents.get(name)
        if value is None:
            errors.append(f"{name}: artifact missing")
            continue
        errors.extend(_validate_document(SPEC_BY_NAME[name], value))
    if set(GROUPS["b25_parents"]).issubset(documents):
        errors.extend(_validate_cross_links(documents))
    return sorted(set(errors))


def validate_archive(group: str = "all") -> list[str]:
    names = GROUPS[group]
    documents, errors = _load_documents(names)
    errors.extend(_validate_documents(names, documents))
    return sorted(set(errors))


def run_self_test() -> dict[str, Any]:
    errors = validate_archive("all")
    return {
        "passed": not errors,
        "artifact_count": len(SPECS),
        "cross_phase_chain_checked": True,
        "current_source_rebinding_used": False,
        "errors": errors,
    }


def run_fault_test() -> dict[str, Any]:
    names = GROUPS["all"]
    documents, load_errors = _load_documents(names)
    if load_errors:
        return {"passed": False, "checks_total": 0, "checks_passed": 0}

    checks: list[bool] = []

    changed_status = copy.deepcopy(documents)
    changed_status["b25_failure"]["status"] = "complete"
    checks.append(bool(_validate_documents(names, changed_status)))

    changed_digest = copy.deepcopy(documents)
    changed_digest["b25_readiness"]["readiness_digest"] = "b25ready_" + "0" * 64
    checks.append(bool(_validate_documents(names, changed_digest)))

    missing_parent = copy.deepcopy(documents)
    missing_parent.pop("b24_repair")
    checks.append(bool(_validate_documents(names, missing_parent)))

    changed_link = copy.deepcopy(documents)
    changed_link["b25_failure"]["protocol"]["protocol_report_digest"] = "drift"
    checks.append(bool(_validate_cross_links(changed_link)))

    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
    }


def _print(value: Any) -> None:
    print(json.dumps(value, sort_keys=True, separators=(",", ":")))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate terminal product-bakeoff public archives"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", choices=sorted(GROUPS))
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--fault-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        result = run_self_test()
        _print(result)
        return 0 if result["passed"] else 1
    if args.fault_test:
        result = run_fault_test()
        _print(result)
        return 0 if result["passed"] else 1
    errors = validate_archive(args.validate)
    _print(
        {
            "passed": not errors,
            "group": args.validate,
            "artifact_count": len(GROUPS[args.validate]),
            "current_source_rebinding_used": False,
            "errors": errors,
        }
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ArtifactSpec",
    "SPECS",
    "GROUPS",
    "validate_archive",
    "run_self_test",
    "run_fault_test",
]
