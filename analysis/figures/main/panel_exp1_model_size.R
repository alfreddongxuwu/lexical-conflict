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

family_order <- c("DeepSeek", "Gemma3", "Llama3", "Qwen3")
size_levels <- c("Small", "Large")
size_key <- data.frame(
  model = c(
    "deepseek_llm_7b", "deepseek_llm_67b",
    "gemma3_4b", "gemma3_27b",
    "llama3_8b", "llama3_70b",
    "qwen3_8b", "qwen3_32b"
  ),
  family = rep(family_order, each = 2L),
  size_group = rep(size_levels, length(family_order)),
  stringsAsFactors = FALSE
)

matched <- match(dat$model, size_key$model)
plot_data <- dat[!is.na(matched), , drop = FALSE]
matched <- matched[!is.na(matched)]
plot_data$family <- factor(
  size_key$family[matched], levels = family_order, ordered = TRUE
)
plot_data$size_group <- factor(
  size_key$size_group[matched], levels = size_levels, ordered = TRUE
)
stopifnot(nrow(plot_data) == 48000L)

bar_data <- summarise_ck(plot_data, c("family", "size_group"))
overall <- summarise_ck(plot_data, "size_group")
overall <- overall[
  match(size_levels, as.character(overall$size_group)), , drop = FALSE
]

bar_group_spacing <- 0.1733333333
bar_group_gap <- 0.0933333333

offsets <- c(-0.020, 0.020)
bar_width <- 0.040
first_model_centre <- 1 + max(offsets) + bar_group_gap -
  min(offsets) + bar_width / 2
model_centres <- first_model_centre +
  (seq_along(family_order) - 1L) * bar_group_spacing
display_centres <- c(1, model_centres)

bar_data$x_position <- model_centres[
  match(as.character(bar_data$family), family_order)
] + offsets[match(as.character(bar_data$size_group), size_levels)]
bar_data$condition <- factor(
  as.character(bar_data$size_group), levels = size_levels, ordered = TRUE
)

colours <- c(Small = "#EE9292", Large = "#F5BABA")
overall_points <- data.frame(
  x = 1 + offsets,
  y = 0,
  yend = overall$rate,
  point_colour = unname(colours[size_levels])
)
overall_line <- gradient_segments(
  overall$rate, 1, offsets, unname(colours[size_levels])
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
    labels = axis_labels(c("Overall", family_order)),
    limits = c(1 + min(offsets) - bar_group_gap, tail(display_centres, 1L) + bar_width + bar_group_gap),
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
    axis.text.x = element_text(size = 10.5),
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
    legend.key.height = grid::unit(10.0, "pt"),
    legend.key.width = grid::unit(13.0, "pt"),
    legend.key.spacing.y = grid::unit(0, "pt"),
    legend.text = element_text(size = 13.5, margin = margin(l = 4)),
    legend.margin = margin(1, 2, 1, 2),
    plot.margin = margin(3, 4, 3, 3)
  )
