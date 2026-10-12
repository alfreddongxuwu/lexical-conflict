# Baseline familiarity rates by model.
# For each model, the left and right bars show the proportion of Familiar
# responses in semantically consistent and inconsistent contexts, respectively.
# A Familiar response contains an accepted translation of the source word's
# familiar meaning. The saved EXPECTED label encodes this response category.

suppressPackageStartupMessages(library(ggplot2))

script_arg <- grep("^--file=", commandArgs(), value = TRUE)
script_path <- normalizePath(
  sub("^--file=", "", script_arg[[1L]]),
  winslash = "/",
  mustWork = TRUE
)
output_dir <- dirname(script_path)
args <- commandArgs(TRUE); data_root <- if (length(args) >= 1L) normalizePath(args[[1L]], winslash = "/", mustWork = TRUE) else normalizePath(file.path(output_dir, "..", "..", "..", "statistics", "primary"), winslash = "/", mustWork = TRUE)
data_path <- normalizePath(
  file.path(
    data_root,
    "data", "derived", "exp1_unfiltered.csv"
  ),
  winslash = "/",
  mustWork = TRUE
)
output_path <- file.path(output_dir, "figure2_baseline_familiarity_rates.pdf")

# Place GPT-5.5 first; order other families alphabetically and sizes small to large.
model_ids <- c(
  "chatgpt5_5_instant",
  "deepseek_llm_7b",
  "deepseek_llm_67b",
  "gemma3_4b",
  "gemma3_27b",
  "llama3_8b",
  "llama3_70b",
  "qwen3_8b",
  "qwen3_32b"
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
context_levels <- c("Consistent", "Inconsistent")
context_colours <- c(Consistent = "#F2B454", Inconsistent = "#67AA76")
context_labels <- c(
  Consistent = "Semantically consistent context",
  Inconsistent = "Semantically inconsistent context"
)

dat <- read.csv(data_path, stringsAsFactors = FALSE, check.names = FALSE)
required_columns <- c(
  "model", "matched_baseline_type", "matched_baseline_prompt_id",
  "matched_baseline_label"
)
stopifnot(all(required_columns %in% names(dat)))

baseline <- unique(dat[required_columns])
baseline <- baseline[baseline$model %in% model_ids, , drop = FALSE]
stopifnot(
  nrow(baseline) == length(model_ids) * 750L,
  !anyDuplicated(baseline[c("model", "matched_baseline_prompt_id")]),
  all(baseline$matched_baseline_type %in%
        c("normal_lexical", "anomalous_no_lexicon")),
  all(baseline$matched_baseline_label %in% c("EXPECTED", "OTHER"))
)
baseline$context <- ifelse(
  baseline$matched_baseline_type == "normal_lexical",
  "Consistent", "Inconsistent"
)
# EXPECTED is the saved coding label for a familiar translation.
# All baseline responses remain in their own context's denominator.
baseline$familiar <- as.integer(baseline$matched_baseline_label == "EXPECTED")
rate_data <- aggregate(
  list(familiar_n = baseline$familiar, total = rep.int(1L, nrow(baseline))),
  by = list(model = baseline$model, context = baseline$context),
  FUN = sum
)
rate_data$model_index <- match(rate_data$model, model_ids)
rate_data$context_index <- match(rate_data$context, context_levels)
rate_data <- rate_data[order(rate_data$model_index, rate_data$context_index), ]
rate_data$rate <- 100 * rate_data$familiar_n / rate_data$total
rate_data$context <- factor(rate_data$context, levels = context_levels, ordered = TRUE)
stopifnot(
  nrow(rate_data) == length(model_ids) * 2L,
  all(rate_data$total == ifelse(rate_data$context == "Consistent", 150L, 600L)),
  !anyNA(rate_data),
  all(rate_data$rate >= 0 & rate_data$rate <= 100)
)

# Split each original 0.40-wide bar into two 0.20-wide bars.
# Preserve the original model centres, 0.12 group gaps and x-axis limits.
bar_width <- 0.40
bar_gap <- 0.12
model_centres <-
  bar_gap + bar_width / 2 +
  (seq_along(model_ids) - 1L) * (bar_width + bar_gap)
context_bar_width <- bar_width / 2
rate_data$x_position <- model_centres[rate_data$model_index] +
  ifelse(rate_data$context == "Consistent", -1, 1) * bar_width / 4
bar_region_end <- tail(model_centres, 1L) + bar_width / 2 + bar_gap
x_limits <- c(0, bar_region_end)

plot_object <- ggplot(rate_data) +
  geom_rect(
    aes(
      xmin = x_position - context_bar_width / 2,
      xmax = x_position + context_bar_width / 2,
      ymin = 0,
      ymax = rate,
      fill = context
    ),
    colour = NA
  ) +
  scale_fill_manual(
    values = context_colours,
    breaks = context_levels,
    labels = unname(context_labels[context_levels]),
    drop = FALSE,
    name = NULL
  ) +
  scale_x_continuous(
    breaks = model_centres,
    labels = unname(model_labels[model_ids]),
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
    title = "Baseline Familiarity Rates",
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
    axis.ticks.length = grid::unit(2.5, "pt"),
    axis.title.y = element_text(size = 15.6, margin = margin(r = 5)),
    axis.text.y = element_text(size = 13.8),
    axis.text.x = element_text(
      size = 8.7, angle = 38, hjust = 1, vjust = 1
    ),
    plot.title = element_text(
      family = "sans", face = "bold", colour = "#000000",
      size = 18, hjust = 0.5, margin = margin(b = 2)
    ),
    legend.position = "inside",
    legend.position.inside = c(0.985, 0.030),
    legend.justification = c(1, 0),
    legend.direction = "vertical",
    legend.background = element_rect(
      fill = grDevices::adjustcolor("white", alpha.f = 0.90),
      colour = "#A6A6A6",
      linewidth = 0.42
    ),
    legend.key = element_rect(fill = "transparent", colour = NA),
    legend.key.height = grid::unit(0.72, "lines"),
    legend.key.width = grid::unit(0.90, "lines"),
    legend.key.spacing.y = grid::unit(0, "pt"),
    legend.title = element_blank(),
    legend.text = element_text(size = 10.8, margin = margin(l = 2)),
    legend.margin = margin(1.5, 2.5, 1.5, 2.5),
    plot.margin = margin(3, 4, 8, 5.6)
  )

grDevices::cairo_pdf(
  output_path,
  width = 6.20,
  height = 3.15,
  bg = "white"
)
print(plot_object)
grDevices::dev.off()

print(rate_data[c("model", "context", "familiar_n", "total", "rate")], row.names = FALSE)
pooled <- aggregate(cbind(familiar_n, total) ~ context, data = rate_data, FUN = sum)
pooled$rate <- 100 * pooled$familiar_n / pooled$total
stopifnot(
  round(pooled$rate[pooled$context == "Consistent"], 2) == 85.56,
  round(pooled$rate[pooled$context == "Inconsistent"], 2) == 71.00
)
print(pooled, row.names = FALSE)
cat("Wrote:\n", normalizePath(output_path, winslash = "/"), "\n")
