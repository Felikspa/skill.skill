#!/usr/bin/env python3
"""Build a deterministic idea seed pack for LLM-driven concept generation."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
DEFAULT_SOURCE_DIR = ROOT_DIR / "idea-seeds"

REQUIRED_POOLS = (
    "keywords",
    "domains",
    "mechanisms",
    "resource_types",
    "roles",
    "constraints",
)


@dataclass(frozen=True)
class SeedSelection:
    keywords: list[str]
    domain: str
    mechanism: str
    resource_type: str
    role: str
    constraint: str


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="generate_seed_pack",
        description="Generate a deterministic seed pack JSON for idea generation.",
    )
    parser.add_argument("--count", type=int, required=True, help="Number of seeds to generate.")
    parser.add_argument("--seed", type=int, required=True, help="Deterministic RNG seed.")
    parser.add_argument("--out", type=str, default="-", help="Output path, or '-' for stdout.")
    return parser.parse_args(argv)


def read_json_file(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_text(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def extend_unique(target: list[str], values: Iterable[Any]) -> None:
    seen = set(target)
    for value in values:
        text = normalize_text(value)
        if text is None or text in seen:
            continue
        target.append(text)
        seen.add(text)


def extract_pools(node: Any, pools: dict[str, list[str]]) -> None:
    if isinstance(node, dict):
        aliases = {
            "words": "keywords",
            "keywords": "keywords",
            "domains": "domains",
            "mechanisms": "mechanisms",
            "resource_constraints": "constraints",
            "resource_types": "resource_types",
            "roles": "roles",
            "constraints": "constraints",
        }
        for raw_key, pool_key in aliases.items():
            if raw_key in node:
                value = node[raw_key]
                if isinstance(value, list):
                    extend_unique(pools[pool_key], value)
                else:
                    text = normalize_text(value)
                    if text is not None:
                        extend_unique(pools[pool_key], [text])
        for value in node.values():
            extract_pools(value, pools)
    elif isinstance(node, list):
        for item in node:
            extract_pools(item, pools)


def load_json_sources(source_dir: Path) -> tuple[dict[str, list[str]], list[str]]:
    pools = {key: [] for key in REQUIRED_POOLS}
    source_files: list[str] = []

    if not source_dir.exists():
        raise FileNotFoundError(f"Seed source directory does not exist: {source_dir}")

    json_files = sorted(path for path in source_dir.glob("*.json") if path.is_file())
    for path in json_files:
        payload = read_json_file(path)
        extract_pools(payload, pools)
        source_files.append(path.name)

    if not source_files:
        raise FileNotFoundError(f"No JSON seed files found in: {source_dir}")

    missing = [key for key, values in pools.items() if not values]
    if missing:
        raise ValueError(f"Seed files are missing required pools: {', '.join(missing)}")

    return pools, source_files


def choose_from_pool(rng: random.Random, pool: list[str], count: int = 1) -> list[str]:
    if not pool:
        raise ValueError("cannot choose from an empty pool")
    if count >= len(pool):
        order = list(pool)
        rng.shuffle(order)
        return order
    return rng.sample(pool, count)


def build_seed_selection(rng: random.Random, pools: dict[str, list[str]]) -> SeedSelection:
    keywords = choose_from_pool(rng, pools["keywords"], count=min(3, len(pools["keywords"])))
    domain = rng.choice(pools["domains"])
    mechanism = rng.choice(pools["mechanisms"])
    resource_type = rng.choice(pools["resource_types"])
    role = rng.choice(pools["roles"])
    constraint = rng.choice(pools["constraints"])
    return SeedSelection(
        keywords=keywords,
        domain=domain,
        mechanism=mechanism,
        resource_type=resource_type,
        role=role,
        constraint=constraint,
    )


def build_pack(count: int, seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    source_pools, source_files = load_json_sources(DEFAULT_SOURCE_DIR)
    source_mode = "json_files"
    pools = {key: list(source_pools[key]) for key in REQUIRED_POOLS}

    selections: list[SeedSelection] = [build_seed_selection(rng, pools) for _ in range(count)]
    pack_keywords = []
    pack_domains = []
    pack_mechanisms = []
    pack_resource_types = []
    pack_roles = []
    pack_constraints = []

    items: list[dict[str, Any]] = []
    for index, selection in enumerate(selections, start=1):
        extend_unique(pack_keywords, selection.keywords)
        extend_unique(pack_domains, [selection.domain])
        extend_unique(pack_mechanisms, [selection.mechanism])
        extend_unique(pack_resource_types, [selection.resource_type])
        extend_unique(pack_roles, [selection.role])
        extend_unique(pack_constraints, [selection.constraint])

        prompt = (
            f"Create a Codex skill idea for {selection.domain}. It should use "
            f"{selection.mechanism}, act with a {selection.role} flavor, and lean on "
            f"{selection.resource_type}. Constraint: {selection.constraint}. "
            f"Anchor it around: {', '.join(selection.keywords)}. Reject generic chat-help ideas."
        )
        items.append(
            {
                "id": f"seed-{index:03d}",
                "keywords": selection.keywords,
                "domain": selection.domain,
                "mechanism": selection.mechanism,
                "resource_type": selection.resource_type,
                "role": selection.role,
                "constraint": selection.constraint,
                "idea_prompt": prompt,
            }
        )

    canonical = json.dumps(
        {
            "count": count,
            "seed": seed,
            "source_mode": source_mode,
            "source_files": source_files,
            "items": items,
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return {
        "schema": {
            "name": "skill.skill.seed_pack",
            "version": "1.0",
            "item": {
                "id": "string",
                "keywords": ["string"],
                "domain": "string",
                "mechanism": "string",
                "resource_type": "string",
                "role": "string",
                "constraint": "string",
                "idea_prompt": "string",
            },
        },
        "metadata": {
            "generator": "scripts/generate_seed_pack.py",
            "deterministic": True,
            "count": count,
            "seed": seed,
            "source_mode": source_mode,
            "source_files": source_files,
            "pack_id": hashlib.sha256(canonical).hexdigest()[:16],
        },
        "selected_keywords": pack_keywords,
        "selected_domains": pack_domains,
        "selected_mechanisms": pack_mechanisms,
        "selected_resource_types": pack_resource_types,
        "selected_roles": pack_roles,
        "selected_constraints": pack_constraints,
        "seeds": items,
    }


def write_output(payload: dict[str, Any], out_path: str) -> None:
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if out_path == "-":
        sys.stdout.write(rendered)
        return

    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.count <= 0:
        raise SystemExit("--count must be greater than 0")

    payload = build_pack(args.count, args.seed)
    write_output(payload, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
