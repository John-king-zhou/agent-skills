"""Behavior checks: hourly parity, irregular-time accuracy, and a complete selected-data fit."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp
from scipy.optimize import curve_fit

spec = importlib.util.spec_from_file_location("skill_fit", Path(__file__).with_name("fit.py"))
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)


class FitTests(unittest.TestCase):
    def test_covariance_matches_scipy_curve_fit(self):
        t = np.linspace(0., 3., 15)
        y = .7*t + .2 + .03*np.sin(5*t)
        J = np.column_stack([t, np.ones_like(t)])
        model = lambda t, a, b: a*t + b
        theta, covariance = curve_fit(model, t, y, method="trf", jac=lambda t, a, b: J)
        got = F.curve_fit_covariance(J, y-model(t, *theta))
        np.testing.assert_allclose(got["covariance"], covariance, rtol=1e-12, atol=1e-16)
        np.testing.assert_allclose(got["standard_errors"], np.sqrt(np.diag(covariance)), rtol=1e-12)
        self.assertEqual(got["rank"], 2)
        self.assertEqual(got["dof"], len(t)-2)
        self.assertEqual(got["status"], "local_approximation")

    def test_rank_deficient_covariance_matches_scipy_and_is_flagged(self):
        t = np.linspace(0., 3., 15)
        y = .7*t + .03*np.sin(5*t)
        J = np.column_stack([t, t])
        model = lambda t, a, b: (a+b)*t
        theta, covariance = curve_fit(model, t, y, p0=[.3, .4], method="trf", jac=lambda t, a, b: J)
        got = F.curve_fit_covariance(J, y-model(t, *theta))
        np.testing.assert_allclose(got["covariance"], covariance, rtol=1e-12, atol=1e-16)
        self.assertEqual(got["rank"], 1)
        self.assertEqual(got["status"], "rank_deficient")
        self.assertTrue(np.isinf(got["condition_number"]))

    def test_covariance_unavailable_for_no_degrees_of_freedom_or_nonfinite_input(self):
        got = F.curve_fit_covariance(np.eye(4), np.zeros(4))
        self.assertEqual(got["status"], "insufficient_dof")
        self.assertTrue(np.isinf(got["standard_errors"]).all())
        got = F.curve_fit_covariance(np.ones((6, 4)), np.full(6, np.nan))
        self.assertEqual(got["status"], "nonfinite_inputs")
        self.assertTrue(np.isnan(got["standard_errors"]).all())

    def test_ode_se_matches_independent_natural_parameter_sensitivities(self):
        t = np.array([0., .3, 1., 2., 4., 6., 9., 13., 18., 24., 36.])
        theta = np.array([.07, .8, .15, 7.])
        def independent(th):
            mu, K, A, tau = th
            return solve_ivp(lambda tt, p: (mu*(1-p/K)+A*np.exp(-tt/tau))*p,
                             (0, t[-1]), [.05], t_eval=t, rtol=1e-12, atol=1e-14).y[0]
        pred = independent(theta)
        y = pred + np.r_[0., .0003*np.sin(np.arange(1, len(t)))]
        J = np.empty((len(t), 4))
        for k in range(4):
            h = 1e-5*theta[k]
            up, down = theta.copy(), theta.copy()
            up[k] += h
            down[k] -= h
            J[:, k] = (independent(up)-independent(down))/(2*h)
        expected = np.sqrt(np.diag(np.linalg.inv(J.T @ J)) * np.sum((y-pred)**2)/(len(y)-4))
        got = F.parameter_standard_errors(F.simulator_for(t), theta, y, scale=7.)
        np.testing.assert_allclose([got[c] for c in F.SE_COLUMNS], expected, rtol=2e-4)
        self.assertAlmostEqual(got["K_original_se"], 7*got["K_se"])
        self.assertEqual(got["se_dof"], len(y)-4)
        self.assertEqual(got["se_jacobian_rank"], 4)

    def test_hourly_matches_existing_simulator(self):
        p = F.jnp.array([.12, -.15, -.08, 1 / 7.])
        t = np.arange(25.)
        got = F.simulator_for(t)(p, F.jnp.array(.4), len(t))
        want = F.L.simulate_one(p, F.jnp.array(.4), len(t))
        np.testing.assert_allclose(got, want, atol=2e-14, rtol=2e-14)

    def test_irregular_times_match_independent_ode_solver(self):
        t = np.array([0., .3, 1.8, 6., 17.2, 24.])
        p = F.jnp.array([.12, -.15, .2, 1 / 7.])
        got = F.simulator_for(t)(p, F.jnp.array(.04), len(t))
        want = solve_ivp(lambda tt, y: (.12 - .15*y + .2*np.exp(-tt/7))*y,
                         (0, t[-1]), [.04], t_eval=t, rtol=1e-11, atol=1e-13).y[0]
        np.testing.assert_allclose(got, want, atol=2e-8, rtol=2e-8)

    def test_default_optimizer_unchanged_by_explicit_hourly_adapter(self):
        t = np.arange(13.)
        p = F.jnp.array([.12, -.15, .2, 1 / 7.])
        y = np.asarray(F.L.simulate_one(p, F.jnp.array(.04), len(t)))[None]
        tf, to_q = F.B.transform_for(np.inf), F.B.to_q_for(np.inf)
        default = F.L.make_lm(len(t), .1, F.B.W_TAU, tf)
        adapted = F.L.make_lm(len(t), .1, F.B.W_TAU, tf, simulate_fn=F.simulator_for(t))
        a = F.B.fit_best(default, F.B.starts_xi(1), y, tf, to_q)
        b = F.B.fit_best(adapted, F.B.starts_xi(1), y, tf, to_q)
        np.testing.assert_allclose(a, b, rtol=1e-5, atol=1e-7)

    def test_selected_days_window_outputs_and_skips_flat(self):
        t = np.array([0., .25, .6, 1., 1.5, 2., 2.5, 3.])
        y = solve_ivp(lambda tt, yy: .04*yy*(1-yy/.8), (0, 72), [.08],
                      t_eval=t*24, rtol=1e-11, atol=1e-13).y[0]
        data = pd.DataFrame(dict(curve=np.repeat(["selected", "flat", "other"], len(t)),
                                 day=np.tile(t, 3), value=np.r_[y, np.ones(len(t))*.2, y], observed=1))
        # This value must be excluded by the observation flag, not fitted or imputed.
        data = pd.concat([data, pd.DataFrame([dict(curve="selected", day=.4, value=.9, observed=0)])])
        with tempfile.TemporaryDirectory() as tmp:
            source, out = Path(tmp)/"data.csv", Path(tmp)/"fit"
            data.to_csv(source, index=False)
            argv = ["fit.py", "--input", str(source), "--output", str(out), "--time-col", "day",
                    "--value-col", "value", "--time-unit", "days", "--group-cols", "curve",
                    "--curve-id", "selected", "--curve-id", "flat", "--observed-col", "observed", "--start", ".25"]
            with patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
                F.main()
            summary = pd.read_csv(out/"fit_summary.csv").set_index("curve")
            self.assertEqual(set(summary.index), {"selected", "flat"})
            self.assertEqual(summary.loc["flat", "status"], "flat")
            self.assertEqual(summary.loc["selected", "status"], "fit")
            self.assertGreater(summary.loc["selected", "r2"], .99)
            row = summary.loc["selected"]
            self.assertTrue(set(F.SE_COLUMNS).issubset(summary.columns))
            self.assertEqual(row.se_dof, row.n_points-4)
            self.assertTrue(row.se_status in {"local_approximation", "rank_deficient"})
            self.assertEqual(summary.loc["flat", "se_status"], "not_fitted")
            self.assertTrue(pd.isna(summary.loc["flat", "K_se"]))
            expected = 1-row.r2 + .1*(np.sqrt(row.A_per_h**2+1e-8)+row.tau_h/24)
            self.assertAlmostEqual(row.objective, expected, places=10)
            pred = pd.read_csv(out/"predictions.csv")
            np.testing.assert_allclose(pred.elapsed_h, (t[1:]-.25)*24)
            self.assertEqual(pred.P_pred_original.iloc[0], pred.value.iloc[0])
            expected_sigma2 = np.sum((pred.P_fit_scale-pred.P_pred_fit_scale)**2)/row.se_dof
            self.assertAlmostEqual(row.se_sigma2, expected_sigma2, places=14)
            self.assertAlmostEqual(row.K_original_se, row.K_se*row.scale)
            metadata = json.loads((out/"metadata.json").read_text())
            self.assertEqual(metadata["settings"]["lambda_penalty"], .1)
            self.assertEqual(metadata["n_iterations"], 200)
            self.assertFalse(metadata["parameter_se"]["refit"])
            self.assertFalse(metadata["parameter_se"]["penalty_included"])
            self.assertEqual(metadata["parameter_se"]["n_parameters"], 4)
            self.assertTrue((out/"fits.png").exists())


if __name__ == "__main__":
    unittest.main()
