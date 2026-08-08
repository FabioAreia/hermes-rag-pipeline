---
name: lorebook-authoring
description: "Build SillyTavern lorebooks from chat JSONL exports."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [sillytavern, lorebook, jsonl, chat-export, character-extraction, nsfw]
---

# Lorebook Authoring

Extract structured character/relationship data from large SillyTavern JSONL chat exports and produce complete lorebooks.

## When to Use

Trigger when the user:
- Wants a lorebook from a SillyTavern/JanitorAI chat export
- Has a `.jsonl` chat log and needs character extraction
- Asks for "detalhes de cada personagem" or "histórico sexual"
- Says "podes ler" + a JSONL file path
- Mentions incomplete reads: "so encontraste essas personagens?", "há muito mais", "leste o inicio?"

## Core Principle

**Read everything before summarizing.** For files with thousands of lines, use programmatic extraction. Never summarize from a partial read.

## Workflow

### System Overview

The old approach was reactive: read fragments, infer, correct, repeat. The correct approach is a **5-pass pipeline** that treats the JSONL as structured data, not prose:

1. **Parse** — fast frequency scan for candidate names
2. **Disambiguate** — resolve ambiguous first names to canonical identities
3. **Deep-extract** — full-text analysis per character
4. **Expand** — BFS/DFS through discovered relations to find hidden characters
5. **Timeline** — extract timestamped events per character

### Step 1: Validate file stats

```python
import json
path = "/path/to/chat.jsonl"
count = 0
models = set()
with open(path) as f:
    for line in f:
        try:
            entry = json.loads(line)
            count += 1
            if entry.get("extra", {}).get("model"):
                models.add(entry["extra"]["model"])
        except: continue
print(f"Lines: {count}, Models: {len(models)}")
```

### Step 2: Extract all assistant narrative text

Only assistant messages contain narrative. User prompts are actions/OOC.

```python
assistant_texts = []
with open(path) as f:
    for line in f:
        entry = json.loads(line)
        if not entry.get("is_user") and len(entry.get("mes", "")) > 100:
            assistant_texts.append(entry["mes"])
full_text = " ".join(assistant_texts)
```

### Step 2: Discover all characters via frequency scan

Capitalized words are the cheapest signal. Filter out common words, keep proper nouns.

```python
import re
from collections import Counter
words = re.findall(r'\b[A-Z][a-záéíóúãõâêîôûç]{2,}\b', full_text)
freq = Counter(words)
exclude = {"Ele", "Ela", "Os", "As", "Uma", "Um", "Mas", "Quando", "Depois",
           "Ainda", "Então", "Agora", "Isso", "Este", "Esta", "Seu", "Sua",
           "Como", "Sobre", "Entre", "Pelo", "Pela", "Com", "Sem", "Para",
           "Porque", "Assim", "Porém", "Todos", "Todas", "Nunca", "Sempre",
           "Nada", "Algo", "Aqui", "Ali", "Onde", "Antes", "Depois"}
names = {w for w, c in freq.items() if c > 5 and w not in exclude}
```

**Output:** candidate name set. This includes first names, full names, nicknames, and potential duplicates.

### Step 2.5: Disambiguate first-name-only characters

For each candidate that has **only a first name** (no surname visible in the text), run a context window scan to identify distinguishing attributes:

- Role/job: "professora de yoga", "massagista", "enfermeira"
- Family role: "mãe da Rita", "filha de X"
- Location: "casa da Sofia", "Rua das Flores", "salão"
- Explicit relationship: "a Sofia... é a mãe", "a irmã dela, a Maria"

Create canonical identities:

```
"Sofia" → Sofia Silva (42, mãe de Rita, yoga) + Sofia Martins (dona de salão, irmã de Maria)
"Filipa" → Filipa Costa (24, enfermeira, loira) + Filipa Santos (23, massagista, morena)
```

**Rule:** Never assign attributes or relations to a first name until you know which person it refers to. If two characters share a first name, keep them separate and add distinguishing fields.

### Step 2.6: Validate extraction with confirmed baseline

Pure regex extraction from narrative prose is **not safe for attributes**. A single passage describing multiple characters will contaminate results — e.g. a paragraph about "Filipa Costa (loira)" next to "Filipa Santos (morena)" can cause the regex to assign the wrong hair color to the wrong character.

**Fix:** After Step 4, cross-check extracted attributes against a confirmed manual baseline. If the baseline says "Filipa Costa = loira" but extraction says "castanho", the extraction is wrong — discard it and keep the confirmed value.

