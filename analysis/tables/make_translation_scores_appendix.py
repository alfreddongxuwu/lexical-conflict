#!/usr/bin/env python3
"""Regenerate appendix-translation-scores.tex from the saved sentence scores.

Usage (from the repository root): python3 <this file> OUTPUT.tex [--delta] [--check CURRENT.tex]
Means pool all sentence rows of the listed models (and both contexts). COMET stays on its
native 0-1 scale (3 decimals); chrF++ is reported on its 0-100 scale (2 decimals; the saved
values are sacrebleu scores divided by 100, so x100 is exact). Bold marks the highest score
in a row (ties all bold); no-rule baseline rows are unmarked. --delta adds a third row per
condition with Supplied minus Familiar. --check compares the COMET and chrF++ means with the
numbers in an existing appendix file and reports any mismatch.
"""
import csv, re, sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SC = ROOT/'results/translation-quality/scores'
ALL = ['chatgpt5_5_instant','deepseek_llm_7b','deepseek_llm_67b','gemma3_4b','gemma3_27b','llama3_8b','llama3_70b','qwen3_8b','qwen3_32b']
R3 = ['chatgpt5_5_instant','qwen3_8b','qwen3_32b']
FR = ['F1','F2','F3','F4','F5']
args = sys.argv[1:]; delta = '--delta' in args; wide = '--wide' in args; inter = '--interleave' in args; comb = '--combined' in args; four = '--four' in args; nobold = '--nobold' in args; pairbold = '--pairbold' in args
out = Path([a for a in args if not a.startswith('--') and a.endswith('.tex')][0])
check = Path(args[args.index('--check')+1]) if '--check' in args else None

def rd(p):
    with open(p, encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
def mean(xs):
    xs = list(xs); return sum(xs)/len(xs)
def load(cond, models, fname):
    rows = []
    for m in models: rows += rd(SC/cond/m/fname)
    return rows
def by_frame(rows, metric, scale):
    return {f: mean(float(r[metric])*scale for r in rows if r['frame_id']==f) for f in FR}
def fmt(x, nd): return str(Decimal(repr(x)).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP))

# (label, condition dir, models, is_layout)
MAIN = [('Experiment 1','main',ALL), ('Experiment 2','exp2',ALL), ('Modal weakening','may_mean',ALL)]
LAYOUTS = [('Before task (B)','position_B'), ('Middle (M; Experiment 1)','main'), ('After source (E)','position_E'),
           ('Two middle copies (M$\\times$2)','reiteration_2'), ('Before task + middle (BM)','position_BM'),
           ('Before task + after source (BE)','position_BE'), ('Middle + after source (ME)','position_ME'),
           ('Three middle copies (M$\\times$3)','reiteration_3'), ('Before task + middle + after source (BME)','position_BME'),
           ('Five middle copies (M$\\times$5)','reiteration')]
REAS = [('Experiment 1, same models','main',R3), ('Explicit reasoning','thinking_on',R3)]

