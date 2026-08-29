from scripts.market_intelligence_refresh import detect_afl_round


def test_detect_afl_round_uses_latest_prepared_round():
    assert detect_afl_round(2026) == 23
