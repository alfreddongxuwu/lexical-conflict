#!/usr/bin/env python3
"""Code all ten lexical-rule layouts with the ORIGINAL accepted-form inventory and
baseline-filter them with the ORIGINAL screening labels, so every number matches
the manuscript's Experiment 1 and reiteration analyses exactly.

Usage (from the repository root):
  python scripts/summarize_rule_layouts_original.py OUTPUT_DIRECTORY

Inputs (read only): results/translation-quality/scores/<layout>/<model>/literal_pk_en.csv
(saved responses; the saved auto_label column is ignored and recoded),
data/coding/accepted_translations.csv (original inventory, byte-identical to data/coding/backups/),
results/runs/baseline/<model>/responses_baseline_autocoded.csv (original Familiar labels).
Validation: for M and M×5 every model/frame/context cell must equal the original study's
results/runs/{main,reiteration}/<model>/responses_autocoded.csv labels, and the filtered M
sample must equal the manuscript's 42,270.
Outputs: layout-summary.csv (900 cells), pooled.csv, model-summary.csv, and the same three
for the baseline-filtered data (prefix filtered-).
"""
import csv, sys, collections
from pathlib import Path
HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from code_english import EnglishLexicalCoder
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
MODELS = ['chatgpt5_5_instant','deepseek_llm_7b','deepseek_llm_67b','gemma3_4b','gemma3_27b',
          'llama3_8b','llama3_70b','qwen3_8b','qwen3_32b']
LAYOUTS = ['position_B','main','position_E','reiteration_2','position_BM','position_BE',
           'position_ME','reiteration_3','position_BME','reiteration']
ORIGINAL_RUN = {'main': 'main', 'reiteration': 'reiteration'}
FRAMES = ['F1','F2','F3','F4','F5']
def rd(p):
    with open(p, encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
coder = EnglishLexicalCoder.from_csv(ROOT/'data/coding/accepted_translations.csv')
full = collections.defaultdict(collections.Counter); filt = collections.defaultdict(collections.Counter)
for m in MODELS:
    base = {(r['source_item_id'], r['context_category']): r['baseline_label']
            for r in rd(ROOT/f'results/runs/baseline/{m}/responses_baseline_autocoded.csv')}
    assert len(base) == 750
    for g in LAYOUTS:
        rows = rd(ROOT/f'results/translation-quality/scores/{g}/{m}/literal_pk_en.csv')
        assert len(rows) == 6000
        labels = {r['prompt_id']: coder.code(r)['auto_label'] for r in rows}
        if g in ORIGINAL_RUN:
            orig = {r['prompt_id']: r['auto_label'] for r in rd(ROOT/f'results/runs/{ORIGINAL_RUN[g]}/{m}/responses_autocoded.csv')}
            assert orig == labels, (m, g, 'recoding differs from the original study')
        for r in rows:
            lab = labels[r['prompt_id']]
            keep = base[(r['source_item_id'], r['context_category'])] == 'EXPECTED'
            for store, ok in ((full, True), (filt, keep)):
                if ok:
                    store[(g, m, r['frame_id'], r['context_type'])][lab] += 1
    print(m, 'coded and validated', flush=True)
def cell(c):
    return dict(n=sum(c.values()), ck_n=c['CK'], inclusive_n=c['CK']+c['BOTH'], pk_n=c['PK'],
                both_n=c['BOTH'], other_n=c['OTHER'], failed_n=c['FAILED'])
def write(name, rows):
    with (OUT/name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
for prefix, store in (('', full), ('filtered-', filt)):
    cells = [dict(group=g, model_key=m, frame_id=fr, context_type=ct, **cell(store[(g, m, fr, ct)]))
             for g in LAYOUTS for m in MODELS for fr in FRAMES for ct in ('PK_context', 'CK_context')]
    assert len(cells) == 900
    pooled, by_model = [], []
    for g in LAYOUTS:
        for fr in ['All'] + FRAMES:
            c = sum((store[k] for k in store if k[0] == g and (fr == 'All' or k[2] == fr)), collections.Counter())
            d = cell(c); pooled.append(dict(group=g, frame_id=fr, **d, ck_percent=100*d['ck_n']/d['n'],
                                            inclusive_percent=100*d['inclusive_n']/d['n']))
        for m in MODELS:
            c = sum((store[k] for k in store if k[0] == g and k[1] == m), collections.Counter())
            d = cell(c); by_model.append(dict(model=m, layout=g, **d, ck_percent=100*d['ck_n']/d['n'],
                                              inclusive_percent=100*d['inclusive_n']/d['n']))
    if prefix:
        assert all(r['n'] == 42270 for r in pooled if r['frame_id'] == 'All')
    else:
        assert all(r['n'] == 54000 for r in pooled if r['frame_id'] == 'All')
    write(prefix+'layout-summary.csv', cells); write(prefix+'pooled.csv', pooled); write(prefix+'model-summary.csv', by_model)
print('wrote', OUT)
