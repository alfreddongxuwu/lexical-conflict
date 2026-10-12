"""Score a saved response tree locally into a fresh destination."""
import argparse, subprocess, sys
from pathlib import Path
from paths import project_path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-root',default='results/runs')
    parser.add_argument('--output-root',required=True)
    parser.add_argument('--no-comet',action='store_true')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    source=project_path(args.input_root);target=project_path(args.output_root)
    files=sorted(p for p in source.rglob('*.csv') if p.name in ['responses_autocoded.csv','responses_baseline_autocoded.csv'])
    if not files:parser.error('No coded response CSVs found')
    tasks=[]
    for path in files:
        relative=path.relative_to(source)
        if len(relative.parts)!=3:parser.error(f'Expected experiment/model/response.csv: {relative}')
        output=target/relative.parent
        if output.exists():parser.error(f'Output already exists: {output}')
        command=[sys.executable,str(Path(__file__).with_name('score_translations.py')),str(path),str(output)]
        if args.no_comet:command.append('--no-comet')
        tasks.append(command)
    for command in tasks:
        if args.dry_run:print(' '.join(command))
        else:subprocess.run(command,check=True)
    print(f'{len(tasks)} inputs ' + ('previewed' if args.dry_run else 'scored'))

if __name__=='__main__':main()
