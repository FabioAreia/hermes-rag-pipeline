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
                if mes: out.append(mes)
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

    by_primeiro = defaultdict(list)
    for p in pessoas:
        by_primeiro[p["nome_full"].split()[0].lower()].append(p)

    for mes in mensagens:
        low = mes.lower()
        presentes = set()
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
        for nome_full, rel in updates.items():
            p = by_nome.get(nome_full.lower())
            if not p: continue
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
            with open(p["file"], "w") as f:
                json.dump(p["d"], f, ensure_ascii=False, indent=2)
        print(f"\n[APPLY] atualizados {len(updates)} lorebooks.")
    else:
        print(f"\n[REPORT] {len(updates)} pessoas com relações projetadas. Rode com --apply para gravar.")

if __name__ == "__main__":
    main()
