---
name: sillytavern-hermes-integration
description: "ST-Hermes data sync: backend gateway, chat JSONL, swipes."
---

# SillyTavern ↔ Hermes Integration

Como o SillyTavern (ST) se liga ao Hermes e como aceder/sincronizar os dados de
roleplay. Cobre: arquitetura do backend, acesso aos ficheiros de chat, formato dos
nós (swipes), e o padrão de archive-sync automático.

## Arquitetura (o que se descobriu — 2026-08-07)

- O backend LLM do ST é o **gateway do Hermes**:
  `hermes-api.fabioareia.duckdns.org/v1` (autentica com `API_SERVER_KEY` do `.env` do
  Hermes). O endpoint DO ST é `sillytavern.fabioareia.duckdns.org` (**eia**, não `ea`).
- **O gateway CORRE o agente Hermes completo — NÃO é pass-through puro de modelo.**
  Como provar:
  1. Um pedido trivial devolve `prompt_tokens` enorme (21k–42k) — só possível se o
     system prompt do agente (skills+ferramentas) for montado a cada chamada.
  2. Um pedido que exige ferramenta devolve o **output real da tool**, não texto do
     modelo (e demora alguns segundos — tempo de execução real).
- Implicação prática: **as skills do Hermes estão ativas no runtime do ST.** Se o ST
  chama o gateway, cada pedido recebe o system prompt do agente com as skills.

## Acesso aos ficheiros de chat ST

- Container: `sillytavern`. Dados em `/home/node/app/data/`.
- **User efetivo é `lulzcz`** (não `default-user` — `default-user/chats` está vazio).
  Chats: `/home/node/app/data/lulzcz/chats/<Cenário>/<chat>.jsonl`.
- O volume `/media/sda/rpi4-server1/docker/volumes/sillytavern_data/_data` dá
  **Permission denied** para `fabio` e para o container Hermes. Ler via
  `docker exec sillytavern cat ...` (corre como dono).
- O container ST é BusyBox (sem python3) — extrai com `head`/`tail`, parseia no lado
  que tem python (host Hermes).
- O volume `/opt/data` do Hermes = `.../volumes/hermes_data/_data`; o host não o grava
  diretamente — escrever via `docker exec hermes`.

## Formato dos nós e swipes

Cada nó de mensagem: `swipes[]` (todas as versões), `swipe_id` (o canónico),
`continueHistory`/`continueSwipe` (aninhados), `mes` (versão ativa), `is_user`.

**Canónico = `swipes[swipe_id]`** (fallback: `mes` se sem swipes; ignorar se `mes` vazio).

## PITFALL crítico — formato do archive que o RAG lê

- Os motores RAG (`parser_rag.py`, `consist.py` da skill roleplay-rag) exigem o campo
  **`mes`** (`if rec.get('mes')`).
- **Linhas em formato `content`/`text`/`scene` são IGNORADAS.**
- Um archive real tinha 3 formatos misturados + uma cena duplicada 3x (o formato que
  o runtime escrevia nem o RAG lia). → Sempre arquivar como `{role, mes, header, ts,
  chars}`, nunca `text`/`content`.

## Padrão de sync (Opção A — escolhida pelo user)

1. `docker exec sillytavern cat/tail` → JSONL com swipes.
2. Extrair canónico por `swipe_id`.
3. Append idempotente por hash SHA-256 do `mes` (rodar 2x nunca duplica).
4. Append via `docker exec -i hermes cat >> archive` (host não grava o volume).
5. Leitura incremental: com offset usar `tail -n +N` no container (não tragar 53MB);
   watermark = nº de linhas via `wc -l`.

**Decisão de trigger:** SEM cron. Trigger no evento = cada pedido do ST ao Hermes
(mensagem/swipe) — o Hermes, sendo o backend, está no ponto do evento. Requer ligar o
sync no fim de cada resposta, o que mexe no runtime de produção → pedir autorização
explícita antes.

## Detalhe por sessão

- Decisão + vantagens/desvantagens: `references/st-sync-decision.md` (também em
  `/opt/data/st_sync_DECISAO.md`).
- Extrator de relações + desambiguação por apelido + router de cenários (passo A+B)
  e OOCs: `references/relations-extractor-scenario-router.md`.
- Diagnóstico do sampling/temperature (swipes idênticos): `references/temperature-sampling-bypass.md`.

## PITFALL — swipes do ST voltam a MESMA resposta (sampling ignorado)

Sintoma: no ST, fazer swipe devolve sempre o mesmo texto; `finish_reason: stop`
(normal) mas a geração não varia. **Não é o RAG nem o canon — é o caminho do sampling.**

Factos verificados no código do Hermes (`gateway/platforms/api_server.py`):
1. `_handle_chat_completions` **NÃO lê** `temperature`/`top_p`/`seed` do body do
   request do ST — ignora-os.
2. `model_options` (campo Hermes-nativo) só processa `reasoning` e `service_tier`,
   **não `temperature`/`sampling`**.
3. O gerador usa a própria temperatura; modelos de *reasoning* (ex: deepseek-v4-flash)
   decodificam quase deterministicamente.
4. Não existe chave de config `model.temperature` / `agent.temperature` (o `hermes
   config set model.temperature` não existe).

**Conclusão:** os sliders de sampling do ST (temperature/seed) **não têm efeito** na
geração atual — o Hermes não os encaminha. Fixes (`temp 1.1`, `seed -1`) não chegam.

**Vias (por risco):** 1) trocar para modelo de *chat* puro (não-reasoning) — varia
melhor; 2) aceitar e variar por prompt ("escreve diferente"); 3) escrever suporte no
gateway (consumir `model_options.sampling.temperature` → provider) — invasivo, requer
rebuild/restart do container; só com justificação forte.

