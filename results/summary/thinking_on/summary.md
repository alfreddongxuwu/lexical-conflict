# thinking_on Cross-Model Summary

Three analysis views are retained:

- `unfiltered/`: all experiment rows.
- `baseline_filtered/`: only rows whose matched baseline label is `EXPECTED`.
- `baseline_stratified/`: all rows, grouped by matched baseline label.

Matching rule:

- `PK_context` rows match `normal_lexical` baseline rows.
- `CK_context` rows match `anomalous_no_lexicon` baseline rows.

## Filter Inventory

| model_id | unfiltered_rows | baseline_filtered_rows | excluded_rows | retained_percent | baseline_rows |
| --- | --- | --- | --- | --- | --- |
| chatgpt5_5_instant | 6000 | 5495 | 505 | 91.58 | 750 |
| qwen3_32b | 6000 | 5160 | 840 | 86.0 | 750 |
| qwen3_8b | 6000 | 4785 | 1215 | 79.75 | 750 |

## Unfiltered By Model

| model_id | n | n_pk | percent_pk | n_ck | percent_ck | n_both | percent_both | n_other | percent_other |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| chatgpt5_5_instant | 6000 | 1164 | 19.4 | 4786 | 79.77 | 5 | 0.08 | 45 | 0.75 |
| qwen3_32b | 6000 | 13 | 0.22 | 5973 | 99.55 | 5 | 0.08 | 9 | 0.15 |
| qwen3_8b | 6000 | 64 | 1.07 | 5918 | 98.63 | 7 | 0.12 | 11 | 0.18 |

## Baseline-Filtered By Model

| model_id | n | n_pk | percent_pk | n_ck | percent_ck | n_both | percent_both | n_other | percent_other |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| chatgpt5_5_instant | 5495 | 1095 | 19.93 | 4382 | 79.75 | 5 | 0.09 | 13 | 0.24 |
| qwen3_32b | 5160 | 12 | 0.23 | 5135 | 99.52 | 5 | 0.1 | 8 | 0.16 |
| qwen3_8b | 4785 | 62 | 1.3 | 4710 | 98.43 | 7 | 0.15 | 6 | 0.13 |
