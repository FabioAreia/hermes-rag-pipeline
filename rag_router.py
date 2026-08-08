#!/usr/bin/env python3
"""
rag_router.py — resolve QUAL cenário trabalhar e manda as ferramentas para lá.

Deteção (por ordem de prioridade):
  1. OOC explícito:  --ooc <scenario_id>   (o user manda; SUBSUpon o automático)
  2. Automática:     --st-active <containerdir>  ouero o ficheiro de chat do ST
     mais recentemente modificado e casa com cenarios.yaml.

Chama:
  - archive_sync  (sync ST → archive)  se --sync
  - extractor     (projeta relações)   se --extract

Uso:
  rag_router.py --ooc stacy-suzy-stepdad --sync --extract
  rag_router.py --sync --extract           # deteção automática
"""
import json, os, sys, subprocess, re, argparse, shlex
from pathlib import Path

BASE = Path("/opt/data")
CARREGADOR = BASE / "cenarios.json"
EXTRACTOR = BASE / "extractor_grupos.py"
ST_CONTAINER = "sillytavern"
# archive_sync.py corre no HOST (precisa do docker.sock, que este container não
# tem montado — `docker exec` daqui dentro falha sempre com "Cannot connect to
# the Docker daemon"). Por isso o --sync tem de saltar por SSH para o host,
# tal como _st_chats_atuais() já faz para listar os chats do ST.
ARCHIVE_SYNC_HOST_PATH = "/media/sda/Scripts/sillytavern/archive_sync.py"
HOST_SSH = "fabio@172.17.0.1"

def carregar_cenarios():
    """Lê cenarios.json (sem dependências). Fallback para cenarios.yaml (manual)."""
    if CARREGADOR.exists():
        with open(CARREGADOR) as f:
            return json.load(f).get("scenarios", {})
    # fallback: se só existe .yaml, tenta minimal (sem pyyaml)
    y = BASE / "cenarios.yaml"
    if y.exists():
        # parsing manual débil do yaml aninhado (só para o caso haver .yaml e não .json)
        try:
            import yaml
            with open(y) as f:
                return yaml.safe_load(f).get("scenarios", {})
        except Exception:
            pass
    return {}

def _st_chats_atuais():
    """Lista os chats do ST por recentidade, via SSH ao host (docker exec não
    funciona de dentro do container Hermes — sem socket docker)."""
    cmd = ("timeout 25 ssh -o ConnectTimeout=15 -o StrictHostKeyChecking=no "
           "fabio@172.17.0.1 \"docker exec sillytavern sh -c 'ls -t "
           "/home/node/app/data/lulzcz/chats/ 2>/dev/null | head -10'\"")
    out = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=35)
    if out.returncode != 0:
        return None, out.stderr
    chats = [ln.strip().rstrip("/") for ln in out.stdout.strip().split("\n")
             if ln.strip()]
    return chats, None

