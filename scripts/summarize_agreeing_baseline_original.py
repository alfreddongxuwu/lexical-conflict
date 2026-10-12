#!/usr/bin/env python3
"""Recode the conventional-meaning (agreeing-rule) baseline and its matched no-rule
responses with the ORIGINAL accepted-form inventory (data/coding/accepted_translations.csv),
so Appendix F agrees with Figure 2 / Section 3.3 (85.56%) and Appendix A's listed forms.

Usage (from the repository root): python3 <this file> OUTPUT_DIRECTORY
Inputs (read only): results/translation-quality/scores/{baseline,conventional_meaning}/<model>/literal_expected_en.csv
Validation: every recoded no-rule label must equal results/runs/baseline/<model>/responses_baseline_autocoded.csv.
Outputs: counts.csv, coding-audit.csv, table-rows.tex (Appendix F table body).
"""
import csv, sys, collections
from pathlib import Path
HERE = Path(__file__).resolve(); ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from code_english import EnglishLexicalCoder
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
MODELS = [('chatgpt5_5_instant','GPT-5.5'),('deepseek_llm_7b','DeepSeek-LLM-7B'),('deepseek_llm_67b','DeepSeek-LLM-67B'),
          ('gemma3_4b','Gemma-3-4B'),('gemma3_27b','Gemma-3-27B'),('llama3_8b','Llama-3-8B'),('llama3_70b','Llama-3-70B'),
          ('qwen3_8b','Qwen3-8B'),('qwen3_32b','Qwen3-32B')]
FR = ['F1','F2','F3','F4','F5']
def rd(p):
    with open(p, encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
coder = EnglishLexicalCoder.from_csv(ROOT/'data/coding/accepted_translations.csv')
SC = ROOT/'results/translation-quality/scores'
counts, audit, rows_tex = [], [], []
tot = collections.Counter()
for m, name in MODELS:
    base = [r for r in rd(SC/'baseline'/m/'literal_expected_en.csv') if r['baseline_type']=='normal_lexical']
    rule = rd(SC/'conventional_meaning'/m/'literal_expected_en.csv')
    assert len(base)==150 and len(rule)==750
    orig = {r['prompt_id']: r['baseline_label'] for r in rd(ROOT/f'results/runs/baseline/{m}/responses_baseline_autocoded.csv')}
    lab = {}
    for cond, rs in (('no_rule', base), ('agreeing_definition', rule)):
        for r in rs:
            c = coder.code(r); lab[(cond, r['prompt_id'])] = c['baseline_label']
            audit.append(dict(model=m, condition=cond, prompt_id=r['prompt_id'], source_item_id=r['source_item_id'],
                              frame_id=r.get('frame_id',''), label=c['baseline_label'], matched_forms=c['expected_matched_forms']))
    for r in base:
        assert lab[('no_rule', r['prompt_id'])] == orig[r['prompt_id']], (m, r['prompt_id'])
    nh = sum(lab[('no_rule', r['prompt_id'])]=='EXPECTED' for r in base)
    counts.append(dict(model=m, condition='no_rule', frame_id='', n=150, hits=nh, completed=150, percent=100*nh/150, completed_percent=100*nh/150))
    fr_pct = []
    for f in FR + ['All']:
        part = [r for r in rule if f=='All' or r['frame_id']==f]
        h = sum(lab[('agreeing_definition', r['prompt_id'])]=='EXPECTED' for r in part)
        comp = sum(lab[('agreeing_definition', r['prompt_id'])]!='FAILED' for r in part)
        counts.append(dict(model=m, condition='agreeing_definition', frame_id=f, n=len(part), hits=h, completed=comp,
                           percent=100*h/len(part), completed_percent=100*h/comp))
        fr_pct.append((h, comp, len(part)))
    tot['nh'] += nh; tot['n0'] += 150
    for i,f in enumerate(FR + ['All']):
        tot[f'h_{f}'] += fr_pct[i][0]; tot[f'c_{f}'] += fr_pct[i][1]; tot[f'n_{f}'] += fr_pct[i][2]
    allh, allc, alln = fr_pct[-1]
    rows_tex.append(f"{name} & {nh}/150 & {100*nh/150:.2f} & " + " & ".join(f"{100*h/n:.2f}" for h,c,n in fr_pct[:-1])
                    + f" & {100*allh/alln:.2f} & {100*allh/allc:.2f} \\\\")
rows_tex.append(r"\textbf{Pooled} & " + f"{tot['nh']}/{tot['n0']} & {100*tot['nh']/tot['n0']:.2f} & "
                + " & ".join(f"{100*tot[f'h_{f}']/tot[f'n_{f}']:.2f}" for f in FR)
                + f" & {100*tot['h_All']/tot['n_All']:.2f} & {100*tot['h_All']/tot['c_All']:.2f} \\\\")
for name, rows in (('counts.csv', counts), ('coding-audit.csv', audit)):
    with (OUT/name).open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
(OUT/'table-rows.tex').write_text("\n".join(rows_tex)+"\n", encoding='utf-8')
print("\n".join(rows_tex))
print(f"no-rule {tot['nh']}/{tot['n0']} = {100*tot['nh']/tot['n0']:.2f}; rule {tot['h_All']}/{tot['n_All']} = {100*tot['h_All']/tot['n_All']:.2f}; completed {tot['h_All']}/{tot['c_All']} = {100*tot['h_All']/tot['c_All']:.2f}")
