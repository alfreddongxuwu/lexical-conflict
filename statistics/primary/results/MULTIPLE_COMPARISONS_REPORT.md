# Multiple-comparisons correction

Method: Holm (family-wise alpha = .05), applied to the saved raw Wald p-values with stats::p.adjust().

## Scope

- Exp1 unfiltered: 4 omnibus tests; a separate family of 9 non-intercept reference contrasts.
- Exp2 unfiltered: 3 omnibus tests; a separate family of 8 non-intercept reference contrasts.
- The baseline-filtered robustness analyses use the same respective family definitions, separately from the unfiltered analyses.
- All four F2-F5 versus F1 contrasts, both source-frequency versus high contrasts, both target-frequency versus high contrasts, and the Exp1 context contrast are included, regardless of raw significance.
- These are the existing reference contrasts. Medium versus low frequency and other additional pairwise contrasts have not been tested.
- This defines 8 families and controls family-wise error within each family; it does not provide a single paper-wide error guarantee.

## Result

48 tests adjusted; 0 significance decisions changed at alpha = .05.

| analysis | experiment | sample | family_type | family_id | method | n_tests | significant_raw | significant_holm | changed_at_05 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| exp1_filtered | exp1 | filtered | omnibus | exp1_filtered:omnibus | holm | 4 | 3 | 3 | 0 |
| exp1_filtered | exp1 | filtered | reference_contrasts | exp1_filtered:reference_contrasts | holm | 9 | 7 | 7 | 0 |
| exp1_unfiltered | exp1 | unfiltered | omnibus | exp1_unfiltered:omnibus | holm | 4 | 3 | 3 | 0 |
| exp1_unfiltered | exp1 | unfiltered | reference_contrasts | exp1_unfiltered:reference_contrasts | holm | 9 | 7 | 7 | 0 |
| exp2_filtered | exp2 | filtered | omnibus | exp2_filtered:omnibus | holm | 3 | 2 | 2 | 0 |
| exp2_filtered | exp2 | filtered | reference_contrasts | exp2_filtered:reference_contrasts | holm | 8 | 6 | 6 | 0 |
| exp2_unfiltered | exp2 | unfiltered | omnibus | exp2_unfiltered:omnibus | holm | 3 | 2 | 2 | 0 |
| exp2_unfiltered | exp2 | unfiltered | reference_contrasts | exp2_unfiltered:reference_contrasts | holm | 8 | 6 | 6 | 0 |

## Reporting

Use Holm-adjusted p-values for inference. Both raw and adjusted values are retained in the new *_holm.csv tables.
The original model fits, raw p-value tables, odds ratios, standard errors, and Wald confidence intervals are preserved.
Confidence intervals are pointwise, unadjusted 95% Wald intervals. They are not simultaneous intervals and should not override the adjusted p-values when making significance decisions.
A raw numeric p-value of zero reflects floating-point underflow for an extremely small tail probability. Such values are shown below as < machine range and should be reported as p < .001, never p = 0.

## P-value audit

