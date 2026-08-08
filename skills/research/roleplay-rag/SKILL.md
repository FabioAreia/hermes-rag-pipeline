---
name: roleplay-rag
description: Roleplay por conteúdo com RAG. Consulta lorebook JSONL (canon) antes de responder — routing por conteúdo, archive vivo, live_state e pre-flight — para nunca inventar/contradizer acontecimentos, relações, actos ou personagens, em QUALQUER persona ou cenário. Use quando fizeres roleplay / ficção erótica / narrativa com canon persistente (Tyronne, Peter Thomson, ou outro), independentemente da persona declarada.
---

# Roleplay RAG — Consistência Proactiva (genérico)

## Objetivo

Mantém o roleplay **100% consistente com o passado**. Antes de descrever qualquer
personagem, relação, acto sexual, evento ou local, consulta o **canon** (lorebook JSONL)
do cenário ativo e usa SÓ o que está provado. **Nunca inventar** factos novos que
contradigam ou extrapolem o estabelecido sem autorização do user.

**Esta skill é genérica** — serve TODAS as personas e cenários (Tyronne, Peter Thomson,
outros). O cenário é decidido pelo conteúdo, nunca pela persona do system prompt.

## Ficheiros (POR CENÁRIO)

Cada story/roleplay distinto é um **cenário** com a sua pasta isolada em
`state/scenarios/<scenario_id>/`. Há um único conjunto de scripts partilhados mas cada
cenário guarda os SEUS dados. Nunca misturar ficheiros entre cenários.

| Ficheiro | Papel |
|---|---|
| `state/scenarios/INDEX.md` | Registo de todos os cenários + canon de referência de cada um |
| `state/scenarios/<id>/canon/` | **Canon do cenário (JSONL)** — cópia limpa em /opt/data, escrita direta do container, SEM SSH |
| `scripts/consist.py` | Motor RAG: busca canon do cenário, ignora swipes, filtra falsos positivos |
| `state/scenarios/<id>/facts/` | Factos canónicos consolidados (por personagem / evento) |
| `state/scenarios/<id>/live_state.md` | **Estado vivo**: histórico contínuo da cena, atualizar a cada resposta |
| `state/scenarios/<id>/archive.jsonl` | **Arquivo vivo de TODA a conversa** (JSONL, sem alterações). Grava cada troca user+cena. Consulta no pre-flight |

## ROUTING POR CONTEÚDO (obrigatório no início de cada resposta)

**NÃO** decidas o cenário pela persona do system prompt nem por "chat que escrevi".
Decide **pelo conteúdo da mensagem** recebida:

1. Olha o texto do user e o que ele **referencia** (personagens, locais, datas, actos).
2. Compara com o histórico:
   - **Bate claramente** com trocas passadas de um cenário já registado (mesmas
     personagens, mesmo lugar, mesmo ato, mesmo estado) → trabalhas **nesse** cenário.
   - **É um first_message / arranque novo** (nova persona, novo setup, nova personagem
     principal, "começa uma nova história") **e não bate em nada** anterior → **nova conversa**.
   - **Contexto ambíguo / personagem reutilizada** → rastreia os ficheiros dos candidatos
     e usa o que fechar a continuidade (nunca por conveniência).
3. Personagens **geradas on demand** (ex.: Marta Uber, colegas de casa) **NÃO criam
   cenário novo por si** — pertencem à conversa corrente onde foram criadas, a menos
   que entrem num arco com canon e estrutura próprios claramente separados.
4. Confirma a escolha no `state/scenarios/INDEX.md`; se não existir, cria o cenário.
   Se existir, **continua esse** — mesmo que o sistema/persona aparente ser outro, o
   conteúdo é quem manda.

## Regra de ouro: CANON FIRST

Quando uma personagem entra na cena, ou um acto/relação/evento é mencionado:

1. **CORRE o motor** (não improvises de memória) contra o canon DO cenário ativo:
   ```bash
   python3 scripts/consist.py "<canon do cenário>" "NomePersonagem" "acto"
   ```
2. Lê os trechos devolvidos e extrai o que está **estabelecido**.
3. Injeta só esse contexto relevante no prompt do modelo ANTES de escrever a cena.
4. Regista o resultado confirmado em `state/scenarios/<id>/facts/` se ainda não lá estiver.

