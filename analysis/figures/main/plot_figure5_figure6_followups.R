#!/usr/bin/env Rscript
# Figures 5-6 now include all ten lexical-rule position/reiteration layouts.
script_flag <- grep("^--file=", commandArgs(FALSE), value = TRUE)
script_path <- sub("^--file=", "", script_flag[[1L]])
script_dir <- dirname(normalizePath(script_path, winslash = "/", mustWork = TRUE))
args <- commandArgs(TRUE)
root <- if (length(args)) normalizePath(args[[1L]], mustWork = TRUE) else
  normalizePath(file.path(script_dir, "..", "..", ".."), mustWork = TRUE)
python <- Sys.getenv("PYTHON_BIN", unset = "python3")
Sys.setenv(LEXICAL_CONFLICT_ROOT = root)
status <- system2(python, c(shQuote(file.path(root, "analysis/figures/main/plot_figures5_6.py")),
                           shQuote(file.path(root, "results/summary/rule-layouts")),
                           shQuote(script_dir)))
if (status != 0L) stop("Figure generation failed; install configs/requirements-analysis.txt and set PYTHON_BIN.")
