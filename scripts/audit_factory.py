#!/usr/bin/env python3
"""Audit a skill factory root for registry, shelf, and directory drift."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


IGNORED_DIRS = {
    ".git",
    "idea-seeds",
    "production-runs",
    "scripts",
    "__pycache__",
}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit a skill factory directory.")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--registry", default="developed-skills.json")
    return parser.parse_args(argv)


def load_registry(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid registry JSON at {path}: {exc}") from exc

    if not isinstance(data, dict) or not isinstance(data.get("skills"), list):
        raise SystemExit("Registry must be an object with a skills list.")
    return data


def skill_dirs(root: Path) -> set[str]:
    result = set()
    for child in root.iterdir():
        if not child.is_dir() or child.name in IGNORED_DIRS:
            continue
        if (child / "SKILL.md").is_file():
            result.add(child.name)
    return result


def registry_dirs(registry: dict[str, Any]) -> set[str]:
    result = set()
    for index, record in enumerate(registry["skills"]):
        if not isinstance(record, dict):
            raise SystemExit(f"registry.skills[{index}] must be an object.")
        directory = record.get("directory")
        if not isinstance(directory, str) or not directory.strip():
            raise SystemExit(f"registry.skills[{index}] missing directory.")
        result.add(directory.strip())
    return result


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = args.root.resolve()
    registry = load_registry(root / args.registry)
    found = skill_dirs(root)
    registered = registry_dirs(registry)

    unregistered = sorted(found - registered)
    missing = sorted(registered - found)

    if unregistered:
        print("Unregistered skill directories:")
        for item in unregistered:
            print(f"- {item}")
    if missing:
        print("Registered skills missing directories:")
        for item in missing:
            print(f"- {item}")

    if unregistered or missing:
        return 1

    print(f"OK: {len(registered)} registered skills match directories.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
