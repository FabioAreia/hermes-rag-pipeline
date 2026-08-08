# Extrator de relações + desambiguação + router de cenários (passo A+B)

Novos componentes construídos 2026-08-07 para manter a consistência de alianças,
amizades, parentesco, trabalho, habitação, hobby — agnóstico por cenário.

## Extrator de relações — `extractor_grupos.py` (no container Hermes, /opt/data)

- Lê `--canon` + `--archive` (incremental) + `--lore <dir>`, projeta relações.
- Modos: `--report` (não grava) / `--apply` (atualiza `relacoes` dos lorebooks).
- Tipos ricos: `parentesco`, `romanticos`, `amizades`, `trabalho`, `habitacao`,
  `hobby`, `grupos`, `conhecidos`.
- **Deteção de presença por PRIMEIRO NOME**, e apelido só para resolver colisões
  (2 pessoas com o mesmo 1º nome na mesma mensagem) — evita o viés do apelido
  compartilhado (ex: toda a família "Jefferson" a inflar co-ocorrência).
- Tipos detetados por TERMO na JANELA à volta do nome (não na mensagem toda):
  "irmã perto do nome" = parentesco; "trabalha com" = trabalho; etc.

## Regra de consistência (validada com o user)

- **Parentesco direto (mãe/filha/irmã/esposa) EXCLUI romance.** Família nunca é
  amante. Ex: Lara é mãe da Mia/Stacy → parentesco, NÃO romance.
- Contraste válido: Suzy mantém "romance" porque é amiga/parceira do Tyronne, não
  filha de sangue.
- Backup dos lorebooks antes de aplicar: `/opt/data/_backup_lorebooks_<data>/`.

## Desambiguação por apelido (crítico)

- **Identidade = nome completo + apelido + casa + profissão.** 1º nome não basta.
- Vários círculos têm os mesmos 1ºs nomes (ex: "Filipa, Teresa, Sara, Marta" aparece
  em grupos diferentes). Nunca cruzar sem prova no canon.
- Ex: "Marta do financeiro" (casa da Andreia, Rua das Flores) ≠ "Marta Umbelino"
  (condutora de Uber, Grupo C).
- Tabela de desambiguação por cenário em `state/scenarios/<id>/grupos.md`.

## Router de cenários — `rag_router.py` + `cenarios.json`

- Cada conversa do ST = um cenário isolado (pasta `state/scenarios/<id>/` com
  canon/archive/lorebooks/grupos/live_state).
- `cenarios.json` mapeia `st_chat` (nome no ST) → paths do cenário. Lido como JSON
  (sem depender de pyyaml; `.yaml` é fallback manual).
- **Deteção do cenário ativo (automático):** lista os chats do ST por mtime
  (`ls -t /home/node/app/data/lulzcz/chats/` via SSH ao host → `docker exec
  sillytavern`), casa o mais recente com `cenarios.json`.
- **OOC subscreve o automático:** `--ooc <id>` força o cenário.
- **Auto-registo com confirmação (opção B escolhida):** chats do ST sem cenário são
  auto-detetados e listados com o slug sugerido (`_slug()` normaliza nome → id);
  só se cria a pasta + entrada com `--register "<nome>"` (confirmado).
- Slugs gerados automaticamente do nome do chat (ex: "Stacy & Suzy as stepdad" →
  `stacy-suzy-as-stepdad`) — o user não decora ids; usa o nome da conversa.

## OOCs válidas (iguais em qualquer card)

- `*Hermes ooc instruction sync history*` → sync + extractor do cenário ativo.
- `*Hermes ooc instruction sync history scenario <nome>*` → força um cenário.
- `*Hermes ooc register scenario <nome>*` → regista conversa nova como cenário.

## System Prompt agnóstico para o ST

- Colar `st_personagem_nota_agnostico.md` no System Prompt de qualquer card: instrui
  o Hermes a detetar o cenário ativo, ler live_state/archive/lorebooks/grupos,
  resolver por apelido, não cruzar círculos, parentesco exclui romance, e responder
  às OOCs `sync history` / `register scenario`. Sem paths hardcoded.
