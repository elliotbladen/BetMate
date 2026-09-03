# UCL xG activation audit

The shared UCL engine now consumes the audited SofaScore shotmap xG for 342 modern-era fixtures and uses an explicit goals fallback for the remaining 36 modern fixtures plus older seasons. The mixed source is labelled per row; no market data is used.

Coverage: 342/1,997 matches (17.1%) have SofaScore xG; 1,655 remain goals fallback. The full walk-forward rerun completed 1,872 predictions with RPS 0.2073, Brier 0.5744, log loss 0.9673 and accuracy 56.25%. On 2024/25–2025/26 (378 matches), RPS was 0.2217, Brier 0.5789, log loss 0.9701 and accuracy 53.97%.

This is an honest mixed-input improvement step, not evidence that SofaScore xG is superior yet. The next gate is provider comparison and expanding xG coverage; the 36 unmapped matches remain quarantined.
