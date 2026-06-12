#!/usr/bin/env python3
"""Read the CI repos manifest, select repos by stage, and output a GitHub
Actions matrix JSON object {include:[...]}.

Uses only Python stdlib. Contains a minimal YAML subset parser sufficient
for the openlocus-ci-repos-v1 manifest format.
"""

import argparse
import json
import sys

# ── Minimal YAML subset parser ──────────────────────────────────────────────

def _parse_yaml_value(raw: str):
    """Parse a simple YAML scalar value."""
    s = raw.strip()
    if not s:
        return None
    # Remove inline comments
    if " #" in s:
        s = s[: s.index(" #")].rstrip()
    if s.lower() in ("true", "yes"):
        return True
    if s.lower() in ("false", "no"):
        return False
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


def parse_manifest_yaml(path: str) -> dict:
    """Parse the CI repos manifest YAML.

    Handles the specific subset used in openlocus-ci-repos-v1.yaml:
    top-level scalars, policy/stages mappings, and the repos list.
    """
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    root: dict = {}
    repos_list: list[dict] | None = None
    current_repo: dict | None = None
    in_repos = False
    repo_indent = 0

    # State machine for nested mappings (policy, stages, stage entries)
    current_section: str | None = None  # "policy" | "stages" | None
    current_stage_name: str | None = None
    current_stage: dict | None = None
    stage_indent = 0

    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        stripped = line.rstrip()

        if not stripped or stripped.lstrip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())
        content = stripped.strip()

        # Handle multi-line > blocks
        if content.endswith(">"):
            while i < len(lines):
                next_line = lines[i]
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_line.strip() and next_indent <= indent:
                    break
                i += 1
            continue

        # ── repos list ──
        if content == "repos:":
            # Flush any pending stage before switching to repos
            if current_stage is not None and current_stage_name is not None:
                root.setdefault("stages", {})[current_stage_name] = current_stage
                current_stage = None
                current_stage_name = None
            in_repos = True
            repos_list = []
            root["repos"] = repos_list
            current_section = None
            continue

        if in_repos and repos_list is not None:
            if content.startswith("- "):
                if current_repo is not None:
                    repos_list.append(current_repo)
                repo_indent = indent
                current_repo = {}
                kv_part = content[2:].strip()
                if ":" in kv_part:
                    k, v = kv_part.split(":", 1)
                    current_repo[k.strip()] = _parse_yaml_value(v)
                continue

            if current_repo is not None and indent > repo_indent:
                if ":" in content:
                    k, v = content.split(":", 1)
                    key = k.strip()
                    val_raw = v.strip()
                    if val_raw.startswith("[") and val_raw.endswith("]"):
                        items = [
                            _parse_yaml_value(item.strip())
                            for item in val_raw[1:-1].split(",")
                            if item.strip()
                        ]
                        current_repo[key] = items
                    else:
                        current_repo[key] = _parse_yaml_value(val_raw)
                continue

            if current_repo is not None:
                repos_list.append(current_repo)
                current_repo = None

            # Could be leaving repos section
            if ":" in content and indent == 0:
                in_repos = False

        # ── top-level sections ──
        if not in_repos and indent == 0 and ":" in content:
            k, v = content.split(":", 1)
            key = k.strip()
            val_raw = v.strip()
            if key == "policy":
                current_section = "policy"
                root["policy"] = {}
                current_stage = None
                continue
            elif key == "stages":
                current_section = "stages"
                root["stages"] = {}
                current_stage = None
                continue
            else:
                current_section = None
                current_stage = None
                if val_raw:
                    if val_raw.startswith("[") and val_raw.endswith("]"):
                        items = [
                            _parse_yaml_value(item.strip())
                            for item in val_raw[1:-1].split(",")
                            if item.strip()
                        ]
                        root[key] = items
                    else:
                        root[key] = _parse_yaml_value(val_raw)
                continue

        # ── policy section ──
        if current_section == "policy" and indent > 0 and current_stage is None:
            # Multi-line list item under a policy key (e.g. allowed_licenses: / - MIT)
            if content.startswith("- "):
                # Find the last policy key that had no inline value (i.e. started a list)
                _policy_list_key = root["policy"].get("__pending_list_key")
                if _policy_list_key is not None:
                    item_val = _parse_yaml_value(content[2:].strip())
                    if isinstance(root["policy"][_policy_list_key], list):
                        root["policy"][_policy_list_key].append(item_val)
                continue
            if ":" in content:
                k, v = content.split(":", 1)
                pkey = k.strip()
                pval_raw = v.strip()
                if pval_raw:
                    if pval_raw.startswith("[") and pval_raw.endswith("]"):
                        items = [
                            _parse_yaml_value(item.strip())
                            for item in pval_raw[1:-1].split(",")
                            if item.strip()
                        ]
                        root["policy"][pkey] = items
                    else:
                        root["policy"][pkey] = _parse_yaml_value(pval_raw)
                    root["policy"].pop("__pending_list_key", None)
                else:
                    # Key with no inline value → starts a multi-line list
                    root["policy"][pkey] = []
                    root["policy"]["__pending_list_key"] = pkey

        # ── stages section ──
        if current_section == "stages" and indent > 0:
            # A stage name line like "pr_smoke:"
            if content.endswith(":") and not content.startswith("-"):
                maybe_name = content[:-1].strip()
                if current_stage is not None and current_stage_name is not None:
                    root["stages"][current_stage_name] = current_stage
                current_stage_name = maybe_name
                current_stage = {}
                stage_indent = indent
                continue

            # A key inside a stage
            if current_stage is not None and indent > stage_indent and ":" in content:
                k, v = content.split(":", 1)
                skey = k.strip()
                sval_raw = v.strip()
                if sval_raw:
                    if sval_raw.startswith("[") and sval_raw.endswith("]"):
                        items = [
                            _parse_yaml_value(item.strip())
                            for item in sval_raw[1:-1].split(",")
                            if item.strip()
                        ]
                        current_stage[skey] = items
                    else:
                        current_stage[skey] = _parse_yaml_value(sval_raw)

    # Flush
    if current_repo is not None and repos_list is not None:
        repos_list.append(current_repo)
    if current_stage is not None and current_stage_name is not None:
        root.setdefault("stages", {})[current_stage_name] = current_stage

    # Clean up internal tracking keys from policy
    if "policy" in root and isinstance(root["policy"], dict):
        root["policy"].pop("__pending_list_key", None)

    return root


