#!/usr/bin/env python3
"""
extractor_grupos.py — projeta relações do canon para os lorebooks.

GENÉRICO/AGNÓSTICO: obra contra o canon/archive de QUALQUER cenário e a pasta
de lorebooks de personagem. Desambigua identidade por NOME COMPLETO (apelido),
nunca por 1º nome, para não cruzar círculos sociais.

--lore é OBRIGATÓRIO e deve ser sempre a pasta ISOLADA do cenário
(state/scenarios/<id>/lorebooks) — nunca uma pasta partilhada entre
cenários, ou os círculos sociais de cenários diferentes misturam-se.

MODOS:
  --report   (default) só calcula e mostra as relações projetadas, NÃO escreve.
  --apply    atualiza os `relacoes` dos lorebook_personagens/*.json.

Uso:
  python3 extractor_grupos.py --canon <file> --lore <dir_isolada_do_cenario> [--archive <file>] [--min N] [--report|--apply]
"""
import json, re, glob, os, sys
from collections import defaultdict, Counter

TERMOS_TIPO = {
    # kinship DIRETO e explícito (quando "X de Y" → parentesco confirmado, EXCLUI romance)
    "parentesco": [
        "mae de", "mãe de", "pai de", "filha de", "filho de", "irma de", "irmã de",
        "irmao de", "irmão de", "esposa de", "esposo de", "marido de", "mulher de",
        "enteada", "enteado", "sogra", "madrasta", "padrasto", "avó", "tia", "sobrinha",
        "prima", "primo", "mãe de", "mae do", "filha da", "irmã da",
    ],
    "romanticos": ["amante", "namorad", "noiva", "noivo", "casal", "parceiro", "parceira",
                   "meu rei", "minha rainha", "apaixonad", "fica com", "namora"],
    "amizades": ["melhor amiga", "melhor amigo", "amiga de", "amigo de", "amiga", "amigo",
                 "colega de casa", "da faculdade", "minha amiga", "minha melhor"],
    "trabalho": ["recursos humanos", "do rh", "dos rh", "do financeiro", "secretária",
                 "secretaria", "enfermeira", "trabalha com", "trabalham", "patrão", "patrao",
                 "patroa", "chefe", "salão de massagens", "salao de massagens", "massagista",
                 "professora", "condutora", "motorista", "uber", "funcionária", "funcionaria",
                 "administrativa", "advogada", "medica", "médica", "banco", "da empresa"],
    "habitacao": ["vive com", "mora com", "moram com", "colega de casa", "vive na", "mora na",
                  "vivem na", "na casa de", "em casa de", "rua das flores", "casa da",
                  "dividem a casa", "vivem juntas", "moram juntas"],
    "hobby": ["yoga", "dança", "danca", "ginastica", "ginástica", "futebol", "praia",
              "faculdade", "universidade", "escola", "cantar", "desenhar", "correr",
              "malhar", "musculação", "musculacao", "spa", "massagem", "aula de"],
}

# Deteção de atos sexuais confirmados — evidência FORTE e dupla (gatilho + verbo de
# ação no MESMO bloco), nunca por proximidade solta. Preferir não detetar a inventar
# historial sexual falso (pior que não ter nada — ver incidente Catarina 2026-08-08).
ACT_PATTERNS = {
    "primeira_vez": {
        "gatilho": r"\b(virgem|hímen|himen|era zero|nunca teve|nunca tive)\b",
        "confirmacao": r"\b(entra|entrou|meter|meteu|penetr|rasgou|rompeu|desliz)\b",
    },
    "anal": {
        "gatilho": r"\b(cu|rabo|anal)\b",
        "confirmacao": r"\b(entra|entrou|meter|meteu|penetr|abrir|abriu|deslizou|desliza|enterra|empurra)\b",
    },
    "vaginal": {
        "gatilho": r"\b(cona|vagina|buceta|racha|fenda|coninha)\b",
        "confirmacao": r"\b(entra|entrou|meter|meteu|penetr|fode|fodeu|foder|desliz)\b",
    },
    "oral": {
        "gatilho": r"\b(chupar|chupou|mamar|mamou|sugar|boquete)\b",
        "confirmacao": None,  # já é auto-confirmatório, não precisa de segunda verificação
    },
}

def carregar_lore(dir_):
    """Devolve: por chave (primeiro nome) -> lista de (nome_completo, dict)."""
    pessoas = []
    for f in glob.glob(os.path.join(dir_, "*.json")):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        nome = (d.get("nome") or "").strip()
        if not nome:
            continue
        pessoas.append({"nome_full": nome, "d": d, "file": f})
    return pessoas

