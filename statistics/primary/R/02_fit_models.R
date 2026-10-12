source(file.path(project_root, "R", "00_utils.R"), chdir = TRUE)

model_specs <- list(
  exp1_unfiltered = list(
    experiment = "exp1", sample = "unfiltered",
    formula = response_ck ~ context + frame + source_freq + target_freq +
      (1 | model) + (1 | word_category) + (1 | source_item_id) + (1 | target_item_id) + (1 | mapping_id),
    effects = c("context", "frame", "source_freq", "target_freq")
  ),
  exp1_filtered = list(
    experiment = "exp1", sample = "filtered",
    formula = response_ck ~ context + frame + source_freq + target_freq +
      (1 | model) + (1 | word_category) + (1 | source_item_id) + (1 | target_item_id) + (1 | mapping_id),
    effects = c("context", "frame", "source_freq", "target_freq")
  ),
  exp2_unfiltered = list(
    experiment = "exp2", sample = "unfiltered",
    formula = response_ck ~ frame + source_freq + target_freq +
      (1 | model) + (1 | word_category) + (1 | source_item_id) + (1 | target_item_id) + (1 | mapping_id),
    effects = c("frame", "source_freq", "target_freq")
  ),
  exp2_filtered = list(
    experiment = "exp2", sample = "filtered",
    formula = response_ck ~ frame + source_freq + target_freq +
      (1 | model) + (1 | word_category) + (1 | source_item_id) + (1 | target_item_id) + (1 | mapping_id),
    effects = c("frame", "source_freq", "target_freq")
  )
)

selected_analysis <- Sys.getenv("LEXCONFLICT_ANALYSIS", unset = "")
if (nzchar(selected_analysis)) {
  stopifnot(selected_analysis %in% names(model_specs))
  model_specs <- model_specs[selected_analysis]
}
fixed_rows <- list()
omnibus_rows <- list()
random_rows <- list()
diagnostic_rows <- list()

optimizer_control <- lme4::glmerControl(
  optimizer = "bobyqa",
  optCtrl = list(maxfun = 200000L),
  calc.derivs = TRUE
)

