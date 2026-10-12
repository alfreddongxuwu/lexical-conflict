# Exp1/Exp2 binary CK GLMM with source and target item random intercepts

Outcome: exact `CK` labels are coded 1; `PK`, `BOTH`, and `OTHER` are coded 0.
Filtered analyses keep only rows with a model-specific matched baseline label of `EXPECTED`.
Holm correction is applied separately within each experiment, sample (unfiltered/filtered), and inference level.
Omnibus families contain 4 tests in Exp1 and 3 in Exp2. Each reference-contrast family contains all 9 non-intercept coefficients in Exp1 or all 8 in Exp2.
Family-wise error control applies within each stated family. The experiments, primary and robustness samples, and inference levels are separate families.
All 95% OR confidence intervals remain unadjusted Wald intervals; significance decisions use Holm-adjusted p-values.

## Multiple-comparisons correction

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

At alpha = .05, 0 of 48 significance decisions changed after correction.

## Sample sizes

| Experiment | Sample | N | CK n | CK % |
| --- | --- | --- | --- | --- |
| EXP1 | filtered | 42270 | 30371 | 71.85 |
| EXP1 | unfiltered | 54000 | 40540 | 75.07 |
| EXP2 | filtered | 23100 | 17971 | 77.80 |
| EXP2 | unfiltered | 27000 | 21487 | 79.58 |

## Model diagnostics

| Analysis | N | Converged | Singular | Max gradient | Theta n |
| --- | --- | --- | --- | --- | --- |
| exp1_unfiltered | 54000 | TRUE | FALSE | 2.03e-03 | 5 |
| exp1_filtered | 42270 | TRUE | FALSE | 8.83e-04 | 5 |
| exp2_unfiltered | 27000 | TRUE | FALSE | 5.33e-04 | 5 |
| exp2_filtered | 23100 | TRUE | FALSE | 4.20e-04 | 5 |

4 of 4 fits passed convergence checks; 0 were singular at tolerance 1e-4.

## Overall fixed-effect joint Wald tests

| Analysis | Effect | df | Chisq | p raw | p Holm |
| --- | --- | --- | --- | --- | --- |
| exp1_unfiltered | context | 1 | 4520.57 | < .001 | < .001 |
| exp1_unfiltered | frame | 4 | 3337.14 | < .001 | < .001 |
| exp1_unfiltered | source_freq | 2 | 55.23 | < .001 | < .001 |
| exp1_unfiltered | target_freq | 2 | 1.79 | .408 | .408 |
| exp1_filtered | context | 1 | 3408.31 | < .001 | < .001 |
| exp1_filtered | frame | 4 | 2927.09 | < .001 | < .001 |
| exp1_filtered | source_freq | 2 | 38.45 | < .001 | < .001 |
| exp1_filtered | target_freq | 2 | 1.57 | .456 | .456 |
| exp2_unfiltered | frame | 4 | 1921.78 | < .001 | < .001 |
| exp2_unfiltered | source_freq | 2 | 25.59 | < .001 | < .001 |
| exp2_unfiltered | target_freq | 2 | 3.50 | .174 | .174 |
| exp2_filtered | frame | 4 | 1859.13 | < .001 | < .001 |
| exp2_filtered | source_freq | 2 | 18.30 | < .001 | < .001 |
| exp2_filtered | target_freq | 2 | 3.29 | .193 | .193 |

Each test jointly evaluates the treatment-coded coefficients for one factor using the full model's fixed-effect covariance matrix.

## Fixed-effect coefficients

References: `PK_context`, `F1`, high source frequency, and high target frequency.

