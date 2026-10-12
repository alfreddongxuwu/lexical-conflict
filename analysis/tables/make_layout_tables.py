#!/usr/bin/env python3
"""Generate the lexical-rule layout appendix table bodies.
Usage: python make_appendix_tables_v2.py COUNTS_DIRECTORY OUTPUT_DIRECTORY
Writes table-pooled-rows-v2.tex (bold marks the highest F1--F5 rate in each row) and
table-full-rows-v2.tex (one row per model x layout: CK-only rates for the PK context and
the CK context, All and F1--F5 each; bold marks the highest frame within each context)."""
import csv, sys
from pathlib import Path
C, O = Path(sys.argv[1]), Path(sys.argv[2]); O.mkdir(parents=True, exist_ok=True)
MODELS = [('chatgpt5_5_instant','GPT-5.5'),('deepseek_llm_7b','DeepSeek-LLM-7B'),('deepseek_llm_67b','DeepSeek-LLM-67B'),
          ('gemma3_4b','Gemma-3-4B'),('gemma3_27b','Gemma-3-27B'),('llama3_8b','Llama-3-8B'),('llama3_70b','Llama-3-70B'),
          ('qwen3_8b','Qwen3-8B'),('qwen3_32b','Qwen3-32B')]
LAYOUTS = [('position_B','B',1),('main','M',1),('position_E','E',1),('reiteration_2','M$\\times$2',2),('position_BM','BM',2),
           ('position_BE','BE',2),('position_ME','ME',2),('reiteration_3','M$\\times$3',3),('position_BME','BME',3),('reiteration','M$\\times$5',5)]
FR = ['F1','F2','F3','F4','F5']
def rd(p):
    with open(p, encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
def mark(vals):
    """Format rates to two decimals; bold every value equal to the row maximum."""
    s = [f"{v:.2f}" for v in vals]; top = max(s, key=float)
    return [f"\\textbf{{{x}}}" if x == top else x for x in s]
pooled = {(r['group'], r['frame_id']): r for r in rd(C/'pooled.csv')}
filt = {(r['group'], r['frame_id']): r for r in rd(C/'filtered-pooled.csv')}
pct = lambda r, k='ck_percent': f"{float(r[k]):.2f}"
rows = [f"{lab} & {k} & {pct(pooled[(g,'All')])} & {pct(pooled[(g,'All')],'inclusive_percent')} & {pct(filt[(g,'All')])} & "
        + ' & '.join(mark([float(pooled[(g,f)]['ck_percent']) for f in FR])) + ' \\\\' for g, lab, k in LAYOUTS]
(O/'table-pooled-rows-v2.tex').write_text('\n'.join(rows) + '\n')
cells = {(r['group'], r['model_key'], r['frame_id'], r['context_type']): r for r in rd(C/'layout-summary.csv')}
out = []
for m, name in MODELS:
    out.append(f"\\multicolumn{{13}}{{@{{}}l}}{{\\textbf{{{name}}}}}\\\\*\n\\hline")
    for g, lab, _ in LAYOUTS:
        parts = [lab]
        for ct in ('PK_context', 'CK_context'):
            cs = [cells[(g, m, f, ct)] for f in FR]
            allrate = 100 * sum(int(c['ck_n']) for c in cs) / sum(int(c['n']) for c in cs)
            parts.append(f"{allrate:.2f}")
            parts.extend(mark([100 * int(c['ck_n']) / int(c['n']) for c in cs]))
        out.append(' & '.join(parts) + ' \\\\')
    out.append('\\hline')
(O/'table-full-rows-v2.tex').write_text('\n'.join(out) + '\n')
print('wrote', O)
