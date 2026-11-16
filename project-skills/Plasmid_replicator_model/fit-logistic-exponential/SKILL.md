---
name: fit-logistic-exponential
description: Fit selected plasmid/gene abundance time series with this repository's logistic plus decaying exponential boost model, using benchmark group 6 and penalty lambda 0.1 by default, or with pure logistic when requested. Supports simulation and experimental trajectories with local parameter SEs.
---

By default, fit the user's selected data with

`dP/dt = mu*P*(1 - P/K) + A*P*exp(-t/tau)`

Use `K > 0`, `tau >= 0.1 h` with no upper bound, and signed `mu` and `A`. Default to group 6 with `lambda = 0.1` and objective

`SSE/SST + lambda*(sqrt(A**2 + 1e-8) + tau/24)`.

This is an integrated trajectory fit; the exponential multiplies P in the ODE. It is not an additive exponential in a closed-form logistic curve. Use the existing benchmark LM optimizer, its 200 iterations, and all three fixed starts; keep the lowest penalized objective. Do not silently substitute plain logistic, derivative regression, or an A-only penalty. See [model provenance](references/model-provenance.md) when confirming historical use.

When the user requests **pure logistic**, use the nested model

`dP/dt = mu*P*(1 - P/K)`.

Only `mu` (per hour, signed) and `K` (same abundance scale as P, strictly positive) are estimated. Set `A = 0` by model definition; tau is absent, not an estimated decay time. Use `lambda = 0` and objective `SSE/SST`, with no exponential or other parameter penalty. Retain the same integrated-trajectory approach, observed times, fixed P0, hours, normalization, and numerical checks. With negative mu, trajectories below K decline; K is then a threshold rather than an attracting carrying capacity.

Reuse the parametrization `q=(mu, log(K))`, `tf`, `to_q`, and `W_NONE` in `random_assembly_simulation_fit/replicator_fit_benchmark/logistic_fit_benchmark.py`, the existing LM's 200 iterations, and all three `(mu,K)` projections of the benchmark starts; retain the lowest unpenalized objective. The rate stored in the simulator's coefficient vector is a dummy when A is zero and must not be reported as a fitted tau. `scripts/fit.py` currently exposes the boost model only: for selected-data pure logistic fits, adapt its observation-time simulator and data handling to the two-parameter benchmark fit in the analysis output area. Do not invoke the logistic benchmark's all-trajectory `main()` for a selected-data request.

For pure logistic, report mu and K with their local SEs, R², and the unpenalized objective; label A as fixed zero and tau as absent. Calculate SEs from the two-column natural-parameter Jacobian `theta=(mu,K)` with `p=2`, hence `sigma2=SSE/(n-2)`, following the covariance convention below. Leave A/tau SEs unavailable, rather than reporting zero uncertainty for parameters that were not estimated. For an explicit comparison with the boost model, keep the observation selection, window, normalization, and P0 convention aligned and record the model in outputs.

Resolve the dataset, curve IDs/grouping, response, time units, fitting window, and normalization from the request and local data documentation. If the user has not selected any data, ask which data to fit; an open IDE tab alone is not a selection. Continue with reversible inspection while clarification is pending. Preserve separate replicates unless pooling is requested. For `ghost_effect_fit`, respect its README: select one experiment and its fitting choices, write new work outside the archive, and do not restart all-experiment fits.

Use hours internally (days × 24, minutes / 60); reset the boost clock to the first retained observation and fix P0 to that observation. Preserve observed sampling times; do not invent hourly observations or impute missing values. Split at interventions when the requested window requires it. Do not change lambda or the 24-hour penalty reference just because observations are reported in days. Flag sparse sampling relative to tau and changes in the fitting horizon when interpreting results.

Use fraction/normalized abundances directly. For other scales, choose and report a normalization appropriate to the data before fitting; the helper offers explicit per-curve maximum normalization. Do not silently convert percentages or normalize each curve. Record excluded observations and failed/flat curves. The helper rejects negative values and records missing values; it skips nonpositive P0, fewer than five observations, and curves with relative range below 1% (configurable).

