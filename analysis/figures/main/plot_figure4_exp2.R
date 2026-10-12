suppressPackageStartupMessages({
  library(ggplot2)
})

script_flag <- grep("^--file=", commandArgs(FALSE), value = TRUE)
script_path <- sub("^--file=", "", script_flag[[1L]])
script_dir <- dirname(normalizePath(script_path, winslash = "/", mustWork = TRUE))
project_root <- script_dir
trailing_args <- commandArgs(TRUE)
if (length(trailing_args) >= 1L) {
  data_project_root <- normalizePath(
    trailing_args[[1L]], winslash = "/", mustWork = TRUE
  )
} else {
  data_project_root <- normalizePath(
    file.path(project_root, "..", "..", "..", "statistics", "primary"),
    winslash = "/",
    mustWork = TRUE
  )
}
raw_data_path <- normalizePath(
  file.path(data_project_root, "data", "derived", "exp2_unfiltered.csv"),
  winslash = "/",
  mustWork = TRUE
)
output_path <- file.path(project_root, "figure4_exp2_overall.pdf")

dat <- read.csv(raw_data_path, stringsAsFactors = FALSE, check.names = FALSE)
stopifnot(nrow(dat) == 27000L, all(dat$response_ck %in% c(0, 1)))

summarise_ck <- function(data, group_variables) {
  key <- interaction(data[group_variables], drop = TRUE, lex.order = TRUE)
  groups <- split(seq_len(nrow(data)), key)
  output <- lapply(groups, function(rows) {
    group_values <- data[rows[[1L]], group_variables, drop = FALSE]
    group_values$n <- length(rows)
    group_values$n_ck <- sum(data$response_ck[rows])
    group_values
  })
  output <- do.call(rbind, output)
  rownames(output) <- NULL
  output
}

model_summary <- summarise_ck(dat, "model")
names(model_summary)[1L] <- "model_id"
frame_summary <- summarise_ck(dat, c("model", "frame_id"))
source_summary <- summarise_ck(dat, c("model", "source_freq_band"))
target_summary <- summarise_ck(dat, c("model", "target_freq_band"))

pool_counts <- function(data, group_variable) {
  groups <- split(seq_len(nrow(data)), data[[group_variable]])
  output <- lapply(names(groups), function(group_name) {
    rows <- groups[[group_name]]
    data.frame(
      level = group_name,
      successes = sum(data$n_ck[rows]),
      total = sum(data$n[rows]),
      stringsAsFactors = FALSE
    )
  })
  output <- do.call(rbind, output)
  rownames(output) <- NULL
  output$estimate <- 100 * output$successes / output$total
  output
}

frame_levels <- paste0("F", 1:5)
frame_overall <- pool_counts(frame_summary, "frame_id")
frame_overall <- frame_overall[
  match(frame_levels, frame_overall$level), , drop = FALSE
]
frame_overall$x <- 1:5
frame_overall$series <- "Prompt Framing"
frame_overall$label <- frame_levels

frequency_overall <- function(data, group_variable, series_name) {
  level_order <- c("high", "medium", "low")
  output <- pool_counts(data, group_variable)
  output <- output[match(level_order, output$level), , drop = FALSE]
  output$x <- c(1, 3, 5)
  output$series <- series_name
  output$label <- c("High", "Medium", "Low")
  output
}

source_overall <- frequency_overall(
  source_summary,
  "source_freq_band",
  "Source Frequency"
)
target_overall <- frequency_overall(
  target_summary,
  "target_freq_band",
  "Target Frequency"
)

size_lookup <- c(
  deepseek_llm_7b = "Small",
  deepseek_llm_67b = "Large",
  gemma3_4b = "Small",
  gemma3_27b = "Large",
  llama3_8b = "Small",
  llama3_70b = "Large",
  qwen3_8b = "Small",
  qwen3_32b = "Large"
)
size_summary <- model_summary[
  model_summary$model_id %in% names(size_lookup), , drop = FALSE
]
size_summary$size_group <- unname(size_lookup[size_summary$model_id])
size_overall <- pool_counts(size_summary, "size_group")
size_levels <- c("Small", "Large")
size_overall <- size_overall[
  match(size_levels, size_overall$level), , drop = FALSE
]
size_overall$x <- c(1, 5)
size_overall$series <- "Model Size"
size_overall$label <- size_levels

frame_colours <- c(
  F1 = "#B94A3A", F2 = "#D7643F", F3 = "#E98A48",
  F4 = "#F2B454", F5 = "#F6D47A"
)
source_colours <- c(
  Low = "#A8D6A5",
  Medium = "#67AA76",
  High = "#2F7D59"
)
target_colours <- c(
  Low = "#B9D7EC",
  Medium = "#78A9CF",
  High = "#4F81BD"
)
size_colours <- c(
  Small = "#EE9292",
  Large = "#F5BABA"
)