def table(metric, scale, nd, title, caption, label):
    L = []
    L.append(r'{\normalsize'); L.append(r'\setlength{\tabcolsep}{5pt}'); L.append(r'\setlength{\LTcapwidth}{\textwidth}')
    L.append(r'\begin{longtable}{@{}>{\raggedright\arraybackslash}p{6.1cm}lrrrrr@{}}')
    L.append(r'\hline'); L.append(r'\multicolumn{7}{c}{\textbf{%s}}\\' % title); L.append(r'\hline')
    hdr = r'\textbf{Condition} & \textbf{Reference} & \textbf{F1} & \textbf{F2} & \textbf{F3} & \textbf{F4} & \textbf{F5} \\'
    L += [hdr, r'\hline', r'\endfirsthead', r'\multicolumn{7}{l}{\tablename\ \thetable\ continued: %s}\\' % title, r'\hline', hdr, r'\hline', r'\endhead', r'\hline', r'\endfoot', r'\endlastfoot', r'\hline']
    def marked(vals):
        mx = max(vals); return ['\\textbf{%s}' % fmt(v, nd) if fmt(v, nd) == fmt(mx, nd) else fmt(v, nd) for v in vals]
    def pair(label, cond, models):
        fam = by_frame(load(cond, models, 'literal_pk_en.csv'), metric, scale)
        sup = by_frame(load(cond, models, 'literal_ck_en.csv'), metric, scale)
        L.append(f'{label} & Familiar & ' + ' & '.join(marked([fam[f] for f in FR])) + r' \\')
        L.append(' & Supplied & ' + ' & '.join(marked([sup[f] for f in FR])) + r' \\')
        if delta:
            L.append(' & $\\Delta$ & ' + ' & '.join(('$+$' if sup[f]-fam[f] >= 0 else '$-$') + fmt(abs(sup[f]-fam[f]), nd) for f in FR) + r' \\')
    # baselines
    base = load('baseline', ALL, 'literal_expected_en.csv')
    cons = mean(float(r[metric])*scale for r in base if r['baseline_type']=='normal_lexical')
    inc = mean(float(r[metric])*scale for r in base if r['baseline_type']!='normal_lexical')
    conv = by_frame(load('conventional_meaning', ALL, 'literal_expected_en.csv'), metric, scale)
    L.append(r'\multicolumn{7}{@{}l}{\textbf{Baselines}}\\*')
    L.append(r'No rule: semantically consistent & Familiar & \multicolumn{5}{c}{%s (no frame)} \\' % fmt(cons, nd))
    L.append(r'No rule: semantically inconsistent & Familiar & \multicolumn{5}{c}{%s (no frame)} \\' % fmt(inc, nd))
    L.append('Conventional-meaning rule & Familiar & ' + ' & '.join(marked([conv[f] for f in FR])) + r' \\')
    L.append(r'\hline'); L.append(r'\multicolumn{7}{@{}l}{\textbf{Main experiments and modal weakening}}\\*')
    for lab, cond, models in MAIN: pair(lab, cond, models)
    L.append(r'\hline'); L.append(r'\multicolumn{7}{@{}l}{\textbf{Position and repetition}}\\*')
    for lab, cond in LAYOUTS: pair(lab, cond, ALL)
    L.append(r'\hline'); L.append(r'\multicolumn{7}{@{}l}{\textbf{Explicit reasoning: GPT-5.5, Qwen3-8B and Qwen3-32B}}\\*')
    for lab, cond, models in REAS: pair(lab, cond, models)
    L.append(r'\hline')
    L.append(r'\caption{%s}\label{%s}\\' % (caption, label))
    L.append(r'\end{longtable}'); L.append('}')
    return L

def table_wide(metric, scale, nd, title, caption, label):
    L = []
    L.append(r'{\small'); L.append(r'\setlength{\tabcolsep}{3.5pt}'); L.append(r'\setlength{\LTcapwidth}{\textwidth}')
    L.append(r'\begin{longtable}{@{}>{\raggedright\arraybackslash}p{5.6cm}rrrrrrrrrr@{}}')
    L.append(r'\hline'); L.append(r'\multicolumn{11}{c}{\textbf{%s}}\\' % title); L.append(r'\hline')
    h1 = r'& \multicolumn{5}{c}{\textbf{Familiar reference}} & \multicolumn{5}{c@{}}{\textbf{Supplied reference}} \\'
    h2 = r'\textbf{Condition} & \textbf{F1} & \textbf{F2} & \textbf{F3} & \textbf{F4} & \textbf{F5} & \textbf{F1} & \textbf{F2} & \textbf{F3} & \textbf{F4} & \textbf{F5} \\'
    L += [h1, h2, r'\hline', r'\endfirsthead', r'\multicolumn{11}{l}{\tablename\ \thetable\ continued: %s}\\' % title, r'\hline', h1, h2, r'\hline', r'\endhead', r'\hline', r'\endfoot', r'\endlastfoot', r'\hline']
    def marked(vals):
        mx = max(vals); return ['\\textbf{%s}' % fmt(v, nd) if fmt(v, nd) == fmt(mx, nd) else fmt(v, nd) for v in vals]
    NA = r'\multicolumn{5}{c@{}}{--}'
    def pair(label, cond, models):
        fam = by_frame(load(cond, models, 'literal_pk_en.csv'), metric, scale)
        sup = by_frame(load(cond, models, 'literal_ck_en.csv'), metric, scale)
        L.append(f'{label} & ' + ' & '.join(marked([fam[f] for f in FR])) + ' & ' + ' & '.join(marked([sup[f] for f in FR])) + r' \\')
    base = load('baseline', ALL, 'literal_expected_en.csv')
    cons = mean(float(r[metric])*scale for r in base if r['baseline_type']=='normal_lexical')
    inc = mean(float(r[metric])*scale for r in base if r['baseline_type']!='normal_lexical')
    conv = by_frame(load('conventional_meaning', ALL, 'literal_expected_en.csv'), metric, scale)
    L.append(r'\multicolumn{11}{@{}l}{\textbf{Baselines (Familiar reference only)}}\\*')
    L.append(r'No rule: semantically consistent & \multicolumn{5}{c}{%s (no frame)} & %s \\' % (fmt(cons, nd), NA))
    L.append(r'No rule: semantically inconsistent & \multicolumn{5}{c}{%s (no frame)} & %s \\' % (fmt(inc, nd), NA))
    L.append('Conventional-meaning rule & ' + ' & '.join(marked([conv[f] for f in FR])) + ' & ' + NA + r' \\')
    L.append(r'\hline'); L.append(r'\multicolumn{11}{@{}l}{\textbf{Main experiments and modal weakening}}\\*')
    for lab, cond, models in MAIN: pair(lab, cond, models)
    L.append(r'\hline'); L.append(r'\multicolumn{11}{@{}l}{\textbf{Position and repetition}}\\*')
    for lab, cond in LAYOUTS: pair(lab, cond, ALL)
    L.append(r'\hline'); L.append(r'\multicolumn{11}{@{}l}{\textbf{Explicit reasoning: GPT-5.5, Qwen3-8B and Qwen3-32B}}\\*')
    for lab, cond, models in REAS: pair(lab, cond, models)
    L.append(r'\hline')
    L.append(r'\caption{%s}\label{%s}\\' % (caption, label))
    L.append(r'\end{longtable}'); L.append('}')
    return L

