---
name: sillytavern-rag-sync
description: Sync SillyTavern chats into Hermes RAG (sync/extract/route). Also covers ST-Hermes backend architecture and access mechanics — merged 2026-08-08 from sillytavern-rag-integration and sillytavern-hermes-integration (archived, see /opt/data/_deprecated_skills_20260808/).
---

# SillyTavern ↔ Hermes RAG Sync

Infrastructure that keeps a SillyTavern roleplay's history and character-relation
graph live inside the Hermes RAG, working for ANY chat/scenario (agnostic — not
tied to one persona). The *content-side* rules (canon-first, pre-flight, groups,
identity resolution by surname, parentesco-exclui-romance) live in the user-owned
`roleplay-rag` skill; THIS skill owns the plumbing: architecture, sync, extraction,
scenario routing.

## Architecture (one line each)

- **ST backend = Hermes gateway.** SillyTavern's endpoint is
  `sillytavern.fabioareia.duckdns.org`; its LLM backend is
  `hermes-api.fabioareia.duckdns.org/v1` (authenticates with `API_SERVER_KEY`).
- **The gateway runs the FULL Hermes agent per request — not a pass-through.**
  Proof (verified 2026-08-07): a trivial ST request still shows `prompt_tokens`
  in the 21k-42k range in `agent.log` (`agent.conversation_loop: API call #N:
  ... in=NNNNN`) — only possible if the whole agent system prompt (skills+tools)
  is assembled every call. A request needing a tool shows the tool's real output
  and takes real execution time (seconds), not just model latency. **Implication:**
  Hermes skills are live at ST runtime — every ST message gets the full agent,
  not a stripped-down persona-only completion.
- **Effective ST user is `lulzcz`** (not `default-user` — that one's chats dir is
  empty). Chats: `/home/node/app/data/lulzcz/chats/<Cenário>/<chat>.jsonl` inside
  the `sillytavern` container. A chat folder can hold multiple `.jsonl` branches
  (ST "checkout branch" feature) — always use the most-recently-modified one
  (`ls -t '<chat_dir>'*.jsonl | head -1`), never assume a fixed filename.
- **Source of truth (ST chat):** the volume gives `Permission denied` to the host
  user and to the Hermes container directly — always go through
  `docker exec sillytavern`, never `ls`/`cat` the volume path directly.
- **RAG files (Hermes):** canon (`.cleaned.jsonl`, the truth), `archive.jsonl`
  (living log, grows), `grupos.md`, `live_state.md`, `lorebooks/` — all **inside
  the scenario's own isolated folder** (see "Per-scenario isolation" below, this
  is no longer a target model, it's how the scripts actually work as of
  2026-08-08). These live in `/opt/data` inside the Hermes container — the host
  cannot write them, so writes happen via `docker exec hermes` or directly from
  the container.
- **`hermes` container has no `docker.sock` mounted.** `docker exec` from inside
  it always fails with "Cannot connect to the Docker daemon". Anything that needs
  to reach the `sillytavern` container or run the host copy of `archive_sync.py`
  must SSH out to the host first (`fabio@172.17.0.1`, the docker bridge gateway)
  and run it from there — `rag_router.py`'s `--sync` does exactly this.

## Trigger: manual, no cron

The user fires sync by a ST note `*Hermes ooc instruction sync history*` (or asking
here). NOT a background watcher — the user explicitly wants zero lingering processes.
Cadence ~10 replies is fine; sync only batch-updates the graph, never corrupts.

## Scripts

### `/media/sda/Scripts/sillytavern/archive_sync.py` (runs on the HOST)
1. Resolves the active scenario from `cenarios.json` — `--ooc <id>` forces it,
   otherwise auto-detects by the most-recently-written ST chat. Never falls back
   to a hardcoded/shared scenario or lorebook folder (fixed 2026-08-08 — it used
   to default to one hardcoded scenario and to the shared `lorebook_personagens/`
   folder, silently mixing characters across scenarios).
2. Resolves `ST_FILE` as the most-recently-modified `.jsonl` inside the chat's
   folder (handles ST branches), `CANON`/`ARCHIVE`/`LORE_DIR` from that scenario's
   `cenarios.json` entry.
3. Reads ST chat JSONL via `docker exec sillytavern` (with offset, `tail -n +N` —
   only new lines, never the whole multi-MB file).
