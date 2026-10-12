#!/usr/bin/env python3
"""Plot the paper follow-ups from saved counts (no model computation).

Usage: python plot_paper_followups.py NEW_OUTPUT_DIRECTORY
Keeps modal/reasoning populations unchanged. Defaults to the historical eight-model
layout summary; --layout-summary accepts a validated nine-model export.
Refuses to overwrite any output directory.
"""
import argparse
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'results/summary'
MODELS = ['chatgpt5_5_instant', 'deepseek_llm_7b', 'deepseek_llm_67b', 'gemma3_4b',
          'gemma3_27b', 'llama3_8b', 'llama3_70b', 'qwen3_8b', 'qwen3_32b']
NAMES = ['GPT-5.5', 'DeepSeek 7B', 'DeepSeek 67B', 'Gemma 4B', 'Gemma 27B',
         'Llama 8B', 'Llama 70B', 'Qwen 8B', 'Qwen 32B']
REASONING = [MODELS[i] for i in (0, 7, 8)]
LAYOUTS = ['position_B', 'main', 'position_E', 'reiteration_2', 'position_BM',
           'position_BE', 'position_ME', 'reiteration_3', 'position_BME', 'reiteration']
LABELS = ['B', 'M', 'E', 'M×2', 'BM', 'BE', 'ME', 'M×3', 'BME', 'M×5']


