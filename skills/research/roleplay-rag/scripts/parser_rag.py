#!/usr/bin/env python3
"""Parser para tyronne-lorebook JSONL com busca semântica, sinônimos e filtros anti-falso-positivo."""

import json
import re
import sys
from pathlib import Path

# Mapa de sinônimos expandido
SYNONYMS = {
    'anal': r'anal|ânus|rabo|cu(?!\s*[a-záéíóúãõç])|cu\.|cu!|cu\?|atrás|trás',
    'virgem': r'virgem|primeira vez|era zero|nunca tive|não tinha|hímen',
    'pau': r'caralho|pau|picha|pica|pênis|verga|pinto',
    'cona': r'cona|coninha|racha|fenda|buceta|vagina',
    'chupar': r'chupar|mamar|sugar|boquete|oral',
    'beijar': r'beijar|beijo|selinho',
    'foder': r'foder|foda|fudida|fuder',
    'gozar': r'gozar|orgasmo|clímax|clitóris',
    'semen': r'sémen|porra|leite|esperma|gozo',
}
ANAL_ACTION_VERBS = r'entra|penetra|meter|abrir|desliza|enterra|empurra|desce'

def build_pattern(query: str) -> str:
    parts = [re.escape(query.lower())]
    q = query.lower()
    for term, pat in SYNONYMS.items():
        if term in q:
            parts.append(pat)
    return '|'.join(parts)

def load_jsonl(path: str) -> list[dict]:
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                # só mensagens de chat com campo 'mes'
                if isinstance(rec, dict) and rec.get('mes'):
                    records.append(rec)
            except json.JSONDecodeError:
                continue
    return records

def search(records: list[dict], query: str, context_lines: int = 5) -> list[dict]:
    pat = build_pattern(query)
    results = []
    for i, rec in enumerate(records):
        text = rec.get('mes', '')
        if not re.search(pat, text, re.IGNORECASE):
            continue
        start = max(0, i - context_lines)
        end = min(len(records), i + context_lines + 1)
        ctx = ' '.join(records[j].get('mes', '') for j in range(start, end))

        if re.search(r'\bcu\b', query.lower()) or re.search(r'\banal\b', query.lower()):
            if not re.search(ANAL_ACTION_VERBS, ctx, re.IGNORECASE):
                continue

        if re.search(r'primeira', query.lower()) or re.search(r'\bvirgem\b', query.lower()):
            if not re.search(r'sangue', ctx, re.IGNORECASE):
                continue

        results.append({
            'index': i,
            'header': '',
            'match': text,
            'context': [records[j].get('mes', '') for j in range(start, end)],
            'source_file': rec.get('source_file', ''),
        })
    return results

def main():
    if len(sys.argv) < 3:
        print('Uso: parser_rag.py <jsonl_path> <query> [context_lines]')
        sys.exit(1)

    jsonl_path = sys.argv[1]
    query = sys.argv[2]
    context_lines = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    if not Path(jsonl_path).exists():
        print(f'ERRO: ficheiro não encontrado: {jsonl_path}')
        sys.exit(1)

    records = load_jsonl(jsonl_path)
    results = search(records, query, context_lines)

    print(f"=== {len(results)} resultados para '{query}' ===\n")
    for r in results:
        header = r['match'][:180]
        print(header)
        print('CONTEXT:', ' | '.join(r['context'][:2])[:500])
        print('-' * 80)

if __name__ == '__main__':
    main()
