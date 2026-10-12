suppressPackageStartupMessages({
  library(ggplot2)
  library(grid)
})

script_flag <- grep("^--file=", commandArgs(FALSE), value = TRUE)
script_path <- sub("^--file=", "", script_flag[[1L]])
script_dir <- dirname(normalizePath(script_path, winslash = "/", mustWork = TRUE))

args <- commandArgs(TRUE)
data_root <- if (length(args) >= 1L) {
  normalizePath(args[[1L]], winslash = "/", mustWork = TRUE)
} else {
  normalizePath(
    file.path(script_dir, "..", "..", "..", "statistics", "primary"),
    winslash = "/",
    mustWork = TRUE
  )
}

main_dir <- normalizePath(
  file.path(script_dir, "..", "main"),
  winslash = "/",
  mustWork = TRUE
)
output_paths <- c(
  unfiltered = file.path(
    script_dir, "figureA_exp2_full_models_unfiltered.pdf"
  ),
  filtered = file.path(
    script_dir, "figureA_exp2_full_models_filtered.pdf"
  )
)
filter_titles <- c(
  unfiltered = "Unfiltered",
  filtered = "Baseline-filtered"
)
panel_scripts <- c(
  framing = "panel_exp1_pragmatic_framing.R",
  source = "panel_exp1_source_frequency.R",
  target = "panel_exp1_target_frequency.R",
  model_size = "panel_exp1_model_size.R"
)
panel_titles <- c(
  framing = "Prompt Framing",
  source = "Source Frequency",
  target = "Target Frequency",
  model_size = "Model Size"
)
transition_script <- file.path(main_dir, "panel_exp1_semantic_context.R")

missing_scripts <- panel_scripts[
  !file.exists(file.path(main_dir, panel_scripts))
]
if (length(missing_scripts)) {
  stop("Missing main panel scripts: ", paste(missing_scripts, collapse = ", "))
}
if (!file.exists(transition_script)) {
  stop("Missing Context source script used for the Transition panel: ", transition_script)
}

reduced_model_block <- paste(c(
  "model_labels <- c(",
  "  chatgpt5_5_instant = \"ChatGPT-5.5\",",
  "  deepseek_llm_7b = \"DeepSeek-7B\",",
  "  gemma3_4b = \"Gemma3-4B\",",
  "  llama3_8b = \"Llama3-8B\",",
  "  qwen3_8b = \"Qwen3-8B\"",
  ")"
), collapse = "\n")

full_model_block <- paste(c(
  "model_labels <- c(",
  "  chatgpt5_5_instant = \"ChatGPT-5.5\",",
  "  deepseek_llm_7b = \"DeepSeek-7B\",",
  "  deepseek_llm_67b = \"DeepSeek-67B\",",
  "  gemma3_4b = \"Gemma3-4B\",",
  "  gemma3_27b = \"Gemma3-27B\",",
  "  llama3_8b = \"Llama3-8B\",",
  "  llama3_70b = \"Llama3-70B\",",
  "  qwen3_8b = \"Qwen3-8B\",",
  "  qwen3_32b = \"Qwen3-32B\"",
  ")"
), collapse = "\n")

reduced_short_block <- paste(c(
  "short_model_labels <- c(",
  "  \"GPT-5.5\", \"DeepSeek-7B\", \"Gemma3-4B\", \"Llama3-8B\", \"Qwen3-8B\"",
  ")"
), collapse = "\n")

full_short_block <- paste(c(
  "short_model_labels <- c(",
  "  \"GPT-5.5\",",
  "  \"DeepSeek-7B\", \"DeepSeek-67B\",",
  "  \"Gemma3-4B\", \"Gemma3-27B\",",
  "  \"Llama3-8B\", \"Llama3-70B\",",
  "  \"Qwen3-8B\", \"Qwen3-32B\"",
  ")"
), collapse = "\n")

