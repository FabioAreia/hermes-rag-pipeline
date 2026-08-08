---
name: lorebook-rag
description: Busca em lorebooks JSONL com filtros anti-falso-positivo.
---

# Lorebook RAG

Busca e recuperação em lorebooks JSONL de roleplay longos.

## Ficheiros padrão

- `<lorebook>.jsonl` — base raw
- `/opt/data/tyronne-lorebook/raw_context.md` — cache opcional
- `/opt/data/tyronne-lorebook/index.json` — índice de tags

## Formato JSONL real

Cada linha é um objeto JSON com campos relevantes:
- `mes`: texto completo da mensagem, **incluindo o header**
- `name`: autor/personagem
- `send_date`: timestamp ISO
- `is_user`: booleano
- `swipes` / `continueSwipe` — alternativas da MESMA mensagem

**Pitfalls:**
- Muitos lorebooks usam `mes`, não `content`. Sempre usa `rec.get("mes", "")`.
- **CANON = 1ª mensagem por header.** Cada cena existe em vários "swipes"
  (reescritas com o mesmo header de data). Para continuity fiável, agrupa por
  header e mantém SÓ a 1ª mensagem de cada um — descarta os swipes. Busca sobre
  o conjunto reduzido, não sobre as linhas cruas.
- Busca por nome sozinho devolve notificações (ex: `"Mia (WhatsApp):"`); combina
  sempre **nome + acto**.
- Nomes repetem-se (várias Sofias/Marias/Martas): desambigua por apelido e círculo.

Ver `references/sillytavern-jsonl-rag-technique.md` para a técnica completa validada.

## Passos

1. **Carregar** com Python: `json.loads(line)` e filtrar registos com `mes`
2. **Normalizar termos** com sinônimos expandidos
3. **Extrair contexto adjacente:** 5-7 linhas antes/depois
4. **Filtrar falsos positivos:**
   - Anal: exigir verbo de acção explícito no bloco (`entra|penetra|meter|abrir|desliza|enterra|empurra|desce`)
   - Primeira vez: exigir `sangue` + `virgem|primeira` + nome no mesmo bloco
5. **Confirmar com evidência directa:** pelo menos 2 linhas adjacentes confirmando o acto
6. **Regra de círculos sociais:** nunca assumir contacto entre personagens de círculos diferentes sem justificação explícita
7. **Extrair header:** formato `**Weekday - YYYY-MM-DD HH:MM – Location**` está no início do `mes`

## Script

Usa `scripts/parser_rag.py` para buscas automatizadas.

## Quando usar

- Perguntas sobre eventos específicos do roleplay
- Verificação de continuity (primeiras vezes, penetrações, datas)
- Busca por personagens, locais, relações
