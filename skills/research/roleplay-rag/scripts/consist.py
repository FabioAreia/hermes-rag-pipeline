#!/usr/bin/env python3
"""
Motor de consistência Tyronne — consulta RAG sobre o JSONL do lorebook.

Uso:
  consist.py <jsonl> "query" [extra_terms...]

Devolve, por cada termo de busca, os trechos mais relevantes do lorebook
com contexto, ignorando swipes alternativos que não fazem parte do canon.

Canon = mensagens reais (mes) na ordem cronológica dos headers de data.
Swipes alternativos (continueSwipe / swipes) com o MESMO header são
descartados — só o primeiro (index original) conta.
"""
import json, re, sys, collections
from pathlib import Path

SYNONYMS = {
    'anal': r'anal|ânus|cu(?!\w)|rabo|atras|trás|por trás|por detras',
    'cona': r'cona|coninha|racha|fenda|buceta|vagina|pussy',
    'pau': r'caralho|pau|picha|pica|pênis|verga|pinto|tronco',
    'virgem': r'virgem|primeira vez|era zero|nunca teve|nunca tive|hímen|donzela',
    'foder': r'foder|foda|fudid|fuder|penetr|entra(?!r|m)|desvirgin',
    'semen': r'sémen|semen|porra|leite|esperma|goz(ou|aste|a)',
    'chupar': r'chupar|mamar|sugar|boquete|oral|chupou',
    'noiva': r'noiva|noivo|namorada',
    'esposa': r'esposa|mulher|casada',
    'irma': r'irmã|irmas|irmão',
    'amiga': r'amiga|amigas|melhor amiga|colega de casa',
    'uba': r'uber|condutora|motorista|taxista',
    'salao': r'salão|massagista|esteticista|clinica',
}

# Verbos que confirmam penetração anal REAL (evita falsos positivos)
ANAL_CONFIRM = r'\b(entra|entrou|meter|meteu|penetr|abrir|abriu|deslizou|desliza|envia|recua|saiu)\b.*\b(cu|rabo|anal)\b|\b(cu|rabo|anal)\b.*\b(entra|entrou|meter|meteu|penetr|abrir|abriu|deslizou|desliza|saiu)\b'

def build_pattern(terms):
    parts=[]
    for t in terms:
        tl=t.lower()
        parts.append(re.escape(tl))
        for key,pat in SYNONYMS.items():
            # only add syn if the literal term is a keyword we know
            if tl in ('anal','cona','pau','virgem','foder','semen','chupar','noiva','esposa','irma','amiga','uber','salao'):
                if tl==key:
                    parts.append(pat)
    return re.compile('|'.join(parts), re.IGNORECASE)

def load_canon(jsonl):
    """Devolve mensagens canon: ignora swipes repetidos com mesmo header."""
    struct=collections.OrderedDict()  # header -> list of msgs
    with open(jsonl, encoding='utf-8') as f:
        for line in f:
            line=line.strip()
            if not line: continue
            try: d=json.loads(line)
            except: continue
            mes=d.get('mes','')
            if not mes: continue
            # header = first **...** line
            hm=re.match(r'^\*\*(.+?)\*\*', mes)
            header=hm.group(1) if hm else ''
            struct.setdefault(header, []).append(mes)
    # canon: keep only FIRST message per header (first swipe); drop identical dups
    canon=[]
    for hdr, msgs in struct.items():
        if msgs:
            canon.append(msgs[0])
    return canon

def search(canon, pattern, max_res=12, window=3):
    res=[]
    for i,mes in enumerate(canon):
        if not pattern.search(mes): continue
        ctx=canon[max(0,i-window):i+window+1]
        res.append((i,mes,' | '.join(ctx)))
        if len(res)>=max_res: break
    return res

def main():
    if len(sys.argv)<3:
        print("Uso: consist.py <jsonl> \"query\" [termo2 termo3 ...]"); sys.exit(1)
    jsonl=sys.argv[1]
    terms=sys.argv[2:]
    pattern=build_pattern(terms)
    canon=load_canon(jsonl)
    print(f"[canon] {len(canon)} mensagens únicas\n")
    for term in terms:
        pat=build_pattern([term])
        print(f"===== '{term}' =====")
        for i,mes,ctx in search(canon, pat):
            # show the matching line(s)
            lines=[l for l in ctx.split('\n') if pat.search(l)]
            shown = ' '.join(l.strip() for l in ctx.split('\n') if l.strip())[:600]
            print(f"  msg{i}: {shown}")
            print("  ---")
        print()

if __name__=='__main__':
    main()