# ── Validation ──────────────────────────────────────────────────────────────

KNOWN_LICENSES = {
    "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause",
    "ISC", "MPL-2.0", "EPL-2.0", "Unlicense", "curl",
}

DUAL_LICENSE_MARKERS = {
    "MIT_OR_UNLICENSE",
    "MIT_OR_APACHE",
}

VALID_STAGES = {"pr_smoke", "nightly_medium", "weekly_large", "manual_extreme"}

TIER_TO_STAGE = {
    "smoke": "pr_smoke",
    "nightly_medium": "nightly_medium",
    "weekly_large": "weekly_large",
    "manual_extreme": "manual_extreme",
}


def validate_manifest(manifest: dict) -> list[str]:
    """Validate the manifest and return a list of error strings (empty = OK)."""
    errors: list[str] = []

    # Check for duplicate repo ids
    repos = manifest.get("repos", [])
    seen_ids: set[str] = set()
    for r in repos:
        rid = r.get("id")
        if rid is None:
            errors.append("Repo entry missing 'id' field")
            continue
        if rid in seen_ids:
            errors.append(f"Duplicate repo id: {rid}")
        seen_ids.add(rid)

    # Check license policy
    allowed = set(manifest.get("policy", {}).get("allowed_licenses", []))
    for r in repos:
        el = r.get("expected_license")
        if el is None:
            continue
        if el in DUAL_LICENSE_MARKERS:
            # Each component must be in allowed_licenses
            if el == "MIT_OR_UNLICENSE":
                components = {"MIT", "Unlicense"}
            elif el == "MIT_OR_APACHE":
                components = {"MIT", "Apache-2.0"}
            else:
                components = set()
            missing = components - allowed
            if missing:
                errors.append(
                    f"Repo '{r['id']}': dual license '{el}' references "
                    f"disallowed license(s): {sorted(missing)}"
                )
        elif el not in KNOWN_LICENSES:
            errors.append(
                f"Repo '{r['id']}': unsupported expected_license '{el}'"
            )
        elif allowed and el not in allowed:
            errors.append(
                f"Repo '{r['id']}': expected_license '{el}' not in allowed_licenses"
            )

    # Check tier values
    for r in repos:
        tier = r.get("tier")
        if tier not in TIER_TO_STAGE:
            errors.append(
                f"Repo '{r.get('id', '?')}': unknown tier '{tier}'"
            )

    return errors