for (analysis_name in names(model_specs)) {
  spec <- model_specs[[analysis_name]]
  data_path <- file.path(project_root, "data", "derived", paste0(analysis_name, ".rds"))
  if (!file.exists(data_path)) stop("Run prepare_inputs.R first: ", data_path)
  data <- readRDS(data_path)
  data$source_item_id <- factor(data$source_item_id)
  data$target_item_id <- factor(data$target_item_id)
  table_output_dir <- file.path(project_root, "results", "tables", "by_analysis", analysis_name)
  dir.create(table_output_dir, recursive = TRUE, showWarnings = FALSE)

  cat("\nFitting ", analysis_name, " (n = ", nrow(data), ")...\n", sep = "")
  started <- Sys.time()
  fit_attempt <- tryCatch(
    capture_warnings(lme4::glmer(
      formula = spec$formula,
      data = data,
      family = stats::binomial(link = "logit"),
      control = optimizer_control,
      nAGQ = 1L
    )),
    error = function(error) list(value = NULL, warnings = character(), error = conditionMessage(error))
  )
  elapsed <- as.numeric(difftime(Sys.time(), started, units = "secs"))

  if (is.null(fit_attempt$value)) {
    diagnostic_rows[[analysis_name]] <- data.frame(
      analysis = analysis_name, experiment = spec$experiment, sample = spec$sample,
      n = nrow(data), converged = FALSE, singular = NA,
      max_abs_gradient = NA_real_, log_likelihood = NA_real_, AIC = NA_real_, BIC = NA_real_,
      theta_parameters = NA_integer_, elapsed_seconds = elapsed, warnings = "",
      convergence_messages = fit_attempt$error, stringsAsFactors = FALSE
    )
    next
  }

  fit <- fit_attempt$value
  saveRDS(fit, file.path(project_root, "results", "models", paste0(analysis_name, ".rds")))

  opt_code <- fit@optinfo$conv$opt
  if (is.null(opt_code)) opt_code <- 0L
  convergence_messages <- fit@optinfo$conv$lme4$messages
  if (is.null(convergence_messages)) convergence_messages <- character()
  gradient <- fit@optinfo$derivs$gradient
  max_abs_gradient <- if (is.null(gradient)) NA_real_ else max(abs(gradient))
  converged <- all(opt_code == 0L) && length(convergence_messages) == 0L
  singular <- lme4::isSingular(fit, tol = 1e-4)

  coefficient_matrix <- coef(summary(fit))
  fixed_rows[[analysis_name]] <- data.frame(
    term = rownames(coefficient_matrix),
    estimate = coefficient_matrix[, "Estimate"],
    std_error = coefficient_matrix[, "Std. Error"],
    z_value = coefficient_matrix[, "z value"],
    p_value = coefficient_matrix[, "Pr(>|z|)"],
    row.names = NULL,
    check.names = FALSE
  ) |>
    dplyr::mutate(
      analysis = analysis_name, experiment = spec$experiment, sample = spec$sample,
      odds_ratio = exp(.data$estimate),
      conf_low = .data$estimate - stats::qnorm(0.975) * .data$std_error,
      conf_high = .data$estimate + stats::qnorm(0.975) * .data$std_error,
      odds_ratio_low = exp(.data$conf_low), odds_ratio_high = exp(.data$conf_high),
      .before = 1L
    )

  random_rows[[analysis_name]] <- as.data.frame(lme4::VarCorr(fit)) |>
    dplyr::mutate(analysis = analysis_name, experiment = spec$experiment, sample = spec$sample, .before = 1L)

  joint_wald_for_effect <- function(effect) {
    fixed_estimates <- lme4::fixef(fit)
    indices <- grep(paste0("^", effect), names(fixed_estimates))
    if (length(indices) == 0L) stop("No fixed-effect coefficients found for ", effect)
    beta <- fixed_estimates[indices]
    covariance <- as.matrix(stats::vcov(fit))[indices, indices, drop = FALSE]
    chisq <- as.numeric(crossprod(beta, solve(covariance, beta)))
    degrees_freedom <- length(indices)
    data.frame(
      analysis = analysis_name, experiment = spec$experiment, sample = spec$sample,
      effect = effect, df = degrees_freedom, chisq = chisq,
      p_value = stats::pchisq(chisq, df = degrees_freedom, lower.tail = FALSE),
      stringsAsFactors = FALSE
    )
  }
  omnibus_rows[[analysis_name]] <- dplyr::bind_rows(lapply(spec$effects, joint_wald_for_effect))

  diagnostic_rows[[analysis_name]] <- data.frame(
    analysis = analysis_name, experiment = spec$experiment, sample = spec$sample,
    n = stats::nobs(fit), converged = converged, singular = singular,
    max_abs_gradient = max_abs_gradient, log_likelihood = as.numeric(stats::logLik(fit)),
    AIC = stats::AIC(fit), BIC = stats::BIC(fit),
    theta_parameters = length(lme4::getME(fit, "theta")), elapsed_seconds = elapsed,
    warnings = collapse_messages(fit_attempt$warnings),
    convergence_messages = collapse_messages(convergence_messages),
    stringsAsFactors = FALSE
  )

  summary_lines <- capture.output({
    cat("Analysis:", analysis_name, "\nFormula:\n")
    print(stats::formula(fit))
    cat("\nFit warnings:\n", collapse_messages(fit_attempt$warnings), "\n")
    cat("\nSingular:", singular, "\nConverged:", converged,
        "\nMax absolute raw gradient:", max_abs_gradient, "\n\n")
    print(summary(fit))
    cat("\nRandom effects:\n")
    print(lme4::VarCorr(fit), comp = c("Variance", "Std.Dev."))
    cat("\nFixed-effect omnibus joint Wald tests:\n")
    print(omnibus_rows[[analysis_name]])
  })
  writeLines(
    summary_lines,
    file.path(project_root, "results", "logs", paste0(analysis_name, "_summary.txt")),
    useBytes = TRUE
  )

  readr::write_csv(fixed_rows[[analysis_name]], file.path(table_output_dir, "fixed_effect_coefficients.csv"))
  readr::write_csv(omnibus_rows[[analysis_name]], file.path(table_output_dir, "fixed_effect_omnibus_wald.csv"))
  readr::write_csv(random_rows[[analysis_name]], file.path(table_output_dir, "random_effect_parameters.csv"))
  readr::write_csv(
    dplyr::select(diagnostic_rows[[analysis_name]], -dplyr::any_of("elapsed_seconds")),
    file.path(table_output_dir, "model_diagnostics.csv")
  )
  cat("Finished ", analysis_name, ": converged=", converged, ", singular=", singular, "\n", sep = "")
}

writeLines(capture.output(sessionInfo()), file.path(project_root, "results", "logs", paste0("session_info_", if (nzchar(selected_analysis)) selected_analysis else "all", ".txt")), useBytes = TRUE)
cat("\nAll requested full models and fixed-effect joint Wald tests have been attempted.\n")
