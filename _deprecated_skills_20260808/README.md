# Skills arquivadas — 2026-08-08

## Protótipos abandonados de lorebook RAG (nunca usados desde 2026-08-07 08:25)
Superados pelo roleplay-rag (nasceu 2026-08-06 23:42, sistema em uso real desde então
— 18 usos, o mais recente em 2026-08-08).

- lorebook-rag — busca genérica em JSONL, superada pela técnica em roleplay-rag/consist.py
- tyronne-lorebook-rag — sem SKILL.md, só um archive.jsonl de teste órfão (1 linha, migração)
- lorebook-loader-rag / lorebook-loader — dois protótipos quase idênticos com paths antigos
  (/opt/data/lorebook_<nome>.json), incompatíveis com a arquitetura atual
  (lorebooks/ isolada por cenário)
- tyronne-rag-lorebook — protótipo append-only (raw_context.md + index.json), primeira
  tentativa (05 Ago), substituída
- narrative-relation-extraction — skill curator-managed, script próprio
  (scripts/extractor_relacoes.py) nunca usado (use_count=0); a técnica documentada
  (desambiguação por apelido, janela de deteção, parentesco-exclui-romance) já vive,
  a funcionar de facto, em extractor_grupos.py (skill sillytavern-rag-sync)

## Consolidadas em sillytavern-rag-sync (2026-08-08)
Descreviam a mesma arquitetura ST↔Hermes com sobreposição real de conteúdo — fundidas
numa só para não pagar a mesma explicação 3x. Nada foi perdido: o conteúdo único de
cada uma (prova de que o gateway corre o agente completo por pedido, formato de
swipes, bug de sampling/temperature, reconstrução de archive poluído) está agora em
sillytavern-rag-sync.

- sillytavern-rag-integration
- sillytavern-hermes-integration

## Ainda ativas (não tocadas)
roleplay-rag (semântica), sillytavern-rag-sync (mecânica/infra, consolidada acima),
lorebook-authoring (bootstrapping de personagens novas — corrigida 2026-08-08 para
escrever no esquema/local atual em vez do antigo /opt/data/lorebook_<nome>.json).
