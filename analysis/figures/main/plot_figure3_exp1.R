suppressPackageStartupMessages({
  library(ggplot2)
  library(grid)
})

script_flag <- grep("^--file=", commandArgs(FALSE), value = TRUE)
script_path <- sub("^--file=", "", script_flag[[1L]])
script_dir <- dirname(normalizePath(script_path, winslash = "/", mustWork = TRUE))
output_path <- file.path(script_dir, "figure3_exp1_all_combined.pdf")

trailing_args <- commandArgs(TRUE)
data_root <- if (length(trailing_args) >= 1L) {
  normalizePath(trailing_args[[1L]], winslash = "/", mustWork = TRUE)
} else {
  normalizePath(
    file.path(script_dir, "..", "..", "..", "statistics", "primary"),
    winslash = "/",
    mustWork = TRUE
  )
}

panel_scripts <- c(
  framing = "panel_exp1_pragmatic_framing.R",
  source = "panel_exp1_source_frequency.R",
  target = "panel_exp1_target_frequency.R",
  context = "panel_exp1_semantic_context.R",
  model_size = "panel_exp1_model_size.R"
)

missing_scripts <- panel_scripts[!file.exists(file.path(script_dir, panel_scripts))]
if (length(missing_scripts)) {
  stop("Missing Exp1 panel scripts: ", paste(missing_scripts, collapse = ", "))
}

load_plot <- function(filename) {
  panel_env <- new.env(parent = globalenv())
  panel_env$commandArgs <- function(trailingOnly = FALSE) {
    if (isTRUE(trailingOnly)) data_root else base::commandArgs(FALSE)
  }
  panel_env$ggsave <- function(...) invisible(NULL)
  panel_env$cat <- function(...) invisible(NULL)

  sys.source(file.path(script_dir, filename), envir = panel_env)
  if (!inherits(panel_env$plot, "ggplot")) {
    stop("No ggplot object was produced by: ", filename)
  }
  panel_env$plot
}

plots <- lapply(panel_scripts, load_plot)

remove_bar_borders <- function(plot_object) {
  for (index in seq_along(plot_object$layers)) {
    if (inherits(plot_object$layers[[index]]$geom, "GeomRect")) {
      plot_object$layers[[index]]$aes_params$colour <- NA
    }
  }
  plot_object
}

plots <- lapply(plots, remove_bar_borders)

panel_title_theme <- theme(
  plot.title = element_text(
    family = "sans",
    face = "bold",
    colour = "#000000",
    size = 18,
    hjust = 0.5,
    margin = margin(b = 2)
  )
)

plots$framing <- plots$framing +
  labs(title = "Prompt Framing") +
  panel_title_theme
plots$source <- plots$source +
  labs(title = "Source Frequency") +
  panel_title_theme
plots$target <- plots$target +
  labs(title = "Target Frequency") +
  panel_title_theme
plots$context <- plots$context +
  labs(title = "Sentence Context") +
  panel_title_theme +
  theme(plot.margin = margin(3, 4, 28.5, 5.6))
plots$model_size <- plots$model_size +
  labs(title = "Model Size") +
  panel_title_theme +
  theme(plot.margin = margin(3, 4, 27, 5.6))

data_path <- normalizePath(
  file.path(data_root, "data", "derived", "exp1_unfiltered.csv"),
  winslash = "/",
  mustWork = TRUE
)
dat <- read.csv(data_path, stringsAsFactors = FALSE, check.names = FALSE)
stopifnot(nrow(dat) == 54000L, all(dat$response_ck %in% c(0, 1)))

