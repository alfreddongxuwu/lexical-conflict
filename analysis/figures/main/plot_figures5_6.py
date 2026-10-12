#!/usr/bin/env python3
"""Figures 5 and 6 in the second-draft three-panel layout, with the middle panel
showing lexical-rule position x repetition for all ten layouts.

Usage (from the repository root):
  python plot_figures5_6.py COUNTS_DIRECTORY OUTPUT_DIRECTORY
Reads saved counts only: results/summary/<condition>/unfiltered/*.csv for modal
weakening and reasoning (original study), and COUNTS_DIRECTORY/{pooled,model-summary}.csv
written by code_layouts.py (ten layouts, original inventory). Writes
figure5_followups_overall_effects.pdf, figure6_followups_condition_effects.pdf,
PNG previews and plotted-counts.csv. Requires matplotlib (not in the project venvs).
"""
import csv
import os
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from matplotlib.transforms import Bbox
import numpy as np

ROOT = Path(os.environ.get("LEXICAL_CONFLICT_ROOT", Path(__file__).resolve().parents[3]))
SRC = ROOT / 'results/summary'
COUNTS = Path(sys.argv[1])
OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)

MODELS = ['chatgpt5_5_instant', 'deepseek_llm_7b', 'deepseek_llm_67b', 'gemma3_4b',
          'gemma3_27b', 'llama3_8b', 'llama3_70b', 'qwen3_8b', 'qwen3_32b']
NAMES = {'chatgpt5_5_instant': 'GPT-5.5', 'deepseek_llm_7b': 'DeepSeek-7B',
         'deepseek_llm_67b': 'DeepSeek-67B', 'gemma3_4b': 'Gemma3-4B', 'gemma3_27b': 'Gemma3-27B',
         'llama3_8b': 'Llama3-8B', 'llama3_70b': 'Llama3-70B', 'qwen3_8b': 'Qwen3-8B',
         'qwen3_32b': 'Qwen3-32B'}
REASONING = [MODELS[i] for i in (0, 7, 8)]
SMALL = MODELS[1::2]; LARGE = MODELS[2::2]

MODAL = ['#956515', '#C59632', '#E8D39A']
GREEN = ['#66742F', '#98A75C', '#D0D7A5']
TEAL = ['#287D8E', '#5BA6B2', '#A9D8DE']
PINK = ['#BC9098', '#DFC0C5']
PURPLE = ['#9A879F', '#C7B6CD']

# Layout families by occupied positions: (layout key, label, copies)
FAMILIES = [('Middle only', [('main', 'M', 1), ('reiteration_2', 'M×2', 2), ('reiteration_3', 'M×3', 3), ('reiteration', 'M×5', 5)], GREEN[0], 'o'),
            ('Before + middle', [('position_B', 'B', 1), ('position_BM', 'BM', 2)], TEAL[0], 's'),
            ('Middle + after', [('position_E', 'E', 1), ('position_ME', 'ME', 2)], PINK[0], '^'),
            ('Before + after', [('position_BE', 'BE', 2), ('position_BME', 'BME', 3)], MODAL[0], 'D')]

plt.rcParams.update({'font.family': 'Liberation Sans', 'font.size': 9.2,
                     'pdf.fonttype': 42, 'axes.linewidth': .45})
PLOTTED = []


def read(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def pct(rows, n='n', k='n_ck'):
    return 100 * sum(int(r[k]) for r in rows) / sum(int(r[n]) for r in rows)


def by_model(cond, ids):
    rows = [r for r in read(SRC / cond / 'unfiltered/01_by_model.csv') if r['model_id'] in ids]
    return {m: pct([r for r in rows if r['model_id'] == m]) for m in ids}, pct(rows)


POOLED = {(r['group'], r['frame_id']): float(r['ck_percent']) for r in read(COUNTS / 'pooled.csv')}
BYMODEL = {(r['model'], r['layout']): float(r['ck_percent']) for r in read(COUNTS / 'model-summary.csv')}


def base_axes(ax):
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=2.5, width=.34)
    ax.set_ylabel('CK Rate (%)', fontsize=10.4)


