---
name: lorebook-loader
description: "Load SillyTavern lorebook JSON by name."
version: 1.0.0
author: Hermes Agent
---

# Lorebook Loader

Load a SillyTavern lorebook JSON into context.

## When to use

Trigger phrases:
- `load lorebook <name>`
- `lorebook <name>`
- `carrega lorebook <name>`
- `usa o lorebook <name>`
- `usa lorebook <name>`

## Instructions

1. Extract the lorebook name from the user's message.
2. Resolve the file path in this order:
   - `/media/sda/lorebook_<name>.json`
   - `/media/sda/lorebook_<name>_stepdad.json`
   - `/opt/data/lorebook_<name>.json`
3. Read the file with `read_file`.
4. Summarize in 3-6 tight bullets:
   - Characters and relationships
   - Key backstory facts
   - Sexual history / boundaries if present
   - Setting and tone
5. Present as **Active Lorebook Context** before continuing.
6. If not found, list available lorebooks with:
   `ls /media/sda/lorebook_*.json`

## Notes

- Only read and summarize. Do not rewrite or add facts.
- Max 6 bullets. Keep it tight.
- If user asks to update or create a lorebook, say: `lorebook-loader only loads existing lorebooks. Use the lorebook-authoring skill for editing.`