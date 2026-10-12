#!/usr/bin/env python3
"""Recode all nine agreeing/no-rule comparisons with the current inventory.

Usage: python summarize_agreeing_baseline.py NEW_OUTPUT_DIRECTORY
Writes counts and a compact per-response coding audit; saved scores stay untouched.
"""
import argparse
import csv
from collections import Counter
from pathlib import Path

from code_english import EnglishLexicalCoder

ROOT = Path(__file__).resolve().parents[1]
MODELS = ('chatgpt5_5_instant', 'deepseek_llm_7b', 'deepseek_llm_67b',
          'gemma3_4b', 'gemma3_27b', 'llama3_8b', 'llama3_70b', 'qwen3_8b', 'qwen3_32b')


def read(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def summarize():
    coder = EnglishLexicalCoder.from_csv(ROOT / 'data/coding/accepted_translations_en.csv')
    counts, audit = [], []
    for model in MODELS:
        score_root = ROOT / 'results/translation-quality/scores'
        baseline = [r for r in read(score_root / 'baseline' / model / 'literal_expected_en.csv')
                    if r['baseline_type'] == 'normal_lexical']
        rule = read(score_root / 'conventional_meaning' / model / 'literal_expected_en.csv')
        assert len(baseline) == 150 and len(rule) == 750, model
        by_item = {r['source_item_id']: r for r in baseline}
        assert len(by_item) == 150 and len({r['prompt_id'] for r in rule}) == 750, model
        assert Counter(r['frame_id'] for r in rule) == Counter({f'F{i}': 150 for i in range(1, 6)}), model
        assert len({(r['source_item_id'], r['frame_id']) for r in rule}) == 750, model
        for row in rule:
            base = by_item[row['source_item_id']]
            for field in ('source_sentence_zh', 'literal_expected_en'):
                assert row[field] == base[field], (model, row['prompt_id'], field)
        for condition, rows in [('no_rule', baseline), ('agreeing_definition', rule)]:
            for row in rows:
                code = coder.code(row)
                audit.append(dict(model=model, condition=condition, prompt_id=row['prompt_id'],
                                  source_item_id=row['source_item_id'], frame_id=row.get('frame_id', ''),
                                  label=code['baseline_label'], matched_forms=code['expected_matched_forms']))
            frames = [''] if condition == 'no_rule' else [f'F{i}' for i in range(1, 6)] + ['All']
            for frame in frames:
                part = [a for a in audit if a['model'] == model and a['condition'] == condition
                        and (frame in ('', 'All') or a['frame_id'] == frame)]
                n, hits = len(part), sum(a['label'] == 'EXPECTED' for a in part)
                completed = sum(a['label'] != 'FAILED' for a in part)
                counts.append(dict(model=model, condition=condition, frame_id=frame, n=n,
                                   hits=hits, completed=completed, percent=100*hits/n,
                                   completed_percent=100*hits/completed))
    return counts, audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output_dir', type=Path)
    args = parser.parse_args()
    counts, audit = summarize()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    for name, rows in [('counts.csv', counts), ('coding-audit.csv', audit)]:
        with (args.output_dir/name).open('x', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)
    for condition, frame in [('no_rule', ''), ('agreeing_definition', 'All')]:
        rows = [r for r in counts if r['condition'] == condition and r['frame_id'] == frame]
        n, hits, complete = (sum(r[k] for r in rows) for k in ('n', 'hits', 'completed'))
        print(f'{condition}: {hits}/{n} ({100*hits/n:.2f}%); completed {hits}/{complete} ({100*hits/complete:.2f}%)')


if __name__ == '__main__':
    main()
