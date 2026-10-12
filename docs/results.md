# Results

| Directory | Contents |
|---|---|
| `results/runs/` | Merged responses, automatic codes and per-model descriptive statistics for the main, baseline, Exp2, modal, M×5 and reasoning conditions |
| `results/summary/{baseline,exp1,exp2,may_mean,reiteration,thinking_on}/` | Cross-model unfiltered, baseline-filtered and baseline-stratified summaries |
| `results/summary/rule-layouts/` | Paper counts for all ten lexical-rule layouts, using the original English inventory |
| `results/summary/agreeing-definition/original-inventory/` | Agreeing-definition and matched no-rule counts and coding audit |
| `results/translation-quality/scores/<condition>/<model>/` | Saved response text, lexical codes and sentence-level translation scores |
| `results/translation-quality/report/` | Translation-quality reports and paired comparisons |
| `results/rule-position/report/` | Lexical-rule layout comparisons, with model populations and inventories identified |
| `results/agreeing-definition/report/` | Agreeing-definition comparisons |
| `results/provenance/` | Recorded run audits and source manifests |

Prompts and stimulus materials are in `data/`, not duplicated under result
directories. Scores for Familiar (`literal_pk_en.csv`), Supplied
(`literal_ck_en.csv`) and no-rule/agreeing-definition references
(`literal_expected_en.csv`) remain separate. Each scored row retains its
response text, generation settings, references, coding and numeric metrics.
Read [evaluation rules](evaluation.md) for the meaning of these comparisons.

Current-inventory reports and original-inventory paper counts describe distinct
coding views. Recorded source hashes identify their input snapshots; the release's
`checksums.sha256` identifies the distributed files.

The `results/runs/` tree contains 48 experiment/model combinations and 213,750
responses. Rule-layout and agreeing-definition response text is also retained
in the corresponding scored CSVs. Pilot prompts are separate from the final runs.

Release CSVs exclude provider request IDs, execution IDs, local paths and
timestamps. Scientific fields and response text are retained.
