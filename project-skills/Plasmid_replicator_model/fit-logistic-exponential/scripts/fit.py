"""Apply the repository's group-6 optimizer to selected long-format time series."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

os.environ.setdefault("XLA_PYTHON_CLIENT_PREALLOCATE", "false")
ROOT = Path(__file__).resolve().parents[4]
BENCH = ROOT / "random_assembly_simulation_fit/replicator_fit_benchmark"
sys.path.insert(0, str(BENCH))
import numpy as np
import pandas as pd
import jax
import jax.numpy as jnp
from jax import lax
import replicator_lib as L
import replicator_fit_benchmark as B

SE_COLUMNS = ["mu_se_per_h", "K_se", "A_se_per_h", "tau_se_h"]


def curve_fit_covariance(jacobian, residuals):
    """Unweighted curve_fit/trf covariance with absolute_sigma=False.

    Evaluated at the supplied solution; no optimization or penalty curvature.
    Like SciPy's bounded curve_fit, singular directions are discarded by SVD.
    A finite pseudoinverse SE does not identify a rank-deficient parameter.
    """
    J = np.asarray(jacobian, dtype=float)
    r = np.asarray(residuals, dtype=float)
    if J.ndim != 2 or J.shape[1] == 0 or r.shape != (J.shape[0],):
        raise ValueError("Expected an (n, p) Jacobian and n residuals, with p > 0")
    n, p = J.shape
    dof = n - p
    result = dict(covariance=np.full((p, p), np.nan), standard_errors=np.full(p, np.nan),
                  dof=dof, sigma2=np.nan, rank=np.nan, condition_number=np.nan,
                  status="nonfinite_inputs")
    if not np.isfinite(J).all() or not np.isfinite(r).all():
        return result
    try:
        _, s, vt = np.linalg.svd(J, full_matrices=False)
    except np.linalg.LinAlgError:
        result["status"] = "svd_failed"
        return result
    threshold = np.finfo(float).eps * max(J.shape) * (s[0] if len(s) else 0.)
    keep = s > threshold
    rank = int(keep.sum())
    result.update(rank=rank, condition_number=float(s[0] / s[-1]) if rank == p else np.inf)
    if dof <= 0:
        result.update(covariance=np.full((p, p), np.inf), standard_errors=np.full(p, np.inf),
                      status="insufficient_dof")
        return result
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        sigma2 = float(r @ r / dof)
        v = vt[keep]
        covariance = (v.T / s[keep]**2) @ v * sigma2
        se = np.sqrt(np.diag(covariance))
    status = "rank_deficient" if rank < p else "local_approximation"
    if not np.isfinite(covariance).all():
        status = "nonfinite_covariance"
    result.update(covariance=covariance, standard_errors=se, sigma2=sigma2, status=status)
    return result


def parameter_standard_errors(simulate, natural, y, scale=1.):
    """Natural-parameter sensitivities, conditional on the observed fixed P0."""
    def forward(theta):
        mu, K, A, tau = theta
        coefficients = jnp.array([mu, -mu / K, A, 1 / tau])
        return simulate(coefficients, jnp.asarray(y[0]), len(y))

    theta = jnp.asarray(natural)
    predicted = np.asarray(forward(theta))
    J = np.asarray(jax.jacfwd(forward)(theta))
    info = curve_fit_covariance(J, y - predicted)
    row = dict(zip(SE_COLUMNS, info["standard_errors"]))
    row.update(K_original_se=row["K_se"] * scale, se_dof=info["dof"],
               se_sigma2=info["sigma2"], se_jacobian_rank=info["rank"],
               se_jacobian_condition=info["condition_number"], se_status=info["status"])
    return row


def simulator_for(t_hours):
    """RK4 at actual observation times, with the benchmark's maximum 0.1 h step."""
    t = np.asarray(t_hours, dtype=float)
    if len(t) < 2 or not np.isfinite(t).all() or t[0] != 0 or np.any(np.diff(t) <= 0):
        raise ValueError("Times must be finite, strictly increasing and start at zero")
    counts = np.maximum(1, np.ceil(np.diff(t) * 10).astype(int))
    edges = np.concatenate([np.linspace(a, b, n + 1)[:-1]
                            for a, b, n in zip(t[:-1], t[1:], counts)])
    widths = np.repeat(np.diff(t) / counts, counts)
    sample_idx = jnp.asarray(np.cumsum(counts) - 1)
    steps = jnp.asarray(np.column_stack([edges, widths]))

    def simulate(p, p0, n_time):
        def rhs(y, tt):
            return (p[0] + p[1] * y + p[2] * jnp.exp(-p[3] * tt)) * y

        def step(y, th):
            tt, h = th
            k1 = rhs(y, tt)
            k2 = rhs(y + h / 2 * k1, tt + h / 2)
            k3 = rhs(y + h / 2 * k2, tt + h / 2)
            k4 = rhs(y + h * k3, tt + h)
            y = jnp.clip(y + h / 6 * (k1 + 2 * (k2 + k3) + k4), -5., 5.)
            return y, y

        _, ys = lax.scan(step, p0, steps)
        return jnp.concatenate([p0[None], ys[sample_idx]])
    return simulate


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--time-col", required=True)
    parser.add_argument("--value-col", required=True)
    parser.add_argument("--time-unit", choices=["hours", "days", "minutes"], required=True)
    parser.add_argument("--group-cols", nargs="+", default=[])
    parser.add_argument("--curve-id", action="append")
    parser.add_argument("--observed-col")
    parser.add_argument("--start", type=float)
    parser.add_argument("--end", type=float)
    parser.add_argument("--normalization", choices=["none", "max"], default="none")
    parser.add_argument("--lambda-penalty", type=float, default=.1)
    parser.add_argument("--min-relative-range", type=float, default=.01)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output directory already exists; select a fresh directory")
    if not np.isfinite(args.lambda_penalty) or args.lambda_penalty < 0:
        parser.error("lambda must be finite and nonnegative")
    if not 0 <= args.min_relative_range <= 1:
        parser.error("min-relative-range must be between zero and one")
    if args.start is not None and args.end is not None and args.start > args.end:
        parser.error("start must be <= end")
    if args.curve_id and len(args.group_cols) != 1:
        parser.error("--curve-id requires exactly one group column")
    frame = pd.read_csv(args.input)
    required = [args.time_col, args.value_col] + args.group_cols
    if args.observed_col:
        required.append(args.observed_col)
    if missing := set(required) - set(frame.columns):
        parser.error(f"Missing columns: {sorted(missing)}")
    n_input = len(frame)
    if args.curve_id:
        col = frame[args.group_cols[0]].astype(str)
        if missing := set(args.curve_id) - set(col):
            parser.error(f"Unknown curve IDs: {sorted(missing)}")
        frame = frame[col.isin(args.curve_id)].copy()
    frame[args.time_col] = pd.to_numeric(frame[args.time_col], errors="raise")
    frame[args.value_col] = pd.to_numeric(frame[args.value_col], errors="raise")
    if args.observed_col:
        frame = frame[frame[args.observed_col] == 1].copy()
    if args.start is not None:
        frame = frame[frame[args.time_col] >= args.start].copy()
    if args.end is not None:
        frame = frame[frame[args.time_col] <= args.end].copy()
    if frame.empty:
        parser.error("Selection contains no observations")
    finite = np.isfinite(frame[[args.time_col, args.value_col]]).all(axis=1)
    excluded = frame.loc[~finite].copy()
    excluded["exclusion_reason"] = "nonfinite_time_or_value"
    frame = frame.loc[finite].copy()
    if frame.empty:
        parser.error("Selection contains no finite observations")
    if (frame[args.value_col] < 0).any():
        parser.error("Negative abundance values require explicit preprocessing")
    if args.normalization == "none" and frame[args.value_col].max() > 1 + 1e-10:
        parser.error("Values exceed 1: convert to fractions or explicitly select --normalization max")
    groups = frame.groupby(args.group_cols, sort=False, dropna=False) if args.group_cols else [((), frame)]
    factor = {"hours": 1., "days": 24., "minutes": 1 / 60}[args.time_unit]
    tf, to_q = B.transform_for(np.inf), B.to_q_for(np.inf)
    rows, predictions = [], []
    for key, group in groups:
        key = key if isinstance(key, tuple) else (key,)
        group = group.sort_values(args.time_col)
        ident = dict(zip(args.group_cols, key))
        t_raw = group[args.time_col].to_numpy(float)
        if np.any(np.diff(t_raw) <= 0):
            parser.error(f"Duplicate times in {ident}; retain replicate IDs in grouping or explicitly aggregate")
        t = (t_raw - t_raw[0]) * factor
        original = group[args.value_col].to_numpy(float)
        scale = original.max() if args.normalization == "max" and original.max() > 0 else 1.
        y = original / scale
        row = dict(ident, n_points=len(y), t_start_input=t_raw[0], t_end_input=t_raw[-1],
                   scale=scale, lambda_penalty=args.lambda_penalty)
        row.update({name: np.nan for name in SE_COLUMNS + ["K_original_se", "se_dof", "se_sigma2",
                    "se_jacobian_rank", "se_jacobian_condition", "tau_at_lower_bound"]})
        row["se_status"] = "not_fitted"
        status = ("too_few_points" if len(y) < 5 else "nonpositive_initial" if y[0] <= 0 else
                  "flat" if np.ptp(y) <= 1e-12 or np.ptp(y) / y.max() < args.min_relative_range else "fit")
        row["status"] = status
        if status == "fit":
            sim = simulator_for(t)
            fit = L.make_lm(len(t), args.lambda_penalty, B.W_TAU, tf, simulate_fn=sim)
            theta = B.fit_best(fit, B.starts_xi(1), y[None], tf, to_q)[0]
            pred = np.asarray(sim(jnp.asarray(theta), jnp.asarray(y[0]), len(t)))
            th = B.natural(theta[None])[0]
            r2 = 1 - np.sum((y - pred)**2) / np.sum((y - y.mean())**2)
            pen = float(L.penalty(jnp.asarray(theta), B.W_TAU))
            objective = 1 - r2 + args.lambda_penalty * pen
            valid = (np.isfinite(th).all() and np.isfinite(pred).all() and np.isfinite(objective)
                     and th[1] > 0 and th[3] >= B.TAU_LO)
            row.update(zip(["mu_per_h", "K", "A_per_h", "tau_h"], th))
            row.update(r2=r2, penalty=pen, objective=objective, K_original=th[1] * scale,
                       status="fit" if valid else "fit_failed",
                       prediction_at_clip=bool(np.any(np.abs(pred) >= 5 - 1e-10)),
                       tau_at_lower_bound=bool(np.isclose(th[3], B.TAU_LO, rtol=0., atol=1e-5)))
            if valid:
                row.update(parameter_standard_errors(sim, th, y, scale))
            else:
                row["se_status"] = "fit_failed"
            p = group.copy()
            p["elapsed_h"], p["P_fit_scale"] = t, y
            p["P_pred_fit_scale"], p["P_pred_original"] = pred, pred * scale
            predictions.append(p)
        rows.append(row)
        print(f"{ident or 'trajectory'}: {row['status']}, R2={row.get('r2', float('nan')):.5g}", flush=True)
    # Validate everything before creating a fresh output directory; never overwrite previous fits.
    args.output.mkdir(parents=True, exist_ok=False)
    pd.DataFrame(rows).to_csv(args.output / "fit_summary.csv", index=False)
    (pd.concat(predictions, ignore_index=True) if predictions else pd.DataFrame()).to_csv(
        args.output / "predictions.csv", index=False)
    excluded.to_csv(args.output / "excluded_observations.csv", index=False)
    metadata = dict(settings={k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
                    model="dP/dt=mu*P*(1-P/K)+A*P*exp(-t/tau)", group=6,
                    objective="SSE/SST+lambda*(sqrt(A**2+1e-8)+tau/24)",
                    bounds="K>0, tau>=0.1 h, no upper cap; signed mu,A", n_iterations=L.N_ITER,
                    starts=B.STARTS_NATURAL, initial_condition="first retained observation; clock reset to zero",
                    time_internal="hours", max_rk4_step_h=.1, weights=B.W_TAU,
                    parameter_se=dict(
                        method="curve_fit-style unweighted covariance; absolute_sigma=False; trf SVD pseudoinverse",
                        formula="covariance=SSE/(n-p) * pinv(J.T@J); SE=sqrt(diag(covariance))",
                        parameters=["mu_per_h", "K", "A_per_h", "tau_h"], n_parameters=4,
                        jacobian="JAX jacfwd of fitted trajectories in natural parameters at actual observation times",
                        observation_count="all retained observations, including the fixed-P0 anchor (zero residual and sensitivity)",
                        noise="independent equal-variance residual errors; sigma2=SSE/(n_points-4), in fit-scale abundance squared",
                        svd_cutoff="eps(float64)*max(J.shape)*largest_singular_value; no eigenvalue floor",
                        penalty_included=False, refit=False, initial_condition_uncertainty_included=False,
                        K_original_se="K_se * scale",
                        caveat="local diagnostic at the penalized estimate, not calibrated penalized-estimator confidence intervals; rank-deficient pseudoinverse SEs are unreliable; inspect conditioning, tau boundary, small A, and clipping"),
                    n_input_rows=n_input, n_selected_rows=len(frame), n_nonfinite_excluded=len(excluded),
                    source=str(args.input.resolve()), input_sha256=digest(args.input),
                    code_sha256={str(p.relative_to(ROOT)): digest(p) for p in
                                 [Path(__file__), BENCH / "replicator_lib.py", BENCH / "replicator_fit_benchmark.py"]},
                    jax_version=jax.__version__, devices=[str(d) for d in jax.devices()])
    (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    if predictions:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(9, 5))
        for i, p in enumerate(predictions):
            label = ", ".join(str(p[c].iloc[0]) for c in args.group_cols) or "trajectory"
            color = f"C{i % 10}"
            ax.plot(p.elapsed_h, p.P_fit_scale, "o", color=color, ms=3)
            ax.plot(p.elapsed_h, p.P_pred_fit_scale, color=color, label=label)
        ax.set(xlabel="Hours since first retained observation", ylabel="Abundance (fit scale)")
        if len(predictions) <= 12:
            ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(args.output / "fits.png", dpi=160)
        plt.close(fig)


if __name__ == "__main__":
    main()
