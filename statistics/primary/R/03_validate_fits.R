source(file.path(project_root, "R", "00_utils.R"), chdir = TRUE)
analysis_names <- c("exp1_unfiltered", "exp1_filtered", "exp2_unfiltered", "exp2_filtered")
table_names <- c("fixed_effect_coefficients.csv", "fixed_effect_omnibus_wald.csv",
  "random_effect_parameters.csv", "model_diagnostics.csv")
tables_dir <- file.path(project_root, "results", "tables")
for (table_name in table_names) {
  paths <- file.path(tables_dir, "by_analysis", analysis_names, table_name)
  if (!all(file.exists(paths))) stop("Missing worker tables: ", paste(paths[!file.exists(paths)], collapse = ", "))
  combined <- dplyr::bind_rows(lapply(paths, readr::read_csv, show_col_types = FALSE))
  readr::write_csv(combined, file.path(tables_dir, table_name))
}
diagnostics <- readr::read_csv(file.path(tables_dir, "model_diagnostics.csv"), show_col_types = FALSE)
coefficients <- readr::read_csv(file.path(tables_dir, "fixed_effect_coefficients.csv"), show_col_types = FALSE)
audit_rows <- list()
formula_lines <- character()
for (name in analysis_names) {
  fit <- readRDS(file.path(project_root, "results", "models", paste0(name, ".rds")))
  data <- readRDS(file.path(project_root, "data", "derived", paste0(name, ".rds")))
  frame <- model.frame(fit)
  grouping_names <- c("model", "word_category", "source_item_id", "target_item_id", "mapping_id")
  stopifnot(setequal(names(lme4::getME(fit, "cnms")), grouping_names),
    all(vapply(lme4::getME(fit, "cnms"), identical, logical(1), "(Intercept)")),
    length(lme4::getME(fit, "theta")) == 5L, nobs(fit) == nrow(data),
    identical(as.integer(frame$response_ck), as.integer(data$response_ck)),
    family(fit)$family == "binomial", family(fit)$link == "logit")
  for (column in setdiff(names(frame), "response_ck")) {
    stopifnot(identical(as.character(frame[[column]]), as.character(data[[column]])))
  }
  fixed_formula <- if (startsWith(name, "exp1")) ~ context + frame + source_freq + target_freq else ~ frame + source_freq + target_freq
  expected_x <- model.matrix(fixed_formula, data)
  fitted_x <- lme4::getME(fit, "X")
  stopifnot(identical(colnames(expected_x), colnames(fitted_x)),
    isTRUE(all.equal(unname(expected_x), unname(fitted_x), check.attributes = FALSE)))
  beta <- lme4::fixef(fit)
  rows <- coefficients[coefficients$analysis == name, ]
  stopifnot(setequal(rows$term, names(beta)),
    max(abs(rows$estimate[match(names(beta), rows$term)] - beta)) < 1e-10)
  hessian <- fit@optinfo$derivs$Hessian
  gradient <- fit@optinfo$derivs$gradient
  hessian_min <- min(eigen(hessian, symmetric = TRUE, only.values = TRUE)$values)
  scaled_gradient <- tryCatch(solve(chol(hessian), gradient), error = function(e) rep(NA_real_, length(gradient)))
  covariance <- as.matrix(vcov(fit))
  stopifnot(all(is.finite(beta)), all(is.finite(covariance)),
    min(eigen(covariance, symmetric = TRUE, only.values = TRUE)$values) > 0)
  code <- fit@optinfo$conv$opt
  if (is.null(code)) code <- 0L
  messages <- fit@optinfo$conv$lme4$messages
  if (is.null(messages)) messages <- character()
  non_singular_messages <- messages[!grepl("boundary.*singular|singular fit", messages, ignore.case = TRUE)]
  converged <- all(code == 0L) && length(non_singular_messages) == 0L
  j <- match(name, diagnostics$analysis)
  diagnostics$converged[[j]] <- converged
  diagnostics$singular[[j]] <- lme4::isSingular(fit, tol = 1e-4)
  audit_rows[[name]] <- data.frame(analysis = name, n = nobs(fit), same_rows_and_predictors = TRUE,
    requested_five_random_intercepts = TRUE, fixed_coefficients_verified = TRUE,
    optimizer_code = paste(code, collapse = ","), converged = converged,
    singular = lme4::isSingular(fit, tol = 1e-4), hessian_min_eigenvalue = hessian_min,
    max_abs_raw_gradient = max(abs(gradient)),
    max_abs_scaled_gradient = max(abs(scaled_gradient)),
    lme4_gradient_check = max(pmin(abs(gradient), abs(scaled_gradient))),
    fixed_vcov_positive_definite = TRUE, optimizer = paste(fit@optinfo$optimizer, collapse = ","),
    function_evaluations = fit@optinfo$feval)
  formula_lines <- c(formula_lines, paste0(name, ": ", paste(deparse(formula(fit)), collapse = " ")))
}
readr::write_csv(diagnostics, file.path(tables_dir, "model_diagnostics.csv"))
readr::write_csv(dplyr::bind_rows(audit_rows), file.path(tables_dir, "fit_validation.csv"))
writeLines(formula_lines, file.path(project_root, "results", "logs", "verified_formulas.txt"))
cat("Verified all four saved fits, exact input rows, requested formulas, and the supplied analysis datasets.\n")
