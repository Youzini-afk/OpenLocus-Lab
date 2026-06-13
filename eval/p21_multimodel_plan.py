#!/usr/bin/env python3
"""Build P21-G cross-model real-provider workflow dispatch plans.

This script does not run model research by itself. It creates a reproducible
matrix of GitHub Actions dispatch commands for existing real-provider stages so
that P21-G can compare model profiles across the same repos/caps.

The generated plan is safe to commit: it contains model IDs and public workflow
inputs only, never provider URLs, API keys, raw snippets, private labels, or
gold answers.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "p21-g-multimodel-dispatch-plan-v1"
WORKFLOW = "real-provider-benchmark.yml"
MODEL_ID_RE = re.compile(r"[A-Za-z0-9_./:@+\-\[\] ]{1,160}")
REPO_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")
PROFILE_ID_RE = re.compile(r"[A-Za-z0-9_.-]{1,80}")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def csv(value: str | None, default: list[str]) -> list[str]:
    if not value:
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


def positive_int(value: str, *, name: str, maximum: int) -> int:
    if not re.fullmatch(r"[1-9][0-9]*", value):
        raise SystemExit(f"{name} must be a positive integer")
    parsed = int(value)
    if parsed > maximum:
        raise SystemExit(f"{name} exceeds cap {maximum}")
    return parsed


def select_profiles(
    profiles: list[dict[str, Any]],
    requested: list[str],
    *,
    include_disabled: bool,
) -> list[dict[str, Any]]:
    by_id = {profile["profile_id"]: profile for profile in profiles}
    if requested:
        missing = [profile_id for profile_id in requested if profile_id not in by_id]
        if missing:
            raise SystemExit(f"unknown profile id(s): {', '.join(missing)}")
        selected = [by_id[profile_id] for profile_id in requested]
    else:
        selected = [profile for profile in profiles if profile.get("enabled_by_default") or include_disabled]
    return [profile for profile in selected if str(profile.get("model_id", "")).strip()]


def parse_custom_llm(values: list[str]) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    for value in values:
        raw = value.strip()
        if not raw:
            continue
        if "=" in raw:
            profile_id, model_id = raw.split("=", 1)
        else:
            digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]
            profile_id, model_id = f"custom_llm_{digest}", raw
        profile_id = profile_id.strip()
        model_id = model_id.strip()
        if not PROFILE_ID_RE.fullmatch(profile_id):
            raise SystemExit(f"invalid custom profile id: {profile_id}")
        if not MODEL_ID_RE.fullmatch(model_id):
            raise SystemExit(f"invalid custom llm model id: {model_id}")
        profiles.append(
            {
                "profile_id": profile_id,
                "model_id": model_id,
                "family": "custom",
                "enabled_by_default": True,
                "provider": "OPENLOCUS_LLM_PROVIDER",
                "roles_planned": ["rerank", "filter", "span_narrow", "inventory_alias"],
                "effective_context_bucket": "unknown",
                "cost_class": "unknown",
                "latency_class": "unknown",
                "notes": "CLI-provided custom LLM profile.",
            }
        )
    return profiles


def gh_command(fields: dict[str, str]) -> list[str]:
    cmd = ["gh", "workflow", "run", WORKFLOW]
    for key, value in fields.items():
        cmd.extend(["-f", f"{key}={value}"])
    return cmd


def shell_command(cmd: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in cmd)


def entry(
    *,
    kind: str,
    profile: dict[str, Any],
    repo_id: str,
    fields: dict[str, str],
) -> dict[str, Any]:
    cmd = gh_command(fields)
    return {
        "kind": kind,
        "profile_id": profile["profile_id"],
        "family": profile.get("family"),
        "model_id": profile.get("model_id"),
        "repo_id": repo_id,
        "stage": fields["stage"],
        "dataset": fields["dataset"],
        "max_tasks": int(fields["max_tasks"]),
        "max_records": int(fields["max_records"]),
        "max_files_per_repo": int(fields["max_files_per_repo"]),
        "workflow_fields": fields,
        "gh_command": cmd,
        "gh_command_shell": shell_command(cmd),
    }


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    cfg = load_json(args.profiles)
    defaults = cfg.get("defaults", {})
    repos = csv(args.repos, defaults.get("repos", []))
    for repo_id in repos:
        if not REPO_ID_RE.fullmatch(repo_id):
            raise SystemExit(f"invalid repo id: {repo_id}")

    max_tasks = positive_int(args.max_tasks or str(defaults.get("max_tasks", 20)), name="max_tasks", maximum=100)
    max_records = positive_int(args.max_records or str(defaults.get("max_records", 80)), name="max_records", maximum=1000)
    max_files = positive_int(
        args.max_files_per_repo or str(defaults.get("max_files_per_repo", 120)),
        name="max_files_per_repo",
        maximum=3000,
    )
    dataset = args.dataset or defaults.get("dataset", "ci_smoke")
    if dataset not in {"self_test", "ci_smoke"}:
        raise SystemExit("dataset must be self_test or ci_smoke")

    llm_profiles = cfg.get("llm_profiles", []) + parse_custom_llm(args.llm_model)
    embedding_profiles = cfg.get("embedding_profiles", [])
    llm_selected = select_profiles(llm_profiles, csv(args.llm_profiles, []), include_disabled=args.include_disabled)
    embedding_selected = select_profiles(
        embedding_profiles,
        csv(args.embedding_profiles, []),
        include_disabled=args.include_disabled,
    )
    if args.mode in {"llm", "both"} and not llm_selected:
        raise SystemExit("no LLM profiles selected; configure model_id or pass --llm-model")
    if args.mode in {"embedding", "both"} and not embedding_selected:
        raise SystemExit("no embedding profiles selected")

    llm_stage = args.llm_stage or defaults.get("llm_stage", "p20_llm_large")
    embedding_stage = args.embedding_stage or defaults.get("embedding_stage", "p2_embedding")
    embedding_for_llm = args.embedding_model_for_llm_stage or defaults.get("embedding_model_for_llm_stage", "BAAI/bge-m3")
    remote = "true" if args.enable_remote_models else "false"

    entries: list[dict[str, Any]] = []
    if args.mode in {"llm", "both"}:
        for profile in llm_selected:
            model_id = str(profile.get("model_id", "")).strip()
            if not MODEL_ID_RE.fullmatch(model_id):
                raise SystemExit(f"invalid llm model id for {profile['profile_id']}: {model_id}")
            for repo_id in repos:
                fields = {
                    "stage": llm_stage,
                    "enable_remote_models": remote,
                    "dataset": dataset,
                    "repo_id": repo_id,
                    "embedding_model": embedding_for_llm,
                    "llm_model": model_id,
                    "max_tasks": str(max_tasks),
                    "max_records": str(max_records),
                    "max_files_per_repo": str(max_files),
                }
                entries.append(entry(kind="llm", profile=profile, repo_id=repo_id, fields=fields))

    if args.mode in {"embedding", "both"}:
        for profile in embedding_selected:
            model_id = str(profile.get("model_id", "")).strip()
            if not MODEL_ID_RE.fullmatch(model_id):
                raise SystemExit(f"invalid embedding model id for {profile['profile_id']}: {model_id}")
            for repo_id in repos:
                fields = {
                    "stage": embedding_stage,
                    "enable_remote_models": remote,
                    "dataset": dataset,
                    "repo_id": repo_id,
                    "embedding_model": model_id,
                    "llm_model": "",
                    "max_tasks": str(max_tasks),
                    "max_records": str(max_records),
                    "max_files_per_repo": str(max_files),
                }
                entries.append(entry(kind="embedding", profile=profile, repo_id=repo_id, fields=fields))

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "source_profiles": str(args.profiles),
        "mode": args.mode,
        "remote_enabled": args.enable_remote_models,
        "dataset": dataset,
        "repos": repos,
        "entry_count": len(entries),
        "promotion_ready": False,
        "default_should_change": False,
        "candidate_not_fact": True,
        "raw_snippets_in_plan": False,
        "private_labels_in_plan": False,
        "provider_url_or_key_in_plan": False,
        "notes": [
            "This is a dispatch plan, not an eval result.",
            "Token count is recorded by downstream P21-G harnesses; model profile and context pack are primary variables.",
            "Existing p20/p2 workflow stages are wiring baselines; rich-context P21-G harnesses should produce separate artifacts.",
        ],
        "entries": entries,
    }


def execute_entries(entries: list[dict[str, Any]]) -> None:
    if os.environ.get("P21_G_ALLOW_DISPATCH") != "1":
        raise SystemExit("Refusing to dispatch unless P21_G_ALLOW_DISPATCH=1")
    for item in entries:
        subprocess.run(item["gh_command"], check=True)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", type=Path, default=Path("eval/p21_model_profiles.json"))
    parser.add_argument("--mode", choices=["llm", "embedding", "both"], default="both")
    parser.add_argument("--dataset", choices=["self_test", "ci_smoke"], default=None)
    parser.add_argument("--repos", default=None, help="Comma-separated repo ids")
    parser.add_argument("--llm-profiles", default="", help="Comma-separated LLM profile ids")
    parser.add_argument("--embedding-profiles", default="", help="Comma-separated embedding profile ids")
    parser.add_argument("--llm-model", action="append", default=[], help="Custom LLM model, optionally profile_id=model_id")
    parser.add_argument("--include-disabled", action="store_true")
    parser.add_argument("--llm-stage", default=None)
    parser.add_argument("--embedding-stage", default=None)
    parser.add_argument("--embedding-model-for-llm-stage", default=None)
    parser.add_argument("--enable-remote-models", action="store_true")
    parser.add_argument("--max-tasks", default=None)
    parser.add_argument("--max-records", default=None)
    parser.add_argument("--max-files-per-repo", default=None)
    parser.add_argument("--out", type=Path, default=Path("artifacts/p21_g/multimodel_dispatch_plan.json"))
    parser.add_argument("--print-commands", action="store_true")
    parser.add_argument("--execute", action="store_true", help="Dispatch via gh; also requires P21_G_ALLOW_DISPATCH=1")
    args = parser.parse_args(argv)

    plan = build_plan(args)
    write_json(args.out, plan)
    if args.print_commands:
        for item in plan["entries"]:
            print(item["gh_command_shell"])
    if args.execute:
        execute_entries(plan["entries"])
    print(json.dumps({"status": "ok", "out": str(args.out), "entry_count": plan["entry_count"]}, sort_keys=True))


if __name__ == "__main__":
    main()