all_model_ids <- c(
  "chatgpt5_5_instant",
  "deepseek_llm_7b", "deepseek_llm_67b",
  "gemma3_4b", "gemma3_27b",
  "llama3_8b", "llama3_70b",
  "qwen3_8b", "qwen3_32b"
)
all_model_labels <- c(
  chatgpt5_5_instant = "GPT-5.5",
  deepseek_llm_7b = "DeepSeek-7B",
  deepseek_llm_67b = "DeepSeek-67B",
  gemma3_4b = "Gemma3-4B",
  gemma3_27b = "Gemma3-27B",
  llama3_8b = "Llama3-8B",
  llama3_70b = "Llama3-70B",
  qwen3_8b = "Qwen3-8B",
  qwen3_32b = "Qwen3-32B"
)
status_levels <- c("CK", "PK", "OTHER", "BOTH")
status_colours <- setNames(
  grDevices::colorRampPalette(c("#795037", "#A77A5B", "#D8BBA5"))(4),
  status_levels
)
title_theme <- theme(
  plot.title = element_text(
    family = "sans",
    face = "bold",
    colour = "#000000",
    size = 12,
    hjust = 0.5,
    margin = margin(b = 2)
  )
)

appendix_text_replacements <- c(
  "base_size = 15.3" = "base_size = 10.2",
  "axis.title = element_text(size = 15.6)" =
    "axis.title = element_text(size = 10.4)",
  "axis.text.y = element_text(size = 13.8)" =
    "axis.text.y = element_text(size = 9.2)",
  "axis.text.x = element_text(size = 8.1)" =
    "axis.text.x = element_text(size = 5.4)",
  "axis.text.x = element_text(size = 8.7)" =
    "axis.text.x = element_text(size = 5.8)",
  "axis.text.x = element_text(size = 10.5)" =
    "axis.text.x = element_text(size = 7.0)",
  "legend.text = element_text(size = 8.4" =
    "legend.text = element_text(size = 5.6",
  "legend.text = element_text(size = 13.5" =
    "legend.text = element_text(size = 9.0"
)

load_full_panel <- function(panel_name, filter_state) {
  source_path <- file.path(main_dir, panel_scripts[[panel_name]])
  source_text <- paste(
    readLines(source_path, warn = FALSE, encoding = "UTF-8"),
    collapse = "\n"
  )

  for (old_text in names(appendix_text_replacements)) {
    source_text <- gsub(
      old_text,
      appendix_text_replacements[[old_text]],
      source_text,
      fixed = TRUE
    )
  }

  source_text <- sub(
    "exp1_unfiltered.csv",
    paste0("exp2_", filter_state, ".csv"),
    source_text,
    fixed = TRUE
  )
  source_text <- sub(
    reduced_model_block,
    full_model_block,
    source_text,
    fixed = TRUE
  )
  source_text <- sub(
    reduced_short_block,
    full_short_block,
    source_text,
    fixed = TRUE
  )
  source_text <- gsub(
    "stopifnot(nrow(dat) == 54000L)",
    "stopifnot(nrow(dat) > 0L, all(dat$response_ck %in% c(0, 1)))",
    source_text,
    fixed = TRUE
  )
  source_text <- gsub(
    "stopifnot(nrow(plot_data) == 30000L, !anyNA(plot_data$model_label))",
    "stopifnot(nrow(plot_data) > 0L, !anyNA(plot_data$model_label))",
    source_text,
    fixed = TRUE
  )
  source_text <- gsub(
    "stopifnot(nrow(plot_data) == 48000L)",
    "stopifnot(nrow(plot_data) > 0L)",
    source_text,
    fixed = TRUE
  )

  panel_env <- new.env(parent = globalenv())
  panel_env$commandArgs <- function(trailingOnly = FALSE) {
    if (isTRUE(trailingOnly)) data_root else base::commandArgs(FALSE)
  }
  panel_env$ggsave <- function(...) invisible(NULL)
  panel_env$cat <- function(...) invisible(NULL)

  eval(parse(text = source_text, keep.source = FALSE), envir = panel_env)
  if (!inherits(panel_env$plot, "ggplot")) {
    stop("No ggplot produced for ", panel_name, " (", filter_state, ")")
  }

  plot_object <- panel_env$plot
  for (index in seq_along(plot_object$layers)) {
    if (inherits(plot_object$layers[[index]]$geom, "GeomRect")) {
      plot_object$layers[[index]]$aes_params$colour <- NA
    }
  }

  plot_object +
    labs(title = panel_titles[[panel_name]]) +
    title_theme
}

