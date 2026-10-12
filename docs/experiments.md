# Experiments and analysis

The project contains cross-category lexical conflict (Exp1), within-category
cross-frequency conflict (Exp2), modal weakening, lexical-rule position and
reiteration, explicit reasoning, no-rule baselines and an agreeing-definition
control. Saved responses are evaluated for lexical choices and translation
quality using BLEU, chrF++ and COMET.

Exp1 uses 6,000 prompts per model; Exp2 uses 3,000. Modal weakening and explicit
reasoning use the Exp1 design. The lexical-rule layouts are B, M, E, BE, BM, ME,
BME, M×2, M×3 and M×5. `main` identifies M, `reiteration` identifies M×5;
the other saved condition identifiers are `position_B`, `position_E`,
`position_BE`, `position_BM`, `position_ME`, `position_BME`, `reiteration_2`
and `reiteration_3`. The agreeing-definition control (`conventional_meaning`)
uses 750 prompts per model and the five unchanged frames. It retains the
existing no-rule baseline for screening.

| Material | Location |
|---|---|
| Prompts and mappings | `data/processed/` |
| Frames and stimulus-design audits | `data/design/` |
| Accepted-form inventories | `data/coding/` |
| Prompt construction, coding, scoring and summaries | `scripts/` |
| Reusable inference and analysis code | `src/lexconflict/` |
| Shell entrypoints | `run/` |
| Responses, metrics, summaries and reports | `results/` |
| Figure code and assets | `analysis/figures/` |
| Table generators and fragments | `analysis/tables/` |
| Offline checks | `tests/` |

Read [evaluation rules](evaluation.md) before interpreting any comparison.
See [data and coding](data.md), [result layout](results.md) and
[figure and table reproduction](../analysis/README.md).

## Build prompts

Run commands from the repository root. Use the supplied prompt files to
reproduce the saved analyses. Builders refuse existing destinations:

```sh
python scripts/make_position_prompts.py --output-dir outputs/prompts/rule-position
python scripts/make_conventional_prompts.py outputs/prompts/agreeing-definition.csv
```

The position builder changes only the rule's location or repetition count in
the saved Exp1 prompts. The agreeing-definition builder checks normal-sentence
and reference identity and exact conflict-prompt equality after replacing only
the definition.

## Run locally

Install `requirements.txt` for generation and `configs/requirements-analysis.txt`
for scoring, reporting and plotting. Ollama uses a running local service;
OpenAI reads `OPENAI_API_KEY` from the environment. Preview five rows without
provider requests or output files:

```sh
python scripts/run_translation.py ollama --model qwen3:8b --model-id qwen3_8b --experiment-id position_BE --prompts data/processed/prompts_position_BE.csv --run-dir outputs/runs/position_BE/qwen3_8b --limit 5 --dry-run
```

Remove `--dry-run` to generate those rows and `--limit` for the full prompt file.
The dispatcher accepts `ollama` and `openai`, `--start`, `--limit` and
`--prompt-ids-file`. It preserves provider response text verbatim, resumes
completed rows and allows one writer per output directory. A different model
or changed prompts require a new output directory.

For the agreeing-definition control use `--experiment-id conventional_meaning`
and `--prompts data/processed/prompts_conventional_meaning.csv`. Its two-stage
GPT-5.5 entrypoint selects 75 prompts for `first` and 675 for `rest`:

```sh
PYTHON_BIN=python bash run/submit_gpt55_agreeing_baseline.sh first --dry-run
```

It uses reasoning off, low verbosity, 128 output tokens and no automatic retries.
A real `rest` run validates the completed first 75 responses. Generation without
`--dry-run` makes real provider requests; saved-response analysis does not.

## Code, score and report

Install `configs/requirements-analysis.txt` for these commands. Scoring and
reporting read supplied or locally generated responses and make no provider calls:

```sh
python scripts/code_english_baseline.py INPUT.csv outputs/coded.csv
python scripts/score_translations.py outputs/coded.csv outputs/scores/conventional_meaning/model --no-comet
python scripts/compare_translation_scores.py results/translation-quality/scores outputs/translation-quality-report
python scripts/summarize_rule_layouts_original.py outputs/layout-counts
python scripts/summarize_agreeing_baseline_original.py outputs/agreeing-counts
python analysis/tables/make_layout_tables.py results/summary/rule-layouts outputs/layout-tables
python analysis/tables/make_translation_scores_appendix.py outputs/translation-scores.tex --interleave --pairbold
python analysis/figures/main/plot_figures5_6.py results/summary/rule-layouts outputs/figures
```

`--no-comet` selects CPU BLEU and chrF++. COMET-22 needs its downloaded model;
reuse the supplied scores to reproduce results without rescoring. Use new
destinations for generated responses, scores and reports.

The paper's lexical-layout counts use `data/coding/accepted_translations.csv`
and the original baseline labels. `scripts/summarize_rule_layouts.py` and
`scripts/summarize_agreeing_baseline.py` use the current English inventory
`accepted_translations_en.csv`; the Mandarin inventory is
`accepted_translations_zh.csv`. These inventory-specific views are kept separate.

## Checks

```sh
python -m unittest discover -s tests -v
```