**Rule:** For high-frequency characters with confirmed data, use manual baseline + regex for NEW characters only. Never trust regex output for appearance when the passage mentions multiple people.

### Step 3: Expand via discovered relations (BFS)

When a relation is found (e.g. "a Sofia tem uma funcionária Filipa"), check if the target is already in the candidate set. If not, **add it** to the scan list.

This prevents holes like missing Filipa Santos because she appears primarily as "a funcionária do salão" rather than in dialogue.

Implementation:

```python
to_scan = set(initial_names)
discovered = set()
queue = list(to_scan)

while queue:
    name = queue.pop(0)
    # full-text scan for this character
    # extract relations
    for relation_target in extracted_relations:
        if relation_target not in to_scan:
            to_scan.add(relation_target)
            queue.append(relation_target)
            discovered.add(relation_target)
```

### Step 4: Deep-extract per character

For each canonical character, filter the full JSONL for all mentions and extract:

**Appearance (direct text only):**
- Eye color: regex `olhos?\s+(azuis|verdes|castanhos|pretos)`
- Hair: `cabelo\s+(loiro|ruivo|castanho|preto|escuro|comprido|curto|encaracolado)`
- Skin: `pele\s+(clara|morena|escura|sardenta|branca)`
- Body: `seios?\s+(grandes|pequenos|médios|firmes)`, `corpo\s+([^,.]{3,40})`

**Personality (multiple consistent passages):**
- Collect dialogue snippets and action descriptions
- Only assign traits that appear 3+ times with consistent meaning
- Flag single-line inferences as "possível" not "confirmado"

**Relations:**
- Parentesco: explicit kinship terms only
- Românticos: explicit declarations, not proximity
- Amizades: explicit statements + consistent co-occurrence
- Grupos: explicit enumeration (e.g. "as três mosqueteiras: X, Y, Z")

**Sexual history (explicit text only, validated by subject AND object grep):**
- Virgindade: explicit "sou virgem", "nunca tive homem"
- First time: date, location, act types, bleeding, orgasm
- Partners: full list with timestamps if available
- **Validate by searching BOTH directions:** `\bNome\b ... (fode|foder|penetrada)` AND `(fode|foder|penetra) ... \bNome\b`
- Distinguish between act types: touching, oral sex, penetration
- Never assume acts happened without explicit description

**Timeline events:**
- Parse `🕰️ <timestamp> | 📍 <location>` headers
- Store per-character: `[{"timestamp": "...", "location": "...", "event": "..."}]`

### Step 5: Build the lorebook JSON

Structure:
```json
{
  "lorebook_version": "X.Y",
  "source": "<path>",
  "source_stats": { "total_linhas", "tamanho_ficheiro", "modelos_usados" },
  "setting": { "data_principal", "localizacoes" },
  "personagens": { "<Nome>": { "role", "idade", "aparencia", "personalidade", "historial_sexual", "relacoes", "detalhes", "segredos" } },
  "relacoes_globais": {},
  "dinamicas": { "power", "linguagem": { "tratamento", "termos" }, "rituais": [] },
  "cenas_chave": [],
  "rede_de_personagens": { "nucleo", "enteadas", "total_mulheres", "total_virgens" },
  "writing_style": { "modelo_original", "idioma", "calao" },
  "prefill_subtle": { "description", "content": [{"role","content"}] }
}
```

### Step 5b: Export per-character files for the live pipeline (obrigatório — 2026-08-08)

O ficheiro monolítico do Step 5 é útil como registo de trabalho, mas **não é o que
o pipeline atual lê**. `roleplay-rag` + `extractor_grupos.py` (skill `sillytavern-rag-sync`)
esperam **um ficheiro JSON por personagem**, na pasta ISOLADA do cenário — nunca
numa pasta partilhada entre cenários (bug real, corrigido em 2026-08-08: escrever
no sítio errado mistura os círculos sociais de cenários diferentes).

Path: `state/scenarios/<scenario_id>/lorebooks/<slug>.json` (dentro de
`/opt/data/skills/research/roleplay-rag/`, ex.:
`/opt/data/skills/research/roleplay-rag/state/scenarios/stacy-suzy-stepdad/lorebooks/stacy_jefferson.json`).
`<scenario_id>` e `<slug>` seguem o mesmo slug de `rag_router.py._slug()` (minúsculas,
sem acentos, espaços→hífen). Se o cenário ainda não está registado em `cenarios.json`,
regista-o primeiro com `rag_router.py --register "<nome do chat no ST>"`.

