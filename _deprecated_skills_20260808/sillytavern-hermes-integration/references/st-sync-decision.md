# Decisão de sync ST→Hermes — Opção A (2026-08-07)

Documento original: `/opt/data/st_sync_DECISAO.md`

## Contexto

Quando o Hermes arquiva o roleplay do ST, só o **canónico** (`swipe_id`) deve entrar
no archive — nunca os swipes rejeitados. Tensão: o ficheiro de chat do ST vive no host
(sem permissão para o Hermes), mas o backend do ST É o Hermes (gateway), logo o Hermes
está no ponto exato do evento (mensagem/swipe).

## Opção A (escolhida) — sync no host, trigger pelo Hermes

- Script no host junto do ficheiro; leitura incremental (tail); append canónico idempotente.
- Trigger = no fim de cada resposta do ST (o Hermes invoca o sync via SSH).

**Vantagens:** leve (parse junto do dado, não traga 53MB), sem processos a correr
(sem cron/daemon), zero swipes rejeitados (lê só `swipe_id`), robustez de permissões
(via `docker exec sillytavern`), lógica de parsing fora do Hermes.

**Desvantagens:** depende de SSH ao host a cada trigger (já se mostrou
lento/instável — ponto mais frágil); dois sistemas em jogo (host script + Hermes
trigger) precisa idempotência; não é "tempo real absoluto"; mantém watermark no host.

## Alternativa B (rejeitada)

Hermes puxa o ficheiro via `docker exec`. Rejeitada porque: mais round-trips, mais
dados a cruzar, duplica lógica de parsing no Hermes. Custo de SSH igual ou pior.

## Implementação

- Script: `/media/sda/Scripts/archive_sync.py` (no host). Leitura `docker exec
  sillytavern`, append idempotente por SHA-256 do `mes` via `docker exec -i hermes`.
- Archive reconstruído limpo: 19 registos `{role, mes, header, ts, chars}`.
- Teste unitário `extract_canonical`: PASS (swipe multi, sem swipe, vazio).
- **Trigger NÃO ligado** — requer autorização explícita (mexe no runtime de prod).