4. Extracts **only the canonical message (`swipe_id`)** — discarded swipes never enter.
5. Appends idempotently (SHA-256 hash of `mes`, running twice never duplicates) to
   the archive via `docker exec hermes` (host can't write /opt/data directly).
   Idempotency check uses a **local hash-cache sidecar**
   (`/tmp/archive_sync.<scenario_id>.watermark.hashes`, rebuilt from the remote
   archive only if missing) instead of re-reading+re-hashing the whole remote
   archive every run — added 2026-08-08, matters once `archive.jsonl` gets big.
6. Watermark at `/tmp/archive_sync.<scenario_id>.watermark` (namespaced per
   scenario since 2026-08-08 — was a single global path before, which would have
   collided across scenarios) tracks the ST-side line offset.
7. After a successful append, runs the extractor via `docker exec hermes` to keep
   the graph alive, with `--lore` pointed at THIS scenario's isolated folder.
   Extractor failure doesn't block the sync (secondary maintenance).
- Manual override by env var if you ever need it: `ST_FILE`, `ARCHIVE`, `CANON`,
  `LORE_DIR`, `RAG_MIN_CO`, `WATERMARK` (all optional — normally resolved from
  `cenarios.json` via `--ooc`).
- `--full` reprocesses the whole ST file ignoring the watermark (first run/rebuild).
- `--rebuild-cache` forces the hash-cache to rebuild from the remote archive.

### `/opt/data/extractor_grupos.py` (runs in the Hermes container)
Reads canon (`--canon`) + archive (`--archive`), resolves identity by **surname**
(never first name alone), projects pairs with rich type (parentesco/romanticos/
amizades/trabalho/habitação/hobby/grupos/conhecidos).
- `--lore` is **required** (fixed 2026-08-08 — used to default silently to the
  shared `/opt/data/lorebook_personagens/`, mixing scenarios). Always the
  scenario's own isolated `lorebooks/` folder.
- `--canon` is now optional if `--archive` is given and exists (fixed 2026-08-08 —
  used to hard-require `--canon` to exist, which made it impossible to run a brand
  new scenario that has no cleaned export yet; a fresh scenario runs fine off
  `archive.jsonl` alone).
- `--report` shows without writing; `--apply` writes the `relacoes` into the lorebooks.
- `--min N` = co-occurrence threshold (default 20).
- **KEY RULE:** parentesco direto (mãe/filha/irmã/esposa) EXCLUDES romance — family
  is never "amante". This was a user correction; encode it as a hard constraint.
- Edge: co-occurrence by first name inflates (whole family shares "Jefferson");
  detect by first name but resolve collisions by surname in the message window.
- **When no surname is visible to break a first-name collision, the extractor now
  logs it (`[AVISO] N deteções ambíguas...`, stderr) instead of silently guessing**
  (fixed 2026-08-08). Real example from this scenario: "Sofia" collided 569x
  between Sofia Silva/Sofia Martins, always defaulted to Sofia Silva — check these
  warnings after `--apply`, the guessed relations may be misattributed.
- Always back up the scenario's `lorebooks/` folder before `--apply` (copy dir to
  a dated backup).
- **`historial_sexual` (added 2026-08-09)**: no mesmo passe, deteta atos sexuais
  confirmados (`anal`/`vaginal`/`oral`) por janela dupla (gatilho + verbo de ação
  no mesmo bloco de 60/120 chars — nunca por proximidade solta) e escreve
  `parceiros` + `actos_confirmados` (append, dedup por tipo+parceiro+data, nunca
  reescreve o que já lá estava). Antes disto o campo era só escrito uma vez à mão
  (`lorebook-authoring`) e nunca mais atualizado — ficava congelado enquanto
  `relacoes` já se atualizava sozinho a cada sync.
  - **`virgindade` NUNCA é escrita por `--apply`** — testado: até um "hub" claramente
    não-virgem (ex. o padrasto/protagonista masculino) dispara o gatilho quando OUTRA
    personagem perde a virgindade na mesma cena perto do nome dele. Fica só como
    sugestão no `--report` ("candidato a primeira vez"), confirmação manual sempre.
  - Nem o sujeito nem o parceiro de um ato podem vir de um fallback ambíguo (1º nome
    sem apelido) — testado: sem este filtro, a colisão Sofia/Marta contaminava
    `historial_sexual` com parceiros de círculos sociais errados.

### `/opt/data/rag_router.py` + `/opt/data/cenarios.json`
Routes WHICH scenario to work on:
- `--ooc <id>` — user explicit, OVERRIDES automatic.
- automatic — the ST chat most recently written (mtime) matched against `cenarios.json`.
- `--sync` SSHs to the host and runs `archive_sync.py --ooc <sid>` there (fixed
  2026-08-08 — used to try `docker exec` a nonexistent/dead in-container copy at
  `/opt/data/archive_sync.py`, which could never work since this container has no
  `docker.sock`; that dead copy is archived at
  `/opt/data/_archive_sync.py.dead-in-container.bak`).
