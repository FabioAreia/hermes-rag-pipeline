# Técnica: RAG fiável sobre export SillyTavern .jsonl

Técnica validada numa sessão real. Elimina os falsos positivos que custaram
várias tentativas até se perceber a estrutura e o conceito de "canon".

## Estrutura real do JSONL SillyTavern

Cada linha (objecto JSON) tem campos úteis:
- `mes` — texto completo da mensagem (narração + diálogo + header de data).
- `name` — autor/personagem.
- `is_user` / `is_system` — bools.
- `send_date` — timestamp ISO.
- `swipes` / `continueSwipe` / `continueSwipeId` — alternativas da MESMA mensagem.

**Armadilha crítica:** a mesma cena existe em vários "swipes" (reescritas) com o
MESMO header de data. Procurar linha-a-linha devolve duplicados, ruído e, pior,
pode ler uma reescrita que contradiz a versão original.

## CANON = 1ª mensagem por header

Para decidir o que "aconteceu mesmo" sem contradição interna:
1. Agrupar mensagens pelo header (1ª linha `**...**` = data/local).
2. Manter SÓ a 1ª mensagem de cada header; descartar todos os swipes.
3. Correr a busca sobre essa lista canónica reduzida.
   (Neste lorebook: 2694 linhas → 829 mensagens únicas. Muito mais limpo.)

Referência de ancoragem (começa logo no `**...**`):
```
header = re.match(r'^\*\*(.+?)\*\*', mes).group(1)
```

## Falsos positivos que apareceram na sessão

- **Busca por NOME sozinho** → devolve sobretudo notificações
  (ex: `"Mia (WhatsApp):"`) em vez da cena real. **Sempre combinar nome + acto**
  (`"Mia virgem"`, `"Sofia Almeida cu"`).
- **`anal/cu`** → apanha "atrás/trás" e "dar chapada no rabo". Exigir VERBO de
  penetração + `cu|rabo|anal` no MESMO bloco.
- **`primeira vez/virgem`** → exigir `virgem|sangue|hímen|era zero` + verbo de
  entrada + nome no mesmo bloco. "Era zero" / "nunca tive" também contam como
  confirmação de virgindade.
- **Nomes repetidos** (ex: duas Sofias, várias Marias/Martas) → desambiguar sempre
  por apelido e círculo social. "Sofia Almeida" (mãe da Rita) ≠ "Sofia Martins"
  (amiga da Lara). NUNCA misturar círculos sociais sem justificação explícita.

## Instrumentação

- USAR `execute_code` para inspeccionar estrutura/tipos/chaves, NÃO terminal
  one-liner python (o gateway envia SIGTERM a processos filho e mata o comando).
  Padrão: `open(path, encoding='utf-8')` + `json.loads` + `collections.Counter`.
- Para contar participantes, regex `\*\*Nome:...:\*\*` sobre o `mes`.
- Ver headers de data: capturar 1ª linha `**...**` e deduplicar.
