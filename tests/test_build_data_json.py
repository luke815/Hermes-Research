"""The dashboard builders: ledger scored forward, backlog as objects, honest readings."""

import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import build_data_json as b  # noqa: E402
import universe_rank as u  # noqa: E402


def days(n, start="2026-01-01"):
    return [d.date().isoformat() for d in pd.date_range(start, periods=n, freq="D")]


def test_ledger_uses_forward_return_and_waits_for_horizon():
    dates = days(30)
    btc = [100.0 + i for i in range(30)]  # rising every day
    rows = [{"date": dates[5], "heat": 0.1, "forecast_10d": 0.02},
            {"date": dates[25], "heat": 0.1, "forecast_10d": -0.01}]
    out = b.score_ledger(rows, dates, btc)
    # day 5 -> day 15: 115 / 105 - 1, forward, not 105 / 95 - 1 trailing
    assert abs(out[0]["realized"] - (115 / 105 - 1) * 100) < 1e-4
    assert out[0]["hit"] is True
    assert out[0]["forecast"] == 2.0
    assert out[0]["matures"] == dates[15]
    # day 25 has no day 35 yet: realized and hit stay empty
    assert out[1]["realized"] is None and out[1]["hit"] is None


def test_ledger_wrong_direction_is_a_miss():
    dates = days(20)
    btc = [100.0 - i for i in range(20)]
    out = b.score_ledger([{"date": dates[0], "heat": 0, "forecast_10d": 0.03}], dates, btc)
    assert out[0]["hit"] is False


def test_backlog_item_is_an_object():
    item = b.backlog_item("D1, continued. Binance symbol lists are recorded, not admitted.", 1)
    assert item["id"] == "D1"
    assert item["title"].startswith("continued. Binance")
    assert item["status"] == "queued"  # "not admitted" is not a verdict
    plain = b.backlog_item("Score the derivatives family on 1-day returns.", 4)
    assert plain["id"] == "4" and plain["status"] == "queued"
    rej = b.backlog_item("X2. Funding gap. Verdict 2026-11-16: rejected on validation.", 2)
    assert rej["id"] == "X2" and rej["status"] == "rejected"


def test_backlog_status_ignores_verdict_words_in_passing():
    item = b.backlog_item("disproof_btc_ret_30_weekly. The admitted momentum factor on weekly bars.", 14)
    assert item["status"] == "queued"
    item = b.backlog_item("btc_funding_level_pct_bottom. Pre-registered 2026-11-16. Not yet scored. "
                          "Extends the rejected funding-level spread.", 20)
    assert item["status"] == "prereg"
    item = b.backlog_item("C1 rerun. Verdict 2026-11-15: recorded, not admitted.", 2)
    assert item["status"] == "done"
    item = b.backlog_item("L1. Inventory of every exchange. Done 2026-11-16: INVENTORY.md lists all 13.", 1)
    assert item["status"] == "done"


def test_decision_of_reads_verdict_words():
    assert b.decision_of("2026-11-16 xs relative strength, rejected") == "rejected"
    assert b.decision_of("Pre-registration: funding level") == "prereg"
    assert b.decision_of("2026-11-16 daily refresh row count") == "ops"
    assert b.decision_of("something else") is None


def test_reading_percentile_and_changes():
    dates = days(400)
    values = [float(i) for i in range(400)]
    got = b.reading(values, dates)
    assert got["value"] == 399.0
    assert got["chg_1d"] == 1.0 and got["chg_7d"] == 7.0
    assert got["pct_1y"] == 1.0
    assert len(got["spark"]) == 30


def test_reading_skips_gaps_without_inventing_changes():
    dates = days(100)
    values = [None] * 100
    values[99], values[90] = 5.0, 4.0
    got = b.reading(values, dates)
    assert got["value"] == 5.0
    assert got["chg_1d"] is None and got["chg_7d"] is None
    assert got["pct_1y"] is None  # under 60 points


def test_derivatives_block_has_both_assets():
    dates = days(120)
    series = {k: [float(i) for i in range(120)] for k in
              ("dvol_btc", "rv_btc", "skew_btc", "rr_btc", "basis_btc", "btc_funding",
               "dvol_eth", "rv_eth", "eth_funding")}
    block = b.derivatives_block(series, dates)
    names = [r["name"] for r in block["assets"]["BTC"]]
    assert "DVOL" in names and "Implied minus realized" in names
    vrp = next(r for r in block["assets"]["BTC"] if r["key"] == "vrp_btc")
    assert vrp["value"] == 0.0
    assert block["assets"]["ETH"]


def test_job_line_reports_real_age():
    ok = b.job_line("2026-11-17T05:43:29Z", "2026-11-16")
    assert ok["status"] == "OK" and ok["age_days"] == 1
    stale = b.job_line("2026-11-17T05:43:29Z", "2026-11-10")
    assert stale["status"] == "STALE" and "age=7d" in stale["line"]


def test_token_filter_drops_raw_exchange_codes():
    assert b.TOKEN.fullmatch("SOL")
    assert b.TOKEN.fullmatch("1000PEPE")
    assert b.TOKEN.fullmatch("HYPEUSDT_PERP.A") is None
    assert b.TOKEN.fullmatch("APTUSDT.6") is None
    assert b.TOKEN.fullmatch("币安人生USDT_PERP.A") is None


def test_universe_excludes_stocks_and_etfs():
    for sym in ("AAPL", "TSLA", "SPY", "QQQ", "XAU", "NATGAS", "HK0700", "ANTHROPIC", "BTC"):
        assert not u.is_crypto(sym), sym
    for sym in ("SOL", "AIN", "1000PEPE", "HYPE"):
        assert u.is_crypto(sym), sym


def test_universe_score_is_relative_to_btc():
    idx = days(100)
    btc = pd.Series([100.0 * 1.01 ** i for i in range(100)], index=idx)
    same = pd.DataFrame({"close": btc.values}, index=idx)
    got = u.score_name(same, btc)
    assert abs(got["_rs_30"]) < 1e-12 and abs(got["_rs_14"]) < 1e-12


def test_zscores_put_components_on_one_scale():
    rows = [{"a": float(i), "b": float(i) / 1000} for i in range(10)]
    za, zb = u.zscores(rows, "a"), u.zscores(rows, "b")
    for r in rows:
        assert abs(za[id(r)] - zb[id(r)]) < 1e-9


class CoverageNote(unittest.TestCase):
    def test_liquidation_row_carries_the_coverage_note(self):
        # An empty note on Liquidations hides the break the page is supposed
        # to show. The note has to name liq and say the F4 results are void,
        # and it has to come from the builder, not a hand edit of data.json.
        rows = b.data_health(["2026-11-18"])
        liq = next(r for r in rows if r["series"] == "Liquidations")
        self.assertIn("liq", liq["note"])
        self.assertIn("void", liq["note"])
        self.assertIn("2026", liq["note"])
        others = [r for r in rows if r["series"] != "Liquidations"]
        self.assertTrue(others)
        self.assertTrue(all(r["note"] == "" for r in others))
