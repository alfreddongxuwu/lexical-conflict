"""Check saved local agreeing-definition responses without API calls."""
import argparse, csv, os
from collections import Counter
from pathlib import Path
PROJECT_ROOT=Path(__file__).resolve().parents[1]
DEFAULT_RUN=PROJECT_ROOT/'outputs/runs/conventional_meaning/chatgpt5_5_instant'
PROMPTS=PROJECT_ROOT/'data/processed/prompts_conventional_meaning.csv'

def read_rows(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:
        rows=list(csv.DictReader(stream))
    if any(None in r or any(v is None for v in r.values()) for r in rows):raise ValueError('Malformed CSV')
    return rows

def check(stage,run_dir,prompts_path=PROMPTS):
    prompts=read_rows(prompts_path)
    if len(prompts)!=750 or len({r['prompt_id'] for r in prompts})!=750:raise ValueError('Expected 750 unique prompts')
    rows=read_rows(Path(run_dir)/'responses_merged.csv')
    if len({r['prompt_id'] for r in rows})!=len(rows):raise ValueError('Duplicate prompt IDs')
    ids={r['prompt_id'] for r in (prompts[:75] if stage=='first' else prompts)}
    original={r['prompt_id']:r for r in prompts}
    if not set(r['prompt_id'] for r in rows)<=set(original):raise ValueError('Unknown prompt IDs')
    selected=[r for r in rows if r['prompt_id'] in ids]
    if {r['prompt_id'] for r in selected}!=ids:raise ValueError('Missing prompt IDs')
    for row in selected:
        if row.get('status')!='ok' or row.get('openai_status')!='completed' or not row.get('response','').strip():raise ValueError('Incomplete or empty response')
        if any(row.get(k)!=v for k,v in original[row['prompt_id']].items()):raise ValueError('Changed prompt contents')
        if row.get('model')!='gpt-5.5' or row.get('reasoning_effort')!='none' or row.get('max_output_tokens')!='128':raise ValueError('Changed generation settings')
    frames=Counter(r['frame_id'] for r in selected)
    expected=15 if stage=='first' else 150
    if frames!=Counter({f'F{i}':expected for i in range(1,6)}):raise ValueError('Frame coverage mismatch')
    print(f'Validated {len(selected)} complete responses; no API calls were made.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['first','all'])
    parser.add_argument('--run-dir',type=Path,default=Path(os.environ.get('GPT_BASELINE_RUN',str(DEFAULT_RUN))))
    args=parser.parse_args()
    try:check(args.stage,args.run_dir)
    except (ValueError,OSError,KeyError) as error:parser.exit(1,f'Check failed: {error}\n')

if __name__=='__main__':main()