frame_overall$point_colour <- unname(frame_colours[frame_overall$label])
source_overall$point_colour <- unname(source_colours[source_overall$label])
target_overall$point_colour <- unname(target_colours[target_overall$label])
size_overall$point_colour <- unname(size_colours[size_overall$label])

series_levels <- c(
  "Prompt Framing",
  "Source Frequency",
  "Target Frequency",
  "Model Size"
)
legend_prefixes <- c(
  "Prompt Framing" = "Frame",
  "Source Frequency" = "Source Freq",
  "Target Frequency" = "Target Freq",
  "Model Size" = "Model Size"
)
legend_ranges <- c(
  "Prompt Framing" = "F1\u2013F5",
  "Source Frequency" = "High\u2013Low",
  "Target Frequency" = "High\u2013Low",
  "Model Size" = "Small\u2013Large"
)
condition_shapes <- c(
  "Prompt Framing" = 21,
  "Source Frequency" = 24,
  "Target Frequency" = 22,
  "Model Size" = 23
)
legend_colours <- c(
  "Prompt Framing" = unname(frame_colours[["F3"]]),
  "Source Frequency" = unname(source_colours[["Medium"]]),
  "Target Frequency" = unname(target_colours[["Medium"]]),
  "Model Size" = unname(size_colours[["Small"]])
)

plot_data <- rbind(
  frame_overall,
  source_overall,
  target_overall,
  size_overall
)
plot_data$series <- factor(
  plot_data$series,
  levels = series_levels,
  ordered = TRUE
)

stopifnot(
  nrow(model_summary) == 9L,
  nrow(frame_overall) == 5L,
  nrow(source_overall) == 3L,
  nrow(target_overall) == 3L,
  nrow(size_overall) == 2L,
  !anyNA(plot_data[c("estimate", "x", "point_colour")])
)

line_segments <- function(data, pieces = 36L) {
  data <- data[order(data$x), , drop = FALSE]
  parts <- lapply(seq_len(nrow(data) - 1L), function(index) {
    x_values <- seq(
      data$x[[index]], data$x[[index + 1L]], length.out = pieces + 1L
    )
    y_values <- seq(
      data$estimate[[index]], data$estimate[[index + 1L]],
      length.out = pieces + 1L
    )
    data.frame(
      x = head(x_values, -1L),
      xend = tail(x_values, -1L),
      y = head(y_values, -1L),
      yend = tail(y_values, -1L),
      segment_colour = grDevices::colorRampPalette(
        data$point_colour[index:(index + 1L)]
      )(pieces),
      stringsAsFactors = FALSE
    )
  })
  do.call(rbind, parts)
}

segment_data <- do.call(
  rbind,
  lapply(split(plot_data, plot_data$series), line_segments)
)
rownames(segment_data) <- NULL

font_family <- "sans"
axis_colour <- "#000000"
legend_font_size <- 5.6

legend_shape_coords <- list(
  "22" = matrix(c(-1, -1, 1, -1, 1, 1, -1, 1), ncol = 2, byrow = TRUE),
  "23" = matrix(c(0, -1, 1, 0, 0, 1, -1, 0), ncol = 2, byrow = TRUE),
  "24" = matrix(c(0, 1, -1, -1, 1, -1), ncol = 2, byrow = TRUE)
)

legend_shape_grob <- function(series_name, y_position) {
  legend_colour <- unname(legend_colours[[series_name]])
  shape <- unname(condition_shapes[[series_name]])
  centre_x <- grid::unit(4.0, "pt")
  centre_y <- grid::unit(y_position, "npc")
  half_size <- 0.50
  shape_gp <- grid::gpar(
    fill = legend_colour,
    col = legend_colour,
    lwd = 0.08 * ggplot2::.pt,
    linejoin = "mitre",
    linemitre = 10
  )

  if (shape == 21) {
    return(grid::circleGrob(
      x = centre_x,
      y = centre_y,
      r = grid::unit(half_size, "mm"),
      gp = shape_gp
    ))
  }

  shape_coords <- legend_shape_coords[[as.character(shape)]]
  grid::polygonGrob(
    x = centre_x + grid::unit(shape_coords[, 1L] * half_size, "mm"),
    y = centre_y + grid::unit(shape_coords[, 2L] * half_size, "mm"),
    gp = shape_gp
  )
}

legend_row_grob <- function(series_name, y_position) {
  legend_colour <- unname(legend_colours[[series_name]])
  prefix_grob <- grid::textGrob(
    paste0(legend_prefixes[[series_name]], " "),
    x = grid::unit(7.67, "pt"),
    y = grid::unit(y_position, "npc"),
    just = c("left", "centre"),
    gp = grid::gpar(
      fontfamily = font_family,
      fontface = "plain",
      fontsize = legend_font_size,
      col = axis_colour
    )
  )

  grid::grobTree(
    legend_shape_grob(series_name, y_position),
    prefix_grob,
    grid::textGrob(
      legend_ranges[[series_name]],
      x = grid::unit(7.67, "pt") + grid::grobWidth(prefix_grob),
      y = grid::unit(y_position, "npc"),
      just = c("left", "centre"),
      gp = grid::gpar(
        fontfamily = font_family,
        fontface = "bold",
        fontsize = legend_font_size,
        col = legend_colour
      )
    )
  )
}

