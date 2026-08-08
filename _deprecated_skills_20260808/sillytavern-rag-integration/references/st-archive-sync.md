# Sync SillyTavern → Archive RAG (Opção A)

Pipeline que apanha as cenas novas do SillyTavern e as arquiva no `archive.jsonl`
do RAG, mantendo só o canónico (swipe_id) e nunca duplicando.

## Arquitetura real (confirmado)

- **Script no HOST:** `/media/sda/Scripts/archive_sync.py`
  (volume ST + docker socket vivem no host; o container Hermes não tem permissão).
- **Fonte de verdade (chat ativo do ST):** ler via `docker exec sillytavern`:
  ```
  docker exec sillytavern sh -c "tail -n +N '<chat>.jsonl'"
  ```
  Chat vive em `/home/node/app/data/<user>/chats/<Cenário>/<...>.jsonl`.
- **User real não é `default-user`** (essa pasta está vazia) — por ex. `lulzcz`.
- Container ST usa **BusyBox** (sem `--time-style`) e **não tem python3** — o parse
  faz-se no host/quem chama, não dentro do container.
- **Destino (archive):** vivo dentro do container Hermes
  (`/opt/data/.../archive.jsonl`). O host não tem permissão no volume hermes_data →
  escrever via:
  ```
  docker exec -i hermes sh -c "cat >> '<archive>'"
  ```

## Extração do canónico (swipe_id)

Cada nó ST tem `mes` (canónico ativo), `swipes[]` e `swipe_id`. Regra:
- Se `swipes` não vazio e `swipe_id` válido → canónico = `swipes[swipe_id]`.
- Senão → canónico = `mes`.
- Ignorar linhas sem `mes` (metadata/scene/beats são invisíveis ao RAG).

## Idempotência + incremental

- **Watermark** (`/tmp/archive_sync.watermark` no host): nº de linhas já processadas.
  Usa `tail -n +N` para ler só o que falta — NÃO ler os 53MB todos a cada trigger.
- **Dedup por hash** do `mes`: rodar 2x nunca duplica.
- **Filtro OOC:** mensagens do user que casam `hermes ooc instruction` NUNCA entram
  no archive (a nota de sync não polui a história).

## Pitfalls reais (custaram iterações)

1. **Nunca despejar o histórico todo do ST no archive** na 1ª execução — offset 0
   manda milhares de nós. Inicializar a watermark no fim do ficheiro antes de ligar
   em produção; o histórico completo já vive no canon (`.cleaned`), o archive é o
   registo vivo/recente.
2. `consist.py`/`parser_rag.py` **só lêem linhas com campo `mes`**
   (`if rec.get('mes')`). Formatos alternativos (`text`, `content`, `scene`) são
   ignorados — o que o runtime grava hoje pode nem ser visto pelo RAG.
3. Archive a misturar 3 formatos + duplicados → reconstruir: dedup por hash do texto
   + converter content/text→mes, normalizando para `{role, mes, header, ts, chars}`.
4. Docker/BusyBox: usar `wc -l`, `tail -n +N`, `cat` — sem flags GNU.
5. O trigger é manual no ST (`*Hermes ooc instruction sync history*`) → sem cron,
   sem watcher, sem processo de fundo (preferência do user).