BOLDNOTE = (' Within each frame, \\textbf{bold} marks the reference against which the outputs score higher; baseline rows have one reference.' if pairbold else ' Within each reference, \\textbf{bold} marks the highest frame score.' if (wide or inter or comb) else ' In each row except the no-rule baselines, \\textbf{bold} marks the highest score.')

def _blocks(metric, scale):
    """All means needed for one metric: baselines and (fam, sup) per condition label."""
    base = load('baseline', ALL, 'literal_expected_en.csv')
    cons = mean(float(r[metric])*scale for r in base if r['baseline_type']=='normal_lexical')
    inc = mean(float(r[metric])*scale for r in base if r['baseline_type']!='normal_lexical')
    conv = by_frame(load('conventional_meaning', ALL, 'literal_expected_en.csv'), metric, scale)
    conds = []
    for group, items in (('Main experiments and modal weakening', [(l,c,m) for l,c,m in MAIN]),
                         ('Position and repetition', [(l,c,ALL) for l,c in LAYOUTS]),
                         ('Explicit reasoning: GPT-5.5, Qwen3-8B and Qwen3-32B', [(l,c,m) for l,c,m in REAS])):
        rows = []
        for lab, cond, models in items:
            fam = by_frame(load(cond, models, 'literal_pk_en.csv'), metric, scale)
            sup = by_frame(load(cond, models, 'literal_ck_en.csv'), metric, scale)
            rows.append((lab, fam, sup))
        conds.append((group, rows))
    return cons, inc, conv, conds

def marked(vals, nd):
    if nobold: return [fmt(v, nd) for v in vals]
    mx = max(vals); return ['\\textbf{%s}' % fmt(v, nd) if fmt(v, nd) == fmt(mx, nd) else fmt(v, nd) for v in vals]