condition_legend_grob <- do.call(
  grid::grobTree,
  c(
    list(
      grid::rectGrob(
        gp = grid::gpar(
          fill = grDevices::adjustcolor("white", alpha.f = 0.90),
          col = "#A6A6A6",
          lwd = 0.38 * ggplot2::.pt
        )
      )
    ),
    Map(
      legend_row_grob,
      series_levels,
      c(0.83, 0.61, 0.39, 0.17)
    )
  )
)

theme_exp1 <- theme_classic(base_family = font_family, base_size = 10.2) +
  theme(
    text = element_text(family = font_family, colour = axis_colour),
    panel.background = element_rect(fill = "white", colour = NA),
    plot.background = element_rect(fill = "white", colour = NA),
    panel.border = element_blank(),
    panel.grid = element_blank(),
    panel.grid.major.y = element_line(
      colour = "#E8E8E8",
      linewidth = 0.32
    ),
    panel.grid.minor.y = element_blank(),
    axis.line = element_blank(),
    axis.line.x.bottom = element_line(colour = axis_colour, linewidth = 0.45),
    axis.line.y.left = element_line(colour = axis_colour, linewidth = 0.45),
    axis.ticks = element_line(colour = axis_colour, linewidth = 0.34),
    axis.ticks.length = grid::unit(2.5, "pt"),
    axis.title.y = element_text(
      family = font_family,
      face = "plain",
      colour = axis_colour,
      size = 10.4 * 2 / 3,
      margin = margin(r = 5)
    ),
    axis.title.x = element_blank(),
    axis.text.y = element_text(
      family = font_family,
      face = "plain",
      colour = axis_colour,
      size = 9.2 * 2 / 3
    ),
    axis.text.x = element_blank(),
    plot.title = element_text(
      family = font_family,
      face = "bold",
      colour = axis_colour,
      size = 12 * 2 / 3,
      hjust = 0.5,
      margin = margin(b = 4)
    ),
    legend.position = c(0.985, 0.025),
    legend.justification = c(1, 0),
    legend.direction = "vertical",
    legend.background = element_rect(
      fill = grDevices::adjustcolor("white", alpha.f = 0.90),
      colour = "#A6A6A6",
      linewidth = 0.38
    ),
    legend.key = element_rect(fill = "transparent", colour = NA),
    legend.key.height = grid::unit(4.0, "pt"),
    legend.key.width = grid::unit(5.0, "pt"),
    legend.key.spacing.y = grid::unit(0, "pt"),
    legend.text = element_text(
      family = font_family,
      face = "plain",
      colour = axis_colour,
      size = 5.6,
      lineheight = 0.85,
      margin = margin(l = 2.67)
    ),
    legend.margin = margin(1, 2, 1, 2),
    plot.margin = margin(5, 6, 5, 5)
  )

plot <- ggplot() +
  geom_segment(
    data = segment_data,
    aes(
      x = x,
      y = y,
      xend = xend,
      yend = yend,
      colour = segment_colour
    ),
    inherit.aes = FALSE,
    linewidth = 0.6,
    lineend = "round",
    show.legend = FALSE
  ) +
  geom_point(
    data = plot_data,
    aes(
      x = x,
      y = estimate,
      fill = point_colour,
      shape = series
    ),
    inherit.aes = FALSE,
    size = 3.8,
    colour = "white",
    stroke = 0.35,
    show.legend = FALSE
  ) +
  scale_colour_identity() +
  scale_fill_identity() +
  scale_shape_manual(values = condition_shapes) +
  annotation_custom(
    condition_legend_grob,
    xmin = 3.40,
    xmax = 5.10,
    ymin = 61.3,
    ymax = 70.97
  ) +
  scale_x_continuous(
    breaks = NULL,
    labels = NULL,
    limits = c(0.72, 5.28),
    expand = expansion(mult = 0)
  ) +
  scale_y_continuous(
    breaks = seq(60, 100, by = 10),
    minor_breaks = NULL,
    labels = function(value) sprintf("%.0f", value),
    expand = expansion(mult = c(0, 0))
  ) +
  coord_cartesian(ylim = c(60, 103), clip = "on") +
  labs(title = "Experiment 2: Condition Effects", x = NULL, y = "CK Rate (%)") +
  theme_exp1

dir.create(dirname(output_path), recursive = TRUE, showWarnings = FALSE)
ggsave(
  filename = output_path,
  plot = plot,
  width = 3.35,
  height = 3.35 / ((1 + sqrt(5)) / 2),
  units = "in",
  device = grDevices::cairo_pdf,
  bg = "white"
)

cat("Wrote:\n", output_path, "\n")
