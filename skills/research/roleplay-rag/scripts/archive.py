#!/usr/bin/env python3
"""
archive.py — arquiva uma troca da conversa de roleplay num JSONL vivo, por cenário.

Cada cenário (chat/roleplay distinto) tem a SUA pasta isolada em:
    state/scenarios/<SCENARIO>/archive.jsonl

Assim uma skill serve N chats — cada um com os seus ficheiros separados,
sem colidir. Escolhe o cenário com a env var SCENARIO ou com -s/--scenario.

Formato de cada linha (JSONL):
{"role": "user"|"assistant", "mes": "<texto completo, sem alterações>",
 "ts": "<YYYY-MM-DD HH:MM>", "header": "<**Dia - data hora – Local** se houver>",
 "chars": ["<personagens presentes>"]}

Uso:
  SCENARIO=marta-uber python3 archive.py "USER" "mensagem do user"
  python3 archive.py -s stacy-suzy-stepdad "ASSISTANT" "cena completa" "header" "p1,p2"
"""
import sys, json, os, datetime, argparse

# Raiz da pasta de cenários (cada cenário = subpasta isolada).
# Resolvida em relação ao próprio script -> a skill funciona de qualquer local,
# sem caminhos hardcoded à persona/cenário.
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "state", "scenarios")

def out_path(scenario):
    return os.path.join(BASE, scenario, "archive.jsonl")

def main():
    p = argparse.ArgumentParser(description="Arquiva uma troca por cenário")
    p.add_argument("-s", "--scenario", help="id do cenário (ex.: stacy-suzy-stepdad)")
    p.add_argument("role", help="USER|ASSISTANT")
    p.add_argument("mes", help="texto completo, sem alterações")
    p.add_argument("header", nargs="?", default="", help="header da cena")
    p.add_argument("chars", nargs="?", default="", help="personagens separadas por vírgula")
    args = p.parse_args()

    scenario = args.scenario or os.environ.get("SCENARIO", "")
    if not scenario:
        print("ERRO: indica o cenário com -s/--scenario ou env SCENARIO", file=sys.stderr)
        sys.exit(2)

    role = "user" if args.role.startswith(("USER", "user")) else "assistant"
    chars = [c.strip() for c in args.chars.split(",") if c.strip()] if args.chars else []
    # Timestamp: se houver header da cena, extrai a data/hora da história (AAAA-MM-DD HH:MM)
    # para que o arquivo reflicta a linha do tempo narrativa, não a hora real do sistema.
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    hdr_m = None
    if args.header:
        import re
        hdr_m = re.search(r"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})", args.header)
    if hdr_m:
        ts = f"{hdr_m.group(1)} {hdr_m.group(2)}"
    entry = {
        "role": role,
        "mes": args.mes,
        "ts": ts,
        "header": args.header,
        "chars": chars,
    }
    path = out_path(scenario)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"[{scenario}] arquivado {role}: {len(args.mes)} chars -> {path}")

if __name__ == "__main__":
    main()