Um ficheiro por personagem, campos no nível de topo (confirmado no schema real em
produção):
```json
{
  "nome": "Nome Completo",
  "versao": "1.0",
  "fonte": "<path do JSONL de origem>",
  "role": "<papel/relação principal em 1 linha>",
  "idade": 20,
  "aparencia": { "cabelo": "...", "olhos": "...", "pele": "..." },
  "personalidade": ["traço1", "traço2"]
}
```
**Não incluir `relacoes` aqui** — esse campo é gerido inteiramente por
`extractor_grupos.py --apply` (lido do canon/archive por co-ocorrência); se
inicializares o ficheiro, ou omite o campo ou deixa-o `{}`. Escrever um valor aqui
só seria pisado na primeira run do extractor.

Depois de criar os ficheiros base, corre o extractor para popular as relações:
```bash
python3 /opt/data/rag_router.py --ooc <scenario_id> --extract
```

### Step 6: Verify completeness

Cross-check: every character found in Step 3 must appear in Step 5. If the frequency scan found "Mia" 1850x but the lorebook has no "Mia" entry, it's incomplete.

### Step 7: Export for SillyTavern

SillyTavern lorebooks use `q`/`a` entry pairs. Convert each character's structured data into query/answer entries and write:

- `/opt/data/sillytavern/<chatname>/lorebooks/<slug>.json` — per-character lorebook entries
- `/opt/data/sillytavern/<chatname>/character_cards/<slug>.json` — character card in `chara_card_v2` format
- `/opt/data/sillytavern/<chatname>/lorebook_master_st.json` — combined master with all entries

Entry generation pattern:

```json
{
  "q": "Quem é <Nome>?",
  "a": "<Nome> é <role>."
}
```

For fields with no data, omit the entry rather than inventing content.

### Step 8: Manual spot-checks

Before finalizing, verify at least 3 characters against the raw JSONL:
- One high-frequency character (Tyronne, Lara, Stacy)
- One ambiguous first-name character (Sofia, Filipa, Maria)
- One low-frequency character (Leonor, Patrícia)

If any spot-check fails, re-run extraction for all characters before delivering.

## Pitfalls

