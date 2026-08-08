# ST→Hermes RAG sync — end-to-end topology & decision log

## Decision: Option A (chosen)

Two options existed for syncing ST history into the RAG:
- **A (chosen):** sync script runs on HOST next to the ST file; Hermes triggers it on
  the event (ST message/swipe). No cron, no watcher, no runtime change to the ST
  backend. Cleanest for "user wants zero lingering processes".
- **B (rejected):** Hermes pulls the ST file per request via `docker exec` and parses
  locally. More round-trips, more data crossing, duplicates parsing on the Hermes side.

**Why A:** the ST file lives on the host; Hermes has no permission to it directly.
A keeps parsing next to the data (only the result crosses, not multi-MB chat logs).

**Downside of A (documented):** depends on SSH to the host, which is slow/unstable and
uses out-of-band Telegram approval — one long timeout, never aggressive retries.

## Exact paths

- ST chat (source of truth): inside ST container
  `/home/node/app/data/lulzcz/chats/<conversation>/<chat>.jsonl`
  (e.g. `.../Stacy & Suzy as stepdad/Resumo 2 - Branch #1.jsonl`, ~53MB, hundreds of
  nodes with `swipe_id`/`swipes[]`/`continueHistory`).
- Write the volume directly? **No** — host gets `Permission denied`. Use
  `docker exec sillytavern`.
- Hermes RAG targets (inside `/opt/data`): canon, `archive.jsonl`, `grupos.md`,
  `live_state.md`, `lorebook_personagens/`. Host can't write them → `docker exec hermes`.

## Trigger (user fires, no cron)

ST note: **`*Hermes ooc instruction sync history*`** (or ask here in the chat).
Runs `archive_sync.py` then the extractor. The OOC note is filtered out (never saved
to the archive) via a regex in `parse()` that drops user nodes matching
`\*?hermes ooc instruction` (case-insensitive).

## Sync (`archive_sync.py`, on host)

1. `docker exec sillytavern` read ST JSONL; with a watermark offset use `tail -n +N`
   so only new lines are read (never the multi-MB file).
2. Extract canonical only — `swipe_id` points at the chosen swipe; discarded swipes
   never enter the archive. No swipe → use `mes`.
3. Append idempotently (SHA256 hash of `mes` dedups — running twice never duplicates)
   via `docker exec hermes` (host can't write /opt/data).
4. Watermark `/tmp/archive_sync.watermark` = last processed line count.
5. Step 6: run `extractor_grupos.py --apply` via `docker exec hermes` to refresh the
   relation graph. Failure doesn't block sync (secondary).
6. Env overrides: `CANON`, `ARCHIVE_RAG`, `LORE_DIR`, `EXTRACTOR`, `RAG_MIN_CO`.

## Extractor (`extractor_grupos.py`, Hermes container)

- `--report` dry-run; `--apply` writes `relacoes` into `lorebook_personagens/*.json`.
- Reads `--canon` + `--archive` (both, so recent scene additions are captured without
  regenerating the canon).
- Identity resolved by **surname** (first-name co-occurrence inflates — the whole
  "Jefferson" family collapses to one blob; first-name detection + surname collision
  resolution in the message window).
- Rich types: parentesco, romanticos, amizades, trabalho, habitacao, hobby, grupos,
  conhecidos.
- **Hard rule (user correction):** parentesco diretto (mãe/filha/irmã/esposa) EXCLUDES
  romance — family is never "amante". Example: Lara (mãe) with Mia/Stacy = parentesco,
  not romance. Valid exception: Suzy stays "romance" (friend/partner of Tyronne, not
  blood daughter).
- Backup `lorebook_personagens/` before `--apply`.

## Router (`rag_router.py` + `cenarios.json`)

- `--ooc <id>` user explicit → OVERRIDES automatic.
- automatic: ST chat with most recent mtime matched against `cenarios.json` `st_chat`.
- Resolves paths to the scenario's isolated folder, then calls sync/extract.
- Prefer JSON over YAML — `pyyaml` not installed on the Hermes container.

## Per-scenario isolation (target model)

`state/scenarios/<id>/` owns `canon/`, `archive.jsonl`, `grupos.md`, `live_state.md`,
`lorebooks/` (only that chat's characters), `relacoes_grafo.md`. Nothing global.

## Pitfalls hit this session

- SSH to host: out-of-band Telegram approval; slow/unstable — one long timeout, no
  aggressive retries; a quick timeout isn't necessarily a script failure.
- ST container has no python3 — parse on Hermes side.
- `pyyaml` absent — use JSON for router config.
- Volume `Permission denied` for `/media/sda/...sillytavern_*` — always `docker exec`.
- `python3 -c "import..."` inline can be killed by the gateway (false-positive
  restart scanner) — write a standalone script file and run it.