def table_interleave(metric, scale, nd, title, caption, label):
    """Familiar and Supplied as two sub-columns under each frame."""
    cons, inc, conv, conds = _blocks(metric, scale)
    pair = r'r@{\hspace{4pt}}r'; gap = r'@{\hspace{11pt}}'
    spec = r'@{}>{\raggedright\arraybackslash}p{5.0cm}@{\hspace{8pt}}' + gap.join([pair]*5) + '@{}'
    L = [r'{\small', r'\setlength{\tabcolsep}{0pt}', r'\setlength{\LTcapwidth}{\textwidth}',
         r'\begin{longtable}{%s}' % spec, r'\hline',
         r'\multicolumn{11}{c}{\textbf{%s}}\\' % title, r'\hline']
    h1 = ' & '.join([''] + [r'\multicolumn{2}{c}{\textbf{%s}}' % f for f in FR]) + r' \\'
    cl = r'\cline{2-3}\cline{4-5}\cline{6-7}\cline{8-9}\cline{10-11}'
    h2 = r'\textbf{Condition} & ' + ' & '.join([r'\textbf{Fam.} & \textbf{Sup.}']*5) + r' \\'
    L += [h1, cl, h2, r'\hline', r'\endfirsthead', r'\multicolumn{11}{l}{\tablename\ \thetable\ continued: %s}\\' % title, r'\hline', h1, cl, h2, r'\hline', r'\endhead', r'\hline', r'\endfoot', r'\endlastfoot', r'\hline']
    L.append(r'\multicolumn{11}{@{}l}{\textbf{Baselines (Familiar reference only)}}\\*')
    L.append(r'No rule: semantically consistent & \multicolumn{10}{c}{%s (no frame)} \\' % fmt(cons, nd))
    L.append(r'No rule: semantically inconsistent & \multicolumn{10}{c}{%s (no frame)} \\' % fmt(inc, nd))
    cv = [fmt(conv[f], nd) for f in FR] if pairbold else marked([conv[f] for f in FR], nd)
    L.append('Conventional-meaning rule & ' + ' & '.join(f'{v} & --' for v in cv) + r' \\')
    for group, rows in conds:
        L.append(r'\hline'); L.append(r'\multicolumn{11}{@{}l}{\textbf{%s}}\\*' % group)
        for lab, fam, sup in rows:
            if pairbold:
                cells = []
                for f in FR:
                    a, b = fmt(fam[f], nd), fmt(sup[f], nd)
                    if a != b:
                        if fam[f] > sup[f]: a = '\\textbf{%s}' % a
                        else: b = '\\textbf{%s}' % b
                    cells.append(f'{a} & {b}')
                L.append(f'{lab} & ' + ' & '.join(cells) + r' \\')
                continue
            fv = marked([fam[f] for f in FR], nd); sv = marked([sup[f] for f in FR], nd)
            L.append(f'{lab} & ' + ' & '.join(f'{a} & {b}' for a, b in zip(fv, sv)) + r' \\')
    L += [r'\hline', r'\caption{%s}\label{%s}\\' % (caption, label), r'\end{longtable}', '}']
    return L

def table_combined(caption, label):
    """One table: Condition, Reference, COMET F1-F5, chrF++ F1-F5."""
    cC, iC, convC, condsC = _blocks('comet', 1); cF, iF, convF, condsF = _blocks('chrf', 100)
    L = [r'{\small', r'\setlength{\tabcolsep}{3pt}', r'\setlength{\LTcapwidth}{\textwidth}',
         r'\begin{longtable}{@{}>{\raggedright\arraybackslash}p{5.2cm}lrrrrrrrrrr@{}}', r'\hline']
    h1 = r'& & \multicolumn{5}{c}{\textbf{COMET (0--1)}} & \multicolumn{5}{c@{}}{\textbf{chrF++ (0--100)}} \\'
    h2 = r'\textbf{Condition} & \textbf{Reference} & ' + ' & '.join([r'\textbf{F1} & \textbf{F2} & \textbf{F3} & \textbf{F4} & \textbf{F5}']*2) + r' \\'
    L += [h1, h2, r'\hline', r'\endfirsthead', r'\multicolumn{12}{l}{\tablename\ \thetable\ continued}\\', r'\hline', h1, h2, r'\hline', r'\endhead', r'\hline', r'\endfoot', r'\endlastfoot', r'\hline']
    L.append(r'\multicolumn{12}{@{}l}{\textbf{Baselines}}\\*')
    L.append(r'No rule: semantically consistent & Familiar & \multicolumn{5}{c}{%s (no frame)} & \multicolumn{5}{c@{}}{%s (no frame)} \\' % (fmt(cC,3), fmt(cF,2)))
    L.append(r'No rule: semantically inconsistent & Familiar & \multicolumn{5}{c}{%s (no frame)} & \multicolumn{5}{c@{}}{%s (no frame)} \\' % (fmt(iC,3), fmt(iF,2)))
    L.append('Conventional-meaning rule & Familiar & ' + ' & '.join(marked([convC[f] for f in FR],3) + marked([convF[f] for f in FR],2)) + r' \\')
    for (group, rowsC), (_, rowsF) in zip(condsC, condsF):
        L.append(r'\hline'); L.append(r'\multicolumn{12}{@{}l}{\textbf{%s}}\\*' % group)
        for (lab, famC, supC), (_, famF, supF) in zip(rowsC, rowsF):
            L.append(f'{lab} & Familiar & ' + ' & '.join(marked([famC[f] for f in FR],3) + marked([famF[f] for f in FR],2)) + r' \\')
            L.append(' & Supplied & ' + ' & '.join(marked([supC[f] for f in FR],3) + marked([supF[f] for f in FR],2)) + r' \\')
    L += [r'\hline', r'\caption{%s}\label{%s}\label{tab:paper-metric-chrf}\\' % (caption, label), r'\end{longtable}', '}']
    return L


