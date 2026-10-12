# Data and coding

The release contains all 48 completed experiment/model combinations and 213,750 selected final responses. Baseline: 9 x 750; main: 9 x 6000; exp2: 9 x 3000; may_mean: 9 x 6000; reiteration: 9 x 6000; thinking_on: 3 x 6000.

Materials are in data/raw, data/design, data/processed and data/coding. The BCC word-frequency input is retained. Exp2 generation includes the initial matching table and overlap-adjustment audit. Prompts and accepted translations are supplied verbatim.

Each run has responses_merged.csv and its corresponding autocoded CSV. PK/CK/BOTH/OTHER code accepted lexical forms; baseline uses EXPECTED/OTHER. Original response text, available thinking text, scientific identifiers, per-row generation settings and coding fields are preserved. Provider request identifiers, local file paths, execution identifiers and timestamps are omitted.

Baseline-filtered primary samples: Exp1 42,270 and Exp2 23,100. Unfiltered samples: 54,000 and 27,000. The R preparation script implements the row-specific Exp1 baseline matching and exact-source-sentence Exp2 matching. Summaries also retain baseline-stratified views.

Standard inference settings and the actual parameter profiles are in configs/. Recovery rows are part of the selected final responses, with their actual settings preserved. API outputs may differ on a new run. Use supplied responses to reproduce the reported analysis.

## Lexical-rule layouts and translation quality

Lexical-rule position, repetition and agreeing-definition prompts are in
`data/processed/`. Saved score CSVs retain responses, references, experimental
settings, lexical labels and numerical BLEU/chrF++/COMET scores under the release
field policy. Per-model descriptive statistics and scientific figures are supplied.
Pilot prompts are retained separately from the 48 runs in `results/runs/`.

`accepted_translations.csv` is the original English inventory used by the paper's
counts. `accepted_translations_en.csv` is the current English inventory and adds
`high-speed rail`; `accepted_translations_zh.csv` contains Mandarin forms.
Read [evaluation rules](evaluation.md) and [experiment instructions](experiments.md).
