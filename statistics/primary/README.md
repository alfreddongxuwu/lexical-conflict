# Reported random-intercept models

Exp1: `response_ck ~ context + frame + source_freq + target_freq + (1 | model) + (1 | word_category) + (1 | source_item_id) + (1 | target_item_id) + (1 | mapping_id)`.
Exp2 omits context. CK is 1; PK/BOTH/OTHER are 0. References: PK_context, F1, high source frequency, high target frequency.

Four supplied fits: Exp1 unfiltered/filtered (54,000 / 42,270), Exp2 unfiltered/filtered (27,000 / 23,100). All four converged and are nonsingular at tolerance 1e-4. Estimation: R 4.5.2, lme4 2.0-1, binomial logit, bobyqa, maxfun 200000, nAGQ 1. Holm families are separate by experiment, sample and inference level. Confidence intervals are unadjusted 95% Wald intervals.

From the repository root:

```sh
Rscript statistics/primary/prepare_inputs.R
Rscript statistics/primary/run_reports.R
Rscript statistics/primary/run_all.R
```

The input construction reads the supplied coded responses directly.
