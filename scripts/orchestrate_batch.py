#!/usr/bin/env python3
"""Coordinate batch validation and write dispatch artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from validate_batch import load_json, validate_batch


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Orchestrate a skill-production batch.")
    parser.add_argument("--batch", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--summaries", type=Path)
    parser.add_argument("--thread-specs", type=Path)
    parser.add_argument("--allow-invalid", action="store_true")
    return parser.parse_args(argv)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        report = validate_batch(load_json(args.batch), load_json(args.registry))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.report:
        write_json(args.report, report)

    if report["ok"] or args.allow_invalid:
        if args.summaries:
            write_json(args.summaries, report["summaries"])
        if args.thread_specs:
            write_json(args.thread_specs, report["thread_specs"])

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
