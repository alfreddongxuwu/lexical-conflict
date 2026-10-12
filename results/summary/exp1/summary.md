# main Cross-Model Summary

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
| chatgpt5_5_instant | 6000 | 882 | 14.7 | 5059 | 84.32 | 6 | 0.1 | 53 | 0.88 |
| deepseek_llm_67b | 6000 | 1870 | 31.17 | 3699 | 61.65 | 88 | 1.47 | 343 | 5.72 |
| deepseek_llm_7b | 6000 | 3500 | 58.33 | 1479 | 24.65 | 45 | 0.75 | 976 | 16.27 |
| gemma3_27b | 6000 | 59 | 0.98 | 5878 | 97.97 | 19 | 0.32 | 44 | 0.73 |
| gemma3_4b | 6000 | 858 | 14.3 | 4929 | 82.15 | 34 | 0.57 | 179 | 2.98 |
| llama3_70b | 6000 | 80 | 1.33 | 5670 | 94.5 | 10 | 0.17 | 240 | 4.0 |
| llama3_8b | 6000 | 474 | 7.9 | 5119 | 85.32 | 77 | 1.28 | 330 | 5.5 |
| qwen3_32b | 6000 | 500 | 8.33 | 5306 | 88.43 | 17 | 0.28 | 177 | 2.95 |
| qwen3_8b | 6000 | 2042 | 34.03 | 3401 | 56.68 | 27 | 0.45 | 530 | 8.83 |

## Baseline-Filtered By Model

| model_id | n | n_pk | percent_pk | n_ck | percent_ck | n_both | percent_both | n_other | percent_other |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| chatgpt5_5_instant | 5495 | 865 | 15.74 | 4594 | 83.6 | 6 | 0.11 | 30 | 0.55 |
| deepseek_llm_67b | 5335 | 1855 | 34.77 | 3118 | 58.44 | 87 | 1.63 | 275 | 5.15 |
| deepseek_llm_7b | 4835 | 3390 | 70.11 | 984 | 20.35 | 41 | 0.85 | 420 | 8.69 |
| gemma3_27b | 4720 | 59 | 1.25 | 4607 | 97.61 | 19 | 0.4 | 35 | 0.74 |
| gemma3_4b | 4445 | 836 | 18.81 | 3480 | 78.29 | 34 | 0.76 | 95 | 2.14 |
| llama3_70b | 3815 | 80 | 2.1 | 3572 | 93.63 | 8 | 0.21 | 155 | 4.06 |
| llama3_8b | 3680 | 446 | 12.12 | 2989 | 81.22 | 74 | 2.01 | 171 | 4.65 |
| qwen3_32b | 5160 | 491 | 9.52 | 4519 | 87.58 | 17 | 0.33 | 133 | 2.58 |
| qwen3_8b | 4785 | 1987 | 41.53 | 2508 | 52.41 | 27 | 0.56 | 263 | 5.5 |