def overlay_panel(ax, title, ids, ref, eff, ref_label, eff_label, palette):
    """Dashed outline = Experiment 1; gradient-filled bars = follow-up."""
    n = len(ids)
    for lab, d in ((ref_label, ref), (eff_label, eff)):
        PLOTTED.append(dict(figure='5', panel=title, series=lab, group='Overall', percent=d[1]))
        PLOTTED.extend(dict(figure='5', panel=title, series=lab, group=NAMES[m], percent=d[0][m]) for m in ids)
    cmap = LinearSegmentedColormap.from_list('p', palette)
    colors = [cmap(i / max(n - 1, 1)) for i in range(n)]
    x = np.arange(n) + 1.0
    ax.bar(x, [eff[0][m] for m in ids], .86, color=colors, lw=0)
    ax.bar(x, [ref[0][m] for m in ids], .86, fill=False, edgecolor='black', lw=.7, ls=(0, (3, 2)))
    xo = [-.38, .38]; yo = [ref[1], eff[1]]
    for xx, yy in zip(xo, yo):
        ax.plot([xx, xx], [0, yy], color='#A6A6A6', lw=.6, ls=(0, (3, 2)))
    segs = 36
    xs = np.linspace(xo[0], xo[1], segs + 1); ys = np.linspace(yo[0], yo[1], segs + 1)
    for i in range(segs):
        ax.plot(xs[i:i + 2], ys[i:i + 2], color=cmap(i / (segs - 1)), lw=1.3, solid_capstyle='round')
    ax.plot(xo[0], yo[0], 'o', ms=3.4, color=palette[0]); ax.plot(xo[1], yo[1], 'o', ms=3.4, color=palette[-1])
    ax.set_xticks([0] + list(x))
    ax.set_xticklabels(['Overall Effect'] + [NAMES[m] for m in ids], rotation=38, ha='right', fontsize=7.2)
    ax.get_xticklabels()[0].set_fontweight('bold')
    ax.set_xlim(-.75, n + .6); ax.set_ylim(0, 103); ax.set_yticks(range(0, 101, 20))
    ax.set_title(title, fontweight='bold', fontsize=12)
    base_axes(ax)
    handles = [Patch(facecolor='none', edgecolor='black', lw=.7, ls=(0, (3, 2)), label=ref_label),
               Patch(facecolor=palette[1], label=eff_label)]
    ax.legend(handles=handles, loc='lower right', fontsize=8.4, frameon=True, framealpha=.9,
              edgecolor='#A6A6A6', borderpad=.4, handlelength=1.4)


LAYOUT_BARS = [('reiteration_2', 'M×2', '#5A6628'), ('reiteration', 'M×5', '#7C8A42'),
               ('position_BM', 'BM', '#98A75C'), ('position_ME', 'ME', '#B9C48A'), ('position_BE', 'BE', '#D9DFB7')]


def grouped_layout_panel(ax, title):
    """Per model: several layouts as bars (dark to light green) inside the Experiment 1 (M)
    dashed outline; pooled slopes at the left from Experiment 1 to each layout."""
    n = len(MODELS); k = len(LAYOUT_BARS); x = np.arange(n) + 1.0
    width = .86 / k; offs = [(-.43 + width / 2) + i * width for i in range(k)]
    ref = {m: BYMODEL[(m, 'main')] for m in MODELS}; ref_all = POOLED[('main', 'All')]
    overall_x_left, overall_x_right = -.6, .1
    PLOTTED.append(dict(figure='5', panel=title, series='Experiment 1', group='Overall', percent=ref_all))
    PLOTTED.extend(dict(figure='5', panel=title, series='Experiment 1', group=NAMES[m], percent=ref[m]) for m in MODELS)
    for (key, lab, col), off in zip(LAYOUT_BARS, offs):
        vals = [BYMODEL[(m, key)] for m in MODELS]
        PLOTTED.append(dict(figure='5', panel=title, series=lab, group='Overall', percent=POOLED[(key, 'All')]))
        PLOTTED.extend(dict(figure='5', panel=title, series=lab, group=NAMES[m], percent=v) for m, v in zip(MODELS, vals))
        ax.bar(x + off, vals, width, color=col, lw=0, zorder=2)
        xe = overall_x_right
        ax.plot([overall_x_left, xe], [ref_all, POOLED[(key, 'All')]], color=col, lw=1.2, solid_capstyle='round', zorder=3)
        ax.plot(xe, POOLED[(key, 'All')], 'o', ms=3, color=col, zorder=4)
    # Match the outer panels: guides only below Exp1 and the lowest follow-up.
    lowest_followup = min(POOLED[(key, 'All')] for key, _, _ in LAYOUT_BARS)
    for guide_x, guide_y in [(overall_x_left, ref_all), (overall_x_right, lowest_followup)]:
        ax.plot([guide_x, guide_x], [0, guide_y], color='#A6A6A6', lw=.6,
                ls=(0, (3, 2)), zorder=1)
    ax.plot(overall_x_left, ref_all, 'o', ms=3.4, color='black', zorder=4)
    ax.bar(x, [ref[m] for m in MODELS], .86, fill=False, edgecolor='black', lw=.7, ls=(0, (3, 2)), zorder=3)
    ax.set_xticks([(overall_x_left + overall_x_right) / 2] + list(x))
    ax.set_xticklabels(['Overall Effect'] + [NAMES[m] for m in MODELS], rotation=38, ha='right', fontsize=7.2)
    ax.get_xticklabels()[0].set_fontweight('bold')
    ax.set_xlim(-.85, n + .6); ax.set_ylim(0, 103); ax.set_yticks(range(0, 101, 20))
    ax.set_title(title, fontweight='bold', fontsize=12)
    base_axes(ax)
    handles = [Patch(facecolor='none', edgecolor='black', lw=.7, ls=(0, (3, 2)), label='Experiment 1')]
    handles += [Patch(facecolor=col, label=lab) for key, lab, col in LAYOUT_BARS]
    ax.legend(handles=handles, loc='lower right', fontsize=7.8, ncol=3, frameon=True, framealpha=.92,
              edgecolor='#A6A6A6', borderpad=.4, handlelength=1.2, columnspacing=.9, labelspacing=.3)


