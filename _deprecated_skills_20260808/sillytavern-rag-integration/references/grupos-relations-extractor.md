# Extrator de relações/grafo a partir do canon (passos B→A)

Projeta `relacoes` nos lorebooks de personagem automaticamente a partir do canon
(+ archive) de um roleplay. Script: `/opt/data/extractor_grupos.py`.

## Deteção de presença (a parte que decide tudo)

- **Presença por PRIMEIRO NOME** — o canon refere personagens sobretudo pelo 1º nome
  ("Lara", "Stacy", "Mia").
- **Apelido só para DESAMBIGUAR** quando dois 1º nomes colidem na mesma mensagem
  (ex: Filipa Costa vs Filipa Santos; Marta Umbelino vs Marta Silva).
- ⚠️ **NUNCA casar só por apelido compartilhado** — viés grave: a família toda tem o
  mesmo apelido ("Jefferson"), e o match por apelido marca TODOS como presentes em
  cada mensagem, inflando co-ocorrência (ex: Lara→Tyronne 470 falso).
- ⚠️ Tipos de relação detetam-se **na janela à volta do nome** (~60 antes / 120
  depois da ocorrência do 1º nome), NÃO na mensagem inteira — senão o termo de
  qualquer tipo dispara em qualquer relação e marca "tudo como tudo".

## Tipos de relação (taxonomia rica)

`parentesco, romanticos, amizades, trabalho, habitacao, hobby, grupos, conhecidos`
(ex.: "equipa", "habitação" = vive/casa, "hobby" = yoga/salão/faculdade).

## Regra de consistência (validada pelo user)

**Parentesco direto (mãe/filha/irmã/esposa) EXCLUI romance — família nunca é amante.**
- Ex: Lara é mãe da Mia/Stacy → `parentesco`, NUNCA `romanticos` nelas.
- Exceção válida: Suzy mantém-se "romance" porque é amiga/parceira do Tyronne, não
  filha de sangue.

## O que o extractor faz MAGNIFICAMENTE vs fracamente

| Componente | Fiabilidade |
|---|---|
| Estrutura/ligação (quem ↔ quem, força/círculos) | ✅ Alta — é o valor real |
| Separar círculos por apelido | ✅ Alta |
| Parentesco exclui romance | ✅ Alta (regra explícita) |
| Etiqueta fina automática (casal vs amante vs colega) | ⚠️ Média — hub (Tyronne amante de quase todas) engana; precisa revisão |

## Workflow seguro

1. **`--report` primeiro** (mostra, não grava). Validar com o user.
2. Backup da pasta de lorebooks antes de `--apply`.
3. `--apply` = **aditivo** (mescla com `relacoes` existentes, não destrói).
4. Manter `grupos.md` do cenário com grupos + tabela de desambiguação por apelido.

## Ficheiros de apoio

- `grupos.md` (por cenário): círculos + regra + desambiguação.
- `relacoes_grafo.md`: grafo de co-ocorrência gerado.