def _slug(nome):
    """Gera o scenario_id normalizado a partir do nome do chat do ST."""
    import unicodedata
    s = unicodedata.normalize("NFKD", nome.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "cenario"

def detectar_por_st(cenarios):
    """Descobre o cenário pela conversa do ST mais recentemente escrita.

    Devolve: (sid_ativo, cfg, candidatos_novos) — candidatos_novos são chats
    do ST que NÃO têm cenário registado (auto-detetados, a aguardar confirmação).
    """
    chats, err = _st_chats_atuais()
    if err:
        return None, None, None, f"SSH/docker falhou: {err[:200]}"
    if not chats:
        return None, None, None, "sem chats no ST"
    print("Chats do ST (por recentidade):")
    for c in chats[:8]:
        print("   ", c)

    def casa(chat):
        for sid, cfg in cenarios.items():
            if cfg.get("st_chat", "").lower() in chat.lower():
                return sid, cfg
        return None, None

    # candidatos novos = chats cujo nome não corresponde a nenhum cenário
    batidos = set()
    for chat in chats[:10]:
        sid, _ = casa(chat)
        if sid:
            batidos.add(chat)
    novos_candidatos = [c for c in chats[:10] if c not in batidos]

    # ativo = primeiro chat (mais recente) que casa com um cenário
    for chat in chats[:8]:
        sid, cfg = casa(chat)
        if cfg:
            return sid, cfg, novos_candidatos, None
    return None, None, novos_candidatos, f"cenário não encontrado para: {chats[:5]}"

def registar_cenario(nome_chat, min_co=20):
    """Regista um chat do ST como novo cenário (gera pasta + entrada). Devolve o id."""
    sid = _slug(nome_chat)
    base_scen = BASE / "skills/research/roleplay-rag/state/scenarios" / sid
    lore = base_scen / "lorebooks"
    groups = base_scen / "grupos.md"
    live = base_scen / "live_state.md"
    canon_dir = base_scen / "canon"
    lore.mkdir(parents=True, exist_ok=True)
    canon_dir.mkdir(parents=True, exist_ok=True)
    (base_scen / "archive.jsonl").touch()
    if not groups.exists():
        groups.write_text(f"# GRUPOS — {nome_chat}\n\n> A preencher a partir do canon.\n")
    if not live.exists():
        live.write_text(f"# ESTADO VIVO — {nome_chat}\n\n(A criar.)\n")
    # adiciona ao cenarios.json
    # NOTA: "canon" tem de ser um FICHEIRO (não a pasta canon/), mesmo que ainda
    # não exista — extractor_grupos.py trata "não existe" como canon vazio (ok,
    # fica tudo no archive.jsonl) mas rebenta (IsADirectoryError) se apontar
    # para uma pasta. Convenção: canon/<slug>.cleaned.jsonl — se um dia limpares
    # um export do ST para este cenário, guarda-o exatamente aí.
    canon_file = canon_dir / f"{sid}.cleaned.jsonl"
    cenarios = carregar_cenarios()
    cenarios[sid] = {
        "st_chat": nome_chat,
        "canon": str(canon_file.relative_to(BASE)),
        "archive": str(base_scen.relative_to(BASE) / "archive.jsonl"),
        "lorebooks": str(base_scen.relative_to(BASE) / "lorebooks"),
        "groups": str(groups.relative_to(BASE)),
        "live_state": str(live.relative_to(BASE)),
        "min_co": min_co,
    }
    with open(CARREGADOR, "w") as f:
        json.dump({"scenarios": cenarios}, f, ensure_ascii=False, indent=2)
    return sid

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ooc", help="scenario_id explícito (sobrescreve automático)")
    p.add_argument("--register", nargs="?", const="_auto", default=None,
                   help="nome do chat do ST a registar como novo cenário (ou auto=primeiro candidato)")
    p.add_argument("--sync", action="store_true", help="corre archive_sync")
    p.add_argument("--extract", action="store_true", help="corre extractor")
    args = p.parse_args()

    cenarios = carregar_cenarios()
    if not cenarios:
        print("ERRO: cenarios.json vazio ou não encontrado em", CARREGADOR, file=sys.stderr)
        sys.exit(1)

    # REGISTER primeiro (não precisa de cenário ativo)
    if args.register is not None:
        _, _, novos, _ = detectar_por_st(cenarios)
        alvo = None
        if args.register == "_auto":
            alvo = novos[0] if novos else None
        else:
            # casa o nome dado com um chat do ST
            chats, _ = _st_chats_atuais()
            alvo = next((c for c in chats if args.register.lower() in c.lower()), None)
            if not alvo:
                for c in (chats or []):
                    if _slug(args.register) == _slug(c):
                        alvo = c; break
        if not alvo:
            print("ERRO: nenhum chat do ST corresponde. Candidatos:", novos, file=sys.stderr)
            sys.exit(1)
        sid = registar_cenario(alvo)
        print(f"[ROUTER] registado novo cenário: {sid}  (chat: '{alvo}')")
        sys.exit(0)

    # 1. resolver cenário
    sid = args.ooc
    cfg = cenarios.get(sid) if sid else None
    origem = "ooc" if sid else None
    candidatos_novos = []
    if not sid:
        sid, cfg, candidatos_novos, err = detectar_por_st(cenarios)
        origem = "auto"
        if not cfg and err:
            print(f"ERRO deteção automática: {err}", file=sys.stderr)
            sys.exit(1)
    if not cfg:
        print(f"ERRO: cenário '{sid}' não existe em cenarios.json", file=sys.stderr)
        sys.exit(1)

    if candidatos_novos:
        print("\n[AUTO-DETETADO] conversas novas do ST sem cenário registado:")
        for c in candidatos_novos:
            print(f"   • {c}  (id sugerido: {_slug(c)})")
        print("   → confirma com: rag_router.py --register \"" + candidatos_novos[0] + "\"")
        print()

    # resolve paths para absolutos
    canon = str(BASE / cfg["canon"])
    archive = str(BASE / cfg["archive"])
    lore = str(BASE / cfg["lorebooks"])
    min_co = cfg.get("min_co", 20)

    print(f"[ROUTER] cenário: {sid} (via {origem})")
    print(f"   canon:    {canon}")
    print(f"   archive:  {archive}")
    print(f"   lorebooks:{lore}")

    # garantir pasta lorebooks por cenário
    Path(lore).mkdir(parents=True, exist_ok=True)
    # os caminhos dentro do extractor/archive usam /opt/data absoluto (no container)
    canon_abs = canon
    archive_abs = archive
    lore_abs = lore

    if args.sync:
        print("\n=== SYNC ===")
        # SSH para o host (este container não tem docker.sock) e corre o
        # archive_sync.py real de lá, já com --ooc para resolver CANON/
        # ARCHIVE/LORE a partir de cenarios.json (nunca cai em defaults
        # hardcoded/partilhados).
        remote_cmd = shlex.quote(f"python3 {ARCHIVE_SYNC_HOST_PATH} --ooc {sid}")
        ssh_cmd = (f"timeout 380 ssh -o ConnectTimeout=15 -o StrictHostKeyChecking=no "
                   f"{HOST_SSH} {remote_cmd}")
        r = subprocess.run(["bash", "-c", ssh_cmd], capture_output=True, text=True, timeout=400)
        print(r.stdout[-1500:])
        if r.returncode != 0:
            print(r.stderr[-500:], file=sys.stderr)
            print("SYNC falhou.")

    if args.extract:
        print("\n=== EXTRACTOR RELAÇÕES ===")
        r = subprocess.run(
            [sys.executable, str(EXTRACTOR),
             "--canon", canon_abs, "--archive", archive_abs,
             "--lore", lore_abs, "--min", str(min_co), "--apply"],
            capture_output=True, text=True, timeout=400)
        print(r.stdout[-1500:])
        if r.returncode != 0:
            print(r.stderr[-500:], file=sys.stderr)
            print("EXTRACTOR falhou.")

    print("\n[ROUTER] fim.")

if __name__ == "__main__":
    main()