def read(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def rate(rows, hit='n_ck'):
    assert rows
    return 100 * sum(int(r[hit]) for r in rows) / sum(int(r['n']) for r in rows)


def summary(condition, filename, ids):
    rows = [r for r in read(SOURCE / condition / 'unfiltered' / filename) if r['model_id'] in ids]
    assert set(r['model_id'] for r in rows) == set(ids)
    return rows


def style(ax):
    ax.set_ylim(0, 105); ax.set_yticks(range(0, 101, 20))
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.set_axisbelow(True); ax.grid(axis='y', color='#e4e4e4', linewidth=.5)
    ax.set_ylabel('CK-only responses (%)')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output_dir', type=Path)
    parser.add_argument('--layout-summary', type=Path, default=ROOT/'results/rule-position/report/eight-model/layout-summary.csv')
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    plt.rcParams.update({'font.size': 9, 'axes.titlesize': 10, 'pdf.fonttype': 42})
    plotted = []
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.1), gridspec_kw={'width_ratios': [2, 1]}, constrained_layout=True)
    conditions = [('may_mean', 'Modal weakening', MODELS, '#956515', '#E8D39A'),
                  ('thinking_on', 'Explicit reasoning', REASONING, '#287D8E', '#A9D8DE')]
    for ax, (condition, title, ids, dark, light) in zip(axes, conditions):
        x = np.arange(len(ids)+1)
        for offset, cond, label, color in [(-.19, 'exp1', 'Experiment 1', dark), (.19, condition, title, light)]:
            rows = summary(cond, '01_by_model.csv', ids)
            parts = [rows]+[[r for r in rows if r['model_id']==m] for m in ids]
            values = [rate(p) for p in parts]
            for group, part in zip(['Overall']+ids, parts):
                plotted.append(dict(figure='overall', condition=cond, group=group, population=condition,
                                    n=sum(int(r['n']) for r in part), ck_n=sum(int(r['n_ck']) for r in part), percent=rate(part)))
            ax.bar(x+offset, values, .37, label=label, color=color, edgecolor=dark, linewidth=.5)
        ax.set_xticks(x); ax.set_xticklabels(['Overall']+[NAMES[MODELS.index(m)] for m in ids], rotation=50, ha='right', fontsize=7)
        ax.set_title(title, fontweight='bold', pad=26); style(ax)
        ax.legend(fontsize=7, loc='lower left', bbox_to_anchor=(0, 1.01), ncol=2, frameon=False, borderaxespad=0)
    fig.savefig(args.output_dir/'figure5_followups_overall_effects.pdf'); plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.0), constrained_layout=True)
    series = [('03_by_frame.csv','frame_id',['F1','F2','F3','F4','F5'],'Frame: F1–F5','#956515','o'),
              ('04_by_source_frequency.csv','source_freq_band',['high','medium','low'],'Source frequency: high–low','#66742F','^'),
              ('05_by_target_frequency.csv','target_freq_band',['high','medium','low'],'Target proxy: high–low','#287D8E','s'),
              ('02_by_context_type.csv','context_type',['PK_context','CK_context'],'Context: PK–CK','#9A879F','v')]
    for ax, (condition,title,ids,_,_) in zip(axes,conditions):
        for filename,key,levels,label,color,marker in series:
            rows = summary(condition, filename, ids)
            parts = [[r for r in rows if r[key]==v] for v in levels]
            for level,part in zip(levels,parts):
                plotted.append(dict(figure='conditions', condition=condition, group=key+':'+level, population=condition,
                                    n=sum(int(r['n']) for r in part), ck_n=sum(int(r['n_ck']) for r in part), percent=rate(part)))
            ax.plot(np.linspace(1,5,len(levels)),[rate(p) for p in parts],label=label,color=color,marker=marker,lw=1,ms=4)
        if condition=='may_mean':
            rows=summary(condition,'01_by_model.csv',MODELS)
            parts=[[r for r in rows if r['model_id'] in MODELS[start::2]] for start in (1,2)]
            ax.plot([1,5],[rate(p) for p in parts],label='Model size: small–large',color='#BC9098',marker='D',lw=1,ms=4)
            for level,part in zip(['small','large'],parts):
                plotted.append(dict(figure='conditions',condition=condition,group='size:'+level,population=condition,
                                    n=sum(int(r['n']) for r in part),ck_n=sum(int(r['n_ck']) for r in part),percent=rate(part)))
        style(ax); ax.set_xticks(range(1,6)); ax.set_xlabel('Ordered level (see legend)')
        ax.set_title(title,fontweight='bold'); ax.legend(fontsize=6.8,loc='lower left',framealpha=.95)
    fig.savefig(args.output_dir/'figure6_followups_condition_effects.pdf'); plt.close(fig)

    rows=read(args.layout_summary)
    present={r['model_key'] for r in rows}
    assert present in (set(MODELS), set(MODELS[1:]))
    population='nine_models' if present==set(MODELS) else 'eight_open_models'
    keys={(r['group'],r['model_key'],r['frame_id'],r['context_type']) for r in rows}
    expected={(g,m,f'F{f}',c) for g in LAYOUTS for m in present for f in range(1,6) for c in ['PK_context','CK_context']}
    assert len(rows)==len(keys)==100*len(present) and keys==expected
    assert all(int(r['n'])==600 and 0<=int(r['ck_n'])<=int(r['inclusive_n'])<=600 for r in rows)
    fig,axes=plt.subplots(1,5,figsize=(7.4,3.55),sharey=True,constrained_layout=True)
    xs=[0,1,2, 4,5,6,7, 9,10, 12]
    for i,ax in enumerate(axes,1):
        values=[]
        for layout in LAYOUTS:
            part=[r for r in rows if r['group']==layout and r['frame_id']==f'F{i}']
            values.append(rate(part,'ck_n'))
            plotted.append(dict(figure='layouts',condition=layout,group=f'F{i}',population=population,
                                n=sum(int(r['n']) for r in part),ck_n=sum(int(r['ck_n']) for r in part),percent=rate(part,'ck_n')))
        # Horizontal facets keep all ten labels readable at manuscript width.
        for a,b in [(-.5,2.5),(8.5,10.5)]: ax.axhspan(a,b,color='#f0f0f0',zorder=0)
        colors=['#287D8E' if g in ['main','reiteration_2','reiteration_3','reiteration'] else '#956515' for g in LAYOUTS]
        ax.scatter(values,xs,c=colors,s=24,zorder=3)
        ax.set_xlim(0,100); ax.set_xticks([0,50,100]); ax.set_xlabel('CK (%)')
        ax.set_title(f'F{i}\n'+('Ignore rule' if i==1 else 'Use supplied'),fontweight='bold',fontsize=9)
        ax.set_yticks(xs); ax.set_yticklabels(LABELS); ax.tick_params(axis='y',length=0)
        ax.grid(axis='x',color='#dedede',lw=.5); ax.set_axisbelow(True)
        for spine in ax.spines.values(): spine.set_visible(False)
    axes[0].set_ylim(12.7,-.7)
    axes[0].set_ylabel('Layout (grouped by 1, 2, 3, 5 copies)')
    fig.savefig(args.output_dir/'figure7_position_repetition.pdf'); plt.close(fig)
    with (args.output_dir/'plotted-counts.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(plotted[0])); writer.writeheader();writer.writerows(plotted)
    print(f'Wrote three figures and {len(plotted)} plotted aggregates to {args.output_dir}')


if __name__=='__main__':
    main()
