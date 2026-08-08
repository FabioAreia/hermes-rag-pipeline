#!/usr/bin/env python3
"""
extractor_relacoes.py — projeta relações de um canon JSONL para os lorebooks.

GENÉRICO/AGNÓSTICO: obra contra o canon/archive de QUALQUER cenário + pasta de
lorebooks de personagens. Desambigua identidade por NOME COMPLETO (apelido), nunca
por 1º nome, para não cruzar círculos sociais.

MODOS:
  --report   (default) só calcula e mostra as relações projetadas, NÃO escreve.
  --apply    atualiza os `relacoes` dos ficheiros de personagens (aditivo + backup).

Uso:
  python3 extractor_relacoes.py --canon <file> --lore <dir> [--min N] [--apply]

LIÇÕES-CHAVE (validadas em produção, 2026-08-07):
  1. Desambigua por APELIDO, nunca 1º nome — dois círculos podem partilhar "Filipa,
     Teresa, Sara, Marta" mas são pessoas diferentes (apelidos Costa/Santos/Silva/Umbelino).
  2. Deteção de TIPO por JANELA à volta do nome (não na mensagem inteira) — senão
     "mulher"/"esposa" em qualquer parte da mensagem dispara parentesco em tudo.
  3. REGRA DE CONSISTÊNCIA: parentesco direto (mãe/filha/irmã/esposa, "X de Y")
     EXCLUI romance — família nunca é amante. (Correção do user: Lara é mãe da Mia,
     logo Lara↔Mia = parentesco, NUNCA romance.)
  4. Co-ocorrência de nomes é fiável para ESTRUTURA (quem com quem/força); a etiqueta
     fina (casal vs amante vs colega) é cinzenta quando há um hub (ex: Tyronne amante
     de quase todas). Aplicar etiquetas exige a regra (3) senão polui a consistência.
  5. Sempre backup da pasta de lorebooks antes de --apply (aditivo, mas reverte fácil).
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


def carregar_pessoas(lore_dir):
    pessoas = []
    for f in glob.glob(os.path.join(lore_dir, "*.json")):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        nome = (d.get("nome") or "").strip()
        if nome:
            pessoas.append({"nome_full": nome, "d": d, "file": f})
    return pessoas


def main():
    args = sys.argv[1:]
    canon, lore_dir, minimo, modo = None, "/opt/data/lorebook_personagens", 20, "report"
    for i, a in enumerate(args):
        if a == "--canon" and i + 1 < len(args): canon = args[i + 1]
        elif a == "--lore" and i + 1 < len(args): lore_dir = args[i + 1]
        elif a == "--min" and i + 1 < len(args): minimo = int(args[i + 1])
        elif a == "--apply": modo = "apply"
    if not canon or not os.path.exists(canon):
        print("ERRO: --canon obrigatório e deve existir"); sys.exit(1)

    pessoas = carregar_pessoas(lore_dir)
    by_nome = {p["nome_full"].lower(): p for p in pessoas}
    by_primeiro = defaultdict(list)
    for p in pessoas:
        by_primeiro[p["nome_full"].split()[0].lower()].append(p)

    mensagens = []
    with open(canon) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            mes = d.get("mes", "")
            if mes:
                mensagens.append(mes)

    presenca = defaultdict(int)
    coco = defaultdict(Counter)
    coco_tipo = {t: defaultdict(Counter) for t in TERMOS_TIPO}

    for mes in mensagens:
        low = mes.lower()
        presentes = set()
        for pn, plist in by_primeiro.items():
            if re.search(r"\b" + re.escape(pn) + r"\b", low):
                if len(plist) == 1:
                    presentes.add(plist[0]["nome_full"])
                else:
                    # colisão de 1º nome: resolve por apelido na mensagem
                    achou = False
                    for cand in plist:
                        partes = cand["nome_full"].split()
                        if len(partes) > 1:
                            ap = partes[-1].lower()
                            if re.search(r"\b" + re.escape(ap) + r"\b", low):
                                presentes.add(cand["nome_full"]); achou = True
                    if not achou:
                        presentes.add(plist[0]["nome_full"])
        pl = list(presentes)
        for p in pl:
            presenca[p] += 1
        for i in range(len(pl)):
            for j in range(i + 1, len(pl)):
                coco[pl[i]][pl[j]] += 1; coco[pl[j]][pl[i]] += 1
        # tipos por JANELA à volta de cada nome (não na mensagem toda)
        for p in pl:
            pn0 = p.split()[0].lower()
            for m in re.finditer(r"\b" + re.escape(pn0) + r"\b", low):
                ja = low[max(0, m.start() - 60): m.start() + 120]
                para_esta = set()
                for outro in pl:
                    if outro == p:
                        continue
                    on = outro.split()[0].lower()
                    if re.search(r"\b" + re.escape(on) + r"\b", ja):
                        para_esta.add(outro)
                for tipo, termos in TERMOS_TIPO.items():
                    if any(t in ja for t in termos):
                        for o2 in para_esta:
                            coco_tipo[tipo][p][o2] += 1; coco_tipo[tipo][o2][p] += 1

    updates = {}
    for p in pessoas:
        nome_full = p["nome_full"]
        rel = {}
        for outro, c in coco[nome_full].most_common():
            if c < minimo or outro == nome_full:
                continue
            tipos = []
            for t in TERMOS_TIPO:
                if coco_tipo[t][nome_full].get(outro, 0) >= (minimo * 0.4):
                    tipos.append(t)
            # REGRA: parentesco direto EXCLUI romance
            if "parentesco" in tipos and "romanticos" in tipos:
                tipos = [t for t in tipos if t != "romanticos"]
            if not tipos:
                tipos = ["conhecidos"]
            rel[outro] = {"forca": c, "tipos": tipos}
        if rel:
            updates[nome_full] = rel

    for nome_full in sorted(updates):
        print(f"### {nome_full}")
        for outro, info in sorted(updates[nome_full].items(), key=lambda x: -x[1]["forca"])[:10]:
            print(f"    -> {outro} (co: {info['forca']}, tipos: {','.join(info['tipos'])})")

    if modo == "apply":
        import shutil, time
        bdir = os.path.join(os.path.dirname(lore_dir.rstrip("/")) or ".", f"_backup_lore_{int(time.time())}")
        if not os.path.exists(bdir):
            shutil.copytree(lore_dir, bdir)
        for nome_full, rel in updates.items():
            p = by_nome.get(nome_full.lower())
            if not p:
                continue
            novo = {"parentesco": {}, "romanticos": {}, "amizades": {},
                    "trabalho": {}, "habitacao": {}, "hobby": {},
                    "grupos": [], "conhecidos": [], "inimigos": []}
            for outro, info in rel.items():
                for t in info["tipos"]:
                    if t == "amizades": novo["amizades"][outro] = "amiga/colega"
                    elif t == "romanticos": novo["romanticos"][outro] = "amante/parceira"
                    elif t == "parentesco": novo["parentesco"][outro] = "familiar"
                    elif t == "trabalho": novo["trabalho"][outro] = "colega de trabalho"
                    elif t == "habitacao": novo["habitacao"][outro] = "colega de casa"
                    elif t == "hobby": novo["hobby"][outro] = "partilha hobby"
                    elif t == "conhecidos": novo["conhecidos"].append(outro)
            ant = p["d"].get("relacoes", {})
            if isinstance(ant, dict):
                for k in ("parentesco", "romanticos", "amizades", "trabalho", "habitacao", "hobby"):
                    novo[k].update(ant.get(k, {}) or {})
                novo["grupos"] = list(dict.fromkeys((ant.get("grupos", []) or []) + novo["grupos"]))
                novo["conhecidos"] = list(dict.fromkeys((ant.get("conhecidos", []) or []) + novo["conhecidos"]))
            p["d"]["relacoes"] = novo
            with open(p["file"], "w") as f:
                json.dump(p["d"], f, ensure_ascii=False, indent=2)
        print(f"\n[APPLY] atualizados {len(updates)} lorebooks. Backup em {bdir}")
    else:
        print(f"\n[REPORT] {len(updates)} pessoas com relações. Rode --apply para gravar.")


if __name__ == "__main__":
    main()
