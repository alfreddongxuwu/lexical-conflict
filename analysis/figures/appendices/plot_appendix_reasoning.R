suppressPackageStartupMessages({
  library(ggplot2)
  library(grid)
})

script_flag <- grep("^--file=", commandArgs(FALSE), value = TRUE)
script_path <- sub("^--file=", "", script_flag[[1L]])
script_dir <- dirname(normalizePath(script_path, winslash = "/", mustWork = TRUE))

args <- commandArgs(TRUE)
project_root <- if (length(args) >= 1L) {
  normalizePath(args[[1L]], winslash = "/", mustWork = TRUE)
} else {
  normalizePath(
    file.path(script_dir, "..", "..", ".."),
    winslash = "/",
    mustWork = TRUE
  )
}
summary_root <- file.path(project_root, "results", "summary")
main_dir <- normalizePath(
  file.path(script_dir, "..", "main"),
  winslash = "/",
  mustWork = TRUE
)
dummy_data_root <- normalizePath(
  if (length(args) >= 2L) args[[2L]] else file.path(script_dir, "..", "..", "..", "statistics", "primary"),
  winslash = "/",
  mustWork = TRUE
)

experiment_id <- "thinking_on"
filter_specs <- c(
  unfiltered = "unfiltered",
  filtered = "baseline_filtered"
)
filter_titles <- c(
  unfiltered = "Unfiltered",
  filtered = "Baseline-filtered"
)

panel_scripts <- c(
  framing = "panel_exp1_pragmatic_framing.R",
  source = "panel_exp1_source_frequency.R",
  target = "panel_exp1_target_frequency.R",
  context = "panel_exp1_semantic_context.R"
)
panel_titles <- c(
  framing = "Prompt Framing",
  source = "Source Frequency",
  target = "Target Frequency",
  context = "Sentence Context"
)
summary_files <- c(
  framing = "03_by_frame.csv",
  source = "04_by_source_frequency.csv",
  target = "05_by_target_frequency.csv",
  context = "02_by_context_type.csv"
)
summary_group_columns <- c(
  framing = "frame_id",
  source = "source_freq_band",
  target = "target_freq_band",
  context = "context_type"
)
pseudo_group_columns <- c(
  framing = "frame",
  source = "source_freq",
  target = "target_freq",
  context = "context"
)

missing_scripts <- panel_scripts[
  !file.exists(file.path(main_dir, panel_scripts))
]
if (length(missing_scripts)) {
  stop("Missing main panel scripts: ", paste(missing_scripts, collapse = ", "))
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
  "  \"GPT-5.5\", \"Qwen3-8B\", \"Qwen3-32B\"",
  ")"
), collapse = "\n")

all_model_ids <- c(
  "chatgpt5_5_instant", "qwen3_8b", "qwen3_32b"
)
all_model_labels <- c(
  chatgpt5_5_instant = "GPT-5.5",
  qwen3_8b = "Qwen3-8B",
  qwen3_32b = "Qwen3-32B"
)

