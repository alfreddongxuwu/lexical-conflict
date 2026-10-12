args <- commandArgs(trailingOnly = FALSE)
project_root <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", args, value = TRUE)[[1L]]), winslash = "/"))
options(contrasts = c("contr.treatment", "contr.poly"))
for (d in c("models", "tables", "logs", "status")) dir.create(file.path(project_root, "results", d), recursive = TRUE, showWarnings = FALSE)
source(file.path(project_root, "R", "common.R"))
source(file.path(project_root, "R", "diagnostics.R"))
selection <- commandArgs(trailingOnly = TRUE)
stopifnot(length(selection) == 1L, selection[[1L]] %in% analysis_order)
analysis_name <- selection[[1L]]
spec <- spec_for(analysis_name)
table_dir <- file.path(project_root, "results", "tables", analysis_name)
dir.create(table_dir, recursive = TRUE, showWarnings = FALSE)
write_diagnostics <- function(x) {
  x$elapsed_seconds <- NULL
  write_csv(x, file.path(table_dir, "model_diagnostics.csv"))
}
event_file <- file.path(project_root, "results", "logs", paste0(analysis_name, "_events.log"))
worker_status <- file.path(project_root, "results", "status", paste0(analysis_name, ".csv"))
started <- Sys.time()
warnings_seen <- character()
messages_seen <- character()
post_errors <- character()
event <- function(stage, text) {
  line <- paste(utc_now(), stage, gsub("[\r\n]+", " ", text), sep = " | ")
  cat(line, "\n", file = event_file, append = TRUE)
  cat(line, "\n", file = stderr())
}
status <- function(stage, details = "") {
  write_csv(data.frame(analysis = analysis_name, stage = stage, updated_utc = utc_now(),
    elapsed_seconds = as.numeric(difftime(Sys.time(), started, units = "secs")),
    details = details), worker_status)
}
observe <- function(expression, stage) withCallingHandlers(expression,
  warning = function(w) {
    warnings_seen <<- unique(c(warnings_seen, paste0(stage, ": ", conditionMessage(w))))
    event(paste0(stage, "_warning"), conditionMessage(w))
    invokeRestart("muffleWarning")
  },
  message = function(m) {
    messages_seen <<- unique(c(messages_seen, paste0(stage, ": ", conditionMessage(m))))
    event(paste0(stage, "_message"), conditionMessage(m))
    invokeRestart("muffleMessage")
  })
safe_post <- function(expression, stage) tryCatch(observe(expression, stage), error = function(e) {
  post_errors <<- c(post_errors, paste0(stage, ": ", conditionMessage(e)))
  event(paste0(stage, "_error"), conditionMessage(e))
  NULL
})
status("loading_data")
data <- read_input(analysis_name)
writeLines(c(paste("Started UTC:", utc_now()), paste("N:", nrow(data)),
  "family = binomial(link = logit); optimizer = bobyqa; maxfun = 200000; nAGQ = 1; calc.derivs = TRUE; verbose = 2",
  paste("Formula:", formula_text(spec$formula))),
  file.path(project_root, "results", "logs", paste0(analysis_name, "_specification.txt")))
writeLines(capture.output(sessionInfo()), file.path(project_root, "results", "logs", paste0(analysis_name, "_session.txt")))
status("fitting")
event("fitting", formula_text(spec$formula))
fit_error <- ""
fit <- tryCatch(observe(lme4::glmer(formula = spec$formula, data = data,
  family = binomial(link = "logit"), nAGQ = 1L,
  control = lme4::glmerControl(optimizer = "bobyqa", optCtrl = list(maxfun = 200000L), calc.derivs = TRUE),
  verbose = 2L), "fit"), error = function(e) {
    fit_error <<- conditionMessage(e)
    event("fit_error", fit_error)
    NULL
  })
fit_elapsed <- as.numeric(difftime(Sys.time(), started, units = "secs"))
if (is.null(fit)) {
  write_diagnostics(data.frame(analysis = analysis_name, experiment = spec$experiment, sample = spec$sample,
    n = nrow(data), fit_returned = FALSE, converged = NA, singular = NA,
    elapsed_seconds = fit_elapsed, error = fit_error,
    warnings = paste(warnings_seen, collapse = " | "), messages = paste(messages_seen, collapse = " | ")))
  status("fit_failed", fit_error)
  quit(save = "no", status = 1L)
}
status("saving_model")
model_path <- file.path(project_root, "results", "models", paste0(analysis_name, ".rds"))
saveRDS(fit, model_path)
event("model_saved", file.path("results", "models", paste0(analysis_name, ".rds")))
status("diagnostics")
formula_ok <- isTRUE(safe_post({
  stopifnot(identical(formula_text(formula(fit)), formula_text(spec$formula)),
    nobs(fit) == nrow(data), identical(as.integer(model.frame(fit)$response_ck), as.integer(data$response_ck)))
  verify_random_blocks(lme4::getME(fit, "cnms"), lme4::getME(fit, "theta"), analysis_name)
  TRUE
}, "formula_validation"))
opt_code <- fit@optinfo$conv$opt
if (is.null(opt_code)) opt_code <- 0L
conv_messages <- fit@optinfo$conv$lme4$messages
if (is.null(conv_messages)) conv_messages <- character()
non_boundary_messages <- conv_messages[!grepl("boundary.*singular|singular fit", conv_messages, ignore.case = TRUE)]
converged <- all(opt_code == 0L) && !length(non_boundary_messages)
singular <- lme4::isSingular(fit, tol = 1e-4)
derivative_result <- safe_post(derivative_diagnostics(fit@optinfo$derivs), "derivative_diagnostics")
if (is.null(derivative_result)) derivative_result <- derivative_diagnostics(NULL)
if (!derivative_result$hessian_available) event("derivatives_unavailable", derivative_result$note)
diagnostics <- data.frame(analysis = analysis_name, experiment = spec$experiment, sample = spec$sample,
  n = nobs(fit), fit_returned = TRUE, converged = converged, singular = singular,
  formula_verified = formula_ok, optimizer_code = paste(opt_code, collapse = ","),
  theta_parameters = length(lme4::getME(fit, "theta")), fixed_coefficients = length(lme4::fixef(fit)),
  elapsed_seconds = fit_elapsed, log_likelihood = as.numeric(logLik(fit)), AIC = AIC(fit), BIC = BIC(fit),
  hessian_available = derivative_result$hessian_available, gradient_available = derivative_result$gradient_available,
  hessian_min_eigenvalue = derivative_result$hessian_min_eigenvalue,
  hessian_positive_definite = derivative_result$hessian_positive_definite,
  derivative_note = derivative_result$note,
  max_abs_raw_gradient = derivative_result$max_abs_raw_gradient,
  max_abs_scaled_gradient = derivative_result$max_abs_scaled_gradient,
  function_evaluations = fit@optinfo$feval, convergence_messages = paste(conv_messages, collapse = " | "),
  inference_caution = !converged || singular || !isTRUE(derivative_result$hessian_positive_definite) || !formula_ok)