def gradient_line(ax, xs, ys, palette, marker, ms=6.5, lw=1.3, zorder=3):
    cmap = LinearSegmentedColormap.from_list('g', palette)
    pts = np.linspace(0, 1, len(xs))
    for i in range(len(xs) - 1):
        xx = np.linspace(xs[i], xs[i + 1], 37); yy = np.linspace(ys[i], ys[i + 1], 37)
        for j in range(36):
            ax.plot(xx[j:j + 2], yy[j:j + 2], color=cmap(pts[i] + (pts[i + 1] - pts[i]) * j / 35), lw=lw, zorder=zorder)
    for xx, yy, p in zip(xs, ys, pts):
        ax.plot(xx, yy, marker=marker, ms=ms, mfc=cmap(p), mec='white', mew=.5, zorder=zorder + 1, ls='')


def finish_condition(ax, title, ylim=(30, 103), yticks=range(30, 101, 10)):
    ax.set_ylim(*ylim); ax.set_yticks(list(yticks))
    ax.yaxis.grid(True, color='#E8E8E8', lw=.5); ax.set_axisbelow(True)
    ax.set_title(title, fontweight='bold', fontsize=12)
    base_axes(ax)


def condition_panel(ax, title, cond, ids, include_size):
    series = []
    rows = [r for r in read(SRC / cond / 'unfiltered/03_by_frame.csv') if r['model_id'] in ids]
    series.append(('Frame', 'F1–F5', [1, 2, 3, 4, 5],
                   [pct([r for r in rows if r['frame_id'] == f]) for f in ['F1', 'F2', 'F3', 'F4', 'F5']], MODAL, 'o'))
    rows = [r for r in read(SRC / cond / 'unfiltered/04_by_source_frequency.csv') if r['model_id'] in ids]
    series.append(('Source Freq', 'High–Low', [1, 3, 5],
                   [pct([r for r in rows if r['source_freq_band'] == b]) for b in ['high', 'medium', 'low']], GREEN, '^'))
    rows = [r for r in read(SRC / cond / 'unfiltered/05_by_target_frequency.csv') if r['model_id'] in ids]
    series.append(('Target Freq', 'High–Low', [1, 3, 5],
                   [pct([r for r in rows if r['target_freq_band'] == b]) for b in ['high', 'medium', 'low']], TEAL, 's'))
    if include_size:
        rows = read(SRC / cond / 'unfiltered/01_by_model.csv')
        series.append(('Model Size', 'Small–Large', [1, 5],
                       [pct([r for r in rows if r['model_id'] in SMALL]), pct([r for r in rows if r['model_id'] in LARGE])], PINK, 'D'))
    rows = [r for r in read(SRC / cond / 'unfiltered/02_by_context_type.csv') if r['model_id'] in ids]
    series.append(('Context', 'PK–CK', [1, 5],
                   [pct([r for r in rows if r['context_type'] == c]) for c in ['PK_context', 'CK_context']], PURPLE, 'v'))
    for name, rng, xs, ys, pal, mk in series:
        PLOTTED.extend(dict(figure='6', panel=title, series=f'{name} {rng}', group=x, percent=y) for x, y in zip(xs, ys))
        gradient_line(ax, xs, ys, pal, mk)
    handles = [Line2D([], [], marker=mk, ms=5, mfc=pal[0], mec=pal[0], ls='', label=f'{name} {rng}')
               for name, rng, xs, ys, pal, mk in series]
    ax.legend(handles=handles, loc='lower right', fontsize=7.6, frameon=True, framealpha=.9, edgecolor='#A6A6A6',
              borderpad=.4, handletextpad=.3, labelspacing=.25)
    ax.set_xlim(.72, 5.28); ax.set_xticks([])
    finish_condition(ax, title)