def main():
    args = sys.argv[1:]
    canon = None
    archive = None
    lore_dir = None
    minimo = 20
    modo = "report"
    for i, a in enumerate(args):
        if a == "--canon" and i+1 < len(args): canon = args[i+1]
        elif a == "--archive" and i+1 < len(args): archive = args[i+1]
        elif a == "--lore" and i+1 < len(args): lore_dir = args[i+1]
        elif a == "--min" and i+1 < len(args): minimo = int(args[i+1])
        elif a == "--apply": modo = "apply"

    if not canon and not archive:
        print("ERRO: indica pelo menos --canon ou --archive"); sys.exit(1)
    if canon and not os.path.exists(canon):
        # normal para um cenário novo, ainda sem export limpo do ST — o RAG
        # funciona só com o archive.jsonl até um canon ser criado manualmente.
        print(f"AVISO: canon '{canon}' ainda não existe — a usar só o archive.", file=sys.stderr)
        canon = None
    if archive and not os.path.exists(archive):
        print(f"AVISO: archive '{archive}' ainda não existe.", file=sys.stderr)
        archive = None
    if not canon and not archive:
        print("ERRO: nem --canon nem --archive existem — nada para ler."); sys.exit(1)
    if not lore_dir:
        print("ERRO: --lore obrigatório — aponta SEMPRE para a pasta isolada do "
              "cenário (state/scenarios/<id>/lorebooks), nunca para uma pasta "
              "partilhada entre cenários.", file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(lore_dir):
        os.makedirs(lore_dir, exist_ok=True)

    pessoas = carregar_lore(lore_dir)
    if not pessoas:
        print(f"AVISO: nenhum lorebook de personagem encontrado em {lore_dir} — "
              f"nada a projetar (a pasta está vazia?)", file=sys.stderr)

    by_nome = {p["nome_full"].lower(): p for p in pessoas}

    def _ler(fonte):
        """Devolve lista de (header, mes) — header extraído do início da mensagem
        (**Dia - AAAA-MM-DD HH:MM – Local**) se houver, para datar eventos sexuais."""
        out = []
        if not fonte or not os.path.exists(fonte):
            return out
        with open(fonte) as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try: d = json.loads(line)
                except Exception: continue
                mes = d.get("mes", "")
                if not mes: continue
                header = d.get("header", "")
                if not header:
                    first = mes.strip().split("\n", 1)[0]
                    if first.startswith("**") and first.endswith("**"):
                        header = first
                out.append((header, mes))
        return out

    mensagens = _ler(canon) + _ler(archive)

    # ---- 1. presença por identidade ----
    # Estratégia: detectar por PRIMEIRO NOME (o canon usa sobretudo o 1º),
    # e usar o APELIDO só para separar quando 2 pessoas partilham o 1º nome na
    # mesma mensagem (ex: Filipa Costa vs Filipa Santos). Evita o viés do apelido
    # compartilhado (ex: toda a família "Jefferson").
    presenca = defaultdict(int)
    coco = defaultdict(Counter)
    coco_tipo = {t: defaultdict(Counter) for t in TERMOS_TIPO}
    ambiguous_fallbacks = Counter()  # colisões de 1º nome sem apelido visível na mensagem
    # eventos sexuais confirmados: pessoa -> lista de (tipo, parceiro_ou_None, header)
    sexual_events = defaultdict(list)

    by_primeiro = defaultdict(list)
    for p in pessoas:
        by_primeiro[p["nome_full"].split()[0].lower()].append(p)

    for header, mes in mensagens:
        low = mes.lower()
        presentes = set()
        presentes_ambiguas = set()  # resolvidas por fallback — nunca usar como parceiro sexual
        for pn, plist in by_primeiro.items():
            if re.search(r"\b" + re.escape(pn) + r"\b", low):
                if len(plist) == 1:
                    presentes.add(plist[0]["nome_full"])
                else:
                    encontrou = False
                    for cand in plist:
                        partes = cand["nome_full"].split()
                        if len(partes) > 1:
                            ap = partes[-1].lower()
                            if re.search(r"\b" + re.escape(ap) + r"\b", low):
                                presentes.add(cand["nome_full"]); encontrou = True
                    if not encontrou:
                        # sem apelido visível: não há como desambiguar com segurança
                        # — regista como ambíguo (visível no relatório) em vez de
                        # assumir silenciosamente que é sempre a mesma pessoa.
                        presentes.add(plist[0]["nome_full"])
                        presentes_ambiguas.add(plist[0]["nome_full"])
                        ambiguous_fallbacks[pn] += 1
        pl = list(presentes)
        for p in pl:
            presenca[p] += 1
        for i in range(len(pl)):
            for j in range(i+1, len(pl)):
                coco[pl[i]][pl[j]] += 1; coco[pl[j]][pl[i]] += 1
        for p in pl:
            pn0 = p.split()[0].lower()
            for m in re.finditer(r"\b" + re.escape(pn0) + r"\b", low):
                start = m.start()
                ja = low[max(0, start-60): start+120]
                para_esta = set()
                for outro in pl:
                    if outro == p: continue
                    on = outro.split()[0].lower()
                    if re.search(r"\b" + re.escape(on) + r"\b", ja):
                        para_esta.add(outro)
                for tipo, termos in TERMOS_TIPO.items():
                    if any(t in ja for t in termos):
                        for outro2 in para_esta:
                            coco_tipo[tipo][p][outro2] += 1
                            coco_tipo[tipo][outro2][p] += 1
                # deteção de atos sexuais — exige gatilho E confirmação no MESMO
                # bloco (janela de 60/120 chars). Parceiro só atribuído se houver
                # exatamente UMA outra pessoa na janela — ambíguo (0 ou 2+) é
                # ignorado, não adivinhado (mesma filosofia do resto do script).
                # Nem o sujeito nem o parceiro podem vir de um fallback ambíguo
                # (1º nome sem apelido visível) — um facto sexual errado por causa
                # de "Marta"/"Sofia" mal resolvida é pior que um "conhecidos" errado.
                if p not in presentes_ambiguas:
                    for act_tipo, pat in ACT_PATTERNS.items():
                        if not re.search(pat["gatilho"], ja):
                            continue
                        if pat["confirmacao"] and not re.search(pat["confirmacao"], ja):
                            continue
                        candidatos_parceiro = para_esta - presentes_ambiguas
                        parceiro = next(iter(candidatos_parceiro)) if len(candidatos_parceiro) == 1 else None
                        sexual_events[p].append((act_tipo, parceiro, header))

    # ---- 2. relatório ----
    print("Pessoas indexadas:", len(pessoas))
    print(f"Modo: {modo} | min co-ocorrência: {minimo}\n")
    updates = {}
    for p in pessoas:
        nome_full = p["nome_full"]
        top = coco[nome_full].most_common()
        rel = {}
        for outro, c in top:
            if c < minimo: continue
            if outro == nome_full: continue
            tipos = []
            for t in TERMOS_TIPO:
                n_t = coco_tipo[t][nome_full].get(outro, 0)
                if n_t >= (minimo * 0.4):
                    tipos.append(t)
            if "parentesco" in tipos and "romanticos" in tipos:
                tipos = [t for t in tipos if t != "romanticos"]
            if not tipos:
                tipos = ["conhecidos"]
            rel[outro] = {"forca": c, "tipos": tipos}
        if rel:
            updates[nome_full] = rel

    for nome_full in sorted(updates):
        rel = updates[nome_full]
        print(f"### {nome_full}")
        for outro, info in sorted(rel.items(), key=lambda x: -x[1]["forca"])[:10]:
            print(f"    -> {outro} (co: {info['forca']}, tipos: {','.join(info['tipos'])})")

    # dedupe de eventos sexuais: a mesma cena pode disparar o mesmo (tipo, parceiro,
    # header) várias vezes (nome mencionado 2x na mensagem) — não é 2 atos, é 1.
    sexual_updates = {}
    for nome_full, eventos in sexual_events.items():
        vistos = set()
        deduped = []
        for tipo, parceiro, header in eventos:
            chave = (tipo, parceiro, header)
            if chave in vistos:
                continue
            vistos.add(chave)
            deduped.append({"tipo": tipo, "parceiro": parceiro, "data": header})
        if deduped:
            sexual_updates[nome_full] = deduped

    if sexual_updates:
        print(f"\n--- eventos sexuais detetados ({sum(len(v) for v in sexual_updates.values())} no total) ---")
        for nome_full in sorted(sexual_updates):
            print(f"### {nome_full}")
            for ev in sexual_updates[nome_full][:15]:
                parceiro_str = ev["parceiro"] or "(parceiro não identificado — ambíguo, ignorado no historial)"
                print(f"    -> {ev['tipo']} com {parceiro_str} | {ev['data']}")
        pv_candidatos = [(n, e) for n, evs in sexual_updates.items() for e in evs if e["tipo"] == "primeira_vez"]
        if pv_candidatos:
            print(f"\n[VIRGINDADE — confirmação manual obrigatória, NUNCA escrita por --apply]")
            for nome_full, ev in pv_candidatos:
                parceiro_str = ev["parceiro"] or "parceiro não identificado (provável falso positivo — verificar)"
                print(f"    {nome_full}: candidato a primeira vez com {parceiro_str} | {ev['data']}")

    if ambiguous_fallbacks:
        total_amb = sum(ambiguous_fallbacks.values())
        print(f"\n[AVISO] {total_amb} deteções ambíguas (1º nome partilhado, sem "
              f"apelido visível na mensagem) resolvidas por default para a 1ª "
              f"pessoa da lista — podem estar mal atribuídas:", file=sys.stderr)
        for pn, c in ambiguous_fallbacks.most_common():
            candidatos = ", ".join(p["nome_full"] for p in by_primeiro[pn])
            assumido = by_primeiro[pn][0]["nome_full"]
            print(f"   '{pn}' ({c}x) — candidatos: [{candidatos}] — assumido: {assumido}", file=sys.stderr)

    # ---- 3. apply ----
    if modo == "apply":
        pessoas_a_atualizar = set(updates) | set(sexual_updates)
        n_sexual = 0
        for nome_full in pessoas_a_atualizar:
            p = by_nome.get(nome_full.lower())
            if not p: continue

            if nome_full in updates:
                rel = updates[nome_full]
                novo_rel = {
                    "parentesco": {}, "romanticos": {}, "amizades": {},
                    "trabalho": {}, "habitacao": {}, "hobby": {},
                    "grupos": [], "conhecidos": [], "inimigos": [],
                }
                for outro, info in rel.items():
                    for t in info["tipos"]:
                        if t == "amizades": novo_rel["amizades"][outro] = "amiga/colega"
                        elif t == "romanticos": novo_rel["romanticos"][outro] = "amante/parceira"
                        elif t == "parentesco": novo_rel["parentesco"][outro] = "familiar"
                        elif t == "trabalho": novo_rel["trabalho"][outro] = "colega de trabalho"
                        elif t == "habitacao": novo_rel["habitacao"][outro] = "colega de casa"
                        elif t == "hobby": novo_rel["hobby"][outro] = "partilha hobby"
                        elif t == "conhecidos": novo_rel["conhecidos"].append(outro)
                rel_ant = p["d"].get("relacoes", {})
                if isinstance(rel_ant, dict):
                    for k in ("parentesco", "romanticos", "amizades", "trabalho", "habitacao", "hobby"):
                        novo_rel[k].update(rel_ant.get(k, {}) or {})
                    novo_rel["grupos"] = list(dict.fromkeys((rel_ant.get("grupos", []) or []) + novo_rel["grupos"]))
                    novo_rel["conhecidos"] = list(dict.fromkeys((rel_ant.get("conhecidos", []) or []) + novo_rel["conhecidos"]))
                p["d"]["relacoes"] = novo_rel

            eventos_novos = sexual_updates.get(nome_full)
            if eventos_novos:
                hs = p["d"].get("historial_sexual")
                if not isinstance(hs, dict):
                    hs = {}
                # virgindade NUNCA é escrita automaticamente — é um facto único e
                # definitivo demais para arriscar um falso positivo (testado: um "hub"
                # como o Tyronne, claramente não-virgem, também dispara o gatilho
                # quando outra personagem perde a virgindade na mesma cena). Fica só
                # como sugestão no --report; confirmação manual obrigatória.
                parceiros_existentes = set(hs.get("parceiros") or [])
                parceiros_novos = {e["parceiro"] for e in eventos_novos if e["parceiro"]}
                if parceiros_novos:
                    hs["parceiros"] = sorted(parceiros_existentes | parceiros_novos)
                # actos_confirmados: junta aos existentes só o que é genuinamente novo
                # (dedup por tipo+parceiro+data) — nunca reescreve o que já lá estava.
                existentes = hs.get("actos_confirmados") or []
                chaves_existentes = {(e.get("tipo"), e.get("parceiro"), e.get("data")) for e in existentes}
                novos_actos = [e for e in eventos_novos
                               if (e["tipo"], e["parceiro"], e["data"]) not in chaves_existentes]
                if novos_actos:
                    hs["actos_confirmados"] = existentes + novos_actos
                p["d"]["historial_sexual"] = hs
                n_sexual += 1

            with open(p["file"], "w") as f:
                json.dump(p["d"], f, ensure_ascii=False, indent=2)
        print(f"\n[APPLY] atualizados {len(pessoas_a_atualizar)} lorebooks "
              f"({len(updates)} com relações, {n_sexual} com historial sexual).")
    else:
        print(f"\n[REPORT] {len(updates)} pessoas com relações projetadas, "
              f"{len(sexual_updates)} com eventos sexuais. Rode com --apply para gravar.")

if __name__ == "__main__":
    main()