# ── Matrix generation ───────────────────────────────────────────────────────

def select_repos_for_stage(
    repos: list[dict],
    stage: str,
    max_repos: int,
) -> list[dict]:
    """Filter repos by stage and limit to max_repos."""
    selected = [r for r in repos if r.get("tier") is not None and TIER_TO_STAGE.get(r.get("tier", "")) == stage]
    return selected[:max_repos]


def build_matrix(
    repos: list[dict],
    stage: str,
    stage_config: dict,
    max_repos_override: int | None = None,
) -> dict:
    """Build the GitHub Actions matrix JSON."""
    max_repos = max_repos_override or stage_config.get("max_repos", 10)
    max_tasks = stage_config.get("max_tasks_per_repo", 60)
    strategies = stage_config.get("strategies", [])
    if strategies == ["all_available"]:
        strategies = [
            "regex", "bm25", "symbol", "rrf",
            "bm25_regex", "bm25_symbol", "rrf_guarded_by_symbol_regex",
            "query_noise_plus_rrf_agree_min", "ast_chunk_bm25",
            "graph_basic", "dense_mock",
        ]

    selected = select_repos_for_stage(repos, stage, max_repos)

    include = []
    for r in selected:
        entry = {
            "repo_id": r["id"],
            "repo": r["repo"],
            "primary_language": r.get("primary_language", "unknown"),
            "expected_license": r.get("expected_license", ""),
            "tier": r.get("tier", ""),
            "max_tasks": max_tasks,
            "strategies": strategies,
        }
        include.append(entry)

    return {"include": include}


# ── CLI ─────────────────────────────────────────────────────────────────────

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate GitHub Actions matrix JSON from the CI repos manifest"
    )
    p.add_argument(
        "--manifest",
        required=True,
        help="Path to the CI repos manifest YAML",
    )
    p.add_argument(
        "--stage",
        required=True,
        choices=sorted(VALID_STAGES),
        help="Stage to generate matrix for",
    )
    p.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate the manifest, don't output matrix",
    )
    p.add_argument(
        "--max-repos",
        type=int,
        default=None,
        help="Optional cap overriding the stage max_repos value",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    manifest = parse_manifest_yaml(args.manifest)

    # Validate
    errors = validate_manifest(manifest)
    if errors:
        for e in errors:
            print(f"VALIDATION ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if args.validate_only:
        print("Manifest validation passed.")
        return

    # Check stage is known (already enforced by argparse choices, but be explicit)
    if args.stage not in VALID_STAGES:
        print(f"ERROR: unknown stage '{args.stage}'", file=sys.stderr)
        sys.exit(1)

    stages_config = manifest.get("stages", {})
    stage_config = stages_config.get(args.stage)
    if stage_config is None:
        print(f"ERROR: stage '{args.stage}' not found in manifest", file=sys.stderr)
        sys.exit(1)

    repos = manifest.get("repos", [])
    matrix = build_matrix(repos, args.stage, stage_config, args.max_repos)

    print(json.dumps(matrix, separators=(",", ":")))


if __name__ == "__main__":
    main()