## PRE-FLIGHT: Deteção proativa de contexto (obrigatório)

Antes de CADA resposta de cena, faz em silêncio (nunca mostres ao user) a varredura
— **"quem está na sala, o que preciso de saber"**:

1. **Varre o texto do user e da cena ativa** e enumera TODAS as personagens presentes
   (não só a principal — TODAS, mesmo as que só assistem).
2. Para **cada** personagem listada, recolhe mentalmente: idade, papel/relação, status
   sexual (virgem / desvirginada / data), grupo social a que pertence, últimos eventos
   conhecidos, marcas físicas persistentes (mordidas, nódoas, roupa, cheiro).
3. Se tiveres **qualquer dúvida** sobre uma personagem → CORRE consist.py para essa
   personagem **antes** de escrever. Não assumes.
4. Confirma que **não cruzas círculos sociais** sem justificação no texto.
5. Só depois de teres o quadro completo é que escreves a cena, com esse contexto ativo.

**Porquê:** o user apanhou erros (presenças erradas, inventar acontecimento fora do
canon). Este passo existe para nunca escrever uma personagem sem saber quem ela é.

**NUNCA declarar "esta personagem não existe no cenário" com base só numa busca
vazia.** Incidente real (2026-08-08→09): pedido OOC sobre a Mia — 3 tentativas de
`search_files` voltaram vazias/sem resultado (18 chars cada), e a resposta concluiu
"não há nenhuma Mia no cenário ativo". Falso: a Mia está no `grupos.md`, GRUPO 1,
linha 1 do ficheiro. `search_files` pode falhar ou não indexar bem sem avisar — não
é prova de ausência.

**Antes de dizer que uma personagem não existe:**
1. `read_file` diretamente ao `grupos.md` do cenário (ficheiro pequeno, ~3-4KB,
   custa pouco) — varre à mão a lista, não confies só numa busca por keyword.
2. Se não estiver no `grupos.md`, `read_file` a `lorebooks/` (glob pelos ficheiros,
   ou grep pelo nome nos `.json`) antes de concluir.
3. Só depois de ler os dois diretamente (não só pesquisar) é que podes dizer ao user
   "não encontro esta personagem no cenário — é de outro cenário ou preciso do nome
   completo?". Uma busca vazia não é o mesmo que ter lido o ficheiro.

## ESTADO VIVO: histórico contínuo (obrigatório atualizar a cada cena)

O `state/scenarios/<scenario_id>/live_state.md` (do cenário ativo) é o **histórico
contínuo** da narrativa. Serve de contexto ao pre-flight — não precisas de re-parsear
o canon inteiro se o estado vivo já tiver o que precisas.

**Quando atualizar (depois de CADA resposta de cena):**
1. Re-escreve a secção **CENA ATUAL**: header mais recente, círculo ativo, quem está
   presente, onde a cena parou (estado físico/emocional exato).
2. Acrescenta o bloco ao rolo **ÚLTIMOS 10 BLOCOS DE CENA** (cima = mais recente;
   mantém ~10, descarta os mais antigos).
3. Atualiza **LINHA DO TEMPO** com qualquer novo evento datado confirmado.
4. Atualiza **ESTADO SEXUAL** e **MARCAS PERSISTENTES** se algo mudou.
5. Regista factos novos confirmados em `state/scenarios/<id>/facts/` se ainda não lá estiverem.

**Quando consultar (pre-flight):** antes de cada nova cena lê o `live_state.md` do
cenário ativo primeiro (mais rápido e contextual que o canon inteiro). Se o estado
vivo não tiver um detalhe (data exata, citação literal) → aí sim cai no canon
(`consist.py`). Estado vivo é contexto; canon é verdade.

**Regra:** nunca deixar o estado vivo desatualizado — se respondeste uma cena e ele não
reflete o novo header/presenças/estado, atualiza antes de terminar a resposta.

## ARQUIVO VIVO: registo completo da conversa (obrigatório a cada troca)

O `state/scenarios/<scenario_id>/archive.jsonl` guarda **TODA a conversa de roleplay,
na íntegra e sem alterações** — cada mensagem do user E cada cena que o modelo escreve,
DO CENÁRIO ATIVO. Serve de histórico completo ao pre-flight.

