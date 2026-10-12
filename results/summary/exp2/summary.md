# Exp2 Cross-Model Summary

Three analysis views are retained:

- `unfiltered/`: all Exp2 rows.
- `baseline_filtered/`: rows whose source item has an `EXPECTED`
  `normal_lexical` baseline response for the same model.
- `baseline_stratified/`: all rows, grouped by matched normal-lexical
  baseline label.

The Exp2 source item and baseline source sentence are required to match exactly.

## Filter Inventory

| model_id | unfiltered_rows | baseline_filtered_rows | excluded_rows | retained_percent | unique_source_items | normal_baseline_expected_items | normal_baseline_other_items |
| --- | --- | --- | --- | --- | --- | --- | --- |
| chatgpt5_5_instant | 3000 | 2940 | 60 | 98.0 | 150 | 147 | 3 |
| deepseek_llm_67b | 3000 | 2880 | 120 | 96.0 | 150 | 144 | 6 |
| deepseek_llm_7b | 3000 | 2520 | 480 | 84.0 | 150 | 126 | 24 |
| gemma3_27b | 3000 | 2700 | 300 | 90.0 | 150 | 135 | 15 |
| gemma3_4b | 3000 | 2360 | 640 | 78.67 | 150 | 118 | 32 |
| llama3_70b | 3000 | 2260 | 740 | 75.33 | 150 | 113 | 37 |
| llama3_8b | 3000 | 2160 | 840 | 72.0 | 150 | 108 | 42 |
| qwen3_32b | 3000 | 2780 | 220 | 92.67 | 150 | 139 | 11 |
| qwen3_8b | 3000 | 2500 | 500 | 83.33 | 150 | 125 | 25 |

## Unfiltered By Model

| model_id | n | n_pk | percent_pk | n_ck | percent_ck | n_both | percent_both | n_other | percent_other |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| chatgpt5_5_instant | 3000 | 536 | 17.87 | 2448 | 81.6 | 5 | 0.17 | 11 | 0.37 |
| deepseek_llm_67b | 3000 | 812 | 27.07 | 2081 | 69.37 | 28 | 0.93 | 79 | 2.63 |
| deepseek_llm_7b | 3000 | 1787 | 59.57 | 838 | 27.93 | 14 | 0.47 | 361 | 12.03 |
| gemma3_27b | 3000 | 3 | 0.1 | 2992 | 99.73 | 5 | 0.17 | 0 | 0.0 |
| gemma3_4b | 3000 | 317 | 10.57 | 2619 | 87.3 | 5 | 0.17 | 59 | 1.97 |
| llama3_70b | 3000 | 5 | 0.17 | 2966 | 98.87 | 7 | 0.23 | 22 | 0.73 |
| llama3_8b | 3000 | 141 | 4.7 | 2810 | 93.67 | 12 | 0.4 | 37 | 1.23 |
| qwen3_32b | 3000 | 92 | 3.07 | 2886 | 96.2 | 5 | 0.17 | 17 | 0.57 |
| qwen3_8b | 3000 | 990 | 33.0 | 1847 | 61.57 | 2 | 0.07 | 161 | 5.37 |

## Baseline-Filtered By Model

| model_id | n | n_pk | percent_pk | n_ck | percent_ck | n_both | percent_both | n_other | percent_other |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| chatgpt5_5_instant | 2940 | 534 | 18.16 | 2394 | 81.43 | 5 | 0.17 | 7 | 0.24 |
| deepseek_llm_67b | 2880 | 812 | 28.19 | 1983 | 68.85 | 28 | 0.97 | 57 | 1.98 |
| deepseek_llm_7b | 2520 | 1753 | 69.56 | 564 | 22.38 | 9 | 0.36 | 194 | 7.7 |
| gemma3_27b | 2700 | 3 | 0.11 | 2692 | 99.7 | 5 | 0.19 | 0 | 0.0 |
| gemma3_4b | 2360 | 313 | 13.26 | 2001 | 84.79 | 5 | 0.21 | 41 | 1.74 |
| llama3_70b | 2260 | 5 | 0.22 | 2231 | 98.72 | 7 | 0.31 | 17 | 0.75 |
| llama3_8b | 2160 | 139 | 6.44 | 1996 | 92.41 | 12 | 0.56 | 13 | 0.6 |
| qwen3_32b | 2780 | 91 | 3.27 | 2671 | 96.08 | 5 | 0.18 | 13 | 0.47 |
| qwen3_8b | 2500 | 970 | 38.8 | 1439 | 57.56 | 2 | 0.08 | 89 | 3.56 |
