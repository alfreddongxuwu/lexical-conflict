derivative_diagnostics <- function(derivs) {
  gradient <- derivs$gradient
  hessian <- derivs$Hessian
  max_abs <- function(x) if (length(x) && all(is.finite(x))) max(abs(x)) else NA_real_
  gradient_available <- !is.null(gradient)
  hessian_available <- !is.null(hessian)
  hessian_min <- NA_real_
  hessian_positive <- NA
  scaled_gradient <- NULL
  if (hessian_available) {
    stopifnot(is.matrix(hessian), nrow(hessian) > 0L,
      nrow(hessian) == ncol(hessian), all(is.finite(hessian)))
    hessian_min <- min(eigen(hessian, symmetric = TRUE, only.values = TRUE)$values)
    hessian_positive <- hessian_min > 0
    if (isTRUE(hessian_positive) && gradient_available) {
      stopifnot(length(gradient) == nrow(hessian))
      scaled_gradient <- solve(chol(hessian), gradient)
    }
  }
  list(hessian_available = hessian_available, gradient_available = gradient_available,
    hessian_min_eigenvalue = hessian_min, hessian_positive_definite = hessian_positive,
    max_abs_raw_gradient = max_abs(gradient), max_abs_scaled_gradient = max_abs(scaled_gradient),
    note = if (!hessian_available) "Hessian unavailable; definiteness and scaled-gradient convergence cannot be assessed." else "")
}
