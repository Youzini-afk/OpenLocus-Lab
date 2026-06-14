#!/usr/bin/env python3
"""Validate the docs/en <-> docs/zh i18n mirror layout."""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
EN = DOCS / "en"
ZH = DOCS / "zh"

MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def collect_errors() -> list[str]:
    errors: list[str] = []

    if not EN.is_dir():
        errors.append("Missing docs/en/ directory")
    if not ZH.is_dir():
        errors.append("Missing docs/zh/ directory")

    en_files = sorted(EN.glob("*.md")) if EN.is_dir() else []
    zh_files = sorted(ZH.glob("*.md")) if ZH.is_dir() else []
    en_names = {p.name for p in en_files}
    zh_names = {p.name for p in zh_files}

    # 1. 1:1 mirror
    for name in sorted(en_names - zh_names):
        errors.append(f"docs/en/{name} has no matching docs/zh/{name}")
    for name in sorted(zh_names - en_names):
        errors.append(f"docs/zh/{name} has no matching docs/en/{name}")

    # 2. No leftover language-suffixed files anywhere under docs/
    for p in DOCS.rglob("*.en.md"):
        errors.append(f"Unexpected .en.md file: {p.relative_to(REPO)}")
    for p in DOCS.rglob("*.zh.md"):
        errors.append(f"Unexpected .zh.md file: {p.relative_to(REPO)}")

    # 3. Root docs should only contain current-research-conclusions.md (+ neutral files)
    for p in DOCS.glob("*.md"):
        if p.name != "current-research-conclusions.md":
            errors.append(f"Unexpected root markdown: {p.relative_to(REPO)}")

    def is_external(target: str) -> bool:
        if target.startswith("#"):
            return True
        if target.startswith(("http://", "https://", "mailto:")):
            return True
        return False

    def resolve(target: str, source: Path) -> Path | None:
        # Strip anchor
        if "#" in target:
            target = target.split("#", 1)[0]
        if not target:
            return None
        target = target.removeprefix("./")
        if target.startswith("/"):
            # Absolute from repo root
            return REPO / target.lstrip("/")
        if target.startswith("../"):
            return (source.parent / target).resolve()
        return (source.parent / target).resolve()

    permissive_root = DOCS / "current-research-conclusions.md"

    # 4. Markdown links checks
    for source in list(en_files) + list(zh_files) + [permissive_root]:
        text = source.read_text(encoding="utf-8")
        for match in MD_LINK_RE.finditer(text):
            target = match.group(1)
            if is_external(target):
                continue
            # No links to removed language-suffixed files
            if target.endswith(".en.md") or target.endswith(".zh.md"):
                errors.append(
                    f"{source.relative_to(REPO)}:{match.start()} links to removed language-suffixed file: {target}"
                )
                continue
            resolved = resolve(target, source)
            if resolved is None:
                continue
            if not resolved.exists():
                errors.append(
                    f"{source.relative_to(REPO)}:{match.start()} broken link to {target} (resolved: {resolved.relative_to(REPO) if resolved.is_relative_to(REPO) else resolved})"
                )

    return errors


def main() -> int:
    errors = collect_errors()
    if errors:
        print("Validation FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("Validation passed:")
    en_count = len(list(EN.glob("*.md")))
    zh_count = len(list(ZH.glob("*.md")))
    print(f"  docs/en/*.md: {en_count}, docs/zh/*.md: {zh_count}, 1:1 OK")
    print("  No stray root markdowns except current-research-conclusions.md")
    print("  No links to removed .en.md/.zh.md files")
    print("  All relative markdown links resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
