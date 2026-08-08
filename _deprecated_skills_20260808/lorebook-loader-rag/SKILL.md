---
name: lorebook-loader-rag
description: "Load lorebook JSON and filter by recent chat context."
version: 1.0.0
author: Hermes Agent
---

# Lorebook Loader RAG

Load a SillyTavern lorebook and inject only relevant entries based on recent chat context.

## When to use

Trigger phrases:
- `lorebook <name>`
- `load lorebook <name>`
- `carrega lorebook <name>`
- `usa o lorebook <name>`
- `contexto lorebook <name>`
- `*lorebook <name>*`
- `@lorebook <name>`

Also trigger when:
- User explicitly asks to continue a story with a known lorebook name
- User references characters that match lorebook entries and asks to "continue", "advance", "next scene"

## Instructions

1. Extract the lorebook name from the user's message.
2. Resolve the file path:
   - `/media/sda/lorebook_<name>.json`
   - `/media/sda/lorebook_<name>_stepdad.json`
   - `/opt/data/lorebook_<name>.json`
3. Read the lorebook with `read_file`.
4. Identify **active context**:
   - Look at the last 10 messages in the current conversation
   - Extract character names, locations, relationship terms, and key nouns
5. Filter lorebook entries:
   - Include entries whose **name** or **content** matches any active context token
   - Also always include `setting` / `tone` / `relationships` if present
   - Exclude entries for characters not mentioned recently
   - If no specific character is mentioned, include only the top 3-4 most important entries (setting, tone, main relationships)
6. Format the injected context as:

   **Active Lorebook Context:**
   - [entry name]: [1-2 sentence summary of relevant facts]
   - ...

7. Then continue with the user's request using only this filtered context.

## Notes

- Do NOT send the full lorebook. Only filtered entries.
- Max 4-6 bullets in the injected context.
- If the lorebook is not found, say: `Lorebook "<name>" not found.`
- If the user asks to update or create a lorebook, say: `Use the lorebook-authoring skill for editing.`