1. **Partial reads create incomplete lorebooks.** A 51MB JSONL with 2694 lines will have characters introduced after line 379. Always scan the full text.
2. **`execute_code` may return empty output for large files.** When it returns empty/truncated results, switch to `terminal` with `python3 << 'PYEOF'` heredoc. This is the reliable pattern for 50MB+ JSONL files.
3. **Don't confuse dialogue frequency with importance.** "Sofia" appeared 2200x in one scan because the model generated dialogue for her even when she wasn't physically present. Verify each name's actual narrative role via context windows.
4. **Common first names are ambiguous.** Two characters can share a first name while being completely different people. Always disambiguate by full name, surname, role, location, or explicit relationship (e.g. "Sofia Silva" ≠ "Sofia Martins"). Never conflate characters just because their first names match.
5. **Named groups must be verified by enumeration, not assumed.** The term "Mosqueteiras" was applied to Stacy/Suzy/Mia/Rita, but the text explicitly enumerates the group as "a minha mãe, a Sofia e a Maria". Trust explicit enumeration over poetic nickname reuse.
6. **End-state matters as much as initial state.** A character's living situation, relationships, or role may change by the final entries. Always inspect the last 20-50 entries of the JSONL to capture ending states. In this session, Tyronne ended up living in Marta Umbelino's house in Braga with 5-6 women — this supersedes earlier living arrangements.
7. **Contact names in WhatsApp/messaging can be unreliable.** A contact labeled "Filipa Massagista" may sign messages as "Filipa Costa" due to author continuity errors. Trust explicit character names and roles from narrative text over contact labels.
6. **UTF-8 and PT-PT diacritics matter.** Use `encoding="utf-8"` and include `áéíóúãõâêîôûç` in regex.
7. **Large files need filtering.** Filter `len(mes) > 100` to drop system prompts.
8. **Permission issues on mounts.** When `/media/sda/` is read-only, save to `/opt/data/` and inform the user. Don't repeatedly fail on the same path.
9. **Verify character states with targeted extraction, not assumptions.** Virgindade, compromisso, e actos sexuais consumados devem ser confirmados por grep/regex directo ao texto completo. Não inferir sem verificar todas as menções.
10. **Check both subject and object positions for sexual acts.** `\bNome\b ... (fode|foder|penetrada)` apanha acts where the character is the object. `(fode|foder|penetra) ... \bNome\b` apanha acts where the character is the subject. Ambos são necessários.
11. **Extract explicit dialogue for relationship status.** Use regex `\*\*Nome\*\*:\s*"([^"]+)"` para apanhar falas directas sobre compromisso, virgindade, ou actos. Isto captura "Mia é minha noiva", "ainda sou virgem", etc.
12. **Verify commitment/fachada relationships explicitly.** Muitas personagens usam fachada lésbica/casamento falso como disfarce. Procurar termos como "noiva", "minha noiva", "minha namorada", "casamento fachada", "fachada" near cada personagem.
13. **Answer specific character questions only after full-file verification.** If the user asks "já fodeu?" or "é comprometida?", run a targeted full-file grep for that character + sexual/relationship keywords before answering. Never answer from memory of a partial read.
14. **Physical descriptions require targeted extraction.** Eye color, hair color, body type are often scattered across the text. Run a regex scan per character for `(cabelo|olhos|pele|corpo|alta|baixa|loira|morena|ruiva|magra|gorda|sardas|peito|seios)` near the character name.
15. **Inference policy: appearance = direct text only.** Physical traits (hair color, eye color, skin tone, body type) must be explicitly stated in the JSONL. Do not infer appearance from context or assume traits shared by other characters. If the text does not describe it, leave the field empty or mark as "não descrito".
16. **Inference policy: personality = multiple consistent passages only.** Personality can be inferred from dialogue and actions, but only when there is strong, consistent evidence across multiple passages. Do not assign personality labels based on a single line or weak implication.
16. **Inference policy: relationships = explicit confirmation only.** Familial ties, romantic status, friendships, and group membership must be confirmed by explicit text. Do not assume relationships based on proximity, shared location, or narrative convenience.
17. **End-state matters more than initial state.** Always inspect the last 20-50 entries of the JSONL to capture ending states. Living arrangements, relationships, and roles can change by the final entries. In this session, Tyronne ended up in Marta Umbelino's house in Braga with 5 women — this supersedes earlier living arrangements.
18. **Same first name ≠ same character.** Two characters can share a first name while being completely different people (Marta Umbelino vs Marta loira; Joana enfermeira vs Joana amiga; Sofia Silva vs Sofia Martins). Always disambiguate by surname, role, location, appearance, or explicit relationship markers like "a outra Marta". Never conflate characters just because their first names match.
19. **WhatsApp contact names can be wrong.** A contact labeled "Filipa Massagista" may sign messages as "Filipa Costa" due to author continuity errors. Trust explicit character names and roles from narrative text over contact labels or sender IDs.
20. **OOC notes are not narrative facts.** User OOC instructions (e.g. "esta filipa nao e a filipa massagista") are meta-commentary, not story content. Do not store OOC corrections as character attributes. Use them only as disambiguation hints during extraction.

## Output Rules

- **Primário (o que o pipeline lê):** um ficheiro por personagem em
  `state/scenarios/<scenario_id>/lorebooks/<slug>.json` — ver Step 5b. Isolado por
  cenário, nunca numa pasta partilhada.
- **Secundário (registo de trabalho, não lido por nada em produção):** o ficheiro
  monolítico do Step 5 em `/opt/data/lorebook_<nome>.json` — mantém-se útil como
  dump de auditoria/debug, mas não confundir com o output primário.
- Inform the user it's there; don't silently fail on unwritable paths
- Include `source_stats` so the user knows the file was fully processed
- Include `rede_de_personagens` summary for quick orientation
- Use `ensure_ascii=False` when writing JSON to preserve PT-PT characters
- Export SillyTavern-format lorebooks (`q`/`a` entries, Step 7) **só se o user pedir
  explicitamente** para importar no próprio ST — não é lido pelo pipeline Hermes.

## Style & Interaction Rules

- Reply in PT-PT, blunt and direct. Don't over-explain, don't hedge, don't write long walkthroughs unless asked.
- When the user corrects you, act immediately — don't re-explain the old wrong answer.
- When the user asks a specific factual question about a character, do a full-file verification first, then answer concisely.
- Don't silently fail on unwritable paths. Tell the user where you saved and why.
