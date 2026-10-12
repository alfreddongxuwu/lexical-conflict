required_packages <- c("lme4")
stopifnot(all(vapply(required_packages, requireNamespace, logical(1), quietly = TRUE)))
analysis_order <- c("exp1_unfiltered", "exp1_filtered", "exp2_unfiltered", "exp2_filtered")
expected_n <- c(exp1_unfiltered = 54000L, exp1_filtered = 42270L, exp2_unfiltered = 27000L, exp2_filtered = 23100L)
exp1_formula <- response_ck ~ context + frame + source_freq + target_freq +
  (0 + context | model) + (0 + frame | model) + (0 + source_freq | model) +
  (1 | mapping_id) + (1 | word_category) + (1 | source_item_id) + (1 | target_item_id)
exp2_formula <- response_ck ~ frame + source_freq + target_freq +
  (0 + frame | model) + (0 + source_freq | model) +
  (1 | mapping_id) + (1 | word_category) + (1 | source_item_id) + (1 | target_item_id)
spec_for <- function(name) {
  stopifnot(name %in% analysis_order)
  exp1 <- startsWith(name, "exp1")
  list(experiment = if (exp1) "exp1" else "exp2", sample = sub("^exp[12]_", "", name),
    formula = if (exp1) exp1_formula else exp2_formula,
    effects = if (exp1) c("context", "frame", "source_freq", "target_freq") else c("frame", "source_freq", "target_freq"),
    expected_theta = if (exp1) 28L else 25L,
    expected_model_block_sizes = if (exp1) c(2L, 3L, 5L) else c(3L, 5L))
}
utc_now <- function() format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
formula_text <- function(x) paste(deparse(x, width.cutoff = 500L), collapse = " ")
write_csv <- function(x, path) write.csv(x, path, row.names = FALSE, na = "NA", fileEncoding = "UTF-8")
read_input <- function(name) {
  manifest <- read.csv(file.path(project_root, "data", "input_manifest.csv"), stringsAsFactors = FALSE, check.names = FALSE)
  row <- manifest[manifest$analysis == name, ]
  stopifnot(nrow(row) == 1L)
  path <- file.path(project_root, row$snapshot_path)
  stopifnot(tolower(unname(tools::md5sum(path))) == tolower(row$md5))
  data <- readRDS(path)
  for (column in c("model", "mapping_id", "word_category", "source_item_id", "target_item_id")) data[[column]] <- factor(data[[column]])
  spec <- spec_for(name)
  columns <- unique(all.vars(spec$formula))
  stopifnot(nrow(data) == expected_n[[name]], !anyNA(data[, columns]),
    identical(as.integer(data$response_ck), as.integer(data$auto_label == "CK")),
    identical(levels(data$frame), paste0("F", 1:5)),
    identical(levels(data$source_freq), c("high", "medium", "low")),
    identical(levels(data$target_freq), c("high", "medium", "low")),
    nlevels(data$model) == 9L, nlevels(data$mapping_id) == 600L,
    nlevels(data$source_item_id) == 150L, nlevels(data$target_item_id) == 150L,
    nlevels(data$word_category) == 5L)
  if (spec$experiment == "exp1") stopifnot(identical(levels(data$context), c("PK_context", "CK_context")))
  if (spec$sample == "filtered") stopifnot(all(data$matched_baseline_label == "EXPECTED"))
  data
}
verify_random_blocks <- function(cnms, theta, name) {
  spec <- spec_for(name)
  model_blocks <- cnms[names(cnms) == "model"]
  others <- cnms[names(cnms) != "model"]
  stopifnot(identical(sort(as.integer(lengths(model_blocks))), spec$expected_model_block_sizes),
    setequal(names(others), c("mapping_id", "word_category", "source_item_id", "target_item_id")),
    all(vapply(others, identical, logical(1), "(Intercept)")),
    !any(vapply(model_blocks, function(x) "(Intercept)" %in% x, logical(1))),
    length(theta) == spec$expected_theta)
  invisible(TRUE)
}
