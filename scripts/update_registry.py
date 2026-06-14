#!/usr/bin/env python3
"""Maintain developed-skills.json and rebuild the concise markdown shelf."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_REGISTRY = Path("developed-skills.json")
DEFAULT_SHELF = Path("developed-skills.md")
REQUIRED_RECORD_FIELDS = (
    "name",
    "display_name",
    "directory",
    "hook",
    "use_when",
    "spark",
    "capability_type",
    "novelty_key",
    "created_at",
    "batch_id",
    "status",
    "readme",
)
SHELF_LIMITS = {
    "skill": 34,
    "hook": 34,
    "use_when": 30,
    "spark": 36,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update developed-skills.json and rebuild developed-skills.md."
    )
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--shelf", type=Path, default=DEFAULT_SHELF)
    parser.add_argument("--add-record", help="Completed skill record as a JSON object.")
    parser.add_argument("--batch-id", help="Optional batch id to record under batches.")
    parser.add_argument("--rebuild-shelf", action="store_true")
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def normalize_name(value: str) -> str:
    return clean_text(value).casefold()


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "updated_at": now_iso(), "skills": [], "batches": []}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid registry JSON at {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise SystemExit("Registry must be a JSON object.")
    if not isinstance(data.get("skills"), list):
        raise SystemExit('Registry must contain a "skills" list.')
    if not isinstance(data.get("batches"), list):
        raise SystemExit('Registry must contain a "batches" list.')
    return data


def validate_record(record: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(record)
    normalized.setdefault("status", "completed")

    missing = [field for field in REQUIRED_RECORD_FIELDS if not clean_text(normalized.get(field))]
    if missing:
        raise SystemExit(f"Record is missing required fields: {', '.join(missing)}")

    if clean_text(normalized["status"]) != "completed":
        raise SystemExit('Only records with status "completed" can be added.')

    readme = Path(clean_text(normalized["readme"]))
    directory = Path(clean_text(normalized["directory"]))
    if readme.name.lower() != "readme.md":
        raise SystemExit('Record field "readme" must point to README.md.')
    if readme.parent.name != directory.name and not str(readme).startswith(str(directory)):
        raise SystemExit('Record "readme" must belong to the skill directory.')

    return normalized


def parse_record(raw: str) -> dict[str, Any]:
    try:
        record = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"--add-record must be valid JSON: {exc}") from exc
    if not isinstance(record, dict):
        raise SystemExit("--add-record must be a JSON object.")
    return validate_record(record)


def upsert_skill(registry: dict[str, Any], record: dict[str, Any]) -> str:
    key = normalize_name(record["name"])
    skills = registry["skills"]
    for index, existing in enumerate(skills):
        if isinstance(existing, dict) and normalize_name(existing.get("name", "")) == key:
            skills[index] = record
            return "updated"
    skills.append(record)
    return "added"


def add_batch(registry: dict[str, Any], batch_id: str | None) -> None:
    if not batch_id:
        return
    batches = registry["batches"]
    if any(isinstance(item, dict) and item.get("batch_id") == batch_id for item in batches):
        return
    batches.append({"batch_id": batch_id, "recorded_at": now_iso()})


def write_registry(path: Path, registry: dict[str, Any]) -> None:
    registry["updated_at"] = now_iso()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def trim_cell(text: str, limit: int) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    if limit <= 3:
        return "..."
    return text[: limit - 3].rstrip() + "..."


def escape_cell(text: str) -> str:
    return text.replace("|", "\\|")


def shelf_row(record: dict[str, Any]) -> str:
    cells = [
        f"`{trim_cell(record['name'], SHELF_LIMITS['skill'])}`",
        trim_cell(record["hook"], SHELF_LIMITS["hook"]),
        trim_cell(record["use_when"], SHELF_LIMITS["use_when"]),
        trim_cell(record["spark"], SHELF_LIMITS["spark"]),
    ]
    return "| " + " | ".join(escape_cell(cell) for cell in cells) + " |"


def build_shelf(registry: dict[str, Any]) -> str:
    completed = [
        skill
        for skill in registry["skills"]
        if isinstance(skill, dict) and clean_text(skill.get("status")) == "completed"
    ]
    completed.sort(key=lambda item: clean_text(item.get("created_at")), reverse=True)

    lines = [
        "# Developed Skills",
        "",
        f"> {len(completed)} skills grown. Grab a spark and try it.",
        "",
        "| Skill | Hook | Use When | Spark |",
        "|---|---|---|---|",
    ]
    lines.extend(shelf_row(record) for record in completed)
    lines.append("")
    return "\n".join(lines)


def write_shelf(path: Path, registry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_shelf(registry), encoding="utf-8")


def main() -> int:
    args = parse_args()
    if not args.add_record and not args.rebuild_shelf and not args.batch_id:
        raise SystemExit("Nothing to do: use --add-record, --batch-id, or --rebuild-shelf.")

    registry = load_registry(args.registry)
    action = None
    if args.add_record:
        action = upsert_skill(registry, parse_record(args.add_record))
    add_batch(registry, args.batch_id)
    write_registry(args.registry, registry)

    if args.rebuild_shelf or args.add_record:
        write_shelf(args.shelf, registry)

    if action:
        print(f"Record {action}: {args.registry}")
    if args.rebuild_shelf or args.add_record:
        print(f"Shelf rebuilt: {args.shelf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
