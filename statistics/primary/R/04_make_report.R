source(file.path(project_root, "R", "00_utils.R"), chdir = TRUE)

tables_dir <- file.path(project_root, "results", "tables")
sample_sizes <- readr::read_csv(file.path(tables_dir, "sample_sizes.csv"), show_col_types = FALSE)
diagnostics <- readr::read_csv(file.path(tables_dir, "model_diagnostics.csv"), show_col_types = FALSE)
omnibus <- readr::read_csv(file.path(tables_dir, "fixed_effect_omnibus_wald_holm.csv"), show_col_types = FALSE)
coefficients <- readr::read_csv(file.path(tables_dir, "fixed_effect_coefficients_holm.csv"), show_col_types = FALSE)

family_summary <- readr::read_csv(file.path(tables_dir, "holm_family_summary.csv"), show_col_types = FALSE)

format_p <- function(value) {
  ifelse(is.na(value), "NA", ifelse(value < 0.001, "< .001", sub("^0", "", sprintf("%.3f", value))))
}

markdown_table <- function(data) {
  data[] <- lapply(data, as.character)
  header <- paste0("| ", paste(names(data), collapse = " | "), " |")
  rule <- paste0("| ", paste(rep("---", ncol(data)), collapse = " | "), " |")
  rows <- apply(data, 1L, function(row) paste0("| ", paste(row, collapse = " | "), " |"))
  paste(c(header, rule, rows), collapse = "\n")
}

sample_report <- sample_sizes |>
  dplyr::filter(.data$model == "ALL") |>
  dplyr::transmute(
    Experiment = toupper(.data$experiment), Sample = .data$sample, N = .data$n,
    `CK n` = .data$ck_n, `CK %` = sprintf("%.2f", 100 * .data$ck_rate)
  )

diagnostic_report <- diagnostics |>
  dplyr::transmute(
    Analysis = .data$analysis, N = .data$n, Converged = .data$converged,
    Singular = .data$singular,
    `Max gradient` = ifelse(is.na(.data$max_abs_gradient), "NA", format(.data$max_abs_gradient, digits = 3, scientific = TRUE)),
    `Theta n` = .data$theta_parameters
  )

omnibus_report <- omnibus |>
  dplyr::transmute(
    Analysis = .data$analysis, Effect = .data$effect, df = .data$df,
    Chisq = ifelse(is.na(.data$chisq), "NA", sprintf("%.2f", .data$chisq)),
    `p raw` = format_p(.data$p_value), `p Holm` = format_p(.data$p_holm)
  )

coefficient_report <- coefficients |>
  dplyr::filter(.data$term != "(Intercept)") |>
  dplyr::transmute(
    Analysis = .data$analysis, Contrast = .data$term,
    Estimate = sprintf("%.3f", .data$estimate), OR = sprintf("%.3f", .data$odds_ratio),
    `95% OR CI (unadjusted)` = paste0("[", sprintf("%.3f", .data$odds_ratio_low), ", ", sprintf("%.3f", .data$odds_ratio_high), "]"),
    `p raw` = format_p(.data$p_value), `p Holm` = format_p(.data$p_holm)
  )

report <- c(
  "# Exp1/Exp2 binary CK GLMM with source and target item random intercepts", "",
  "Outcome: exact `CK` labels are coded 1; `PK`, `BOTH`, and `OTHER` are coded 0.",
  "Filtered analyses keep only rows with a model-specific matched baseline label of `EXPECTED`.",
  "Holm correction is applied separately within each experiment, sample (unfiltered/filtered), and inference level.",
  "Omnibus families contain 4 tests in Exp1 and 3 in Exp2. Each reference-contrast family contains all 9 non-intercept coefficients in Exp1 or all 8 in Exp2.",
  "Family-wise error control applies within each stated family. The experiments, primary and robustness samples, and inference levels are separate families.",
  "All 95% OR confidence intervals remain unadjusted Wald intervals; significance decisions use Holm-adjusted p-values.", "",
  "## Multiple-comparisons correction", "", markdown_table(family_summary), "",
  paste0("At alpha = .05, ", sum(family_summary$changed_at_05), " of ", sum(family_summary$n_tests), " significance decisions changed after correction."), "",
  "## Sample sizes", "", markdown_table(sample_report), "",
  "## Model diagnostics", "", markdown_table(diagnostic_report), "",
  paste0(sum(diagnostics$converged), " of ", nrow(diagnostics), " fits passed convergence checks; ", sum(diagnostics$singular), " were singular at tolerance 1e-4."), "",
  "## Overall fixed-effect joint Wald tests", "", markdown_table(omnibus_report), "",
  "Each test jointly evaluates the treatment-coded coefficients for one factor using the full model's fixed-effect covariance matrix.", "",
  "## Fixed-effect coefficients", "",
  "References: `PK_context`, `F1`, high source frequency, and high target frequency.", "",
  markdown_table(coefficient_report), "",
  "Full-precision results and model diagnostics are in `results/tables/`."
)

