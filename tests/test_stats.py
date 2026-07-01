from evals.stats import bootstrap_ci


def test_ci_brackets_mean_and_is_deterministic():
    vals = [1.0] * 50 + [0.0] * 50   # mean 0.5
    lo, hi = bootstrap_ci(vals, n_resamples=500, seed=1)
    assert lo <= 0.5 <= hi
    assert (lo, hi) == bootstrap_ci(vals, n_resamples=500, seed=1)  # deterministic


def test_ci_all_same_is_degenerate():
    lo, hi = bootstrap_ci([1.0, 1.0, 1.0], n_resamples=200, seed=0)
    assert lo == 1.0 and hi == 1.0
