"""Empirical-Bayes shrinkage for the NRL base-rate matrices (v2).

Why
---
Matrix cells are split by month, venue, opponent, rest, moon phase and so on, so
a great many of them rest on a handful of games: 27% of H2H cells and 24% of
handicap cells are built on N<=5, and 128 H2H cells with N<=4 still clear the 15%
flag. A 3-0 venue record reads as a huge "backing" edge when it is three games.

The v1 sheets treat those identically to a 40-game cell. In a confluence score —
which is how these matrices are actually used — that is the damaging failure: the
net count cannot tell seven thin cells from seven solid ones.

What
----
Each cell is an observed rate p_hat over N decided games against a baseline p0
(the market-implied win probability for H2H, a flat 50% for handicap). The raw
signal is d = p_hat - p0 in percentage points.

Sampling noise alone gives d a variance of sigma^2 = p0(1-p0)/N. Pooling every
cell, method of moments splits the observed spread into real between-cell
variation and noise:

    tau^2 = max(0, var(d_observed) - mean(sigma_i^2))

and each cell is shrunk toward zero by its own reliability:

    d_shrunk = d * tau^2 / (tau^2 + sigma_i^2)

An N=3 cell keeps almost nothing; a 100-game cell keeps almost all of it. This is
the same estimator already used for the EFL Championship referee cards workbook.

Edges are reported in PERCENTAGE POINTS, not as a fraction of the baseline. v1's
H2H edge divided by the implied probability, so the same "15%" label meant 4.5pp
for a big dog and 10.7pp for a heavy favourite — 92% of big-dog cells cleared the
flag against 39% of big-favourite cells. Points are the same unit everywhere.
"""

from __future__ import annotations


class Shrinker:
    """Two-pass empirical-Bayes shrinker. Feed every cell, then call fit()."""

    def __init__(self) -> None:
        self._cells: list[tuple[float, float, int]] = []
        self.tau2: float | None = None

    def observe(self, actual_pct: float, baseline_pct: float, n: int) -> None:
        if n and n > 0:
            self._cells.append((actual_pct, baseline_pct, n))

    @staticmethod
    def _sigma2(baseline_pct: float, n: int) -> float:
        """Sampling variance of the rate, in pp^2."""
        p = min(max(baseline_pct / 100.0, 1e-6), 1 - 1e-6)
        return p * (1 - p) / max(n, 1) * 10000.0

    def fit(self) -> float:
        if not self._cells:
            self.tau2 = 0.0
            return 0.0
        ds = [a - b for a, b, _ in self._cells]
        mean_d = sum(ds) / len(ds)
        var_obs = sum((d - mean_d) ** 2 for d in ds) / len(ds)
        mean_sig = sum(self._sigma2(b, n) for _, b, n in self._cells) / len(self._cells)
        self.tau2 = max(0.0, var_obs - mean_sig)
        return self.tau2

    def factor(self, baseline_pct: float, n: int) -> float:
        """Reliability weight in [0, 1] — the share of the raw gap that survives."""
        if self.tau2 is None:
            raise RuntimeError("call fit() before factor()")
        if self.tau2 <= 0:
            return 0.0
        s2 = self._sigma2(baseline_pct, n)
        return self.tau2 / (self.tau2 + s2)

    def shrink(self, actual_pct: float, baseline_pct: float, n: int) -> float:
        """Shrunk edge in percentage points, signed."""
        return (actual_pct - baseline_pct) * self.factor(baseline_pct, n)

    def report(self) -> str:
        if self.tau2 is None:
            return "unfitted"
        ns = sorted({n for _, _, n in self._cells})
        ex = [(n, self.factor(50.0, n)) for n in (3, 5, 10, 25, 50, 100) if n <= max(ns)]
        keeps = "  ".join(f"N={n}:{f*100:.0f}%" for n, f in ex)
        return (f"tau={self.tau2**0.5:.2f}pp over {len(self._cells)} cells; "
                f"share of raw gap kept -> {keeps}")
