---
name: skill-skill
description: Batch-generate, score, and coordinate new Codex skills from random seed packs. Use when building a new skill matrix, generating creative skill ideas, deduplicating against an existing registry, spawning one independent worker per approved skill, updating the shelf, or maintaining concise developed-skill lists.
---

# Skill Skill

## Overview
Generate skills that extend Codex's capability, not generic tasks it already handles. Use `skill-creator` for every child skill. Keep the root shelf short, readable, and fun.

## Workflow
1. Load `developed-skills.json`.
2. Generate a seed pack with `scripts/generate_seed_pack.py`.
3. Produce 20-50 candidate ideas from the seed pack.
4. Reject ideas that overlap with base-model ability or duplicate existing skills.
5. Score the rest by capability extension, novelty, resource fit, trigger clarity, batchability, and delight.
6. Confirm the shortlist.
7. Spawn one worker per approved idea. Give each worker a disjoint target directory.
8. Build each child skill with `skill-creator` only.
9. Write a short `README.md` for each child skill.
10. Validate each child skill with `scripts/validate_skill_output.py`.
11. Append finished records with `scripts/update_registry.py`.
12. Refresh `developed-skills.md`.
13. Save the batch under `production-runs/<batch-id>/`.

## Selection Rules
- Prefer skills that stabilize a style, encode a workflow, bundle references, or ship scripts.
- Reject plain summarization, generic writing, generic planning, or ordinary chat help.
- Every approved skill must answer: what capability does this add or stabilize that the base model does not already do reliably?

## Worker Rules
- One approved skill per worker.
- No overlapping write sets.
- Workers only edit their own target directory.
- Root registry and shelf updates happen after validation.
- Every child skill must include a short `README.md` that makes the user want to try it quickly.

## README Rules
- Include only: title, one-line hook, best use cases, quick start, and what makes it different.
- Keep it short enough to scan in under 30 seconds.
- Do not include build logs, internal scoring, or long design notes.
- If the README does not make the skill's value obvious, the skill is not complete.

## Shelf Rules
- Keep `developed-skills.md` concise and scannable.
- One row per skill.
- Keep `Hook`, `Use When`, and `Spark` brief.
- Trim long text with ellipses.
- Do not add build logs or long notes to the shelf.

## Resources
- `idea-seeds/seed-banks.json`: local random word banks.
- `references/production-schema.md`: registry, batch, and worker contracts.
- `scripts/`: seed generation, validation, output checks, orchestration, and registry updates.
