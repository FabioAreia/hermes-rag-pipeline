---
name: tyronne-rag-lorebook
description: Store and retrieve Tyronne roleplay lore with simple RAG.
---

# Tyronne Jefferson RAG Lorebook

## Setup
- Base path: `/opt/data/tyronne-lorebook/`
- Raw file: `/opt/data/tyronne-lorebook/raw_context.md`
- Index file: `/opt/data/tyronne-lorebook/index.json`
- Append-only. No rewrites.

## Storage Protocol
When storing new context:
1. Append to `raw_context.md`:
```markdown
---
### CONTEXT_BLOCK_<ISO_TIMESTAMP>
**Source:** user message
**Date:** <date if provided>
**Chars:** <length>
<exact content>
```
2. Update `index.json` with:
   - block_id, timestamp, char_count
   - tags: `#<FirstName>_<LastName>`, `#date:<YYYY-MM-DD>`, `#loc:<Location>`, `#event:<keyword>`
   - summary (1 sentence)

## Retrieval Protocol (RAG)
1. Load `index.json`
2. Match user query terms against tags + summary
3. Read matching blocks from `raw_context.md`
4. Inject relevant excerpts into model prompt with block_id and date
5. Print: Stored N blocks, Retrieved M blocks, sources used

## Persistence
- Store verbatim — no summarization.
- If raw_context.md > 50KB, split into `raw_context_001.md`, `raw_context_002.md`, etc.
- Always update index on every append or split.

## Verification
After any store/retrieve, print:
- Stored: N blocks, total chars
- Retrieved: M blocks, N chars injected
- Sources: list of block_ids used