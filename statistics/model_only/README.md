# Appendix C.7: model_only

Exact model specifications and input checks are in `R/common.R`. Four supplied fits cover Exp1/Exp2, each unfiltered and baseline-filtered. All four returned singular fits at tolerance 1e-4; they are retained as alternative-model attempts. Fixed-effect estimates carry `inference_caution` and are not the reported primary inference.

```sh
Rscript statistics/model_only/preflight.R
Rscript statistics/model_only/fit_one.R exp1_unfiltered
```

The other analysis names are `exp1_filtered`, `exp2_unfiltered`, and `exp2_filtered`. `fit_one.R` writes the fit and its diagnostics. Existing result tables and models are the saved experiment outputs. Numerical derivatives were unavailable for these singular fits; unavailable Hessian values remain NA. R 4.5.2, lme4 2.0-1; binomial logit, bobyqa, maxfun 200000, nAGQ 1.
