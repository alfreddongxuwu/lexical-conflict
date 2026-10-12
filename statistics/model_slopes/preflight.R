args <- commandArgs(trailingOnly = FALSE)
project_root <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", args, value = TRUE)[[1L]]), winslash = "/"))
options(contrasts = c("contr.treatment", "contr.poly"))
for (d in c("tables", "logs")) dir.create(file.path(project_root, "results", d), recursive = TRUE, showWarnings = FALSE)
source(file.path(project_root, "R", "common.R"))
output_root <- if ("--validation" %in% commandArgs(trailingOnly = TRUE)) file.path(project_root, "validation", "preflight") else file.path(project_root, "results")
for (subdir in c("tables", "logs")) dir.create(file.path(output_root, subdir), recursive = TRUE, showWarnings = FALSE)
rows <- list()
block_rows <- list()
for (name in analysis_order) {
  data <- read_input(name)
  spec <- spec_for(name)
  parsed <- lme4::glFormula(spec$formula, data = data, family = binomial(link = "logit"))
  verify_random_blocks(parsed$reTrms$cnms, parsed$reTrms$theta, name)
  stopifnot(nrow(parsed$fr) == expected_n[[name]])
  rows[[name]] <- data.frame(analysis = name, n = nrow(data), formula = formula_text(spec$formula),
    theta_parameters = length(parsed$reTrms$theta), fixed_coefficients = ncol(parsed$X),
    random_coefficients = nrow(parsed$reTrms$Zt), data_verified = TRUE, formula_verified = TRUE)
  for (i in seq_along(parsed$reTrms$cnms)) {
    block_rows[[length(block_rows) + 1L]] <- data.frame(analysis = name, block = i,
      group = names(parsed$reTrms$cnms)[[i]], coefficients = paste(parsed$reTrms$cnms[[i]], collapse = ";"),
      dimension = length(parsed$reTrms$cnms[[i]]))
  }
}
write_csv(do.call(rbind, rows), file.path(output_root, "tables", "preflight.csv"))
write_csv(do.call(rbind, block_rows), file.path(output_root, "tables", "random_structure.csv"))
writeLines(capture.output(sessionInfo()), file.path(output_root, "logs", "preflight_session.txt"))
cat("Verified four input datasets and exact requested random-effect blocks; no models fitted in preflight.\n")
print(do.call(rbind, rows)[, c("analysis", "n", "theta_parameters", "fixed_coefficients", "random_coefficients")], row.names = FALSE)
