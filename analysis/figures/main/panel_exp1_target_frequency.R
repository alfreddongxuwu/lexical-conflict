suppressPackageStartupMessages(library(ggplot2))

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
data_path <- normalizePath(
  file.path(data_root, "data", "derived", "exp1_unfiltered.csv"),
  winslash = "/",
  mustWork = TRUE
)

summarise_ck <- function(data, groups) {
  keys <- interaction(data[groups], drop = TRUE, lex.order = TRUE)
  rows_by_group <- split(seq_len(nrow(data)), keys)
  output <- lapply(rows_by_group, function(rows) {
    result <- data[rows[[1L]], groups, drop = FALSE]
    result$successes <- sum(data$response_ck[rows])
    result$total <- length(rows)
    result
  })
  output <- do.call(rbind, output)
  rownames(output) <- NULL

  z <- qnorm(0.975)
  proportion <- output$successes / output$total
  denominator <- 1 + z^2 / output$total
  centre <- (proportion + z^2 / (2 * output$total)) / denominator
  half_width <- z * sqrt(
    proportion * (1 - proportion) / output$total +
      z^2 / (4 * output$total^2)
  ) / denominator

  output$rate <- 100 * proportion
  output$conf_low <- 100 * pmax(0, centre - half_width)
  output$conf_high <- 100 * pmin(1, centre + half_width)
  output
}

gradient_segments <- function(rates, centre, offsets, colours, pieces = 36L) {
  parts <- lapply(seq_len(length(rates) - 1L), function(index) {
    x_values <- seq(
      centre + offsets[[index]], centre + offsets[[index + 1L]],
      length.out = pieces + 1L
    )
    y_values <- seq(
      rates[[index]], rates[[index + 1L]], length.out = pieces + 1L
    )
    data.frame(
      x = head(x_values, -1L),
      xend = tail(x_values, -1L),
      y = head(y_values, -1L),
      yend = tail(y_values, -1L),
      segment_colour = grDevices::colorRampPalette(
        colours[index:(index + 1L)]
      )(pieces)
    )
  })
  do.call(rbind, parts)
}

axis_labels <- function(labels) {
  as.expression(lapply(labels, function(label) {
    if (identical(label, "Overall")) bquote(bold(.(label))) else bquote(.(label))
  }))
}

dat <- read.csv(data_path, stringsAsFactors = FALSE, check.names = FALSE)
stopifnot(nrow(dat) == 54000L)

frequency_levels <- c("high", "medium", "low")
condition_labels <- c(high = "High", medium = "Medium", low = "Low")
model_labels <- c(
  chatgpt5_5_instant = "ChatGPT-5.5",
  deepseek_llm_7b = "DeepSeek-7B",
  gemma3_4b = "Gemma3-4B",
  llama3_8b = "Llama3-8B",
  qwen3_8b = "Qwen3-8B"
)
model_order <- unname(model_labels)
short_model_labels <- c(
  "GPT-5.5", "DeepSeek-7B", "Gemma3-4B", "Llama3-8B", "Qwen3-8B"
)

plot_data <- dat[dat$model %in% names(model_labels), , drop = FALSE]
plot_data$target_freq <- factor(
  plot_data$target_freq, levels = frequency_levels, ordered = TRUE
)
plot_data$model_label <- factor(
  unname(model_labels[plot_data$model]), levels = model_order, ordered = TRUE
)
stopifnot(nrow(plot_data) == 30000L, !anyNA(plot_data$model_label))

bar_data <- summarise_ck(plot_data, c("model_label", "target_freq"))
overall <- summarise_ck(plot_data, "target_freq")
overall <- overall[
  match(frequency_levels, as.character(overall$target_freq)), , drop = FALSE
]

bar_group_spacing <- 0.460
bar_group_gap <- 0.100

offsets <- c(-0.120, 0, 0.120)
bar_width <- 0.120
first_model_centre <- 1 + max(offsets) + bar_group_gap -
  min(offsets) + bar_width / 2
model_centres <- first_model_centre +
  (seq_along(model_order) - 1L) * bar_group_spacing
display_centres <- c(1, model_centres)

