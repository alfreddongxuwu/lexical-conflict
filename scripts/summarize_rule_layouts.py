#!/usr/bin/env python3
"""Recode nine-model paper layouts, validate matched inputs, export counts.

Usage: python summarize_paper_layouts.py NEW_OUTPUT_DIRECTORY
No generation or scoring. Saved responses and historical screening labels stay
unchanged. Current-inventory and saved-label screening are exported separately.
"""
import argparse
import csv
import hashlib
from collections import Counter, defaultdict
from pathlib import Path
from code_english import EnglishLexicalCoder
from summarize_agreeing_baseline import MODELS

ROOT = Path(__file__).resolve().parents[1]
LAYOUTS = ['position_B', 'main', 'position_E', 'reiteration_2', 'position_BM',
           'position_BE', 'position_ME', 'reiteration_3', 'position_BME', 'reiteration']
IDENTITY = ['mapping_id', 'frame_id', 'context_type', 'context_category',
            'source_item_id', 'target_item_id', 'source_sentence_zh',
            'literal_pk_en', 'literal_ck_en', 'source_freq_band', 'target_freq_band']


def write(path, rows):
    with path.open('x', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output_dir', type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    manifest = {}
    def read(path):
        manifest[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        with path.open(encoding='utf-8-sig', newline='') as f:
            return list(csv.DictReader(f))
    inventory = ROOT/'data/coding/accepted_translations_en.csv'
    read(inventory)
    coder = EnglishLexicalCoder.from_csv(inventory)
    historical = {(r['group'], r['model_key'], r['frame_id'], r['context_type']): r
                  for r in read(ROOT/'results/rule-position/report/eight-model/layout-summary.csv')}
    assert len(historical) == 800
    prompts = {g: {r['prompt_id']: r for r in read(ROOT/f'data/processed/prompts_{g}.csv')}
               for g in LAYOUTS if g not in ('main', 'reiteration')}
    cells, coverage, screened, changed, examples = [], [], [], [], []
    score_root = ROOT/'results/translation-quality/scores'
    for model in MODELS:
        baseline = read(score_root/'baseline'/model/'literal_expected_en.csv')
        bases = {(r['source_item_id'], r['context_category']): r for r in baseline}
        assert len(bases) == len(baseline) == 750
        for row in bases.values():
            row['current_baseline_label'] = coder.code(row)['baseline_label']
        anchor = None
        paired = {}
        for group in ['main'] + [g for g in LAYOUTS if g != 'main']:
            rows = read(score_root/group/model/'literal_pk_en.csv')
            keyed = {r['prompt_id']: r for r in rows}
            assert len(rows) == len(keyed) == 6000, (model, group)
            identities = {k: tuple(r[c] for c in IDENTITY) for k, r in keyed.items()}
            if anchor is None:
                anchor = identities
            assert identities == anchor, (model, group, 'input mismatch')
            assert Counter((r['frame_id'], r['context_type']) for r in rows) == Counter(
                {(f'F{i}', c): 600 for i in range(1,6) for c in ('PK_context','CK_context')})
            counts = defaultdict(Counter)
            for row in rows:
                if group in prompts:
                    p = prompts[group][row['prompt_id']]
                    assert all(row[c] == p[c] for c in IDENTITY + ['prompt']), (model, group, row['prompt_id'])
                base = bases[(row['source_item_id'], row['context_category'])]
                assert row['source_sentence_zh'] == base['source_sentence_zh']
                assert row['literal_pk_en'] == base['literal_expected_en']
                code = coder.code(row)
                label = code['auto_label']
                counts[(row['frame_id'], row['context_type'])][label] += 1
                if label != row['auto_label']:
                    changed.append(dict(group=group, model=model, prompt_id=row['prompt_id'],
                                        saved=row['auto_label'], current=label))
                if group in ('reiteration_2', 'position_BE'):
                    paired[(group, row['prompt_id'])] = (label, base['baseline_label'], base['current_baseline_label'])
                if model == MODELS[0] and row['prompt_id'] == 'prompt_000049':
                    examples.append(dict(group=group, prompt_id=row['prompt_id'], prompt=row['prompt']))
            for (frame, context), c in sorted(counts.items()):
                item = dict(group=group, model_key=model, frame_id=frame, context_type=context,
                            n=sum(c.values()), ck_n=c['CK'], inclusive_n=c['CK']+c['BOTH'],
                            pk_n=c['PK'], both_n=c['BOTH'], other_n=c['OTHER'], failed_n=c['FAILED'])
                key = (group, model, frame, context)
                if model != MODELS[0]:
                    old = historical[key]
                    assert all(int(old[k]) == item[k] for k in ['n','ck_n','inclusive_n']), key
                cells.append(item)
            totals = sum(counts.values(), Counter())
            coverage.append(dict(group=group, model=model, n=len(rows), complete=len(rows)-totals['FAILED'],
                                 failed=totals['FAILED'], empty=sum(not r['response'].strip() for r in rows)))
        for screening, idx in [('saved_baseline_labels', 1), ('current_inventory', 2)]:
            for frame in ['All'] + [f'F{i}' for i in range(1,6)]:
                ids = [pid for pid, identity in anchor.items() if frame == 'All' or identity[1] == frame]
                ids = [pid for pid in ids if paired[('reiteration_2',pid)][idx] == 'EXPECTED']
                assert all(paired[('position_BE',pid)][idx] == 'EXPECTED' for pid in ids)
                for group in ['reiteration_2','position_BE']:
                    c = Counter(paired[(group,pid)][0] for pid in ids)
                    screened.append(dict(screening=screening, model=model, frame_id=frame, group=group,
                                         n=len(ids), ck_n=c['CK'], inclusive_n=c['CK']+c['BOTH'], failed_n=c['FAILED']))
        print(model, 'validated', flush=True)
    assert len(cells) == 900
    write(args.output_dir/'layout-summary.csv', cells)
    write(args.output_dir/'coverage.csv', coverage)
    write(args.output_dir/'screened-comparison.csv', screened)
    write(args.output_dir/'exact-prompts.csv', examples)
    write(args.output_dir/'input-sha256.csv', [dict(path=p, sha256=h) for p,h in manifest.items()])
    if changed:
        write(args.output_dir/'coding-changes.csv', changed)
    pooled = []
    for group in LAYOUTS:
        for frame in ['All']+[f'F{i}' for i in range(1,6)]:
            part = [r for r in cells if r['group']==group and (frame=='All' or r['frame_id']==frame)]
            totals = {k:sum(r[k] for r in part) for k in ['n','ck_n','inclusive_n','pk_n','both_n','other_n','failed_n']}
            pooled.append(dict(group=group, frame_id=frame, **totals,
                               ck_percent=100*totals['ck_n']/totals['n'],
                               inclusive_percent=100*totals['inclusive_n']/totals['n']))
    write(args.output_dir/'pooled.csv', pooled)
    print('900 cells; 800 existing open-model cells reproduced; recoding changes:', len(changed))
    for r in pooled:
        if r['frame_id']=='All': print(r['group'], r['ck_n'], r['n'], round(r['ck_percent'],4), 'failed', r['failed_n'])

if __name__ == '__main__':
    main()
