source(file.path(project_root, "R", "00_utils.R"), chdir = TRUE)

cat("Preparing canonical Exp1, Exp2, and baseline data...\n")

main_required <- c(
  "prompt_id", "mapping_id", "frame_id", "frame_name", "context_type",
  "context_category", "source_item_id", "target_item_id", "source_category",
  "target_category", "source_freq_band", "target_freq_band",
  "source_sentence_zh", "auto_label", "status"
)
baseline_required <- c(
  "prompt_id", "baseline_type", "source_item_id", "context_category",
  "source_sentence_zh", "baseline_label", "status"
)
allowed_response_labels <- c("PK", "CK", "BOTH", "OTHER")
allowed_baseline_labels <- c("EXPECTED", "OTHER")

experiment_models <- function(experiment) {
  root <- file.path(runs_root, experiment)
  if (!dir.exists(root)) stop("Missing experiment directory: ", root)
  sort(basename(list.dirs(root, recursive = FALSE, full.names = TRUE)))
}

model_ids <- Reduce(
  intersect,
  list(experiment_models("main"), experiment_models("exp2"), experiment_models("baseline"))
)
if (length(model_ids) != 9L) {
  stop("Expected 9 shared models, found ", length(model_ids), ": ", paste(model_ids, collapse = ", "))
}

input_paths <- character()

read_experiment_model <- function(experiment, model_id, expected_rows) {
  path <- file.path(runs_root, experiment, model_id, "responses_autocoded.csv")
  input_paths <<- c(input_paths, path)
  data <- read_result_csv(path)
  assert_columns(data, main_required, paste(experiment, model_id))
  if (nrow(data) != expected_rows) {
    stop(experiment, "/", model_id, ": expected ", expected_rows, " rows, found ", nrow(data))
  }
  assert_no_duplicates(data, "prompt_id", paste(experiment, model_id))
  unexpected <- setdiff(unique(data$auto_label), allowed_response_labels)
  if (length(unexpected) > 0L) {
    stop(experiment, "/", model_id, ": unexpected auto_label values: ", paste(unexpected, collapse = ", "))
  }
  data |>
    dplyr::select(dplyr::all_of(main_required)) |>
    dplyr::mutate(model = model_id, .before = 1L)
}

read_baseline_model <- function(model_id) {
  path <- file.path(runs_root, "baseline", model_id, "responses_baseline_autocoded.csv")
  input_paths <<- c(input_paths, path)
  data <- read_result_csv(path)
  assert_columns(data, baseline_required, paste("baseline", model_id))
  if (nrow(data) != 750L) {
    stop("baseline/", model_id, ": expected 750 rows, found ", nrow(data))
  }
  assert_no_duplicates(data, "prompt_id", paste("baseline", model_id))
  unexpected <- setdiff(unique(data$baseline_label), allowed_baseline_labels)
  if (length(unexpected) > 0L) {
    stop("baseline/", model_id, ": unexpected labels: ", paste(unexpected, collapse = ", "))
  }
  data |>
    dplyr::select(dplyr::all_of(baseline_required)) |>
    dplyr::mutate(model = model_id, .before = 1L)
}

exp1_raw <- dplyr::bind_rows(lapply(model_ids, read_experiment_model, experiment = "main", expected_rows = 6000L))
exp2_raw <- dplyr::bind_rows(lapply(model_ids, read_experiment_model, experiment = "exp2", expected_rows = 3000L))
baseline_raw <- dplyr::bind_rows(lapply(model_ids, read_baseline_model))

if (!setequal(unique(exp1_raw$context_type), c("PK_context", "CK_context"))) {
  stop("Exp1 context_type levels are invalid")
}
if (!identical(unique(exp2_raw$context_type), "within_category_context")) {
  stop("Exp2 context_type must be within_category_context")
}

baseline_exp1_key <- baseline_raw |>
  dplyr::transmute(
    model = .data$model,
    source_item_id = .data$source_item_id,
    matched_baseline_context_category = .data$context_category,
    matched_baseline_type = .data$baseline_type,
    matched_baseline_prompt_id = .data$prompt_id,
    matched_baseline_label = .data$baseline_label,
    matched_baseline_status = .data$status
  )
assert_no_duplicates(
  baseline_exp1_key,
  c("model", "source_item_id", "matched_baseline_context_category", "matched_baseline_type"),
  "Exp1 baseline key"
)

