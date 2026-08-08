# Arquivo automático de roleplay ST → Hermes (Opção A)

**Data:** 2026-08-07
**Decisão:** Opção A — script de sync no host, trigger no evento (mensagem/swipe do ST), **sem cron**.

---

## Problema

O SillyTavern gera swipes (versões alternativas de um nó). Ao arquivar a história no
`archive.jsonl` para o RAG do Hermes, só o **canónico** (`swipe_id`) deve entrar — nunca
os swipes rejeitados.

Tensão: o ficheiro de chat real do ST está no **host** (sem permissão para o Hermes),
mas o backend LLM do ST **é o Hermes** (gateway). O Hermes está no ponto exato do
evento (mensagem/swipe), mas não lê o ficheiro diretamente.

---

## Opção ESCOLHIDA: A — sync no host, trigger pelo Hermes

- **Script de sync vive no host**, junto do ficheiro do ST.
- **Trigger:** o Hermes invoca o script via SSH **no fim de cada resposta** a uma
  mensagem/swipe do ST (é aí que o canónico fica fixado). Sem cron, sem watcher,
  sem processo a correr — só no evento.
- **Leitura incremental** (tail com offset) — não traga os 53MB todos, só os nós novos.
- **Saída:** append canónico para `/opt/data/.../archive.jsonl` (que o RAG lê).

---

## Vantagens (A)

1. **Leve e rápido** — o parsing fica junto do dado (host); não cruzam 53MB por SSH,
   só o resultado (bytes por trigger).
2. **Sem processos a correr** — não há cron meu nem daemon; o Hermes invoca no momento
   do evento, que é exatamente "quando faço swipe/mensagem".
3. **Zero swipes rejeitados** — o script lê `swipe_id`; os que foram rejeitados nunca
   entram no registo (por construção, não por limpeza tardia).
4. **Robustez de permissões** — via `docker exec sillytavern` (como dono legítimo),
   contornando o `Permission denied` do volume.
5. **Architecture limpa** — o Hermes não ganha lógica de parsing; só invoca e recebe
   o resultado.

---

## Desvantagens (A)

1. **Depende de SSH ao host** — a cada trigger há um round-trip; o SSH já se mostrou
   lento/instável por vezes, e pode exigir aprovação. É o ponto mais frágil.
2. **Dois sistemas em jogo** — o script no host + o trigger no Hermes; se um falhar,
   o archive fica desatualizado até o outro repor. Precisa de idempotência (offset).
3. **Não é "tempo real absoluto"** — é "no evento", mas entre o swipe e o append há o
   tempo do SSH + parse. Negligenciável em uso normal, mas não é instantâneo literal.
4. **Mantém estado no host** (offset/último ponto sincronizado) — precisa de um ficheiro
   de marca d'água para saber onde retomar.

---

## Alternativa rejeitada — B (Hermes puxa o ficheiro via docker exec)

- Hermes faz `docker exec` para obter o tail e parsear cá dentro.
- **Porquê rejeitada:** mais round-trips, mais dados a cruzar, e duplica a lógica de
  parsing no Hermes quando ela está melhor junto do dado. Custo igual ou pior de SSH,
  com mais overhad. A só vence em simplicidade e peso.

---

## Notas técnicas (para quem for retomar)

- **Ficheiro ativo (fonte de verdade):**
  `/home/node/app/data/lulzcz/chats/Stacy & Suzy as stepdad/Resumo 2 - Branch #1.jsonl`
  (2822 nós, ~53MB, escrito a cada alteração). Aceder via `docker exec sillytavern`.
- **Estrutura do nó:** `swipes[]`, `swipe_id` (canónico), `continueHistory`/
  `continueSwipe` aninhados. O `clean_swipes.py` da skill `roleplay-rag` já sabe
  extrair o canónico.
- **Local de escrita do append:**
  `/opt/data/skills/research/roleplay-rag/state/scenarios/stacy-suzy-stepdad/archive.jsonl`
- **ID do cenário:** `stacy-suzy-stepdad`
- **Trigger no Hermes:** no fim de cada resposta do ST (mensagem/swipe) invocar o sync
  via `ssh fabio@172.17.0.1 "<script>"`.
