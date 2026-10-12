# Lexical conflict

Code, data and statistical models for the lexical-conflict translation experiments.

Code is licensed under [MIT](LICENSE). Original experimental materials and result datasets are licensed under [CC BY 4.0](data/LICENSE). BCC frequency data, including counts reproduced in derived tables, retain [BCC's terms](https://bcc.blcu.edu.cn/help.html).

## Contents

| Directory | Contents |
| --- | --- |
| `data/` | Lexical inventory, frequencies, contexts, frames, mappings, prompts and accepted translations |
| `src/lexconflict/`, `scripts/` | Material construction, local inference, lexical coding, scoring, reports and descriptive summaries |
| `configs/` | Experiment sizes, inference settings, observed parameter profiles and R package versions |
| `results/` | Saved responses, lexical codes, translation scores, numerical summaries and reports |
| `statistics/primary/` | Four reported GLMM fits with source and target item random intercepts |
| `statistics/model_only/`, `statistics/model_slopes/` | Eight alternative fits with model-specific random coefficients |
| `analysis/figures/` | Plotting code and saved scientific figures |
| `analysis/tables/` | Table generators and LaTeX fragments |
| `tests/` | Local runner and request-handling checks |

The three statistical specifications each have Exp1/Exp2 unfiltered and baseline-filtered fits. The four primary fits are nonsingular; all eight alternatives are singular at tolerance 1e-4. The `results/runs/` tree contains 213,750 responses; lexical-rule position and agreeing-definition responses are retained in their scored CSVs. Data and model details are in `docs/data.md` and the statistics README files.

The experimental conditions include lexical-rule layouts B, M, E, BE, BM, ME, BME, M×2, M×3 and M×5, modal weakening, explicit reasoning and the agreeing-definition control. Read [experiment instructions](docs/experiments.md), [evaluation rules](docs/evaluation.md), [result layout](docs/results.md) and [figure/table reproduction](analysis/README.md).

## Environment

Validation uses Python 3.12.3 and R 4.5.2. Install Python dependencies with `python -m pip install -r requirements.txt`. R requires lme4, dplyr and readr for analysis, and ggplot2 for figures. Recorded R package versions are in `configs/r_package_versions.csv`; the supplied fits use lme4 2.0-1. Install `configs/requirements-analysis.txt` for Python scoring, reporting and plotting. Run the following commands from the repository root.

## Reproduce existing results

```sh
python scripts/verify_release.py
python scripts/recode_results.py --check
python scripts/reproduce_summaries.py --output-dir outputs/summary
Rscript statistics/primary/prepare_inputs.R
Rscript statistics/primary/run_reports.R
Rscript scripts/verify_models.R
python scripts/summarize_rule_layouts_original.py outputs/layout-counts
python scripts/summarize_agreeing_baseline_original.py outputs/agreeing-counts
python analysis/tables/make_layout_tables.py results/summary/rule-layouts outputs/layout-tables
python analysis/tables/make_translation_scores_appendix.py outputs/translation-scores.tex --interleave --pairbold
```

These commands use the supplied responses and saved fits. The summary output directory must be empty. Rebuilding reports or data can update generated files, so checksum verification should be run on the original checkout first.

To fit the primary specification again, use `Rscript statistics/primary/run_all.R`. The two alternative directories document their preflight and individual-fit commands. Refitting large models can take substantial time.

The eight plotting entrypoints are:

```sh
Rscript analysis/figures/main/plot_figure2_baseline.R
Rscript analysis/figures/main/plot_figure3_exp1.R
Rscript analysis/figures/main/plot_figure4_exp2.R
Rscript analysis/figures/main/plot_figure5_figure6_followups.R
Rscript analysis/figures/appendices/plot_appendix_exp1.R
Rscript analysis/figures/appendices/plot_appendix_exp2.R
Rscript analysis/figures/appendices/plot_appendix_modal_reiteration.R
Rscript analysis/figures/appendices/plot_appendix_reasoning.R
```

## Run new prompts locally

Ollama must be running locally with the chosen model available. Required memory depends on the model. OpenAI inference requires `OPENAI_API_KEY` in the environment and makes API requests.

Inspect a run without making requests or writing output:

```sh
python scripts/run_experiment.py ollama --model qwen3:8b --model-id qwen3_8b --experiment-id main --run-dir outputs/main/qwen3_8b --dry-run
```

Run the first five prompts:

```sh
python scripts/run_experiment.py ollama --model qwen3:8b --model-id qwen3_8b --experiment-id main --run-dir outputs/main/qwen3_8b --limit 5
python scripts/run_experiment.py openai --model gpt-5.5 --model-id chatgpt5_5_instant --experiment-id main --run-dir outputs/main/chatgpt5_5_instant --limit 5
```

Omit `--limit` to process the full prompt file. `--start` selects a zero-based starting row; identifier filtering is applied before `--start` and `--limit`. Use `--prompts` with a file from `configs/experiments.json` for another experiment. Results are saved as `responses_merged.csv` in the requested output directory.

Repeating a command skips complete responses and retries incomplete responses. To use recovery settings, repeat it with the required output/context limits; each response retains its actual settings. `--prompt-ids-file` selects identifiers listed one per line. A different model or changed prompt contents require a new output directory. Each directory allows one active writer; after an interrupted process, inspect the run before removing a stale `.run.lock`.

Standard output limits are 128 tokens for both providers. Qwen3 thinking is disabled automatically for standard runs. For the thinking-on follow-up, use `--think true --num-predict 1048` with Qwen3, or `--reasoning-effort medium` with GPT-5.5. Further recovery settings are recorded in `configs/observed_generation_profiles.csv` and the response rows. Newly generated outputs may differ from the supplied responses.

Code a completed local run:

```sh
python scripts/code_responses.py --run-dir outputs/main/qwen3_8b
```

Add `--baseline` when coding baseline responses. Provider-specific options are available with `python scripts/run_experiment.py ollama --help` and `python scripts/run_experiment.py openai --help`.

## Regenerate materials

Run these scripts in order:

```sh
python scripts/01_make_category_freq_tables.py
python scripts/02_select_freq_bands.py
python scripts/03_merge_items.py
python scripts/04_make_mappings.py
python scripts/04_make_exp2_mappings.py
python scripts/05_make_prompts.py
python scripts/05_make_exp2_prompts.py
python scripts/05_make_may_prompts.py
python scripts/05_make_reiteration_prompts.py
python scripts/07_make_baseline_prompts.py
```

Rule-layout and agreeing-definition builders are documented in `docs/experiments.md`. Thinking-on uses the main prompts unchanged. Material regeneration updates generated data files.

## Checks

Run `python -m unittest discover -s tests -v` for local runner tests. The tests mock provider requests and make no external inference calls.
