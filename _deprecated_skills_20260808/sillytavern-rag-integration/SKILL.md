---
name: sillytavern-rag-integration
description: 'Processar JSONL SillyTavern p/ RAG: swipes, sync, relações.'
---

# SillyTavern ↔ Hermes RAG Integration

Como ligar um SillyTavern (backend = gateway Hermes) a um pipeline de memória
persistente por ficheiros (`archive.jsonl`, lorebooks de personagem, grafo de
relações). Cobre a **mecânica** de processar o export/chat do ST; a *semântica*
(canon-first, pre-flight, círculos sociais) vive na skill `roleplay-rag`.

## Acesso ao chat do ST

- O chat real não está em `default-user` (vazio): user é por ex. `lulzcz`.
- Path: `/home/node/app/data/<user>/chats/<Cenário>/<...>.jsonl`
- Ler via host: `docker exec sillytavern sh -c "cat/tail '<path>'"`.
- Container ST: **BusyBox** (sem `--time-style`) e **sem python3** → parse fora.

## Sincronizar cenas novas (archive_sync)

Padrão da Opção A — script no host, trigger no evento (nota OOC `*Hermes ooc
instruction sync history*`), **sem cron/watcher**:

1. `tail -n +N` (watermark) lê só as linhas novas do JSONL ST.
2. Extrai o canónico de cada nó: `swipes[swipe_id]` se válido, senão `mes`.
3. Dedup por hash do `mes` (idempotente) + filtra notas OOC do user.
4. Append via `docker exec -i hermes cat >> archive.jsonl` (volume não gravável do host).

Detalhes e pitfalls: `references/st-archive-sync.md`.

## Reconstruir/limpar um archive poluído

- O RAG (`consist.py`/`parser_rag.py`) **só lê linhas com `mes`** — formatos
  `text`/`content`/`scene` são ignorados.
- Archive que mistura 3 formatos + duplicados → reconstruir por hash do texto e
  normalizar para `{role, mes, header, ts, chars}`.

## Extrair grafo de relações do canon

Extrator que projeta `relacoes` nos lorebooks de personagem a partir do canon+archive:
- **Presença por PRIMEIRO NOME** (o canon usa o 1º), usando o **apelido só para
  desambiguar** quando dois 1º nomes colidem. NUNCA casar só por apelido compartilhado
  (viés: família toda "Jefferson").
- Tipos ricos: parentesco, romanticos, amizades, trabalho, habitacao, hobby.
- **Regra de consistência:** parentesco direto (mãe/filha/irmã/esposa) **exclui**
  romance — família nunca é amante.
- Tipos de relação detetam-se **na janela à volta do nome** (60 antes / 120 depois),
  não na mensagem inteira (senão dispara tudo).

Detalhes e pitfalls: `references/grupos-relations-extractor.md`.

## Regra circulos sociais

Cada mulher dorme na casa do SEU grupo. Dois grupos podem ter os mesmos 1º nomes
("Filipa/Teresa/Sara/Marta") → identidade por **apelido + casa + profissão**.
Nunca cruzar pessoas entre grupos sem prova no canon.

## Ver também
- `roleplay-rag` (user-owned): semântica canon-first + pre-flight + círculos sociais.
- `remote-host-access`: SSH ao host para docker exec.
