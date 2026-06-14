#!/usr/bin/env python3
"""Validate a skill-production batch against the developed registry."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


STOP_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "for",
    "in",
    "of",
    "on",
    "or",
    "skill",
    "the",
    "to",
    "with",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def clean_text(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("expected non-empty string")
    text = " ".join(value.split())
    if not text:
        raise ValueError("expected non-empty string")
    return text


def normalize_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "-", clean_text(value).lower()).strip("-")


def normalize_concept(value: Any) -> str:
    words = [word for word in re.findall(r"[a-z0-9]+", clean_text(value).lower()) if word not in STOP_WORDS]
    return " ".join(words)


def concept_terms(value: str) -> set[str]:
    return set(normalize_concept(value).split())


def extract_items(data: dict[str, Any], key: str, source: str) -> list[dict[str, Any]]:
    items = data.get(key)
    if not isinstance(items, list):
        raise ValueError(f"{source} must contain a '{key}' list")
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"{source}.{key}[{index}] must be an object")
    return items


def load_registry_skills(registry: dict[str, Any]) -> list[dict[str, Any]]:
    skills = registry.get("skills")
    if not isinstance(skills, list):
        raise ValueError("registry must contain a 'skills' list")
    result: list[dict[str, Any]] = []
    for index, skill in enumerate(skills):
        if not isinstance(skill, dict):
            raise ValueError(f"registry.skills[{index}] must be an object")
        result.append(skill)
    return result


def summarize_idea(idea: dict[str, Any], index: int) -> dict[str, Any]:
    name = normalize_name(idea.get("name"))
    concept = clean_text(idea.get("concept"))
    hook = clean_text(idea.get("hook"))
    use_when = clean_text(idea.get("use_when"))
    spark = clean_text(idea.get("spark"))
    capability_type = clean_text(idea.get("capability_type"))
    directory = normalize_name(idea.get("directory"))
    novelty_key = normalize_concept(idea.get("novelty_key"))
    return {
        "index": index,
        "name": name,
        "concept": concept,
        "hook": hook,
        "use_when": use_when,
        "spark": spark,
        "capability_type": capability_type,
        "directory": directory,
        "novelty_key": novelty_key,
    }


def build_thread_spec(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": summary["name"],
        "title": f"Build skill: {summary['name']}",
        "agent": "skill-production-worker",
        "prompt": (
            "Build one Codex skill from this approved idea.\n"
            f"Name: {summary['name']}\n"
            f"Directory: {summary['directory']}\n"
            f"Concept: {summary['concept']}\n"
            f"Hook: {summary['hook']}\n"
            f"Use when: {summary['use_when']}\n"
            f"Spark: {summary['spark']}\n"
            f"Capability type: {summary['capability_type']}\n"
            f"Novelty key: {summary['novelty_key']}\n"
            "Requirements: use skill-creator, write README.md, keep the root shelf concise, and do not edit global files. "
            "Include at least one meaningful references, scripts, or assets file. "
            "Write only to the absolute target directory supplied by the main agent, and report that absolute path in the final response. "
            "The worker is not done until scripts/validate_skill_output.py --skill-dir <target> passes from the factory root."
        ),
        "metadata": {
            "batch_index": summary["index"],
            "directory": summary["directory"],
            "capability_type": summary["capability_type"],
            "novelty_key": summary["novelty_key"],
        },
    }


def validate_batch(batch: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    ideas = extract_items(batch, "ideas", "batch")
    registry_skills = load_registry_skills(registry)
    summaries = [summarize_idea(idea, index) for index, idea in enumerate(ideas)]

    registry_names = {normalize_name(skill.get("name")) for skill in registry_skills if skill.get("name")}
    registry_directories = {clean_text(skill.get("directory")) for skill in registry_skills if skill.get("directory")}
    registry_concepts = {
        normalize_concept(skill.get("concept"))
        for skill in registry_skills
        if isinstance(skill.get("concept"), str) and skill.get("concept").strip()
    }
    registry_novelty_keys = {
        normalize_concept(skill.get("novelty_key"))
        for skill in registry_skills
        if isinstance(skill.get("novelty_key"), str) and skill.get("novelty_key").strip()
    }

    issues: list[dict[str, Any]] = []
    name_counts = Counter(summary["name"] for summary in summaries)
    directory_counts = Counter(summary["directory"] for summary in summaries)
    concept_counts = Counter(normalize_concept(summary["concept"]) for summary in summaries)
    novelty_key_counts = Counter(summary["novelty_key"] for summary in summaries)

    for name, count in name_counts.items():
        if count > 1:
            issues.append({"code": "duplicate_batch_name", "name": name, "count": count})
        if name in registry_names:
            issues.append({"code": "duplicate_registry_name", "name": name})

    for directory, count in directory_counts.items():
        if count > 1:
            issues.append({"code": "duplicate_batch_directory", "directory": directory, "count": count})
        if directory in registry_directories:
            issues.append({"code": "duplicate_registry_directory", "directory": directory})

    for concept, count in concept_counts.items():
        if count > 1:
            names = [summary["name"] for summary in summaries if normalize_concept(summary["concept"]) == concept]
            issues.append({"code": "repeated_batch_concept", "concept": concept, "names": names})
        if concept in registry_concepts:
            names = [summary["name"] for summary in summaries if normalize_concept(summary["concept"]) == concept]
            issues.append({"code": "repeated_registry_concept", "concept": concept, "names": names})

    for novelty_key, count in novelty_key_counts.items():
        if count > 1:
            names = [summary["name"] for summary in summaries if summary["novelty_key"] == novelty_key]
            issues.append({"code": "duplicate_batch_novelty_key", "novelty_key": novelty_key, "names": names})
        if novelty_key in registry_novelty_keys:
            names = [summary["name"] for summary in summaries if summary["novelty_key"] == novelty_key]
            issues.append({"code": "duplicate_registry_novelty_key", "novelty_key": novelty_key, "names": names})

    term_sets = {summary["name"]: concept_terms(summary["concept"]) for summary in summaries}
    for left_index, left_summary in enumerate(summaries):
        left_terms = term_sets[left_summary["name"]]
        for right_summary in summaries[left_index + 1 :]:
            right_terms = term_sets[right_summary["name"]]
            overlap = left_terms & right_terms
            if not overlap:
                continue
            similarity = len(overlap) / max(len(left_terms), len(right_terms))
            if similarity >= 0.65:
                issues.append(
                    {
                        "code": "similar_batch_concept",
                        "names": [left_summary["name"], right_summary["name"]],
                        "shared_terms": sorted(overlap),
                        "similarity": round(similarity, 3),
                    }
                )

    missing_readme = [
        summary["name"]
        for summary in summaries
        if not summary["directory"] or not summary["directory"].strip()
    ]
    if missing_readme:
        issues.append({"code": "missing_directory", "names": missing_readme})

    return {
        "ok": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "summaries": summaries,
        "thread_specs": [build_thread_spec(summary) for summary in summaries],
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a skill batch against a registry.")
    parser.add_argument("--batch", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--summaries-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        report = validate_batch(load_json(args.batch), load_json(args.registry))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    payload: Any = report["summaries"] if args.summaries_only else report
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