def table_single(metric, scale, nd, title, ref, caption, label):
    """One reference only: Condition + F1-F5. Familiar tables carry the baselines block."""
    cons, inc, conv, conds = _blocks(metric, scale)
    L = [r'{\normalsize', r'\setlength{\tabcolsep}{5pt}', r'\setlength{\LTcapwidth}{\textwidth}',
         r'\begin{longtable}{@{}>{\raggedright\arraybackslash}p{7.2cm}rrrrr@{}}', r'\hline',
         r'\multicolumn{6}{c}{\textbf{%s, %s reference}}\\' % (title, ref), r'\hline']
    h = r'\textbf{Condition} & \textbf{F1} & \textbf{F2} & \textbf{F3} & \textbf{F4} & \textbf{F5} \\'
    L += [h, r'\hline', r'\endfirsthead', r'\multicolumn{6}{l}{\tablename\ \thetable\ continued: %s, %s reference}\\' % (title, ref), r'\hline', h, r'\hline', r'\endhead', r'\hline', r'\endfoot', r'\endlastfoot', r'\hline']
    if ref == 'Familiar':
        L.append(r'\multicolumn{6}{@{}l}{\textbf{Baselines}}\\*')
        L.append(r'No rule: semantically consistent & \multicolumn{5}{c@{}}{%s (no frame)} \\' % fmt(cons, nd))
        L.append(r'No rule: semantically inconsistent & \multicolumn{5}{c@{}}{%s (no frame)} \\' % fmt(inc, nd))
        L.append('Conventional-meaning rule & ' + ' & '.join(marked([conv[f] for f in FR], nd)) + r' \\')
        L.append(r'\hline')
    first = True
    for group, rows in conds:
        if not first: L.append(r'\hline')
        first = False
        L.append(r'\multicolumn{6}{@{}l}{\textbf{%s}}\\*' % group)
        for lab, fam, sup in rows:
            vals = fam if ref == 'Familiar' else sup
            L.append(f'{lab} & ' + ' & '.join(marked([vals[f] for f in FR], nd)) + r' \\')
    L += [r'\hline', r'\caption{%s}\label{%s}\\' % (caption, label), r'\end{longtable}', '}']
    return L

delta_note = (' $\\Delta$ is the Supplied mean minus the Familiar mean.' if delta else '')
TB = table_wide if wide else (table_interleave if inter else table)
comet = TB('comet', 1, 3, 'COMET',
    'COMET mean sentence scores (0--1 scale) by condition and frame, pooling sentence contexts and all nine models unless a block names its models.' + BOLDNOTE + delta_note,
    'tab:paper-metric-comet')
chrf = TB('chrf', 100, 2, 'chrF++',
    'chrF++ mean sentence scores (0--100 scale) by condition and frame, pooling sentence contexts and all nine models unless a block names its models.' + BOLDNOTE + delta_note,
    'tab:paper-metric-chrf')

