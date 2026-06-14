#!/usr/bin/env python3
"""Validate one generated child skill before registry insertion."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$")
README_REQUIRED_HEADINGS = (
    "## Use When",
    "## Quick Start",
    "## Why Try It",
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate one generated skill directory.")
    parser.add_argument("--skill-dir", required=True, type=Path)
    parser.add_argument("--max-skill-lines", type=int, default=180)
    parser.add_argument("--max-readme-lines", type=int, default=80)
    parser.add_argument(
        "--allow-no-resources",
        action="store_true",
        help="Allow a child skill with no references, scripts, or assets.",
    )
    return parser.parse_args(argv)


def read_text(path: Path) -> str:
    if not path.exists():
        raise ValueError(f"Missing required file: {path}")
    if not path.is_file():
        raise ValueError(f"Required path is not a file: {path}")
    return path.read_text(encoding="utf-8")


def extract_frontmatter(text: str, path: Path) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path} must start with YAML frontmatter.")
    try:
        end = lines[1:].index("---") + 1
    except ValueError as exc:
        raise ValueError(f"{path} frontmatter is not closed.") from exc

    fields: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" not in line:
            raise ValueError(f"{path} frontmatter line is not key-value: {line}")
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"')
    return fields


def validate_skill_md(skill_dir: Path, issues: list[str], max_lines: int) -> str:
    path = skill_dir / "SKILL.md"
    text = read_text(path)
    lines = text.splitlines()
    if len(lines) > max_lines:
        issues.append(f"SKILL.md has {len(lines)} lines, above limit {max_lines}.")

    fields = extract_frontmatter(text, path)
    name = fields.get("name", "")
    description = fields.get("description", "")
    if not NAME_PATTERN.match(name):
        issues.append(f"Invalid skill name in frontmatter: {name}")
    if len(description.split()) < 12:
        issues.append("Frontmatter description is too short to trigger reliably.")
    if name != skill_dir.name:
        issues.append(f"Frontmatter name '{name}' does not match directory '{skill_dir.name}'.")
    return name


def validate_readme(skill_dir: Path, issues: list[str], max_lines: int) -> None:
    path = skill_dir / "README.md"
    text = read_text(path)
    lines = [line.rstrip() for line in text.splitlines()]
    if len(lines) > max_lines:
        issues.append(f"README.md has {len(lines)} lines, above limit {max_lines}.")
    if not lines or not lines[0].startswith("# "):
        issues.append("README.md must start with a title.")
    for heading in README_REQUIRED_HEADINGS:
        if heading not in text:
            issues.append(f"README.md missing heading: {heading}")
    meaningful = [line for line in lines if line.strip() and not line.startswith("#")]
    if len(meaningful) < 4:
        issues.append("README.md is too thin to explain the skill quickly.")


def validate_openai_yaml(skill_dir: Path, issues: list[str]) -> None:
    path = skill_dir / "agents" / "openai.yaml"
    text = read_text(path)
    required = ("display_name:", "short_description:", "default_prompt:")
    for token in required:
        if token not in text:
            issues.append(f"agents/openai.yaml missing {token}")


def validate_resources(skill_dir: Path, issues: list[str]) -> None:
    resource_dirs = ("references", "scripts", "assets")
    has_resource = False
    for name in resource_dirs:
        path = skill_dir / name
        if path.exists() and any(item.is_file() for item in path.rglob("*")):
            has_resource = True
            break
    if not has_resource:
        issues.append("Skill must include at least one reference, script, or asset file.")


def validate_skill_dir(
    skill_dir: Path,
    max_skill_lines: int,
    max_readme_lines: int,
    allow_no_resources: bool = False,
) -> list[str]:
    if not skill_dir.exists():
        return [f"Skill directory does not exist: {skill_dir}"]
    if not skill_dir.is_dir():
        return [f"Skill path is not a directory: {skill_dir}"]

    issues: list[str] = []
    validate_skill_md(skill_dir, issues, max_skill_lines)
    validate_readme(skill_dir, issues, max_readme_lines)
    validate_openai_yaml(skill_dir, issues)
    if not allow_no_resources:
        validate_resources(skill_dir, issues)
    return issues


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        issues = validate_skill_dir(
            args.skill_dir,
            args.max_skill_lines,
            args.max_readme_lines,
            args.allow_no_resources,
        )
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if issues:
        for issue in issues:
            print(f"error: {issue}", file=sys.stderr)
        return 1

    print(f"OK: {args.skill_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