write_diagnostics(diagnostics)
safe_post({
  random <- as.data.frame(lme4::VarCorr(fit))
  random <- cbind(analysis = analysis_name, random)
  write_csv(random, file.path(table_dir, "random_effect_parameters.csv"))
}, "random_effects")
safe_post({
  pca <- lme4::rePCA(fit)
  pca_rows <- do.call(rbind, lapply(names(pca), function(group) data.frame(
    analysis = analysis_name, group = group, component = seq_along(pca[[group]]$sdev), sdev = pca[[group]]$sdev)))
  write_csv(pca_rows, file.path(table_dir, "random_effect_pca.csv"))
}, "random_pca")
safe_post({
  beta <- lme4::fixef(fit)
  covariance <- as.matrix(vcov(fit))
  stopifnot(all(is.finite(covariance)), all(diag(covariance) > 0))
  se <- sqrt(diag(covariance))
  z <- beta / se
  p <- 2 * pnorm(abs(z), lower.tail = FALSE)
  coefficients <- data.frame(analysis = analysis_name, experiment = spec$experiment, sample = spec$sample,
    term = names(beta), estimate = unname(beta), std_error = unname(se), z_value = unname(z),
    p_value = unname(p), odds_ratio = exp(unname(beta)),
    odds_ratio_low = exp(unname(beta - qnorm(.975) * se)), odds_ratio_high = exp(unname(beta + qnorm(.975) * se)),
    inference_caution = diagnostics$inference_caution, row.names = NULL)
  coefficients$p_holm <- NA_real_
  selected <- coefficients$term != "(Intercept)"
  if (all(is.finite(coefficients$p_value[selected]))) {
    coefficients$p_holm[selected] <- p.adjust(coefficients$p_value[selected], method = "holm")
  }
  write_csv(coefficients, file.path(table_dir, "fixed_effect_coefficients.csv"))
  omnibus <- do.call(rbind, lapply(spec$effects, function(effect) {
    indices <- grep(paste0("^", effect), names(beta))
    values <- beta[indices]
    matrix <- covariance[indices, indices, drop = FALSE]
    statistic <- as.numeric(crossprod(values, solve(matrix, values)))
    data.frame(analysis = analysis_name, experiment = spec$experiment, sample = spec$sample,
      effect = effect, df = length(indices), chisq = statistic,
      p_value = pchisq(statistic, df = length(indices), lower.tail = FALSE),
      inference_caution = diagnostics$inference_caution)
  }))
  omnibus$p_holm <- if (all(is.finite(omnibus$p_value))) p.adjust(omnibus$p_value, "holm") else NA_real_
  write_csv(omnibus, file.path(table_dir, "fixed_effect_omnibus_wald.csv"))
}, "fixed_effects")
safe_post({
  summary_lines <- capture.output({
    cat("Formula:", formula_text(formula(fit)), "\n")
    cat("Converged:", converged, "\nSingular:", singular, "\nInference caution:", diagnostics$inference_caution, "\n")
    print(summary(fit))
    print(diagnostics)
  })
  writeLines(summary_lines, file.path(project_root, "results", "logs", paste0(analysis_name, "_summary.txt")))
}, "summary")
diagnostics$inference_caution <- diagnostics$inference_caution || length(post_errors) > 0L
 diagnostics$postprocess_errors <- paste(post_errors, collapse = " | ")
diagnostics$warnings <- paste(warnings_seen, collapse = " | ")
diagnostics$messages <- paste(messages_seen, collapse = " | ")
diagnostics$model_md5 <- unname(tools::md5sum(model_path))
write_diagnostics(diagnostics)
status(if (length(post_errors)) "completed_with_postprocess_errors" else "completed",
  paste0("converged=", converged, "; singular=", singular, "; caution=", diagnostics$inference_caution))
event("finished", paste0("converged=", converged, "; singular=", singular,
  "; fit_seconds=", round(fit_elapsed, 1), "; postprocess_errors=", length(post_errors)))
quit(save = "no", status = if (length(post_errors)) 2L else 0L)
