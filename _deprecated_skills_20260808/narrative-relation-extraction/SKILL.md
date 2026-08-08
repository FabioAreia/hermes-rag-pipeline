---
name: narrative-relation-extraction
description: Extract relationship graphs from lorebook/narrative text.
version: 1.0.0
---

# Narrative Relation Extraction

Extract a relationship graph from narrative text — lorebook JSONL, canon, or chat
logs — and project it into per-entity structured files. Distinct from RAG *retrieval*:
here you build the MAP of who-relates-to-whom; retrieval later queries it.

## When to use

- User wants to remember/auto-maintain **alianças, amizades, relações** across a story.
- Building a per-character `relacoes` structure from a canon.
- Detecting clusters/circles (which people form a group/household).
- Detecting parentesco, romance, trabalho, habitação, hobby ties.

## Working script

`scripts/extractor_relacoes.py` — CLI: `--canon <file> --lore <dir> [--min N] [--apply]`.
Run `--report` first (no writes); verify; then `--apply` (writes + backup).

## Core techniques (the hard-won lessons)

### 1. Desambiguate identity by SURNAME, never first name
Two distinct circles can share first names ("Filipa, Teresa, Sara, Marta" appears in
two different households). Always resolve identity by **full name + apelido + casa +
profissão**. When a first name collides in a message, pick by the surname present.
Example: "Marta do financeiro" (house of Andreia) ≠ "Marta Umbelino" (Uber driver, Group C).

### 2. Detect relation TYPE by a WINDOW around the name, not the whole message
Searching the whole message for "mulher"/"esposa"/"irmã" fires parentesco in every
message that contains those words anywhere. Instead, take a ~60-char window around
each **occurrence of the character's name** and check the type terms inside that window.
This is what separates "irmã near the name" (real parentesco) from noise.

### 3. ENFORCE "parentesco excludes romance" (user-critical)
If a direct kinship relation exists ("mãe de X", "filha de X", "irmã de X", "esposa de X" —
terms matching `X de Y`), that pair is NEVER romance. Family is not lovers. Example:
Lara is mother of Mia/Stacy → Lara↔Mia = parentesco, never "amante". This was a user
correction; without it the extractor wrongly tagged every mother-daughter pair as romance.
In code: if `parentesco in tipos and romanticos in tipos`, drop `romanticos`.

### 4. Co-occurrence is reliable for STRUCTURE; fine type labels are noisy
Name co-occurrence robustly finds **who is connected to whom** and cluster/circle
structure. But fine type labels are ambiguous when the story has a **hub** (e.g. one
character is lover to almost everyone) — "romance" fires everywhere near the hub.
Structure is safe; treat fine labels as candidates, especially around a hub.

## Type taxonomy

parentesco, romanticos, amizades, trabalho, habitatio, hobby, grupos, conhecidos.
Kinship terms must be direct ("X de Y") to confirm parentesco group.

## Pitfalls

- **Surname shared across a family** (all "Jefferson") destroys surname-only matching —
  everyone gets flagged present whenever the surname appears. Detect by first name
  first, use surname only to disambiguate collisions.
- **Append aditively**: preserve existing `relacoes` that aren't contradicted; merge,
  don't overwrite. Always back up the entity files before `--apply`.
- **Circles/social groups have a rule**: each person belongs to one household/group;
  never cross members between groups without canon justification. Record the groups
  (per scenario, e.g. `grupos.md`) with a disambiguation table for shared first names.

## Notes for the user's environment

User-created lorebook skills (roleplay-rag, lorebook-rag, tyronne-*) under
`/opt/data/skills/` are **user-owned / not curator-managed** — do not edit them;
recommend `hermes curator adopt <name>` if they need official ownership.
This relationship-extraction skill is the curator-managed home for the technique and
works on ANY persona/canon, complementing (not replacing) those user skills.