load_transition_panel <- function(filter_state) {
  source_text <- paste(
    readLines(transition_script, warn = FALSE, encoding = "UTF-8"),
    collapse = "\n"
  )

  for (old_text in names(appendix_text_replacements)) {
    source_text <- gsub(
      old_text,
      appendix_text_replacements[[old_text]],
      source_text,
      fixed = TRUE
    )
  }

  source_text <- sub(
    "exp1_unfiltered.csv",
    paste0("exp2_", filter_state, ".csv"),
    source_text,
    fixed = TRUE
  )
  source_text <- sub(
    reduced_model_block,
    full_model_block,
    source_text,
    fixed = TRUE
  )
  source_text <- sub(
    reduced_short_block,
    full_short_block,
    source_text,
    fixed = TRUE
  )

  original_data_setup <- paste(c(
    "dat <- read.csv(data_path, stringsAsFactors = FALSE, check.names = FALSE)",
    "stopifnot(nrow(dat) == 54000L)"
  ), collapse = "\n")
  transition_data_setup <- paste(c(
    "dat <- read.csv(data_path, stringsAsFactors = FALSE, check.names = FALSE)",
    "frequency_score <- c(low = 1L, medium = 2L, high = 3L)",
    "transition_direction <- unname(",
    "  frequency_score[dat$target_freq_band] -",
    "    frequency_score[dat$source_freq_band]",
    ")",
    "stopifnot(",
    "  nrow(dat) > 0L, !anyNA(transition_direction),",
    "  all(transition_direction != 0L),",
    "  all(dat$response_ck %in% c(0, 1))",
    ")",
    "dat$transition <- ifelse(",
    "  transition_direction > 0L,",
    "  \"toward_higher_target\",",
    "  \"toward_lower_target\"",
    ")"
  ), collapse = "\n")
  source_text <- sub(
    original_data_setup,
    transition_data_setup,
    source_text,
    fixed = TRUE
  )
  source_text <- gsub(
    "stopifnot(nrow(plot_data) == 30000L, !anyNA(plot_data$model_label))",
    "stopifnot(nrow(plot_data) > 0L, !anyNA(plot_data$model_label))",
    source_text,
    fixed = TRUE
  )
  source_text <- gsub("\\bcontext\\b", "transition", source_text)
  source_text <- gsub("context_levels", "transition_levels", source_text, fixed = TRUE)
  source_text <- gsub("PK_context", "toward_higher_target", source_text, fixed = TRUE)
  source_text <- gsub("CK_context", "toward_lower_target", source_text, fixed = TRUE)
  source_text <- gsub("PK transition", "Toward higher target", source_text, fixed = TRUE)
  source_text <- gsub("CK transition", "Toward lower target", source_text, fixed = TRUE)
  source_text <- gsub("# Context uses", "# Transition uses", source_text, fixed = TRUE)

  panel_env <- new.env(parent = globalenv())
  panel_env$commandArgs <- function(trailingOnly = FALSE) {
    if (isTRUE(trailingOnly)) data_root else base::commandArgs(FALSE)
  }
  panel_env$ggsave <- function(...) invisible(NULL)
  panel_env$cat <- function(...) invisible(NULL)

  eval(parse(text = source_text, keep.source = FALSE), envir = panel_env)
  if (!inherits(panel_env$plot, "ggplot")) {
    stop("No ggplot produced for transition (", filter_state, ")")
  }

  plot_object <- panel_env$plot
  for (index in seq_along(plot_object$layers)) {
    if (inherits(plot_object$layers[[index]]$geom, "GeomRect")) {
      plot_object$layers[[index]]$aes_params$colour <- NA
    }
  }

  plot_object + labs(title = "Transition") + title_theme
}
build_distribution_panel <- function(filter_state) {
  data_path <- file.path(
    data_root, "data", "derived", paste0("exp2_", filter_state, ".csv")
  )
  dat <- read.csv(data_path, stringsAsFactors = FALSE, check.names = FALSE)
  dat <- dat[
    dat$model %in% all_model_ids & dat$auto_label %in% status_levels,
    c("model", "auto_label"),
    drop = FALSE
  ]
  stopifnot(nrow(dat) > 0L)

  grid_data <- expand.grid(
    model = all_model_ids,
    status = status_levels,
    stringsAsFactors = FALSE
  )
  counts <- aggregate(
    list(n = rep.int(1L, nrow(dat))),
    by = list(model = dat$model, status = dat$auto_label),
    FUN = sum
  )
  stack_data <- merge(
    grid_data, counts,
    by = c("model", "status"),
    all.x = TRUE,
    sort = FALSE
  )
  stack_data$n[is.na(stack_data$n)] <- 0L
  stack_data$model_index <- match(stack_data$model, all_model_ids)
  stack_data$status_index <- match(stack_data$status, status_levels)
  stack_data <- stack_data[
    order(stack_data$model_index, stack_data$status_index),
    ,
    drop = FALSE
  ]

  totals <- ave(stack_data$n, stack_data$model, FUN = sum)
  stack_data$rate <- 100 * stack_data$n / totals
  stack_data$ymax <- ave(stack_data$rate, stack_data$model, FUN = cumsum)
  stack_data$ymin <- stack_data$ymax - stack_data$rate
  stack_data$status <- factor(
    stack_data$status,
    levels = status_levels,
    ordered = TRUE
  )

  axis_limits <- c(0.5, length(all_model_ids) + 0.5)
  region_width <- diff(axis_limits) * 4 / 5
  target_group_gap_fraction <- 0.100 / 2.755
  bar_gap <- diff(axis_limits) * target_group_gap_fraction / 2
  bar_width <- (
    region_width - (length(all_model_ids) - 1L) * bar_gap
  ) / length(all_model_ids)
  region_limits <- mean(axis_limits) + c(-0.5, 0.5) * region_width
  model_centres <- seq(
    region_limits[[1L]] + bar_width / 2,
    region_limits[[2L]] - bar_width / 2,
    length.out = length(all_model_ids)
  )
  stack_data$x_position <- model_centres[stack_data$model_index]
  separator_data <- stack_data[
    stack_data$status_index < length(status_levels),
    ,
    drop = FALSE
  ]

  ggplot(stack_data) +
    geom_rect(
      aes(
        xmin = x_position - bar_width / 2,
        xmax = x_position + bar_width / 2,
        ymin = ymin,
        ymax = ymax,
        fill = status
      ),
      colour = NA
    ) +
    geom_segment(
      data = separator_data,
      aes(
        x = x_position - bar_width / 2,
        xend = x_position + bar_width / 2,
        y = ymax,
        yend = ymax
      ),
      colour = "white",
      linewidth = 0.45,
      lineend = "butt",
      inherit.aes = FALSE
    ) +
    scale_fill_manual(
      values = status_colours,
      breaks = status_levels,
      drop = FALSE,
      name = NULL
    ) +
    scale_x_continuous(
      breaks = model_centres,
      labels = unname(all_model_labels[all_model_ids]),
      limits = axis_limits,
      expand = expansion(mult = 0)
    ) +
    scale_y_continuous(
      breaks = seq(0, 100, by = 20),
      labels = function(value) sprintf("%.0f", value),
      expand = expansion(mult = c(0, 0))
    ) +
    coord_cartesian(ylim = c(0, 103), clip = "on") +
    labs(
      title = "Response Type Distribution",
      x = NULL,
      y = "Rate (%)"
    ) +
    theme_classic(base_family = "sans", base_size = 10.2) +
    theme(
      text = element_text(family = "sans", colour = "#000000"),
      panel.border = element_blank(),
      panel.grid = element_blank(),
      axis.line = element_blank(),
      axis.line.x.bottom = element_line(colour = "#000000", linewidth = 0.45),
      axis.line.y.left = element_line(colour = "#000000", linewidth = 0.45),
      axis.ticks = element_line(colour = "#000000", linewidth = 0.34),
      axis.ticks.length = unit(2.5, "pt"),
      axis.title.y = element_text(size = 10.4, margin = margin(r = 5)),
      axis.text.y = element_text(size = 9.2),
      axis.text.x = element_text(
        size = 5.8, angle = 38, hjust = 1, vjust = 1
      ),
      plot.title = element_text(
        family = "sans", face = "bold", colour = "#000000",
        size = 12, hjust = 0.5, margin = margin(b = 2)
      ),
      legend.position = "inside",
      legend.position.inside = c(0.985, 0.025),
      legend.justification = c(1, 0),
      legend.direction = "vertical",
      legend.background = element_rect(
        fill = grDevices::adjustcolor("white", alpha.f = 0.90),
        colour = "#A6A6A6",
        linewidth = 0.42
      ),
      legend.key = element_rect(fill = "transparent", colour = NA),
      legend.key.height = unit(0.72, "lines"),
      legend.key.width = unit(0.90, "lines"),
      legend.key.spacing.y = unit(0, "pt"),
      legend.text = element_text(size = 7.2, margin = margin(l = 2)),
      legend.margin = margin(1.5, 2.5, 1.5, 2.5),
      plot.margin = margin(3, 4, 8, 5.6)
    )
}
build_page <- function(filter_state) {
  loaded <- lapply(names(panel_scripts), function(panel_name) {
    load_full_panel(panel_name, filter_state)
  })
  names(loaded) <- names(panel_scripts)

  transition_plot <- load_transition_panel(filter_state) +
    theme(plot.margin = margin(3, 4, 28.5, 5.6))
  model_size_plot <- loaded$model_size +
    theme(plot.margin = margin(3, 4, 27, 5.6))

  list(
    framing = loaded$framing,
    source = loaded$source,
    target = loaded$target,
    transition = transition_plot,
    model_size = model_size_plot,
    distribution = build_distribution_panel(filter_state)
  )
}

