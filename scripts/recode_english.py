"""Recode saved English score CSVs; preserve prior files and every noncoding cell.

Usage: python recode_english.py SCORES_ROOT PREVIOUS_INVENTORY CURRENT_INVENTORY
Validates saved coding against the previous inventory before making changes.
Changed files are preserved at SCORES_ROOT/backups/<experiment>/<model>/<file>.
"""
from __future__ import annotations
import argparse
import csv
import os
import shutil
import tempfile
from collections import Counter
from pathlib import Path
from code_english import EnglishLexicalCoder


def recode(root: Path, previous: Path, current: Path) -> None:
    before=EnglishLexicalCoder.from_csv(previous)
    after=EnglishLexicalCoder.from_csv(current)
    inputs=sorted(root.glob('*/*/literal_*_en.csv'))
    if not inputs: raise ValueError('No English score files')
    transitions=Counter();rows_checked=0;files_changed=0
    for path in inputs:
        with path.open(encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
        if not rows: raise ValueError(f'Empty input: {path}')
        seen=set();changed=False
        for row in rows:
            if None in row or any(v is None for v in row.values()): raise ValueError(f'Malformed CSV: {path}')
            if not row['prompt_id'] or row['prompt_id'] in seen: raise ValueError(f'Duplicate/empty prompt identity: {path}')
            seen.add(row['prompt_id'])
            old,new=before.code(row),after.code(row)
            for key,value in old.items():
                if row.get(key)!=value: raise ValueError(f'Saved coding disagrees with previous inventory: {path} {row["prompt_id"]} {key}: {row.get(key)!r} != {value!r}')
            label='baseline_label' if 'baseline_label' in new else 'auto_label'
            if old[label]!=new[label]: transitions[(path.parts[-3],path.parts[-2],path.stem,old[label],new[label])]+=1
            if old!=new:
                row.update(new);changed=True
            rows_checked+=1
        if not changed: continue
        backup=root/'backups'/path.relative_to(root)
        if backup.exists(): raise FileExistsError(f'Backup already exists; inspect before repeating: {backup}')
        backup.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile('w',encoding='utf-8-sig',newline='',dir=path.parent,prefix='.recoding-',delete=False) as f:
            temp=Path(f.name);writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
        with path.open(encoding='utf-8-sig',newline='') as old_file,temp.open(encoding='utf-8-sig',newline='') as new_file:
            original=list(csv.DictReader(old_file));updated=list(csv.DictReader(new_file))
        assert len(original)==len(updated)
        for old_row,new_row in zip(original,updated):
            coding=set(after.code(old_row))
            assert {k:v for k,v in old_row.items() if k not in coding}=={k:v for k,v in new_row.items() if k not in coding}
        shutil.copy2(path,backup)
        os.replace(temp,path)
        files_changed+=1
        print(f'{path.relative_to(root)}: {len(rows)} rows checked; original at {backup}',flush=True)
    print(f'Checked {rows_checked} response/reference rows; {files_changed} files updated. All noncoding cells unchanged.')
    for key,n in sorted(transitions.items()): print('LABEL CHANGE',*key,n)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('scores_root',type=Path);p.add_argument('previous_inventory',type=Path);p.add_argument('current_inventory',type=Path)
    a=p.parse_args();recode(a.scores_root,a.previous_inventory,a.current_inventory)