**Formato de cada linha (JSONL):**
```json
{"role": "user|assistant", "mes": "<texto completo, intacto>",
 "ts": "AAAA-MM-DD HH:MM", "header": "<header da cena, se houver>",
 "chars": ["<personagens presentes>"]}
```

**Quando gravar — depois de CADA resposta de cena, sem exceção:**
1. Grava a mensagem do user (tal como veio, sem alterar uma palavra).
2. Grava a cena que o modelo escreveu (na íntegra).
3. Usa o script, SEMPRE com `-s <scenario_id>` para escrever na pasta certa:
   ```bash
   python3 scripts/archive.py -s <scenario_id> "USER" "mensagem do user" "header" "Personagem1,Personagem2"
   python3 scripts/archive.py -s <scenario_id> "ASSISTANT" "cena completa" "header" "Personagem1,Personagem2"
   ```

**Quando consultar (pre-flight):** antes de uma nova cena, se precisares de rever os
últimos blocos, lê as últimas ~10-20 linhas do `archive.jsonl` (tail) do cenário ativo.
O arquivo é a **fonte cronológica completa**; o `live_state.md` é o resumo do momento;
o `consist.py`+canon é a verdade para factos antigos/duvidosos.

**Regra de integridade:** nunca editar/reescrever linhas passadas do arquivo. Só append.
É o teu registo fiel — qualquer alteração quebraria a história.

## TIMELINE (archive.jsonl) vs FICHEIROS ORGANIZADOS — quem manda quando há contradição
(corrigido 2026-08-08, incidente real: ver abaixo)

O `archive.jsonl` é uma **timeline honesta**, não uma fonte de verdade infalível.
Cada linha regista o que era canónico **no momento em que foi sincronizada** — texto
puro, sem metadados de swipe misturados (mantém-se limpo para greps/`consist.py`).
Mas o user pode re-swipar/regenerar uma mensagem DEPOIS de já ter sido sincronizada —
o archive, sendo só-acrescenta e baseado em offset, nunca volta atrás para verificar.
Fica uma "fotografia" de um momento que já não existe, e passa a contradizer os
ficheiros organizados (`lorebooks/*.json`, `live_state.md`, `grupos.md`).

**Ordem de confiança quando há conflito:**
1. `lorebooks/<slug>.json` (`relacoes`) e `live_state.md` — **mandam sempre**. São
   ficheiros curados, corrigíveis, e é para isso que existem.
2. `canon/*.cleaned.jsonl` — verdade histórica consolidada.
3. `archive.jsonl` — timeline crua, só usar para reconstituir cronologia/detalhe,
   **nunca** para decidir um facto de identidade/relação que contradiga o nº 1.

**Incidente real:** uma mensagem WhatsApp rotulou um contacto como "noiva da Mia"
usando um nome (Catarina) que já era prima da Filipa Costa no canon — e nem sequer
era a swipe final escolhida (o user regenerou depois). `mia.json` continuava correto
(`Rita` = noiva). O erro só aconteceu porque o modelo confiou no "eco" da conversa
recente em vez de verificar `relacoes` antes de escrever o rótulo (ver regra
"VERIFICAR RÓTULOS DE RELAÇÃO" mais abaixo).

**Correções sem violar o append-only:** `scripts/audit_stale_archive.py --ooc <id>
--apply-corrections` compara o archive contra o estado atual das swipes do ST e
acrescenta marcadores a `correcoes.jsonl` (mesma pasta do cenário) para linhas que já
não batem com nada canónico — nunca edita/apaga `archive.jsonl`. Se encontrares uma
linha do archive referenciada em `correcoes.jsonl`, trata-a como não-confiável.

## Registar uma nova conversa (quando o routing deteta um arranque novo)

Cria um cenário novo **só** quando o routing justificar (first_message novo / contexto
que não bate em nada). NUNCA criar por veres um nome/persona novo que já faz parte de
uma conversa corrente.

**IMPORTANTE (corrigido 2026-08-08):** o registo tem de passar SEMPRE por
`rag_router.py --register`, nunca só por escrever `state/scenarios/INDEX.md` à mão.
`INDEX.md` é só um índice humano — quem os scripts de sync/extract realmente leem é
`/opt/data/cenarios.json`. Um cenário criado só no INDEX.md fica invisível para
`archive_sync.py`/`extractor_grupos.py`: nunca sincroniza, nunca aparece na deteção
automática. Já aconteceu (duas mecânicas de registo paralelas e desencontradas) — a
partir de agora há um único caminho:

1. `python3 /opt/data/rag_router.py --register "<nome exato do chat no ST>"` (ou, se
   ambíguo, `--register` sozinho para o candidato mais recente). Isto cria a estrutura
   toda de uma vez — `archive.jsonl`, `canon/` (vazio, aponta para um ficheiro que
   ainda não existe até haver export limpo), `lorebooks/` (vazio), `grupos.md`,
   `live_state.md` — e adiciona a entrada em `cenarios.json`, que é o que importa.
2. Depois disso, acrescenta também uma linha em `state/scenarios/INDEX.md` (id,
   descrição, canon) — só para leitura humana rápida, não é o que os scripts usam.
3. A partir daí, todas as leituras/escritas usam **só** essa pasta — e o
   `rag_router.py` deteta automaticamente qual está ativo pelo chat do ST mais
   recentemente escrito, sem precisares de dizer `--ooc` outra vez.
4. Um cenário novo nasce **sem canon** (normal — canon é o export limpo, só existe se
   um dia quiseres consolidar). Até lá o RAG funciona só a partir do `archive.jsonl`
   que vai crescer sync a sync. Ver `lorebook-authoring` (skill) para bootstrapping
   dos ficheiros de personagem quando quiseres consistência mais forte desde cedo.

**Nota:** o canon de cada cenário pode apontar para um ficheiro JSONL diferente, mas
pre-flight/archive/live_state funcionam exatamente igual.

## Regra de armazenamento: UMA PASTA POR TIPO DE ROLEPLAY, SEM SSH

- **Cada tipo/cenário de roleplay** (Tyronne, Peter Thomson, outro) tem a **sua própria
  pasta isolada** em `state/scenarios/<scenario_id>/` — nunca misturar ficheiros entre
  cenários. Canon, facts, archive e live_state de um cenário vivem todos nessa pasta.
- **Tudo em /opt/data.** O canon de cada cenário é a cópia **limpa** (sem swipes) — ex.:
  `state/scenarios/stacy-suzy-stepdad/canon/Stacy Suzy as Stepdad.cleaned.jsonl`. O
  container escreve/ler diretamente em /opt/data, **sem SSH, sem tocar no host**.
- **Nunca apontar canon para /media/sda** — é o host, não escrevível pelo container.
  Se um canon estiver lá, copia para /opt/data antes de usar o pipeline.
- O raw de backup (com swipes) pode existir em /media/sda no host, mas **nunca** é o
  canon ativo — o pipeline lê sempre a cópia limpa em /opt/data.

## Deteção de linhas necessárias (o que puxar do canon)

Nem tudo no canon é relevante para a cena do momento. Puxa **só** o que o modelo precisa:

- **Linhas sobre a personagem ativa** → identidade, status sexual, último estado.
- **Linhas sobre o ato em curso** → a última vez que este ato/pessoa apareceu, para
  manter continuidade (ex.: "a viagem de Uber da Marta — pagou ela?").
- **Linhas da cena atual** → os últimos ~5-10 blocos, para apanhar o estado físico e
  emocional exato.
- **NÃO puxar** lore de outras personagens/círculos que não estão na cena.

Se o modelo precisar de um trecho exato (citação literal, data, detalhe de um ato),
extrai-o do canon e cola-o no prompt na primeira pessoa, em vez de o reescreveres de
memória — garantia de zero invenção.

## Dispara automaticamente quando:
- Um **nome de personagem** entra na cena (novo ou que não lembras bem)
- Um **acto** é referido (anal, primeira vez, chupar, etc.)
- Uma **relação** é mencionada (noiva, irmã, patroa, ex-mulher)
- Um **evento passado** entra em jogo (o jantar, o Uber, o salão, a clínica)

## Termos de busca (sinónimos PT-PT)