page_width <- 18.60
page_height <- 430 / 72
header_height <- 0.34
row_gap <- 0.20
panel_height_difference <- 0.10
content_height <- page_height - header_height
panel_height_total <- content_height - row_gap
top_height <- (panel_height_total - panel_height_difference) / 2
bottom_height <- top_height + panel_height_difference

for (filter_state in names(output_paths)) {
  plots <- build_page(filter_state)
  figure_title <- paste(
    "Experiment 2",
    filter_titles[[filter_state]],
    sep = ": "
  )
  grDevices::cairo_pdf(
    output_paths[[filter_state]],
    width = page_width,
    height = page_height,
    bg = "white"
  )

  grid.newpage()
  grid.text(
    figure_title,
    x = unit(0.5, "npc"),
    y = unit(content_height + header_height / 2, "in"),
    gp = gpar(fontfamily = "sans", fontface = "bold", fontsize = 14)
  )
  pushViewport(viewport(
    x = unit(0.5, "npc"),
    y = unit(bottom_height + row_gap + top_height / 2, "in"),
    width = unit(page_width, "in"),
    height = unit(top_height, "in"),
    layout = grid.layout(nrow = 1, ncol = 3)
  ))
  for (index in seq_len(3L)) {
    print(
      plots[[index]],
      vp = viewport(layout.pos.row = 1, layout.pos.col = index)
    )
  }
  upViewport()

  pushViewport(viewport(
    x = unit(0.5, "npc"),
    y = unit(bottom_height / 2, "in"),
    width = unit(page_width, "in"),
    height = unit(bottom_height, "in"),
    layout = grid.layout(nrow = 1, ncol = 3)
  ))
  for (index in 4:6) {
    print(
      plots[[index]],
      vp = viewport(layout.pos.row = 1, layout.pos.col = index - 3L)
    )
  }
  upViewport()
  dev.off()
}

cat("Wrote:\n", paste(output_paths, collapse = "\n"), "\n")
