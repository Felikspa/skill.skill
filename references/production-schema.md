# Production Schema

## Purpose
Use this contract to keep batch generation, worker handoff, registry updates, and the shelf in sync.

## Seed Pack
```json
{
  "batch_id": "2026-06-15-001",
  "seed": 12345,
  "count": 40,
  "generated_at": "2026-06-15T12:00:00+08:00",
  "items": [
    {
      "id": "seed-001",
      "keywords": ["atlas", "mirror", "tide"],
      "domain": "frontend design",
      "mechanism": "constraint matrix",
      "role": "curator",
      "resource_type": "references",
      "constraint": "must extend a capability the base model does not do reliably",
      "creative_brief": "..."
    }
  ]
}
```

## Idea Record
```json
{
  "name": "apple-native-ui-builder",
  "display_name": "Apple Native UI Builder",
  "hook": "Make UI feel native on Apple platforms",
  "use_when": "Frontend style keeps drifting",
  "spark": "Treat HIG like a hard scene graph",
  "capability_type": "style_specialization",
  "novelty_score": 8.7,
  "duplicate_score": 0.1,
  "directory": "apple-native-ui-builder",
  "status": "approved"
}
```

## Registry Record
Keep `developed-skills.json` machine-readable and append-only by name.

Required fields:
- `name`
- `display_name`
- `directory`
- `hook`
- `use_when`
- `spark`
- `capability_type`
- `created_at`
- `batch_id`
- `status`
- `readme`

Optional fields:
- `tags`
- `novelty_score`
- `duplicate_score`
- `notes`

## Shelf Rules
`developed-skills.md` must stay short.

Required columns:
- `Skill`
- `Hook`
- `Use When`
- `Spark`

Formatting rules:
- Keep one row per skill.
- Trim long strings with `...`.
- Sort newest first.
- Do not include scores, paths, or build logs.

## Worker Contract
Each approved idea becomes one worker task.

Worker payload should include:
- target skill name
- target directory
- concept summary
- required resource types
- validation checklist

Workers must:
- follow `skill-creator`
- write `README.md`
- pass `scripts/validate_skill_output.py`
- avoid rewriting global files
- avoid overlapping directories
- return the files they changed

## README Contract
Each generated child skill must have a user-facing `README.md`.

Required sections:
- `# <Display Name>`
- one-line hook
- `## Use When`
- `## Quick Start`
- `## Why Try It`

Style rules:
- Keep it brief.
- Make the function clear at a glance.
- Make the skill sound worth trying without hype.
- Do not include development logs.

## Batch Contract
Batch flow:
1. Generate seed pack.
2. Produce candidate ideas.
3. Validate against registry.
4. Confirm shortlist.
5. Dispatch one worker per idea.
6. Validate outputs.
7. Update registry and shelf.
8. Write batch artifacts under `production-runs/<batch-id>/`.