- **Endpoint do ST (backend):** gateway Hermes `hermes-api.fabioareia.duckdns.org/v1`.

## Estado

- [x] Documentar decisão
- [x] Criar script de sync no host (`/media/sda/Scripts/archive_sync.py`)
- [ ] Ligar trigger no Hermes
- [x] Testar com dados reais

## Notas de implementação (2026-08-07)

- **Script:** `/media/sda/Scripts/archive_sync.py` no host. Lê o JSONL do ST via
  `docker exec sillytavern`, extrai canónico (`swipe_id`), faz append idempotente
  por hash via `docker exec hermes` (o volume /opt/data não é gravável pelo host).
- **Leitura incremental:** com offset usa `tail -n +N` no container — só as linhas
  novas, não os 53MB todos. Watermark em `/tmp/archive_sync.watermark`.
- **Archive reconstruído limpo** (19→20 registos, {role,mes,header,ts,chars}) — o original
  misturava 3 formatos (um ignorado pelo RAG) e uma cena estava duplicada 3x.
- **Teste unitário:** extract_canonical PASS em 3 casos (swipe multi, sem swipe, vazio);
  filtro OOC PASS (ignora `*Hermes ooc instruction ...*`, mantém o resto).
- **TESTADO EM PRODUÇÃO:** apanhou a cena nova 17:02 (que crescera no ST) e appendou
  sem duplicar — end-to-end validado com dados reais.

## TRIGGER (definido) — variante B (hook manual via nota no ST)

- Usuário escreve no ST: **`*Hermes ooc instruction sync history*`**
- O ST envia ao backend (gateway Hermes). O Hermes reconhece a instrução,
  corre `ssh fabio@172.17.0.1 /media/sda/Scripts/archive_sync.py`, e responde
  com o nº de cenas sincronizadas.
- A nota OOC NUNCA entra no archive (filtro no parse).
- **Vantagem:** sem cron, sem watcher, sem alteração ao runtime — só no comando.
- **Limitação (documentada):** não é automático a cada swipe; só sincroniza quando
  a nota é enviada. Evolução futura = Opção A (runtime trigger).

## Busca RAG proativa (2026-08-07) — CONSISTÊNCIA > VELOCIDADE; TOKENS > TUDO

- **Skill `roleplay-rag` atualizada** com secção "Busca RAG PROATIVA por termos":
  em cada resposta do ST, o Hermes extrai os termos-chave da mensagem (personagens,
  cargos, relações, locais, actos) e corre `consist.py` contra o canon — mesmo para
  personagens FORA da cena (ex: "directora de RH" → Andreia).
- **Prioridades do user (gravadas na skill):** 1) poupar tokens → injeta só o trecho
  relevante (1-3 linhas/facto); 2) consistência → nunca inventar, ir ao disco;
  3) velocidade → aceitar a latência da leitura.
- **Teste real:** "quem é a directora de RH da esposa e quando fodeu?" → respondido
  com consist.py: **Andreia** (RH), desflorada por Tyronne a **14/02/2026 08:14**,
  quarto da Joana, com Joana presente. Tudo do disco, zero invenção.
- **Nota de system prompt do personagem** pronta em `/opt/data/st_personagem_nota.md`.

## EXTRACTOR DE RELAÇÕES (passo A+B, genérico) — 2026-08-07

- **`/opt/data/extractor_grupos.py`** (no container Hermes): lê o canon + lorebooks,
  resolve identidade por **apelido** (não cruza círculos), projeta **relações ricas**
  (parentesco, românticos, amizades, trabalho, habitação, hobby, grupos, conhecidos),
  e atualiza os `relacoes` dos lorebooks (`--apply`).
- **Regra de consistência:** parentesco direto (mãe/filha/irmã/esposa) **EXCLUI**
  romance — família nunca é amante. Ex: Lara mãe da Mia/Stacy → parentesco, não romance.
- **Integrado no `archive_sync.py`:** após cada sync, corre o extractor via
  `docker exec hermes` (passo 6) para manter o grafo vivo. Não bloqueia se falhar.
- **Ficheiros:** `grupos.md` (círculos + regra + desambiguação) e `relacoes_grafo.md`
  (grafo) no cenário. Backup de lorebooks em `/opt/data/_backup_lorebooks_20260807/`.