def layout_frame_panel(ax, title):
    """Pooled CK by frame F1-F5 for all ten layouts: middle-only layouts in greens,
    layouts with a before/after copy in ochres; marker shape = number of copies."""
    gcm = LinearSegmentedColormap.from_list('g', ['#C9D29A', '#4F5A22'])
    ocm = LinearSegmentedColormap.from_list('o', ['#E8C98A', '#7A4F0E'])
    mk = {1: 'o', 2: 's', 3: '^', 5: 'D'}
    layouts = [('main', 'M', 1, gcm(0.0)), ('reiteration_2', 'M×2', 2, gcm(.33)), ('reiteration_3', 'M×3', 3, gcm(.66)),
               ('reiteration', 'M×5', 5, gcm(1.0)), ('position_B', 'B', 1, ocm(0.0)), ('position_E', 'E', 1, ocm(.2)),
               ('position_BM', 'BM', 2, ocm(.4)), ('position_ME', 'ME', 2, ocm(.6)), ('position_BE', 'BE', 2, ocm(.8)),
               ('position_BME', 'BME', 3, ocm(1.0))]
    xs = [1, 2, 3, 4, 5]; handles = []
    for key, lab, copies, col in layouts:
        ys = [POOLED[(key, f'F{i}')] for i in xs]
        PLOTTED.extend(dict(figure='6', panel=title, series=lab, group=f'F{i}', percent=y) for i, y in zip(xs, ys))
        ax.plot(xs, ys, color=col, marker=mk[copies], ms=5, mfc=col, mec='white', mew=.5, lw=1.2, zorder=3)
        handles.append(Line2D([], [], color=col, marker=mk[copies], ms=4.5, mfc=col, mec=col, lw=1.2, label=lab))
    ax.legend(handles=handles, loc='lower right', fontsize=7.2, ncol=2, frameon=True, framealpha=.92, edgecolor='#A6A6A6',
              borderpad=.4, handletextpad=.4, labelspacing=.2, columnspacing=.9)
    ax.set_xlim(.72, 5.28); ax.set_xticks(xs); ax.set_xticklabels(['F1', 'F2', 'F3', 'F4', 'F5'], fontsize=8)
    finish_condition(ax, title)


# ---------------- Figure 5 ----------------
fig = plt.figure(figsize=(12.2, 3.1))
fig.suptitle('Follow-up Experiments: Overall Effects', fontweight='bold', fontsize=14, y=.995)
gs = fig.add_gridspec(1, 3, width_ratios=[4.2, 5.4, 2.6], left=.045, right=.995, top=.84, bottom=.27, wspace=.26)
axs = [fig.add_subplot(gs[0, i]) for i in range(3)]
overlay_panel(axs[0], 'Modal Weakening', MODELS, by_model('exp1', MODELS), by_model('may_mean', MODELS),
              'Experiment 1', 'Modal Weakening', MODAL)
grouped_layout_panel(axs[1], 'Reiteration and Position')
overlay_panel(axs[2], 'Reasoning', REASONING, by_model('exp1', REASONING), by_model('thinking_on', REASONING),
              'Experiment 1', 'With Reasoning', TEAL)
# Trim 3 mm from the bottom, below the rotated model labels.
figure5_trim_in = 3.0 / 25.4
figure5_export_box = Bbox.from_extents(0, figure5_trim_in, 12.2, 3.1)
fig.savefig(OUT / 'figure5_followups_overall_effects.pdf', bbox_inches=figure5_export_box, pad_inches=0)
fig.savefig(OUT / 'figure5_followups_overall_effects.png', dpi=110, bbox_inches=figure5_export_box, pad_inches=0)
plt.close(fig)

# ---------------- Figure 6 ----------------
fig = plt.figure(figsize=(12.2, 3.1))
fig.suptitle('Follow-up Experiments: Condition Effects', fontweight='bold', fontsize=14, y=.995)
gs = fig.add_gridspec(1, 3, left=.045, right=.995, top=.84, bottom=.14, wspace=.25)
axs = [fig.add_subplot(gs[0, i]) for i in range(3)]
condition_panel(axs[0], 'Modal Weakening', 'may_mean', MODELS, True)
layout_frame_panel(axs[1], 'Reiteration and Position')
condition_panel(axs[2], 'Reasoning', 'thinking_on', REASONING, False)
# Trim 3.5 mm in total from the bottom, below the F1-F5 labels.
figure6_trim_in = 3.5 / 25.4
figure6_export_box = Bbox.from_extents(0, figure6_trim_in, 12.2, 3.1)
fig.savefig(OUT / 'figure6_followups_condition_effects.pdf', bbox_inches=figure6_export_box, pad_inches=0)
fig.savefig(OUT / 'figure6_followups_condition_effects.png', dpi=110, bbox_inches=figure6_export_box, pad_inches=0)
plt.close(fig)
with (OUT / 'plotted-counts.csv').open('w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(PLOTTED[0])); w.writeheader(); w.writerows(PLOTTED)
print('done', OUT)