model_order <- c(
  "chatgpt5_5_instant",
  "deepseek_llm_7b", "deepseek_llm_67b",
  "gemma3_4b", "gemma3_27b",
  "llama3_8b", "llama3_70b",
  "qwen3_8b", "qwen3_32b"
)
model_labels <- c(
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

summarise_model <- function(model_id) {
  rows <- dat$model == model_id
  successes <- sum(dat$response_ck[rows])
  total <- sum(rows)
  proportion <- successes / total
  z <- qnorm(0.975)
  denominator <- 1 + z^2 / total
  centre <- (proportion + z^2 / (2 * total)) / denominator
  half_width <- z * sqrt(
    proportion * (1 - proportion) / total + z^2 / (4 * total^2)
  ) / denominator

  data.frame(
    model = model_id,
    rate = 100 * proportion,
    conf_low = 100 * pmax(0, centre - half_width),
    conf_high = 100 * pmin(1, centre + half_width),
    stringsAsFactors = FALSE
  )
}

overall_data <- do.call(rbind, lapply(model_order, summarise_model))
overall_model_order <- overall_data$model[order(overall_data$rate)]
overall_data <- overall_data[match(overall_model_order, overall_data$model), , drop = FALSE]
overall_axis_limits <- c(0.5, length(model_order) + 0.5)
overall_region_width <- diff(overall_axis_limits) * 4 / 5
target_group_gap_fraction <- 0.100 / 2.755
overall_gap <- diff(overall_axis_limits) * target_group_gap_fraction / 2
overall_bar_width <- (
  overall_region_width - (length(model_order) - 1L) * overall_gap
) / length(model_order)
overall_region_limits <- mean(overall_axis_limits) +
  c(-0.5, 0.5) * overall_region_width
overall_data$x_position <- seq(
  overall_region_limits[[1L]] + overall_bar_width / 2,
  overall_region_limits[[2L]] - overall_bar_width / 2,
  length.out = length(model_order)
)
overall_data$model_label <- factor(
  unname(model_labels[overall_data$model]),
  levels = unname(model_labels[overall_model_order]),
  ordered = TRUE
)

overall_colours <- setNames(
  grDevices::colorRampPalette(c("#795037", "#A77A5B", "#D8BBA5"))(
    length(model_order)
  ),
  unname(model_labels[overall_model_order])
)

overall_plot <- ggplot(overall_data) +
  geom_rect(
    aes(
      xmin = x_position - overall_bar_width / 2,
      xmax = x_position + overall_bar_width / 2,
      ymin = 0,
      ymax = rate,
      fill = model_label
    ),
    colour = "#000000",
    linewidth = 0.24,
    show.legend = FALSE
  ) +
  geom_errorbar(
    aes(x = x_position, ymin = conf_low, ymax = conf_high),
    width = overall_bar_width * 0.52,
    linewidth = 0.42,
    colour = "#000000"
  ) +
  scale_fill_manual(values = overall_colours, guide = "none") +
  scale_x_continuous(
    breaks = overall_data$x_position,
    labels = unname(model_labels[overall_model_order]),
    limits = overall_axis_limits,
    expand = expansion(mult = 0)
  ) +
  scale_y_continuous(
    breaks = seq(0, 100, by = 20),
    labels = function(value) sprintf("%.0f", value),
    expand = expansion(mult = c(0, 0))
  ) +
  coord_cartesian(ylim = c(0, 103), clip = "on") +
  labs(title = "Overall CK Rate", x = NULL, y = "CK Rate (%)") +
  theme_classic(base_family = "sans", base_size = 15.3) +
  theme(
    text = element_text(family = "sans", colour = "#000000"),
    panel.border = element_blank(),
    panel.grid = element_blank(),
    axis.line = element_blank(),
    axis.line.x.bottom = element_line(colour = "#000000", linewidth = 0.45),
    axis.line.y.left = element_line(colour = "#000000", linewidth = 0.45),
    axis.ticks = element_line(colour = "#000000", linewidth = 0.34),
    axis.ticks.length = unit(2.5, "pt"),
    axis.title = element_text(size = 15.6),
    axis.text.y = element_text(size = 13.8),
    axis.text.x = element_text(
      size = 8.7,
      angle = 38,
      hjust = 1,
      vjust = 1
    ),
    plot.title = element_text(
      family = "sans",
      face = "bold",
      colour = "#000000",
      size = 18,
      hjust = 0.5,
      margin = margin(b = 2)
    ),
    plot.margin = margin(3, 4, 8, 5.6)
  )

plots$overall <- remove_bar_borders(overall_plot)

# Figure 3 only: use 10 pt x-axis labels and 11 pt legend labels.
# Preserve label angles; use 9 pt for Overall CK Rate and 7.5 pt for Frame below.
plots$overall <- plots$overall + theme(axis.text.x = element_text(size = 9))
for (panel_name in c("framing", "source", "target", "context", "model_size")) {
  plots[[panel_name]] <- plots[[panel_name]] +
    theme(
      axis.text.x = element_text(size = 10),
      legend.text = element_text(size = 11)
    )
}
plots$framing <- plots$framing +
  guides(fill = guide_legend(ncol = 1, byrow = TRUE)) +
  theme(
    legend.text = element_text(size = 7.5),
    legend.direction = "vertical"
  )

page_width <- 18.60
top_height <- 3.05
bottom_height <- 3.15
row_gap <- 0.20
header_height <- 0.34
content_height <- top_height + row_gap + bottom_height
page_height <- content_height + header_height

grDevices::cairo_pdf(
  output_path,
  width = page_width,
  height = page_height,
  bg = "white"
)
grid.newpage()
grid.text(
  "Experiment 1: Condition Effects",
  x = unit(0.5, "npc"),
  y = unit(content_height + header_height / 2, "in"),
  gp = gpar(fontfamily = "sans", fontface = "bold", fontsize = 21)
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
cat("Wrote:\n", output_path, "\n")