writeLines(report, file.path(project_root, "results", "ANALYSIS_REPORT.md"), useBytes = TRUE)
cat("Wrote results/ANALYSIS_REPORT.md\n")

format_p_numeric <- function(value) {
  ifelse(value == 0, "< machine range", formatC(value, format = "g", digits = 6))
}
p_details <- dplyr::bind_rows(
  omnibus |> dplyr::transmute(
    Analysis = .data$analysis, Family = "Omnibus", Test = .data$effect,
    `p raw` = format_p_numeric(.data$p_value), `p Holm` = format_p_numeric(.data$p_holm),
    `Significant after Holm` = .data$significant_holm
  ),
  coefficients |> dplyr::transmute(
    Analysis = .data$analysis, Family = "Reference contrasts", Test = .data$term,
    `p raw` = format_p_numeric(.data$p_value), `p Holm` = format_p_numeric(.data$p_holm),
    `Significant after Holm` = .data$significant_holm
  )
)
correction_report <- c(
  "# Multiple-comparisons correction", "",
  "Method: Holm (family-wise alpha = .05), applied to the saved raw Wald p-values with stats::p.adjust().", "",
  "## Scope", "",
  "- Exp1 unfiltered: 4 omnibus tests; a separate family of 9 non-intercept reference contrasts.",
  "- Exp2 unfiltered: 3 omnibus tests; a separate family of 8 non-intercept reference contrasts.",
  "- The baseline-filtered robustness analyses use the same respective family definitions, separately from the unfiltered analyses.",
  "- All four F2-F5 versus F1 contrasts, both source-frequency versus high contrasts, both target-frequency versus high contrasts, and the Exp1 context contrast are included, regardless of raw significance.",
  "- These are the existing reference contrasts. Medium versus low frequency and other additional pairwise contrasts have not been tested.",
  "- This defines 8 families and controls family-wise error within each family; it does not provide a single paper-wide error guarantee.", "",
  "## Result", "",
  paste0(sum(family_summary$n_tests), " tests adjusted; ", sum(family_summary$changed_at_05), " significance decisions changed at alpha = .05."), "",
  markdown_table(family_summary), "",
  "## Reporting", "",
  "Use Holm-adjusted p-values for inference. Both raw and adjusted values are retained in the new *_holm.csv tables.",
  "The original model fits, raw p-value tables, odds ratios, standard errors, and Wald confidence intervals are preserved.",
  "Confidence intervals are pointwise, unadjusted 95% Wald intervals. They are not simultaneous intervals and should not override the adjusted p-values when making significance decisions.",
  "A raw numeric p-value of zero reflects floating-point underflow for an extremely small tail probability. Such values are shown below as < machine range and should be reported as p < .001, never p = 0.", "",
  "## P-value audit", "", markdown_table(p_details), "",
  "## Reproduce", "",
  "From the analysis project directory, run source(\"run_reports.R\") in R.",
  "run_all.R also includes correction before report generation.",
  "The correction families were defined during manuscript revision, after inspecting the existing results.", "",
  "Method reference: https://stat.ethz.ch/R-manual/R-devel/library/stats/html/p.adjust.html"
)
writeLines(correction_report, file.path(project_root, "results", "MULTIPLE_COMPARISONS_REPORT.md"), useBytes = TRUE)
cat("Wrote results/MULTIPLE_COMPARISONS_REPORT.md\n")