- `anal/cu` → exige VERA de penetração (`entra|meter|penetr|abrir|deslizou`) + `cu|rabo|anal` no MESMO bloco. Falso +: `atrás|trás|"dar chapada no rabo"`.
- `primeira vez/virgem` → exige `virgem|sangue|hímen|era zero` + verbo de entrada + nome.
- `pau` → `caralho|pau|picha|pica|verga|pênis|tronco`
- `cona` → `cona|coninha|racha|fenda|buceta`
- `chupar` → `chupar|mamar|sugar|boquete|oral`
- Contacto WhatsApp → `(WhatsApp)` / `(chamada de voz)` no mesmo bloco.

## Nota sobre canon genérico

Esta skill não carrega factos de NENHUM cenário no próprio corpo — os factos vivem em
`state/scenarios/<id>/facts/` e no canon de cada cenário. Para recolher o contexto de uma
nova história desconhecida, corre `consist.py` contra o canon desse cenário OU, se não
houver canon ainda, cria o `live_state` inicial com o que o user fornecer no arranque
e vai-o acumulando. Nunca assumir conhecimento de outra história.

## Modo SERVIR SillyTavern com pouco histórico (obrigatório)

Quando o pedido vem do SillyTavern (backend = gateway Hermes) e o ST manda **pouco**
histórico, o contexto de longo prazo VIVE NOS FICHEIROS, não nas mensagens recebidas.
Regra: **os ficheiros de /opt/data são a memória; o histórico do ST é só o fio recente.**

Antes de responder, em silêncio, faz a reconstrução a partir do disco:
1. Lê o `live_state.md` do cenário ativo (quem está presente, onde parou, estado físico).
2. Lê o `tail` (~10-20 linhas) do `archive.jsonl` do mesmo cenário (o que aconteceu agora).
3. Para CADA personagem mencionada, lê o lorebook da personagem em
   `/opt/data/lorebook_personagens/<nome>.json` (idade, papel, status sexual, relações).
4. Injeta no prompt do modelo SÓ o que é relevante para a mensagem atual — o antigo
   mas pertinente (relações, primeira vez, estado, um acto passado que ligue).
5. **Nunca** usar apenas o histórico curto do ST se o disco disser outra coisa.
   Se houver divergência, o disco (ficheiro) é a autoridade.

**Timeout/limitação:** se os ficheiros não forem acessíveis num dado momento, escreve
com o que houver e nota a limitação — mas o default é SEMPRE ir ao disco.

## Busca RAG PROATIVA por termos (consistência > velocidade; tokens > consistência)

Para factos sobre personagens/relações/actos que NÃO estão na cena atual, não te
limites aos lorebooks das personagens presentes. Antes de responder, identifica os
**termos-chave da mensagem do user** e corre `consist.py` contra o canon do cenário
para puxar o que está provado — mesmo que a personagem não esteja na sala.

Como fazer (em silêncio, antes de escrever):
1. Extrai da mensagem do user os termos de busca: nomes de personagens, cargos
   ("directora de RH", "secretária"), relações ("esposa", "irmã"), locais, actos.
2. Para cada termo, corre:
   ```bash
   python3 /opt/data/skills/research/roleplay-rag/scripts/consist.py \
     "<canon do cenário>" "<termo>"
   ```
3. Lê os trechos devolvidos e extrai SÓ o facto provado (quem é, cargo, quando,
   o que aconteceu). Injeta no prompt apenas o trecho relevante.
4. Exemplo real: se o user perguntar "quem é a directora de RH e quando fodeu?",
   corre consist.py com "RH"/"recursos humanos" → encontra a Andreia (RH) e o ato
   (14/02 08:14, quarto da Joana). Responde com isso, sem inventar.

**Regra de poupança de tokens:** corre o consist.py por termo, mas injeta SÓ o trecho
relevante (1-3 linhas por facto) — nunca o canon inteiro nem os contextos todos.
A prioridade é: consistência do facto garantida, com o mínimo de tokens injetados.
Se não houver certeza (nenhum trecho prova), diz que não há registo provado — NUNCA inventa.

**Prioridades (ordem):** 1) poupar tokens na IA → injeta só o relevante;
2) consistência → nunca inventar, ir ao disco; 3) velocidade → aceita a latência
da leitura de ficheiros. Esta ordem está certa para o ST.

## GRUPOS COMO ENTIDADE AGNÓSTICA (genérico — qualquer cenário/chat)

Grupos são uma **entidade de primeira classe**, agnósticos ao cenário. A skill NÃO
presume grupos específicos de nenhuma história — são **descobertos e registados**
por cenário, e adicionáveis a qualquer chat.