| Analysis | Contrast | Estimate | OR | 95% OR CI (unadjusted) | p raw | p Holm |
| --- | --- | --- | --- | --- | --- | --- |
| exp1_unfiltered | contextCK_context | 2.112 | 8.265 | [7.771, 8.789] | < .001 | < .001 |
| exp1_unfiltered | frameF2 | 2.007 | 7.441 | [6.825, 8.112] | < .001 | < .001 |
| exp1_unfiltered | frameF3 | 1.525 | 4.594 | [4.234, 4.983] | < .001 | < .001 |
| exp1_unfiltered | frameF4 | 0.977 | 2.655 | [2.458, 2.868] | < .001 | < .001 |
| exp1_unfiltered | frameF5 | 2.314 | 10.110 | [9.239, 11.064] | < .001 | < .001 |
| exp1_unfiltered | source_freqmedium | 0.393 | 1.481 | [1.215, 1.805] | < .001 | < .001 |
| exp1_unfiltered | source_freqlow | 0.753 | 2.124 | [1.741, 2.592] | < .001 | < .001 |
| exp1_unfiltered | target_freqmedium | 0.136 | 1.145 | [0.939, 1.397] | .181 | .361 |
| exp1_unfiltered | target_freqlow | 0.068 | 1.070 | [0.879, 1.302] | .500 | .500 |
| exp1_filtered | contextCK_context | 2.041 | 7.699 | [7.189, 8.245] | < .001 | < .001 |
| exp1_filtered | frameF2 | 2.045 | 7.726 | [7.032, 8.488] | < .001 | < .001 |
| exp1_filtered | frameF3 | 1.641 | 5.162 | [4.719, 5.648] | < .001 | < .001 |
| exp1_filtered | frameF4 | 1.076 | 2.932 | [2.692, 3.193] | < .001 | < .001 |
| exp1_filtered | frameF5 | 2.388 | 10.895 | [9.874, 12.021] | < .001 | < .001 |
| exp1_filtered | source_freqmedium | 0.351 | 1.420 | [1.149, 1.756] | .001 | .004 |
| exp1_filtered | source_freqlow | 0.684 | 1.982 | [1.596, 2.460] | < .001 | < .001 |
| exp1_filtered | target_freqmedium | 0.132 | 1.141 | [0.928, 1.404] | .211 | .423 |
| exp1_filtered | target_freqlow | 0.057 | 1.059 | [0.863, 1.300] | .584 | .584 |
| exp2_unfiltered | frameF2 | 2.646 | 14.098 | [12.232, 16.248] | < .001 | < .001 |
| exp2_unfiltered | frameF3 | 1.888 | 6.603 | [5.808, 7.507] | < .001 | < .001 |
| exp2_unfiltered | frameF4 | 1.342 | 3.826 | [3.390, 4.318] | < .001 | < .001 |
| exp2_unfiltered | frameF5 | 2.717 | 15.129 | [13.107, 17.462] | < .001 | < .001 |
| exp2_unfiltered | source_freqmedium | 0.585 | 1.795 | [1.267, 2.542] | < .001 | .003 |
| exp2_unfiltered | source_freqlow | 0.885 | 2.422 | [1.709, 3.433] | < .001 | < .001 |
| exp2_unfiltered | target_freqmedium | 0.272 | 1.313 | [0.981, 1.758] | .067 | .135 |
| exp2_unfiltered | target_freqlow | 0.087 | 1.091 | [0.816, 1.459] | .556 | .556 |
| exp2_filtered | frameF2 | 2.777 | 16.069 | [13.811, 18.697] | < .001 | < .001 |
| exp2_filtered | frameF3 | 2.049 | 7.757 | [6.761, 8.898] | < .001 | < .001 |
| exp2_filtered | frameF4 | 1.490 | 4.437 | [3.899, 5.049] | < .001 | < .001 |
| exp2_filtered | frameF5 | 2.866 | 17.570 | [15.070, 20.484] | < .001 | < .001 |
| exp2_filtered | source_freqmedium | 0.541 | 1.718 | [1.195, 2.471] | .004 | .011 |
| exp2_filtered | source_freqlow | 0.780 | 2.182 | [1.510, 3.151] | < .001 | < .001 |
| exp2_filtered | target_freqmedium | 0.251 | 1.286 | [0.967, 1.710] | .084 | .169 |
| exp2_filtered | target_freqlow | 0.060 | 1.062 | [0.802, 1.407] | .673 | .673 |

Full-precision results and model diagnostics are in `results/tables/`.