Run from the repo root with the `replicator-jax` environment. `scripts/fit.py` accepts long-format CSV with one response and time column, plus optional curve/group columns; adapt wide CSV, arrays, or other sources into a documented long-format CSV in the analysis output area. Carry identifying columns in `--group-cols` and use `--observed-col` when observation flags are present. Select curve IDs with repeatable `--curve-id` (single group column), or prepare a filtered input CSV for complex selections. Never treat SE/SD columns as separate trajectories. Fits use the benchmark's unweighted reconstruction objective, not SE weights.

Example (only when LT5 has actually been selected):

```bash
conda run -n replicator-jax python .agents/skills/fit-logistic-exponential/scripts/fit.py \
  --input ghost_effect_data/data/by_experiment/LT5.csv \
  --time-col day --time-unit days --value-col P_rel --group-cols curve_id \
  --observed-col observed --curve-id 'LT5|clonal|MG1655|pSC101|P0=100%|rep1' \
  --output ghost_effect_fit/LT5_logistic_exponential
```

Use `--start`/`--end` in the input time unit for a window, `--lambda-penalty` to honor an explicit override, and `--normalization max` only when selected. Use a fresh output directory. For large datasets, use an appropriate batch/GPU job rather than launching an unbounded login-node fit.

Review `fit_summary.csv`, `predictions.csv`, `fits.png`, and `metadata.json`. Report the model and its estimated parameters and local SEs with units, unpenalized reconstruction R² separately from the objective, skipped/failure counts, source/window/normalization, and the penalty used. With maximum normalization, `K_original` and `K_original_se` restore K and its SE to the input abundance scale. Inspect overlays and clipping flags before interpreting a fit; numerical clipping is inherited from the benchmark. A near-zero boost leaves tau uninformative; near-zero mu confounds K. Penalized tau is not an independent measurement of decay time. Do not claim identifiability from R² alone; use the benchmark sensitivity/FIM methods if that analysis is requested.

For every successful fit, calculate **curve_fit-style parameter SEs** using the unweighted `sigma=None, absolute_sigma=False` convention from [SciPy curve_fit](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.curve_fit.html). Keep the selected model's benchmark optimizer, bounds, starts, and point estimates; do not refit with SciPy. Evaluate the trajectory Jacobian `J[i,j] = dP_pred(t_i)/dtheta_j` in natural parameters `theta=(mu,K,A,tau)` for boost fits or `theta=(mu,K)` for pure logistic, with JAX AD at the actual observation times, holding P0 fixed. Use unpenalized residuals on the fit abundance scale:

```text
n = number of retained observations; p = 4 for boost, 2 for pure logistic
sigma2 = SSE / (n - p)
covariance = sigma2 * (J.T @ J)^-1
SE = sqrt(diag(covariance))
```

Count the fixed-P0 first observation in n to match applying curve_fit to the full prediction vector; its residual and sensitivity are zero. This is conditional on P0, with no propagation of its measurement uncertainty. For explicitly requested shared-parameter fits, stack the observation residuals and sensitivities and count only the jointly estimated free parameters once.

The helper writes `mu_se_per_h`, `K_se`, `A_se_per_h`, `tau_se_h`, `K_original_se`, `se_sigma2`, `se_dof`, `se_jacobian_rank`, `se_jacobian_condition`, `se_status`, and `tau_at_lower_bound` to `fit_summary.csv`, with the convention in `metadata.json`. Use the bounded curve_fit (`trf`/`dogbox`) SVD pseudoinverse convention: discard singular values at or below `eps*max(J.shape)*s_max`, without the benchmark FIM's eigenvalue floor. Flag rank deficiency; finite pseudoinverse SEs do not establish identifiability. Nonpositive residual degrees of freedom give unavailable/infinite SEs; failed/skipped fits have no SEs. Keep any separately requested benchmark 5%-noise FIM SEs distinctly labeled.

Describe these SEs as local linear approximations at the selected solution, assuming independent equal-variance residual errors. They exclude temporal correlation and biological model variation. For boost fits, they also exclude penalty curvature and shrinkage bias and are not calibrated confidence intervals for the penalized estimator. Flag a large condition number, near-zero mu, numerical clipping, and (for boost fits) near-zero A or `tau_at_lower_bound` before interpreting SEs. Do not present symmetric confidence intervals as reliable in these cases.
