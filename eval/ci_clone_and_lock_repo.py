#!/usr/bin/env python3
"""Clone a public GitHub repo, verify license, lock HEAD SHA, and produce repo-lock.json
plus repos.lock.jsonl entries for the OpenLocus CI corpus pipeline.

Uses only Python stdlib + git CLI.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# ── License recognition ──────────────────────────────────────────────────────

KNOWN_LICENSES = {
    "MIT",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "MPL-2.0",
    "EPL-2.0",
    "Unlicense",
    "curl",
}

DUAL_LICENSE_MARKERS = {
    "MIT_OR_UNLICENSE": {"MIT", "Unlicense"},
    "MIT_OR_APACHE": {"MIT", "Apache-2.0"},
}

# File names to probe for license information (order matters — first match wins).
LICENSE_FILE_PATTERNS = [
    "LICENSE",
    "LICENSE.md",
    "LICENSE.txt",
    "LICENSE.rst",
    "license",
    "license.md",
    "license.txt",
    "COPYING",
    "COPYING.md",
    "COPYING.txt",
    "COPYING.rst",
    "LICENCE",
    "LICENCE.md",
    "LICENCE.txt",
]

# ── License detection helpers ────────────────────────────────────────────────

_MIT_RE = re.compile(r"permission is hereby granted, free of charge|spdx-license-identifier:\s*mit", re.IGNORECASE)
_APACHE_RE = re.compile(r"apache license.*version 2\.0|spdx-license-identifier:\s*apache-2\.0", re.IGNORECASE | re.DOTALL)
_BSD2_RE = re.compile(r"redistribution and use in source and binary forms.*(?:this list of conditions|disclaimer)|spdx-license-identifier:\s*bsd-2-clause", re.IGNORECASE | re.DOTALL)
_BSD3_RE = re.compile(r"redistribution and use in source and binary forms.*(?:endorse|promote)|spdx-license-identifier:\s*bsd-3-clause", re.IGNORECASE | re.DOTALL)
_ISC_RE = re.compile(r"isc license|permission to use, copy, modify.*(?:with or without fee)|spdx-license-identifier:\s*isc", re.IGNORECASE | re.DOTALL)
_MPL2_RE = re.compile(r"mozilla public license.*version 2\.0|spdx-license-identifier:\s*mpl-2\.0", re.IGNORECASE | re.DOTALL)
_EPL2_RE = re.compile(r"eclipse public license.*version 2\.0|spdx-license-identifier:\s*epl-2\.0", re.IGNORECASE | re.DOTALL)
_UNLICENSE_RE = re.compile(r"unlicense|this is free and unencumbered software released|spdx-license-identifier:\s*unlicense", re.IGNORECASE)
_CURL_RE = re.compile(r"curl license|copyright.*daniel stenberg|spdx-license-identifier:\s*curl", re.IGNORECASE | re.DOTALL)


def _detect_license_from_text(text: str) -> list[str]:
    """Return list of license identifiers detected in *text*."""
    found: list[str] = []
    if _MIT_RE.search(text):
        found.append("MIT")
    if _APACHE_RE.search(text):
        found.append("Apache-2.0")
    if _UNLICENSE_RE.search(text):
        found.append("Unlicense")
    if _MPL2_RE.search(text):
        found.append("MPL-2.0")
    if _EPL2_RE.search(text):
        found.append("EPL-2.0")
    if _CURL_RE.search(text):
        found.append("curl")
    # BSD checks — 3-clause is more specific, check first
    if _BSD3_RE.search(text):
        found.append("BSD-3-Clause")
    elif _BSD2_RE.search(text):
        found.append("BSD-2-Clause")
    if _ISC_RE.search(text):
        found.append("ISC")
    return found


def detect_license(repo_root: str) -> list[str]:
    """Detect license(s) by reading root license/copying files.

    Dual-license projects often use names such as LICENSE-MIT,
    LICENSE-APACHE, or UNLICENSE rather than a single LICENSE file, so scan all
    root files with license-like names and return a stable de-duplicated list.
    """
    candidate_names = set(LICENSE_FILE_PATTERNS)
    try:
        for child in os.listdir(repo_root):
            upper = child.upper()
            if (
                upper.startswith("LICENSE")
                or upper.startswith("LICENCE")
                or upper.startswith("COPYING")
                or upper in {"UNLICENSE", "NOTICE"}
            ):
                candidate_names.add(child)
    except OSError:
        pass

    detected_all: list[str] = []
    for name in sorted(candidate_names):
        p = os.path.join(repo_root, name)
        if not os.path.isfile(p):
            continue
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                text = f.read(16384)
        except OSError:
            continue
        detected_all.extend(_detect_license_from_text(text))

    deduped: list[str] = []
    for license_id in detected_all:
        if license_id not in deduped:
            deduped.append(license_id)
    return deduped


def resolve_expected_license(value: str) -> set[str]:
    """Resolve an expected_license value (possibly a dual marker) to a set of
    concrete license IDs that are individually acceptable."""
    if value in DUAL_LICENSE_MARKERS:
        return DUAL_LICENSE_MARKERS[value]
    return {value}


def check_license(detected: list[str], expected: str | None) -> str | None:
    """Return None if license is OK, or an error message string."""
    if expected is None:
        return None  # no expectation → pass
    acceptable = resolve_expected_license(expected)
    for lic in detected:
        if lic in acceptable:
            return None
    return (
        f"License mismatch: expected one of {sorted(acceptable)}, "
        f"detected {detected or ['NONE']}"
    )


def validate_license_policy(expected: str | None, allowed_licenses: set[str]) -> str | None:
    """Validate that the expected license (or its dual components) are in the
    allowed set. Return error message or None."""
    if expected is None:
        return None
    concrete = resolve_expected_license(expected)
    disallowed = concrete - allowed_licenses
    if disallowed:
        return f"Expected license includes disallowed identifiers: {sorted(disallowed)}"
    return None


# ── Git helpers ─────────────────────────────────────────────────────────────

def _git(*args: str, cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


def clone_repo(repo: str, out_root: str) -> str:
    """Clone a public GitHub repo into *out_root* and return the clone path."""
    clone_url = f"https://github.com/{repo}.git"
    clone_dir = os.path.join(out_root, repo.replace("/", "__"))

    if os.path.isdir(os.path.join(clone_dir, ".git")):
        # Already cloned — fetch to refresh
        _git("fetch", "--depth=1", "--filter=blob:none", cwd=clone_dir)
    else:
        os.makedirs(out_root, exist_ok=True)
        _git(
            "clone",
            "--filter=blob:none",
            "--depth=1",
            "--no-recurse-submodules",
            clone_url,
            clone_dir,
        )
    return clone_dir


def resolve_head_sha(clone_dir: str) -> str:
    """Return the full SHA of the current HEAD."""
    r = _git("rev-parse", "HEAD", cwd=clone_dir)
    return r.stdout.strip()


def detach_head(clone_dir: str) -> None:
    """Detach HEAD so the working tree is at a known commit."""
    _git("checkout", "--detach", "HEAD", cwd=clone_dir)


# ── File manifest ───────────────────────────────────────────────────────────

# Default extensions used for indexing (source code only).
DEFAULT_INDEX_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs",
    ".rs", ".go", ".java", ".kt", ".kts",
    ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx", ".hxx",
    ".cs", ".fs", ".fsi",
    ".rb", ".php", ".swift", ".scala", ".clj",
    ".sh", ".bash", ".zsh",
    ".yaml", ".yml", ".toml", ".json", ".cfg", ".ini",
    ".md", ".rst", ".txt",
    ".css", ".scss", ".less", ".html", ".svg",
}

EXCLUDE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", "target", "coverage", ".next", ".nuxt",
    ".openlocus", "fixtures", "eval", "docs", "runs",
}


def compute_manifest(
    clone_dir: str,
    extensions: set[str] | None = None,
    max_indexed_bytes: int | None = None,
) -> dict:
    """Walk the clone directory, compute per-file SHA-256 (normalized), and
    return manifest info including aggregate SHA, file count, and total bytes.

    Returns dict with:
      content_manifest_sha: str
      content_manifest_algorithm: str
      indexed_file_count: int
      indexed_bytes: int
      extensions: list[str]
    """
    if extensions is None:
        extensions = DEFAULT_INDEX_EXTENSIONS

    file_entries: list[dict[str, Any]] = []
    total_bytes = 0
    file_count = 0
    found_extensions: set[str] = set()
    truncated_by_byte_cap = False

    for dirpath, dirnames, filenames in os.walk(clone_dir, topdown=True):
        # Prune excluded dirs in-place
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            _, ext = os.path.splitext(fname)
            ext_lower = ext.lower()

            if ext_lower not in extensions:
                continue

            try:
                st = os.stat(fpath)
            except OSError:
                continue

            if max_indexed_bytes is not None and total_bytes + st.st_size > max_indexed_bytes:
                truncated_by_byte_cap = True
                continue

            try:
                h = hashlib.sha256()
                with open(fpath, "rb") as f:
                    while True:
                        chunk = f.read(65536)
                        if not chunk:
                            break
                        h.update(chunk)
                rel_path = os.path.relpath(fpath, clone_dir).replace(os.sep, "/")
                content_sha = h.hexdigest()
                try:
                    with open(fpath, "rb") as line_file:
                        line_count = line_file.read().count(b"\n") + 1
                except OSError:
                    line_count = 0
                file_entries.append({
                    "path": rel_path,
                    "sha256": content_sha,
                    "bytes": st.st_size,
                    "lines": line_count,
                })
                total_bytes += st.st_size
                file_count += 1
                found_extensions.add(ext_lower)
            except OSError:
                continue

    # Aggregate: sort by path and hash canonical JSON lines. The aggregate uses
    # path + sha + size + line count so two repos with identical file contents in
    # different layouts cannot collide.
    file_entries.sort(key=lambda item: item["path"])
    aggregate = "".join(json.dumps(entry, sort_keys=True) + "\n" for entry in file_entries)
    manifest_sha = hashlib.sha256(aggregate.encode("utf-8")).hexdigest()

    return {
        "content_manifest_sha": manifest_sha,
        "content_manifest_algorithm": "normalized_sha256_per_file_sorted",
        "indexed_file_count": file_count,
        "indexed_bytes": total_bytes,
        "extensions": sorted(found_extensions),
        "file_manifest": file_entries,
        "truncated_by_byte_cap": truncated_by_byte_cap,
        "max_indexed_bytes": max_indexed_bytes,
    }


# ── Output helpers ──────────────────────────────────────────────────────────

def build_repo_lock(
    repo_id: str,
    repo: str,
    head_sha: str,
    manifest: dict,
    detected_licenses: list[str],
    expected_license: str | None,
    primary_language: str | None,
    tier: str | None,
    clone_dir: str,
) -> dict:
    """Build the repo-lock.json object."""
    return {
        "repo_id": repo_id,
        "source": {
            "type": "github_public",
            "repo": repo,
            "clone_url": f"https://github.com/{repo}.git",
            "path": str(Path(clone_dir).resolve()),
        },
        "commit": head_sha,
        "license": {
            "detected": detected_licenses,
            "expected": expected_license,
        },
        "content_manifest_sha": manifest["content_manifest_sha"],
        "content_manifest_algorithm": manifest["content_manifest_algorithm"],
        "indexed_file_count": manifest["indexed_file_count"],
        "indexed_bytes": manifest["indexed_bytes"],
        "extensions": manifest["extensions"],
        "metadata": {
            "files": manifest["indexed_file_count"],
            "bytes": manifest["indexed_bytes"],
            "extensions": manifest["extensions"],
            "file_manifest": manifest["file_manifest"],
            "source_repo_kind": "github_public",
            "truncated_by_byte_cap": manifest["truncated_by_byte_cap"],
            "max_indexed_bytes": manifest["max_indexed_bytes"],
        },
        "primary_language": primary_language,
        "tier": tier,
        "policy": {
            "exclude": [
                ".git/**", "node_modules/**", "target/**", "dist/**", "build/**",
                ".venv/**", "venv/**", "__pycache__/**", ".openlocus/**",
                ".next/**", ".nuxt/**", "coverage/**", "*.pyc", "*.log",
            ],
        },
    }


def build_jsonl_entry(repo_lock: dict) -> dict:
    """Build a repos.lock.jsonl-compatible entry from a repo-lock dict."""
    return {
        "repo_id": repo_lock["repo_id"],
        "source": repo_lock["source"],
        "commit": repo_lock["commit"],
        "content_manifest_sha": repo_lock["content_manifest_sha"],
        "content_manifest_algorithm": repo_lock["content_manifest_algorithm"],
        "metadata": {
            **repo_lock["metadata"],
        },
        "language": {
            "primary": (repo_lock["primary_language"] or "unknown").lower(),
            "secondary": [],
            "tier": repo_lock["tier"] or "M",
        },
        "license": repo_lock["license"],
        "policy": repo_lock.get("policy", {}),
    }


# ── CLI ─────────────────────────────────────────────────────────────────────

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Clone a public GitHub repo, verify license, lock HEAD, produce repo-lock.json"
    )
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--manifest",
        help="Path to the CI repos manifest YAML (use with --repo-id)",
    )
    group.add_argument(
        "--repo",
        help="GitHub owner/repo slug, e.g. pallets/flask",
    )
    p.add_argument("--repo-id", help="Short identifier for the repo (required with --repo)")
    p.add_argument("--out-root", required=True, help="Root directory for cloned repos")
    p.add_argument("--lock-out", help="Path to write repo-lock.json, or a directory for {repo_id}-repo-lock.json (default: out-root)")
    p.add_argument("--jsonl-out", help="Path to append repos.lock.jsonl entry")
    p.add_argument("--expected-license", help="Expected license (e.g. MIT, MIT_OR_UNLICENSE)")
    p.add_argument("--primary-language", help="Primary language of the repo")
    p.add_argument("--tier", help="Tier label (smoke, nightly_medium, weekly_large, manual_extreme)")
    p.add_argument("--max-indexed-bytes", type=int, default=None, help="Max total indexed bytes")
    p.add_argument(
        "--extensions",
        help="Comma-separated list of file extensions to index (with dots), e.g. .py,.rs,.go",
    )
    return p.parse_args(argv)


# ── Minimal YAML subset parser (for manifest only) ─────────────────────────

def _parse_yaml_value(raw: str):
    """Parse a simple YAML scalar value."""
    s = raw.strip()
    if not s:
        return None
    # Remove inline comments
    if " #" in s:
        s = s[: s.index(" #")].rstrip()
    # Booleans
    if s.lower() in ("true", "yes"):
        return True
    if s.lower() in ("false", "no"):
        return False
    # Numbers
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    # Quoted strings
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


def parse_manifest_yaml(path: str) -> dict:
    """Parse the CI repos manifest YAML sufficiently to extract repos and policy.

    This is a minimal parser that handles only the subset of YAML used in
    openlocus-ci-repos-v1.yaml. It does NOT handle anchors, complex mappings,
    or multi-line scalars beyond the > style.
    """
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    root: dict = {}
    current_path: list[tuple[int, str]] = []  # (indent, key) stack
    repos_list: list[dict] | None = None
    current_repo: dict | None = None
    in_repos = False
    repo_indent = 0

    # We'll track structure manually for the specific shape of this file
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        stripped = line.rstrip()

        # Skip blanks and comments
        if not stripped or stripped.lstrip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())
        content = stripped.strip()

        # Handle multi-line > blocks (purpose field etc.) — skip them
        if content.endswith(">"):
            while i < len(lines):
                next_line = lines[i]
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_line.strip() and next_indent <= indent:
                    break
                i += 1
            continue

        # Parse repos list
        if content == "repos:":
            in_repos = True
            repos_list = []
            root["repos"] = repos_list
            continue

        if in_repos and repos_list is not None:
            # A new repo entry starts with - id: ...
            if content.startswith("- "):
                # Save previous repo
                if current_repo is not None:
                    repos_list.append(current_repo)
                repo_indent = indent
                current_repo = {}
                # Parse the first key: value from the "- key: value" line
                kv_part = content[2:].strip()
                if ":" in kv_part:
                    k, v = kv_part.split(":", 1)
                    current_repo[k.strip()] = _parse_yaml_value(v)
                continue

            # If we're inside a repo entry and the indent is greater than repo_indent
            if current_repo is not None and indent > repo_indent:
                if ":" in content:
                    k, v = content.split(":", 1)
                    key = k.strip()
                    val_raw = v.strip()
                    # Handle list values like [a, b, c]
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

            # If indent drops to or below repo_indent, we've left the current repo
            if current_repo is not None:
                repos_list.append(current_repo)
                current_repo = None

            # Could be a top-level key after repos
            if ":" in content and indent == 0:
                in_repos = False

        # Top-level key: value
        if not in_repos and ":" in content and indent == 0:
            k, v = content.split(":", 1)
            key = k.strip()
            val_raw = v.strip()
            if val_raw:
                # Handle list values
                if val_raw.startswith("[") and val_raw.endswith("]"):
                    items = [
                        _parse_yaml_value(item.strip())
                        for item in val_raw[1:-1].split(",")
                        if item.strip()
                    ]
                    root[key] = items
                else:
                    root[key] = _parse_yaml_value(val_raw)
            # else: nested mapping — we skip for this minimal parser
            # (policy and stages are not needed by ci_clone_and_lock_repo)

    # Don't forget the last repo
    if current_repo is not None and repos_list is not None:
        repos_list.append(current_repo)

    return root


def load_repo_from_manifest(manifest_path: str, repo_id: str) -> dict:
    """Load a single repo entry from the manifest by id."""
    manifest = parse_manifest_yaml(manifest_path)
    repos = manifest.get("repos", [])
    for r in repos:
        if r.get("id") == repo_id:
            return r
    print(f"ERROR: repo id '{repo_id}' not found in manifest", file=sys.stderr)
    sys.exit(1)


# ── Main ─────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    # Resolve repo info
    if args.manifest:
        if not args.repo_id:
            print("ERROR: --repo-id is required when using --manifest", file=sys.stderr)
            sys.exit(1)
        repo_entry = load_repo_from_manifest(args.manifest, args.repo_id)
        repo = repo_entry["repo"]
        repo_id = repo_entry["id"]
        expected_license = args.expected_license or repo_entry.get("expected_license")
        primary_language = args.primary_language or repo_entry.get("primary_language")
        tier = args.tier or repo_entry.get("tier")
    else:
        repo = args.repo
        repo_id = args.repo_id or repo.replace("/", "__")
        expected_license = args.expected_license
        primary_language = args.primary_language
        tier = args.tier

    # Validate expected license policy
    allowed = KNOWN_LICENSES
    err = validate_license_policy(expected_license, allowed)
    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)

    # Clone
    print(f"Cloning {repo} ...")
    clone_dir = clone_repo(repo, args.out_root)
    detach_head(clone_dir)
    head_sha = resolve_head_sha(clone_dir)
    print(f"HEAD → {head_sha}")

    # License check
    detected = detect_license(clone_dir)
    lic_err = check_license(detected, expected_license)
    if lic_err:
        print(f"WARNING: {lic_err}", file=sys.stderr)
        # Fail-closed: if expected license was specified and didn't match, exit 1
        sys.exit(1)
    if detected:
        print(f"License detected: {detected}")

    # File manifest
    ext_set = None
    if args.extensions:
        ext_set = {e.strip() if e.strip().startswith(".") else f".{e.strip()}" for e in args.extensions.split(",")}
    manifest = compute_manifest(clone_dir, extensions=ext_set, max_indexed_bytes=args.max_indexed_bytes)
    print(f"Manifest: {manifest['indexed_file_count']} files, {manifest['indexed_bytes']} bytes, sha={manifest['content_manifest_sha'][:16]}...")

    # Build outputs
    repo_lock = build_repo_lock(
        repo_id=repo_id,
        repo=repo,
        head_sha=head_sha,
        manifest=manifest,
        detected_licenses=detected,
        expected_license=expected_license,
        primary_language=primary_language,
        tier=tier,
        clone_dir=clone_dir,
    )

    # Write repo-lock.json
    lock_out = args.lock_out or args.out_root
    lock_out_path = Path(lock_out)
    if lock_out_path.suffix == ".json":
        lock_path = lock_out_path
        lock_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        lock_out_path.mkdir(parents=True, exist_ok=True)
        lock_path = lock_out_path / f"{repo_id}-repo-lock.json"
    with lock_path.open("w", encoding="utf-8") as f:
        json.dump(repo_lock, f, indent=2, sort_keys=True)
        f.write("\n")
    print(f"Wrote {lock_path}")

    # Append to repos.lock.jsonl
    if args.jsonl_out:
        jsonl_entry = build_jsonl_entry(repo_lock)
        os.makedirs(os.path.dirname(os.path.abspath(args.jsonl_out)), exist_ok=True)
        with open(args.jsonl_out, "a", encoding="utf-8") as f:
            f.write(json.dumps(jsonl_entry, sort_keys=True))
            f.write("\n")
        print(f"Appended entry to {args.jsonl_out}")


if __name__ == "__main__":
    main()