| Analysis | Family | Test | p raw | p Holm | Significant after Holm |
| --- | --- | --- | --- | --- | --- |
| exp1_unfiltered | Omnibus | context | < machine range | < machine range | TRUE |
| exp1_unfiltered | Omnibus | frame | < machine range | < machine range | TRUE |
| exp1_unfiltered | Omnibus | source_freq | 1.01383e-12 | 2.02767e-12 | TRUE |
| exp1_unfiltered | Omnibus | target_freq | 0.407948 | 0.407948 | FALSE |
| exp1_filtered | Omnibus | context | < machine range | < machine range | TRUE |
| exp1_filtered | Omnibus | frame | < machine range | < machine range | TRUE |
| exp1_filtered | Omnibus | source_freq | 4.46686e-09 | 8.93372e-09 | TRUE |
| exp1_filtered | Omnibus | target_freq | 0.456028 | 0.456028 | FALSE |
| exp2_unfiltered | Omnibus | frame | < machine range | < machine range | TRUE |
| exp2_unfiltered | Omnibus | source_freq | 2.78145e-06 | 5.56289e-06 | TRUE |
| exp2_unfiltered | Omnibus | target_freq | 0.173581 | 0.173581 | FALSE |
| exp2_filtered | Omnibus | frame | < machine range | < machine range | TRUE |
| exp2_filtered | Omnibus | source_freq | 0.000106288 | 0.000212576 | TRUE |
| exp2_filtered | Omnibus | target_freq | 0.193278 | 0.193278 | FALSE |
| exp1_unfiltered | Reference contrasts | contextCK_context | < machine range | < machine range | TRUE |
| exp1_unfiltered | Reference contrasts | frameF2 | < machine range | < machine range | TRUE |
| exp1_unfiltered | Reference contrasts | frameF3 | 1.43736e-291 | 8.62416e-291 | TRUE |
| exp1_unfiltered | Reference contrasts | frameF4 | 1.84283e-135 | 9.21417e-135 | TRUE |
| exp1_unfiltered | Reference contrasts | frameF5 | < machine range | < machine range | TRUE |
| exp1_unfiltered | Reference contrasts | source_freqmedium | 0.000102175 | 0.000306525 | TRUE |
| exp1_unfiltered | Reference contrasts | source_freqlow | 1.1077e-13 | 4.4308e-13 | TRUE |
| exp1_unfiltered | Reference contrasts | target_freqmedium | 0.180534 | 0.361067 | FALSE |
| exp1_unfiltered | Reference contrasts | target_freqlow | 0.500195 | 0.500195 | FALSE |
| exp1_filtered | Reference contrasts | contextCK_context | < machine range | < machine range | TRUE |
| exp1_filtered | Reference contrasts | frameF2 | < machine range | < machine range | TRUE |
| exp1_filtered | Reference contrasts | frameF3 | 1.15714e-280 | 6.94283e-280 | TRUE |
| exp1_filtered | Reference contrasts | frameF4 | 8.79684e-135 | 4.39842e-134 | TRUE |
| exp1_filtered | Reference contrasts | frameF5 | < machine range | < machine range | TRUE |
| exp1_filtered | Reference contrasts | source_freqmedium | 0.00117756 | 0.00353269 | TRUE |
| exp1_filtered | Reference contrasts | source_freqlow | 5.89314e-10 | 2.35726e-09 | TRUE |
| exp1_filtered | Reference contrasts | target_freqmedium | 0.211403 | 0.422805 | FALSE |
| exp1_filtered | Reference contrasts | target_freqlow | 0.583891 | 0.583891 | FALSE |
| exp2_unfiltered | Reference contrasts | frameF2 | 2.95802e-292 | 2.36642e-291 | TRUE |
| exp2_unfiltered | Reference contrasts | frameF3 | 6.34209e-183 | 3.80526e-182 | TRUE |
| exp2_unfiltered | Reference contrasts | frameF4 | 8.92829e-105 | 4.46415e-104 | TRUE |
| exp2_unfiltered | Reference contrasts | frameF5 | 1.41054e-291 | 9.87378e-291 | TRUE |
| exp2_unfiltered | Reference contrasts | source_freqmedium | 0.000983863 | 0.00295159 | TRUE |
| exp2_unfiltered | Reference contrasts | source_freqlow | 6.68504e-07 | 2.67402e-06 | TRUE |
| exp2_unfiltered | Reference contrasts | target_freqmedium | 0.0673311 | 0.134662 | FALSE |
| exp2_unfiltered | Reference contrasts | target_freqlow | 0.556157 | 0.556157 | FALSE |
| exp2_filtered | Reference contrasts | frameF2 | 8.19264e-283 | 5.73485e-282 | TRUE |
| exp2_filtered | Reference contrasts | frameF3 | 5.82647e-188 | 3.49588e-187 | TRUE |
| exp2_filtered | Reference contrasts | frameF4 | 3.62448e-113 | 1.81224e-112 | TRUE |
| exp2_filtered | Reference contrasts | frameF5 | 2.73405e-292 | 2.18724e-291 | TRUE |
| exp2_filtered | Reference contrasts | source_freqmedium | 0.00350245 | 0.0105073 | TRUE |
| exp2_filtered | Reference contrasts | source_freqlow | 3.20105e-05 | 0.000128042 | TRUE |
| exp2_filtered | Reference contrasts | target_freqmedium | 0.0843707 | 0.168741 | FALSE |
| exp2_filtered | Reference contrasts | target_freqlow | 0.673351 | 0.673351 | FALSE |

## Reproduce

From the analysis project directory, run source("run_reports.R") in R.
run_all.R also includes correction before report generation.
The correction families were defined during manuscript revision, after inspecting the existing results.

Method reference: https://stat.ethz.ch/R-manual/R-devel/library/stats/html/p.adjust.html