intro = r"""% Source: ../results/translation-quality/scores/<condition>/<model>/literal_*_en.csv.
% Generated by analysis/tables/make_translation_scores_appendix.py
% (means of the saved four-decimal sentence scores; chrF++ x100 to its native 0-100 scale). 10 October 2026.

In our study, we use a binary lexical inclusion score to systematically evaluate the extent to which models use novel CK translations in their outputs. Detailed evaluation of the effects of lexical conflict on translation quality is an open field of research beyond our study's scope. We therefore provide COMET and chrF++ scores for each condition as a high-level supplement to support the findings in the main paper.

Because the meaning assigned to the target word depends on the prompt frame used in the experiment, we score each output with respect to both a \emph{Familiar} reference, which uses the source word's conventional (PK) meaning to translate the target word, and a \emph{Supplied} reference, which uses the prompt's assigned (CK) meaning to translate the target word. Both \emph{Familiar} and \emph{Supplied} references otherwise preserve the remaining sentence as an identical translation of the Mandarin source text, and all model outputs are scored verbatim against each reference.

Tables~\ref{tab:paper-metric-comet} and~\ref{tab:paper-metric-chrf} cover the no-rule and conventional-meaning baselines, both main experiments, modal weakening, all ten lexical-rule layouts, and the explicit-reasoning runs; the layouts are described in Appendix~\ref{app:reiteration-prompts}, and their CK rates appear in Appendix~\ref{app:paper-position-repetition}. COMET is reported on its native 0--1 scale and chrF++ on its 0--100 scale. Consistent with the results reported in the main paper, mean COMET and chrF++ scores are higher when measured against the \emph{Supplied} reference for every frame in both main experiments, including F1.

\onecolumn
"""
coverage = r"""

\paragraph{Coverage.}
In Experiment~1, the modal-weakening follow-up, and each lexical-rule layout, each frame contains 10,800 responses; 5,400 responses are evaluated in Experiment~2; 1,350 in the conventional-meaning baseline; and 3,600 in each reasoning-block row. The no-rule baselines contain 1,350 semantically consistent and 5,400 semantically inconsistent responses.
"""
if four:
    def cap(metric, scale_txt, ref):
        extra = ' In each row except the no-rule baselines, \\textbf{bold} marks the highest score.' if ref == 'Familiar' else ' In each row, \\textbf{bold} marks the highest score.'
        return f'{metric} mean sentence scores ({scale_txt}) against the {ref} reference, by condition and frame, pooling sentence contexts and all nine models unless a block names its models.' + extra
    comet = (table_single('comet', 1, 3, 'COMET', 'Familiar', cap('COMET', '0--1 scale', 'Familiar'), 'tab:paper-metric-comet-familiar')
             + ['', '\\bigskip', ''] + table_single('comet', 1, 3, 'COMET', 'Supplied', cap('COMET', '0--1 scale', 'Supplied'), 'tab:paper-metric-comet-supplied'))
    chrf = (table_single('chrf', 100, 2, 'chrF++', 'Familiar', cap('chrF++', '0--100 scale', 'Familiar'), 'tab:paper-metric-chrf-familiar')
            + ['', '\\bigskip', ''] + table_single('chrf', 100, 2, 'chrF++', 'Supplied', cap('chrF++', '0--100 scale', 'Supplied'), 'tab:paper-metric-chrf-supplied'))
    intro = intro.replace('Tables~\\ref{tab:paper-metric-comet} and~\\ref{tab:paper-metric-chrf} cover', 'Tables~\\ref{tab:paper-metric-comet-familiar}--\\ref{tab:paper-metric-chrf-supplied} cover')
if comb:
    comet = table_combined('COMET (0--1 scale) and chrF++ (0--100 scale) mean sentence scores by condition and frame, pooling sentence contexts and all nine models unless a block names its models. Within each metric and reference, \\textbf{bold} marks the highest frame score.', 'tab:paper-metric-comet'); chrf = []
    intro = intro.replace('Tables~\\ref{tab:paper-metric-comet} and~\\ref{tab:paper-metric-chrf} cover', 'Table~\\ref{tab:paper-metric-comet} covers')
text = intro + '\n'.join(comet) + ('' if comb else ('\n\n\\bigskip\n' if wide else '\n\n\\clearpage\n')) + '\n'.join(chrf) + coverage
out.write_text(text, encoding='utf-8'); print('wrote', out)

if check:
    cur = check.read_text(encoding='utf-8')
    def nums(s):
        s = re.sub(r'\\textbf\{([^}]*)\}', r'\1', s); s = re.sub(r'\\underline\{([^}]*)\}', r'\1', s)
        return re.findall(r'\d+\.\d+', s)
    def rows(s):
        return [l for l in s.splitlines() if re.match(r'^(\S.*&|\s*&)', l) and '\\textbf{Condition}' not in l and 'multicolumn{7}{c}' not in l and 'continued' not in l and 'tablename' not in l and not l.strip().startswith('&amp;')]
    def split_tables(s):
        parts = s.split(r'\begin{longtable}'); return parts[1], parts[2]
    cc, cf = split_tables(cur); nc, nf = split_tables(text)
    for name, c, n, scale in (('COMET', cc, nc, 1), ('chrF++', cf, nf, 100)):
        cr = [l for l in rows(c) if 'Delta' not in l]; nr = [l for l in rows(n) if 'Delta' not in l]
        assert len(cr) == len(nr), (name, len(cr), len(nr))
        bad = 0
        for a, b in zip(cr, nr):
            va = [float(x)*scale for x in nums(a)]; vb = [float(x) for x in nums(b)]
            if any(abs(x-y) > 0.5*(10**-3 if scale==1 else 10**-2) + 1e-9 for x, y in zip(va, vb)) or len(va)!=len(vb):
                bad += 1; print('MISMATCH', name, a.strip()[:60], va, vb)
        print(name, len(cr), 'rows compared,', bad, 'mismatches')
