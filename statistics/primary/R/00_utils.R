if (!exists("project_root", inherits = TRUE)) {
  project_root <- normalizePath(getwd(), winslash = "/")
}

runs_root_default <- normalizePath(file.path(project_root, "..", "..", "results", "runs"), winslash = "/", mustWork = TRUE)
runs_root <- Sys.getenv("LEXCONFLICT_RUNS_ROOT", unset = runs_root_default)

required_packages <- c("lme4", "dplyr", "readr")
missing_packages <- required_packages[
  !vapply(required_packages, requireNamespace, logical(1), quietly = TRUE)
]
if (length(missing_packages) > 0L) {
  stop("Missing required R packages: ", paste(missing_packages, collapse = ", "))
}

dir.create(file.path(project_root, "data", "derived"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(project_root, "results", "models"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(project_root, "results", "tables"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(project_root, "results", "logs"), recursive = TRUE, showWarnings = FALSE)

read_result_csv <- function(path) {
  if (!file.exists(path)) {
    stop("Missing canonical input file: ", path)
  }

  readr::read_csv(
    path,
    col_types = readr::cols(.default = readr::col_character()),
    locale = readr::locale(encoding = "UTF-8"),
    na = character(),
    name_repair = "minimal",
    show_col_types = FALSE,
    progress = FALSE
  )
}

assert_columns <- function(data, required, label) {
  missing <- setdiff(required, names(data))
  if (length(missing) > 0L) {
    stop(label, " is missing columns: ", paste(missing, collapse = ", "))
  }
}

assert_no_duplicates <- function(data, columns, label) {
  duplicate_n <- data |>
    dplyr::count(dplyr::across(dplyr::all_of(columns)), name = "n") |>
    dplyr::filter(.data$n > 1L) |>
    nrow()
  if (duplicate_n > 0L) {
    stop(label, " has ", duplicate_n, " duplicated key(s): ", paste(columns, collapse = ", "))
  }
}

analysis_factorize <- function(data, experiment) {
  data <- data |>
    dplyr::mutate(
      response_ck = as.integer(.data$auto_label == "CK"),
      model = factor(.data$model),
      frame = factor(.data$frame_id, levels = paste0("F", 1:5)),
      source_freq = factor(.data$source_freq_band, levels = c("high", "medium", "low")),
      target_freq = factor(.data$target_freq_band, levels = c("high", "medium", "low")),
      mapping_id = factor(.data$mapping_id),
      word_category = factor(.data$source_category)
    )

  if (identical(experiment, "exp1")) {
    data <- data |>
      dplyr::mutate(context = factor(.data$context_type, levels = c("PK_context", "CK_context")))
  }

  droplevels(data)
}

capture_warnings <- function(expression) {
  warning_messages <- character()
  value <- withCallingHandlers(
    expression,
    warning = function(warning) {
      warning_messages <<- c(warning_messages, conditionMessage(warning))
      invokeRestart("muffleWarning")
    }
  )
  list(value = value, warnings = unique(warning_messages))
}

collapse_messages <- function(messages) {
  messages <- unique(messages[nzchar(messages)])
  if (length(messages) == 0L) "" else paste(messages, collapse = " | ")
}
