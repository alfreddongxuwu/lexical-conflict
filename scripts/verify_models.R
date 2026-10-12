file_arg <- grep("^--file=", commandArgs(), value = TRUE)
root <- normalizePath(file.path(dirname(sub("^--file=", "", file_arg[[1L]])), ".."), winslash = "/")
stopifnot(requireNamespace("lme4", quietly = TRUE))
names_expected <- c("exp1_unfiltered", "exp1_filtered", "exp2_unfiltered", "exp2_filtered")
n_expected <- c(54000L, 42270L, 27000L, 23100L)
for (specification in c("primary", "model_only", "model_slopes")) {
  project <- file.path(root, "statistics", specification)
  if (specification != "primary") {
    checks <- new.env(parent = globalenv())
    sys.source(file.path(project, "R/common.R"), envir = checks)
  }
  for (i in seq_along(names_expected)) {
    name <- names_expected[[i]]
    fit <- readRDS(file.path(project, "results/models", paste0(name, ".rds")))
    input <- readRDS(file.path(project, "data/derived", paste0(name, ".rds")))
    stopifnot(nobs(fit) == n_expected[[i]], nrow(input) == n_expected[[i]],
      identical(as.integer(model.frame(fit)$response_ck), as.integer(input$response_ck)),
      lme4::isSingular(fit, tol = 1e-4) == (specification != "primary"))
    if (specification == "primary") {
      blocks <- lme4::getME(fit, "cnms")
      stopifnot(setequal(names(blocks), c("model", "word_category", "mapping_id", "source_item_id", "target_item_id")),
        all(vapply(blocks, identical, logical(1), "(Intercept)")))
      table <- read.csv(file.path(project, "results/tables/fixed_effect_coefficients.csv"))
      table <- table[table$analysis == name, ]
    } else {
      checks$verify_random_blocks(lme4::getME(fit, "cnms"), lme4::getME(fit, "theta"), name)
      table <- read.csv(file.path(project, "results/tables", name, "fixed_effect_coefficients.csv"))
    }
    beta <- lme4::fixef(fit)
    stopifnot(setequal(names(beta), table$term), max(abs(beta - table$estimate[match(names(beta), table$term)])) < 1e-10)
    cat(specification, name, nobs(fit), "singular", lme4::isSingular(fit, tol = 1e-4), "verified\n")
  }
}