bar_data$x_position <- model_centres[
  match(as.character(bar_data$model_label), model_order)
] + offsets[match(as.character(bar_data$target_freq), frequency_levels)]
bar_data$condition <- factor(
  unname(condition_labels[as.character(bar_data$target_freq)]),
  levels = unname(condition_labels),
  ordered = TRUE
)

colours <- c(High = "#4F81BD", Medium = "#78A9CF", Low = "#B9D7EC")
overall_points <- data.frame(
  x = 1 + offsets,
  y = 0,
  yend = overall$rate,
  point_colour = unname(colours[unname(condition_labels)])
)
overall_line <- gradient_segments(
  overall$rate, 1, offsets, unname(colours[unname(condition_labels)])
)

plot <- ggplot(bar_data) +
  geom_rect(
    aes(
      xmin = x_position - bar_width / 2,
      xmax = x_position + bar_width / 2,
      ymin = 0,
      ymax = rate,
      fill = condition
    ),
    colour = "#000000",
    linewidth = 0.24
  ) +
  geom_errorbar(
    aes(x = x_position, ymin = conf_low, ymax = conf_high),
    width = bar_width * 0.52,
    linewidth = 0.42,
    colour = "#000000"
  ) +
  geom_segment(
    data = overall_points,
    aes(x = x, y = y, xend = x, yend = yend),
    inherit.aes = FALSE,
    colour = "#A6A6A6",
    linewidth = 0.48,
    linetype = "dashed",
    show.legend = FALSE
  ) +
  geom_segment(
    data = overall_line,
    aes(x = x, y = y, xend = xend, yend = yend, colour = segment_colour),
    inherit.aes = FALSE,
    linewidth = 0.60,
    lineend = "round",
    show.legend = FALSE
  ) +
  geom_point(
    data = overall_points,
    aes(x = x, y = yend, colour = point_colour),
    inherit.aes = FALSE,
    size = 1.62,
    show.legend = FALSE
  ) +
  scale_fill_manual(values = colours, drop = FALSE) +
  scale_colour_identity() +
  scale_x_continuous(
    breaks = display_centres,
    labels = axis_labels(c("Overall", short_model_labels)),
    limits = c(1 + min(offsets) - bar_group_gap, tail(display_centres, 1L) + 0.295),
    expand = expansion(mult = 0)
  ) +
  scale_y_continuous(
    breaks = seq(0, 100, by = 20),
    labels = function(value) sprintf("%.0f", value),
    expand = expansion(mult = c(0, 0))
  ) +
  coord_cartesian(ylim = c(0, 103), clip = "on") +
  labs(x = NULL, y = "CK Rate (%)", fill = NULL) +
  theme_classic(base_family = "sans", base_size = 15.3) +
  theme(
    text = element_text(family = "sans", colour = "#000000"),
    panel.border = element_blank(),
    panel.grid = element_blank(),
    axis.line = element_blank(),
    axis.line.x.bottom = element_line(colour = "#000000", linewidth = 0.45),
    axis.line.y.left = element_line(colour = "#000000", linewidth = 0.45),
    axis.ticks = element_line(colour = "#000000", linewidth = 0.34),
    axis.ticks.length = grid::unit(2.5, "pt"),
    axis.title = element_text(size = 15.6),
    axis.text.y = element_text(size = 13.8),
    axis.text.x = element_text(size = 8.1),
    legend.position = "inside",
    legend.position.inside = c(0.985, 0.030),
    legend.justification.inside = c(1, 0),
    legend.direction = "vertical",
    legend.background = element_rect(
      fill = grDevices::adjustcolor("white", alpha.f = 0.90),
      colour = "#A6A6A6",
      linewidth = 0.45
    ),
    legend.key = element_rect(fill = "white", colour = NA),
    legend.key.height = grid::unit(6.0, "pt"),
    legend.key.width = grid::unit(7.5, "pt"),
    legend.key.spacing.y = grid::unit(0, "pt"),
    legend.text = element_text(size = 8.4, margin = margin(l = 4)),
    legend.margin = margin(1, 2, 1, 2),
    plot.margin = margin(3, 4, 3, 5.6)
  )
