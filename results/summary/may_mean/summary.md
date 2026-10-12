# may_mean Cross-Model Summary

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
| chatgpt5_5_instant | 6000 | 2207 | 36.78 | 3676 | 61.27 | 10 | 0.17 | 107 | 1.78 |
| deepseek_llm_67b | 6000 | 2835 | 47.25 | 2593 | 43.22 | 158 | 2.63 | 414 | 6.9 |
| deepseek_llm_7b | 6000 | 4113 | 68.55 | 706 | 11.77 | 23 | 0.38 | 1158 | 19.3 |
| gemma3_27b | 6000 | 518 | 8.63 | 5318 | 88.63 | 66 | 1.1 | 98 | 1.63 |
| gemma3_4b | 6000 | 2434 | 40.57 | 2967 | 49.45 | 47 | 0.78 | 552 | 9.2 |
| llama3_70b | 6000 | 650 | 10.83 | 4842 | 80.7 | 13 | 0.22 | 495 | 8.25 |
| llama3_8b | 6000 | 1084 | 18.07 | 4103 | 68.38 | 33 | 0.55 | 780 | 13.0 |
| qwen3_32b | 6000 | 1256 | 20.93 | 4298 | 71.63 | 18 | 0.3 | 428 | 7.13 |
| qwen3_8b | 6000 | 2833 | 47.22 | 2463 | 41.05 | 35 | 0.58 | 669 | 11.15 |

## Baseline-Filtered By Model

| model_id | n | n_pk | percent_pk | n_ck | percent_ck | n_both | percent_both | n_other | percent_other |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| chatgpt5_5_instant | 5495 | 2192 | 39.89 | 3237 | 58.91 | 10 | 0.18 | 56 | 1.02 |
| deepseek_llm_67b | 5335 | 2805 | 52.58 | 2083 | 39.04 | 155 | 2.91 | 292 | 5.47 |
| deepseek_llm_7b | 4835 | 3947 | 81.63 | 447 | 9.25 | 21 | 0.43 | 420 | 8.69 |
| gemma3_27b | 4720 | 510 | 10.81 | 4085 | 86.55 | 66 | 1.4 | 59 | 1.25 |
| gemma3_4b | 4445 | 2339 | 52.62 | 1847 | 41.55 | 45 | 1.01 | 214 | 4.81 |
| llama3_70b | 3815 | 615 | 16.12 | 2933 | 76.88 | 13 | 0.34 | 254 | 6.66 |
| llama3_8b | 3680 | 993 | 26.98 | 2348 | 63.8 | 30 | 0.82 | 309 | 8.4 |
| qwen3_32b | 5160 | 1230 | 23.84 | 3613 | 70.02 | 17 | 0.33 | 300 | 5.81 |
| qwen3_8b | 4785 | 2713 | 56.7 | 1752 | 36.61 | 34 | 0.71 | 286 | 5.98 |