- `--extract` calls `extractor_grupos.py` directly (this container CAN run Python
  scripts locally, it just can't `docker exec` — extraction is pure file I/O).

**Scenario registration (new-chat auto-detect, confirm-then-create):**
- On a run with no `--ooc`, the router lists ST chats not registered in `cenarios.json`
  as **candidatos novos**, each with its **auto-generated slug** (`_slug()`: lowercase,
  accents stripped, spaces → hyphens, e.g. "Tyronne And Emily" → `tyronne-and-emily`).
- The user confirms creation with:
  `rag_router.py --register "<nome do chat no ST>"` (or `--register` = first candidate),
  or OOC in ST: `*Hermes ooc register scenario <nome>*`.
  `registar_cenario()` then creates the isolated folder + adds the `cenarios.json` entry.
  Its `canon` entry now points to a **file** path (`canon/<slug>.cleaned.jsonl`,
  which doesn't need to exist yet) rather than the `canon/` directory (fixed
  2026-08-08 — pointing it at the directory made the extractor crash with
  `IsADirectoryError` the first time it tried to read it).
- User is never required to know or type an id — the **conversation name in the ST IS
  the identifier**; the slug is derived automatically.
- To populate a brand-new scenario's character files (the extractor only *enriches*
  existing `lorebooks/*.json`, it never invents characters), use `lorebook-authoring`'s
  Step 5b to bootstrap one JSON per character in the right isolated folder.

**How the user switches/continues scenarios (ask at session start if they wonder):**
- **Continue a past conversation:** open it in the ST — the router detects it as most
  recently written and follows automatically. No action needed; `--ooc` only for ambiguity.
- **Start a new conversation:** create the char in ST, write, then confirm register once
  (OOC `register scenario <nome>` or ask here). After that it's automatic like the others.
- **Per-cadence:** `*Hermes ooc instruction sync history*` alone is enough — Hermes
  detects the active conversation; append `scenario <nome>` only to force a non-active one.

## Per-scenario isolation (verified working, 2026-08-08)

Each conversation = `state/scenarios/<id>/` (under
`/opt/data/skills/research/roleplay-rag/`) with its OWN `canon/`, `archive.jsonl`,
`grupos.md`, `live_state.md`, `lorebooks/` (only that chat's characters),
`relacoes_grafo.md`. Nothing shared globally. Register in `cenarios.json`.

This used to be documented as a "target model" but the scripts didn't actually
implement it — `archive_sync.py` and `extractor_grupos.py` both defaulted to the
shared `/opt/data/lorebook_personagens/` folder regardless of scenario, silently
pooling characters from every story together. Fixed and end-to-end verified
2026-08-08 (real `--ooc stacy-suzy-stepdad` run: synced correctly, extractor wrote
only to that scenario's isolated `lorebooks/`, the shared folder was untouched).

## Pitfalls

- **SSH to host is slow/unstable** and uses out-of-band Telegram approval. Use one
  long timeout, not aggressive retries; don't treat a quick timeout as script failure.
- **ST container has no python3** — parse/extract JSONL on the Hermes side, not via
  `docker exec sillytavern python3`.
- **`pyyaml` not installed** on the Hermes container — prefer `cenarios.json` over
  `.yaml` for the router.
- **Volume `Permission denied`** for `/media/sda/...docker/volumes/sillytavern_*` —
  always via `docker exec sillytavern`.
- **Validate the graph before trusting auto-etiquetage** — e.g. confirm a mother is NOT
  listed as "romance" with her daughter. Auto-type on a dense multi-Hub canon is
  heuristic, not proof.
- **Prefer standalone script files over `python3 -c "import..."`** — the gateway may
  kill inline exec (false-positive scanner on restart); write a file and run it.
- **A polluted/mixed-format archive breaks silently.** The RAG only reads lines with
  a `mes` field — `text`/`content`/`scene` formatted lines are ignored, not errored.
  If an archive mixes 3 formats + duplicated scenes (can happen if something wrote
  the wrong shape once), reconstruct it: dedupe by hash of the text, normalize every
  line to `{role, mes, header, ts, chars}`.

## Swipes returning the same message — VERIFIED (2026-08)

When "swipes" (regenerate) keep returning identical text, the cause is almost always
SAMPLING determinism, not the RAG. Verified in source:
`/opt/hermes/gateway/platforms/api_server.py` `_runtime_options_from_model_options`
reads ONLY `reasoning` and `service_tier` from the request body — it **ignores
`temperature` / `seed` / `top_p`** that SillyTavern sends in a `/v1/chat/completions`
body. So ST sliders have no effect on the Hermes generation path.

Diagnosis: same output token-for-token + Finish=stop + constant input-token count
per swipe = deterministic sampling at the Hermes/agent layer, not a gateway override
bug and not the RAG.

Fix at the **Hermes/gateway** level, not the ST sliders. `_fixed_temperature_for_model`
in `agent/auxiliary_client.py` returns `None` for deepseek-v4-flash (no per-model
override there), so the determinism comes from the agent's own default sampling —
raise temperature via Hermes config (`hermes config set ...`) for variation.
Checked before blaming the pipeline; the ST sliders were fine.

## Reference

- `references/sillytavern-sync.md` — end-to-end topology, exact paths, decision log
  (option A vs B: sync on host + trigger on event vs Hermes pulling per request).
