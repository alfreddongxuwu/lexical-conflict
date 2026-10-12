# Figures, tables and numerical summaries

Numerical summaries are stored in `results/summary/`. Lexical-rule layout
counts cover all ten layouts and nine models; agreeing-definition counts are
in `results/summary/agreeing-definition/original-inventory/`.

`analysis/figures/` contains plotting code and saved scientific figures.
`analysis/tables/` contains table generators and saved LaTeX fragments.
`analysis/reporting/theme.css` supplies report styling.

Run from the repository root with `configs/requirements-analysis.txt` installed:

```sh
python scripts/summarize_rule_layouts_original.py outputs/layout-counts
python scripts/summarize_agreeing_baseline_original.py outputs/agreeing-counts
python analysis/tables/make_layout_tables.py results/summary/rule-layouts outputs/layout-tables
python analysis/tables/make_translation_scores_appendix.py outputs/translation-scores.tex --interleave --pairbold
python analysis/figures/main/plot_figures5_6.py results/summary/rule-layouts outputs/figures
```

The figure and table counts use the original English inventory and baseline
screening labels. Recomputed M and M×5 labels are validated against the supplied
`main` and `reiteration` results. Current-inventory summaries have separate
entrypoints in `scripts/`. See [evaluation rules](../docs/evaluation.md).

`analysis/figures/main/plot_figure5_figure6_followups.R` calls the Python plotting
entrypoint; set `PYTHON_BIN` to an environment with Matplotlib. Other figures
retain their documented R plotting entrypoints.