palette_replacements <- c(
  "#B94A3A" = "#956515",
  "#D7643F" = "#AD7D23",
  "#E98A48" = "#C59632",
  "#F2B454" = "#D6B466",
  "#F6D47A" = "#E8D39A",
  "#2F7D59" = "#66742F",
  "#67AA76" = "#98A75C",
  "#A8D6A5" = "#D0D7A5",
  "#4F81BD" = "#287D8E",
  "#78A9CF" = "#5BA6B2",
  "#B9D7EC" = "#A9D8DE",
  "#9E7DBD" = "#9A879F",
  "#CDBADE" = "#C7B6CD",
  "#EE9292" = "#BC9098",
  "#F5BABA" = "#DFC0C5"
)
status_levels <- c("CK", "PK", "OTHER", "BOTH")
status_colours <- setNames(
  grDevices::colorRampPalette(c("#777777", "#AAAAAA", "#DEDEDE"))(4),
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

read_summary <- function(experiment, filter_dir, file_name) {
  path <- file.path(summary_root, experiment, filter_dir, file_name)
  if (!file.exists(path)) stop("Missing summary file: ", path)
  read.csv(
    path,
    stringsAsFactors = FALSE,
    check.names = FALSE,
    fileEncoding = "UTF-8-BOM"
  )
}

build_pseudo_data <- function(panel_name, experiment, filter_dir) {
  summary_data <- read_summary(
    experiment,
    filter_dir,
    summary_files[[panel_name]]
  )
  required <- c("model_id", "n", "n_ck")
  missing_columns <- setdiff(required, names(summary_data))
  if (length(missing_columns)) {
    stop("Missing columns for ", panel_name, ": ", paste(missing_columns, collapse = ", "))
  }
  missing_models <- setdiff(all_model_ids, summary_data$model_id)
  if (length(missing_models)) {
    stop("Missing models for ", panel_name, ": ", paste(missing_models, collapse = ", "))
  }

  totals <- as.integer(summary_data$n)
  successes <- as.integer(summary_data$n_ck)
  stopifnot(all(totals >= successes), all(successes >= 0L))
  response_ck <- unlist(
    Map(
      function(success, total) {
        c(rep.int(1L, success), rep.int(0L, total - success))
      },
      successes,
      totals
    ),
    use.names = FALSE
  )
  pseudo <- data.frame(
    model = rep(summary_data$model_id, times = totals),
    response_ck = response_ck,
    stringsAsFactors = FALSE
  )

  source_group <- summary_group_columns[[panel_name]]
  target_group <- pseudo_group_columns[[panel_name]]
  if (!is.na(source_group)) {
    if (!source_group %in% names(summary_data)) {
      stop("Missing group column for ", panel_name, ": ", source_group)
    }
    pseudo[[target_group]] <- rep(summary_data[[source_group]], times = totals)
  }
  pseudo
}

load_followup_panel <- function(panel_name, experiment, filter_dir) {
  pseudo_data <- build_pseudo_data(panel_name, experiment, filter_dir)
  source_path <- file.path(main_dir, panel_scripts[[panel_name]])
  source_text <- paste(
    readLines(source_path, warn = FALSE, encoding = "UTF-8"),
    collapse = "\n"
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
  for (old_colour in names(palette_replacements)) {
    source_text <- gsub(
      old_colour,
      unname(palette_replacements[[old_colour]]),
      source_text,
      fixed = TRUE
    )
  }

  evaluate_panel <- function(panel_data) {
    panel_env <- new.env(parent = globalenv())
    panel_env$commandArgs <- function(trailingOnly = FALSE) {
      if (isTRUE(trailingOnly)) dummy_data_root else base::commandArgs(FALSE)
    }
    panel_env$read.csv <- function(...) panel_data
    panel_env$ggsave <- function(...) invisible(NULL)
    panel_env$cat <- function(...) invisible(NULL)

    eval(parse(text = source_text, keep.source = FALSE), envir = panel_env)
    if (!inherits(panel_env$plot, "ggplot")) {
      stop(
        "No ggplot produced for ", panel_name, " / ", experiment,
        " / ", filter_dir
      )
    }
    panel_env
  }

  panel_env <- evaluate_panel(pseudo_data)
  exp1_env <- evaluate_panel(
    build_pseudo_data(panel_name, "exp1", filter_dir)
  )

  plot_object <- panel_env$plot
  plot_object$layers <- Filter(
    function(layer) !inherits(layer$geom, "GeomErrorbar"),
    plot_object$layers
  )
  for (index in seq_along(plot_object$layers)) {
    if (inherits(plot_object$layers[[index]]$geom, "GeomRect")) {
      plot_object$layers[[index]]$aes_params$colour <- NA
    }
  }

  exp1_bar_data <- exp1_env$bar_data
  exp1_bar_width <- exp1_env$bar_width
  stopifnot(
    is.data.frame(exp1_bar_data),
    all(c("x_position", "rate") %in% names(exp1_bar_data)),
    length(exp1_bar_width) == 1L
  )

  plot_object +
    geom_rect(
      data = exp1_bar_data,
      aes(
        xmin = x_position - exp1_bar_width / 2,
        xmax = x_position + exp1_bar_width / 2,
        ymin = 0,
        ymax = rate,
        linetype = "Experiment 1"
      ),
      fill = NA,
      colour = "#A6A6A6",
      linewidth = 0.48,
      inherit.aes = FALSE,
      show.legend = TRUE
    ) +
    scale_linetype_manual(
      name = NULL,
      values = c("Experiment 1" = "dashed"),
      breaks = "Experiment 1",
      drop = FALSE
    ) +
    guides(
      fill = guide_legend(title = NULL, order = 2),
      linetype = guide_legend(
        title = NULL,
        order = 1,
        override.aes = list(
          fill = NA,
          colour = "#A6A6A6",
          linewidth = 0.48
        )
      )
    ) +
    labs(title = panel_titles[[panel_name]]) +
    title_theme +
    theme(
      legend.background = element_blank(),
      legend.box.background = element_rect(
        fill = grDevices::adjustcolor("white", alpha.f = 0.90),
        colour = "#A6A6A6",
        linewidth = 0.42
      ),
      legend.box.margin = margin(1.5, 3, 1.5, 3),
      legend.spacing.y = unit(0, "pt")
    )
}

gradient_legend_key <- function(colours) {
  force(colours)
  function(data, params, size) {
    rectGrob(
      width = unit(1, "npc") - unit(1.5, "mm"),
      height = unit(1, "npc") - unit(1.5, "mm"),
      gp = gpar(
        fill = linearGradient(
          colours,
          x1 = unit(0, "npc"), y1 = unit(0.5, "npc"),
          x2 = unit(1, "npc"), y2 = unit(0.5, "npc")
        ),
        col = NA
      )
    )
  }
}

reasoning_colours <- c(
  "GPT-5.5" = "#C59632",
  "Qwen3-8B" = "#98A75C",
  "Qwen3-32B" = "#5BA6B2"
)

build_distribution_panel <- function(experiment, filter_dir) {
  model_summary <- read_summary(experiment, filter_dir, "01_by_model.csv")
  status_levels <- c("CK", "PK", "OTHER", "BOTH")
  count_columns <- c(
    CK = "n_ck", PK = "n_pk", OTHER = "n_other", BOTH = "n_both"
  )
  required <- c("model_id", "n", unname(count_columns))
  stopifnot(all(required %in% names(model_summary)))
  model_summary <- model_summary[
    match(all_model_ids, model_summary$model_id),
    required,
    drop = FALSE
  ]
  stopifnot(!anyNA(model_summary$model_id))

  model_palettes <- setNames(
    rep(list(unname(status_colours)), length(all_model_ids)),
    unname(all_model_labels[all_model_ids])
  )

  stack_data <- do.call(rbind, lapply(seq_along(all_model_ids), function(index) {
    model_id <- all_model_ids[[index]]
    model_row <- model_summary[index, , drop = FALSE]
    model_label <- unname(all_model_labels[[model_id]])
    counts <- as.numeric(model_row[1, unname(count_columns)])
    data.frame(
      model_id = model_id,
      model_label = model_label,
      model_index = index,
      status = status_levels,
      status_index = seq_along(status_levels),
      rate = 100 * counts / model_row$n,
      fill_key = paste(model_label, status_levels, sep = "__"),
      stringsAsFactors = FALSE
    )
  }))
  stack_data$ymax <- ave(
    stack_data$rate, stack_data$model_id, FUN = cumsum
  )
  stack_data$ymin <- stack_data$ymax - stack_data$rate
  stopifnot(all(abs(ave(stack_data$rate, stack_data$model_id, FUN = sum) - 100) < 1e-8))

  bar_width <- 0.48
  bar_gap <- 0.16
  model_centres <- 1 +
    (seq_along(all_model_ids) - 1L) * (bar_width + bar_gap)
  x_limits <- c(
    model_centres[[1L]] - bar_width / 2 - bar_gap,
    tail(model_centres, 1L) + bar_width / 2 + bar_gap
  )
  stack_data$x_position <- model_centres[stack_data$model_index]
  separator_data <- stack_data[
    stack_data$status_index < length(status_levels),
    ,
    drop = FALSE
  ]

  fill_values <- unlist(lapply(names(model_palettes), function(model_label) {
    setNames(
      model_palettes[[model_label]],
      paste(model_label, status_levels, sep = "__")
    )
  }))
  legend_y <- c(0.80, 0.60, 0.40, 0.20)
  legend_children <- list(
    rectGrob(
      x = 0.5, y = 0.5, width = 1, height = 1,
      gp = gpar(
        fill = grDevices::adjustcolor("white", alpha.f = 0.90),
        col = "#A6A6A6",
        lwd = 0.42 * ggplot2::.pt
      )
    )
  )
  for (index in seq_along(status_levels)) {
    legend_children <- c(
      legend_children,
      list(
        rectGrob(
          x = 0.16, y = legend_y[[index]],
          width = 0.20, height = 0.13,
          gp = gpar(
            fill = linearGradient(
              vapply(
                model_palettes,
                function(palette) palette[[index]],
                character(1)
              ),
              x1 = unit(0, "npc"), y1 = unit(0.5, "npc"),
              x2 = unit(1, "npc"), y2 = unit(0.5, "npc")
            ),
            col = NA
          )
        ),
        textGrob(
          status_levels[[index]],
          x = 0.31, y = legend_y[[index]], just = "left",
          gp = gpar(col = "#000000", fontsize = 7.2)
        )
      )
    )
  }
  distribution_legend <- do.call(grobTree, legend_children)

  ggplot(stack_data) +
    geom_rect(
      aes(
        xmin = x_position - bar_width / 2,
        xmax = x_position + bar_width / 2,
        ymin = ymin,
        ymax = ymax,
        fill = fill_key
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
    annotation_custom(
      distribution_legend,
      xmin = x_limits[[2L]] - 0.72,
      xmax = x_limits[[2L]] - 0.02,
      ymin = 2,
      ymax = 31
    ) +
    scale_fill_manual(values = fill_values, guide = "none") +
    scale_x_continuous(
      breaks = model_centres,
      labels = unname(all_model_labels[all_model_ids]),
      limits = x_limits,
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
      axis.text.x = element_text(size = 5.4),
      plot.title = element_text(
        family = "sans", face = "bold", colour = "#000000",
        size = 12, hjust = 0.5, margin = margin(b = 2)
      ),
      legend.position = "none",
      plot.margin = margin(3, 4, 3, 5.6)
    )
}
build_page <- function(experiment, filter_dir) {
  plots <- lapply(names(panel_scripts), function(panel_name) {
    load_followup_panel(panel_name, experiment, filter_dir)
  })
  names(plots) <- names(panel_scripts)
  plots$distribution <- build_distribution_panel(experiment, filter_dir)
  plots
}

page_width <- 18.60
content_height <- 3.15
header_height <- 0.34
page_height <- content_height + header_height
written_paths <- character()

for (filter_label in names(filter_specs)) {
  filter_dir <- unname(filter_specs[[filter_label]])
  figure_title <- paste(
    "Reasoning Effect",
    filter_titles[[filter_label]],
    sep = ": "
  )
  output_path <- file.path(
    script_dir,
    sprintf(
      "figureA_reasoning_full_models_%s.pdf",
      filter_label
    )
  )
  plots <- build_page(experiment_id, filter_dir)

  grDevices::cairo_pdf(
    output_path,
    width = page_width,
    height = page_height,
    bg = "white"
  )
  grid.newpage()
  grid.text(
    figure_title,
    x = unit(0.5, "npc"),
    y = unit(content_height + header_height / 2, "in"),
    gp = gpar(fontsize = 14, fontface = "bold")
  )
  pushViewport(viewport(
    x = unit(0.5, "npc"),
    y = unit(content_height / 2, "in"),
    width = unit(page_width, "in"),
    height = unit(content_height, "in"),
    layout = grid.layout(nrow = 1, ncol = 5)
  ))
  for (index in seq_len(5L)) {
    print(
      plots[[index]],
      vp = viewport(layout.pos.row = 1, layout.pos.col = index)
    )
  }
  upViewport()
  dev.off()
  written_paths <- c(written_paths, output_path)
}

cat("Wrote:\n", paste(written_paths, collapse = "\n"), "\n")