**Onde se registam (por cenário):** `state/scenarios/<id>/grupos.md` (ou `grupos.json`).
Estrutura sugerida (agnóstica — adapta ao cenário):
```
## <Nome do Grupo>  [casa/local]
- Personagem (nome completo, apelido, profissão/identidade)
- ...
- Relação interna: <tipo> (ex: casal, irmãs, colegas)
```
**Como adicionar um grupo novo:** quando uma personagem diz "somos N, vivemos em X",
ou quando o canon/archive revela um círculo com casa/local próprio, **regista-o** em
`grupos.md` do cenário — mesmo em chats novos. Nunca assumir que um grupo já existe.

**Regra dos círculos:** uma personagem pertence a UM grupo/casa (dorme na casa do
seu grupo). **Nunca cruzar personagens de um grupo para outro sem justificação no
canon.** Se dois grupos têm membros com o mesmo 1º nome, são entidades separadas.

## RESOLUÇÃO DE IDENTIDADE POR APELIDO (crítico — nunca cruzar pessoas erradas)

Vários grupos podem ter a **mesma letra/primeiro nome** (ex: "Filipa, Teresa, Sara,
Marta" aparece em dois círculos diferentes). Para não cruzar pessoas erradas:

1. **Identidade = nome completo + apelido + casa + profissão.** Um 1º nome NÃO é
   suficiente para dizer quem é a personagem.
2. Quando um nome aparece e há **ambiguidade** (duas personagens com o mesmo 1º nome
   em grupos diferentes), **resolve antes de responder**: pesquisa no canon o apelido,
   a casa/morada, a profissão. Só liga/traze a personagem certa.
3. **Nunca** assumir que dois "Marta"/"Filipa"/"Sara" de grupos diferentes são a
   mesma mulher. Se o canon não provar, são distintas.
4. Concretamente: ex. "Marta do financeiro" (casa da Andreia) ≠ "Marta Umbelino"
   (condutora de Uber, Grupo C). Apelido completo + profissão desambigua.
5. Este passo é obrigatório no pre-flight sempre que o texto traga 1º nomes repetidos
   entre grupos.

## VERIFICAR RÓTULOS DE RELAÇÃO ANTES DE ESCREVER (crítico — incidente real 2026-08-08)

Nunca escrever um rótulo de relação — `(Noiva de X)`, `(Irmã de X)`, `(Namorada de X)`,
nomes de contacto WhatsApp, etc. — sem confirmar contra o `relacoes` já estabelecido
da personagem em `lorebooks/<slug>.json`. Um rótulo novo que contradiz uma relação já
confirmada é um facto inventado, mesmo que soe natural na cena.

**O que aconteceu:** uma cena rotulou um contacto WhatsApp como "Catarina Sousa
(Noiva da Mia)". Mas `mia.json` já tinha `romanticos: {"Rita": "noiva (fachada
lésbica)"}` — a noiva estabelecida da Mia é a Rita, não a Catarina. Pior: a Catarina
já existia no canon como **prima da Filipa Costa** (23 anos, enfermagem, virgem),
sem qualquer ligação à Mia. O RAG disparou nessa cena (5 tool calls, ficheiros lidos)
mas o resultado final contradisse o canon na mesma. Ter disparado não é garantia de
ter verificado o campo certo.

**Regra:** antes de escrever QUALQUER rótulo `(<Relação> de <Nome>)`:
1. Abre `lorebooks/<slug_do_Nome>.json` e olha o campo `relacoes.romanticos` (ou o
   tipo relevante) — se já lá está uma pessoa diferente com esse tipo de relação,
   o rótulo novo está errado. Não escrevas por cima sem o user resolver.
2. Se a personagem que vais rotular já tem um `role`/perfil estabelecido no canon
   (ex.: "prima de X") que não bate com o rótulo que estás prestes a escrever, para
   e usa o papel já estabelecido, não o que "soa bem" na cena.
3. Se genuinamente for uma reviravolta nova da história (ex.: a Rita deixou de ser
   noiva, entra uma noiva nova), isso é uma decisão do user — não decidas sozinho
   ao escrever um nome de contacto; confirma OOC antes ou marca claramente a
   inconsistência em vez de a apagar silenciosamente.


