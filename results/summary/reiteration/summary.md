# reiteration Cross-Model Summary

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
| deepseek_llm_67b | 6000 | 5335 | 665 | 88.92 | 750 |
| deepseek_llm_7b | 6000 | 4835 | 1165 | 80.58 | 750 |
| gemma3_27b | 6000 | 4720 | 1280 | 78.67 | 750 |
| gemma3_4b | 6000 | 4445 | 1555 | 74.08 | 750 |
| llama3_70b | 6000 | 3815 | 2185 | 63.58 | 750 |
| llama3_8b | 6000 | 3680 | 2320 | 61.33 | 750 |
| qwen3_32b | 6000 | 5160 | 840 | 86.0 | 750 |
| qwen3_8b | 6000 | 4785 | 1215 | 79.75 | 750 |

## Unfiltered By Model

| model_id | n | n_pk | percent_pk | n_ck | percent_ck | n_both | percent_both | n_other | percent_other |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| chatgpt5_5_instant | 6000 | 1647 | 27.45 | 4264 | 71.07 | 8 | 0.13 | 81 | 1.35 |
| deepseek_llm_67b | 6000 | 1935 | 32.25 | 3429 | 57.15 | 298 | 4.97 | 338 | 5.63 |
| deepseek_llm_7b | 6000 | 3538 | 58.97 | 1418 | 23.63 | 67 | 1.12 | 977 | 16.28 |
| gemma3_27b | 6000 | 91 | 1.52 | 5857 | 97.62 | 9 | 0.15 | 43 | 0.72 |
| gemma3_4b | 6000 | 1093 | 18.22 | 4592 | 76.53 | 18 | 0.3 | 297 | 4.95 |
| llama3_70b | 6000 | 231 | 3.85 | 5484 | 91.4 | 7 | 0.12 | 278 | 4.63 |
| llama3_8b | 6000 | 464 | 7.73 | 5183 | 86.38 | 113 | 1.88 | 240 | 4.0 |
| qwen3_32b | 6000 | 625 | 10.42 | 5016 | 83.6 | 21 | 0.35 | 338 | 5.63 |
| qwen3_8b | 6000 | 1939 | 32.32 | 3448 | 57.47 | 25 | 0.42 | 588 | 9.8 |

## Baseline-Filtered By Model

| model_id | n | n_pk | percent_pk | n_ck | percent_ck | n_both | percent_both | n_other | percent_other |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| chatgpt5_5_instant | 5495 | 1613 | 29.35 | 3839 | 69.86 | 8 | 0.15 | 35 | 0.64 |
| deepseek_llm_67b | 5335 | 1920 | 35.99 | 2867 | 53.74 | 286 | 5.36 | 262 | 4.91 |
| deepseek_llm_7b | 4835 | 3449 | 71.33 | 902 | 18.66 | 63 | 1.3 | 421 | 8.71 |
| gemma3_27b | 4720 | 91 | 1.93 | 4588 | 97.2 | 9 | 0.19 | 32 | 0.68 |
| gemma3_4b | 4445 | 1058 | 23.8 | 3224 | 72.53 | 18 | 0.4 | 145 | 3.26 |
| llama3_70b | 3815 | 222 | 5.82 | 3439 | 90.14 | 7 | 0.18 | 147 | 3.85 |
| llama3_8b | 3680 | 450 | 12.23 | 3001 | 81.55 | 103 | 2.8 | 126 | 3.42 |
| qwen3_32b | 5160 | 613 | 11.88 | 4291 | 83.16 | 20 | 0.39 | 236 | 4.57 |
| qwen3_8b | 4785 | 1881 | 39.31 | 2607 | 54.48 | 25 | 0.52 | 272 | 5.68 |
