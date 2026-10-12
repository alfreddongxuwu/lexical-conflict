source(file.path(project_root, "R", "00_utils.R"), chdir = TRUE)

tables_dir <- file.path(project_root, "results", "tables")
omnibus_raw <- readr::read_csv(file.path(tables_dir, "fixed_effect_omnibus_wald.csv"), show_col_types = FALSE)
coefficients_raw <- readr::read_csv(file.path(tables_dir, "fixed_effect_coefficients.csv"), show_col_types = FALSE)

expected_analyses <- c("exp1_unfiltered", "exp1_filtered", "exp2_unfiltered", "exp2_filtered")
expected_effects <- list(
  exp1 = c("context", "frame", "source_freq", "target_freq"),
  exp2 = c("frame", "source_freq", "target_freq")
)
reference_contrasts <- c(paste0("frameF", 2:5), "source_freqmedium", "source_freqlow",
                        "target_freqmedium", "target_freqlow")
expected_contrasts <- list(exp1 = c("contextCK_context", reference_contrasts), exp2 = reference_contrasts)

adjust_family <- function(data, test_column, family_type, expected_tests) {
  assert_columns(data, c("analysis", "experiment", "sample", "p_value", test_column), family_type)
  assert_no_duplicates(data, c("analysis", test_column), family_type)
  if (!setequal(unique(data$analysis), expected_analyses)) {
    stop("Expected all four canonical analyses for ", family_type)
  }
  if (anyNA(data$p_value) || any(!is.finite(data$p_value)) || any(data$p_value < 0 | data$p_value > 1)) {
    stop("Missing or invalid raw p-values in ", family_type)
  }
  for (analysis_name in expected_analyses) {
    rows <- data[data$analysis == analysis_name, ]
    experiment <- sub("_(unfiltered|filtered)$", "", analysis_name)
    sample <- sub("^exp[12]_", "", analysis_name)
    if (any(rows$experiment != experiment) || any(rows$sample != sample) ||
        !setequal(rows[[test_column]], expected_tests[[experiment]])) {
      stop("Unexpected test family: ", analysis_name, " / ", family_type)
    }
  }
  data |>
    dplyr::group_by(.data$analysis, .data$experiment, .data$sample) |>
    dplyr::mutate(
      p_holm = stats::p.adjust(.data$p_value, method = "holm"),
      adjustment_method = "holm",
      family_type = .env$family_type,
      family_id = paste(.data$analysis, .env$family_type, sep = ":"),
      family_n = dplyr::n(),
      significant_raw = .data$p_value < 0.05,
      significant_holm = .data$p_holm < 0.05,
      significance_changed = .data$significant_raw != .data$significant_holm
    ) |>
    dplyr::ungroup()
}

omnibus_holm <- adjust_family(omnibus_raw, "effect", "omnibus", expected_effects)
coefficients_holm <- adjust_family(
  dplyr::filter(coefficients_raw, .data$term != "(Intercept)"),
  "term", "reference_contrasts", expected_contrasts
)

family_summary <- dplyr::bind_rows(
  dplyr::select(omnibus_holm, analysis, experiment, sample, family_type:significance_changed),
  dplyr::select(coefficients_holm, analysis, experiment, sample, family_type:significance_changed)
) |>
  dplyr::group_by(.data$analysis, .data$experiment, .data$sample, .data$family_type, .data$family_id) |>
  dplyr::summarise(
    method = "holm", n_tests = dplyr::n(),
    significant_raw = sum(.data$significant_raw),
    significant_holm = sum(.data$significant_holm),
    changed_at_05 = sum(.data$significance_changed), .groups = "drop"
  )

readr::write_csv(omnibus_holm, file.path(tables_dir, "fixed_effect_omnibus_wald_holm.csv"))
readr::write_csv(coefficients_holm, file.path(tables_dir, "fixed_effect_coefficients_holm.csv"))
readr::write_csv(family_summary, file.path(tables_dir, "holm_family_summary.csv"))
cat("Holm adjustment:", sum(family_summary$n_tests), "tests in", nrow(family_summary),
    "families;", sum(family_summary$changed_at_05), "decisions changed at alpha = .05.\n")