exp1_enriched <- exp1_raw |>
  dplyr::mutate(
    matched_baseline_type = dplyr::if_else(
      .data$context_type == "PK_context", "normal_lexical", "anomalous_no_lexicon"
    ),
    matched_baseline_context_category = dplyr::if_else(
      .data$context_type == "PK_context", .data$source_category, .data$target_category
    )
  ) |>
  dplyr::left_join(
    baseline_exp1_key,
    by = c("model", "source_item_id", "matched_baseline_context_category", "matched_baseline_type")
  )
if (any(is.na(exp1_enriched$matched_baseline_label))) {
  stop("Exp1 contains missing baseline matches")
}

baseline_exp2_key <- baseline_raw |>
  dplyr::filter(.data$baseline_type == "normal_lexical") |>
  dplyr::transmute(
    model = .data$model,
    source_item_id = .data$source_item_id,
    baseline_source_sentence_zh = .data$source_sentence_zh,
    matched_baseline_type = .data$baseline_type,
    matched_baseline_prompt_id = .data$prompt_id,
    matched_baseline_label = .data$baseline_label,
    matched_baseline_status = .data$status
  )
assert_no_duplicates(baseline_exp2_key, c("model", "source_item_id"), "Exp2 baseline key")

exp2_enriched <- exp2_raw |>
  dplyr::left_join(baseline_exp2_key, by = c("model", "source_item_id"))
if (any(is.na(exp2_enriched$matched_baseline_label))) {
  stop("Exp2 contains missing baseline matches")
}
if (any(exp2_enriched$source_sentence_zh != exp2_enriched$baseline_source_sentence_zh)) {
  stop("Exp2 contains source-sentence mismatches against normal lexical baseline")
}

analysis_sets <- list(
  exp1_unfiltered = analysis_factorize(exp1_enriched, "exp1"),
  exp1_filtered = analysis_factorize(
    dplyr::filter(exp1_enriched, .data$matched_baseline_label == "EXPECTED"), "exp1"
  ),
  exp2_unfiltered = analysis_factorize(exp2_enriched, "exp2"),
  exp2_filtered = analysis_factorize(
    dplyr::filter(exp2_enriched, .data$matched_baseline_label == "EXPECTED"), "exp2"
  )
)

for (name in names(analysis_sets)) {
  saveRDS(analysis_sets[[name]], file.path(project_root, "data", "derived", paste0(name, ".rds")))
  readr::write_csv(
    analysis_sets[[name]],
    file.path(project_root, "data", "derived", paste0(name, ".csv")),
    na = ""
  )
}

sample_sizes <- dplyr::bind_rows(lapply(names(analysis_sets), function(name) {
  parts <- strsplit(name, "_", fixed = TRUE)[[1L]]
  analysis_sets[[name]] |>
    dplyr::count(.data$model, name = "n") |>
    dplyr::mutate(
      experiment = parts[[1L]],
      sample = paste(parts[-1L], collapse = "_"),
      ck_n = vapply(
        as.character(.data$model),
        function(model_id) sum(analysis_sets[[name]]$response_ck[analysis_sets[[name]]$model == model_id]),
        integer(1)
      ),
      ck_rate = .data$ck_n / .data$n,
      .before = 1L
    )
}))
sample_sizes <- dplyr::bind_rows(
  sample_sizes,
  sample_sizes |>
    dplyr::group_by(.data$experiment, .data$sample) |>
    dplyr::summarise(model = "ALL", n = sum(.data$n), ck_n = sum(.data$ck_n), ck_rate = .data$ck_n / .data$n, .groups = "drop")
)
readr::write_csv(sample_sizes, file.path(project_root, "results", "tables", "sample_sizes.csv"))

descriptive_rates <- dplyr::bind_rows(lapply(names(analysis_sets), function(name) {
  data <- analysis_sets[[name]]
  parts <- strsplit(name, "_", fixed = TRUE)[[1L]]
  experiment <- parts[[1L]]
  sample <- paste(parts[-1L], collapse = "_")
  factors <- c("model", if (experiment == "exp1") "context" else character(), "frame", "source_freq", "target_freq", "word_category")

  dplyr::bind_rows(lapply(factors, function(variable) {
    data |>
      dplyr::mutate(level = as.character(.data[[variable]])) |>
      dplyr::group_by(.data$level) |>
      dplyr::summarise(n = dplyr::n(), ck_n = sum(.data$response_ck), ck_rate = mean(.data$response_ck), .groups = "drop") |>
      dplyr::mutate(experiment = experiment, sample = sample, variable = variable, .before = 1L)
  }))
}))
readr::write_csv(descriptive_rates, file.path(project_root, "results", "tables", "descriptive_ck_rates.csv"))

cat("Prepared four analysis datasets.\n")
print(sample_sizes |> dplyr::filter(.data$model == "ALL"))
