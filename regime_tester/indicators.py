"""Indicator and factor library for the research sweep.

indicators(frame) returns one column per indicator the frame can support, on
daily, 4-hour or hourly bars alike. Each indicator carries metadata: family,
the inputs it needs, the minimum history before its value means anything, and
whether it is a level, an oscillator, a flag or a count.

The packaged set comes from the ta library (pandas-ta needs numba, which does
not build here). The custom set is what neither package carries: TD Sequential,
Pi cycle, Mayer multiple, the weekly moving-average band, funding persistence,
open interest on down days, liquidation cascades, breadth, and cross-venue
funding dispersion.
"""

import numpy as np
import pandas as pd
from ta.momentum import (
    AwesomeOscillatorIndicator, KAMAIndicator, ROCIndicator, RSIIndicator,
    StochasticOscillator, TSIIndicator, WilliamsRIndicator,
)
from ta.trend import (
    ADXIndicator, AroonIndicator, CCIIndicator, DPOIndicator, EMAIndicator,
    KSTIndicator, MACD, PSARIndicator, SMAIndicator, STCIndicator, TRIXIndicator,
    VortexIndicator, WMAIndicator,
)
from ta.volatility import AverageTrueRange, BollingerBands, DonchianChannel, KeltnerChannel
from ta.volume import (
    AccDistIndexIndicator, ChaikinMoneyFlowIndicator, EaseOfMovementIndicator,
    ForceIndexIndicator, MFIIndicator, OnBalanceVolumeIndicator,
)
from regime_tester.derivatives import DERIVATIVES_META, market_measures

LIBRARY_VERSION = "1.1.0"

# name -> (family, inputs, minimum history, kind)
META = {
    "rsi_14": ("momentum", ["close"], 15, "oscillator"),
    "stoch_k": ("momentum", ["high", "low", "close"], 14, "oscillator"),
    "williams_r": ("momentum", ["high", "low", "close"], 14, "oscillator"),
    "roc_12": ("momentum", ["close"], 13, "oscillator"),
    "tsi": ("momentum", ["close"], 39, "oscillator"),
    "awesome": ("momentum", ["high", "low"], 34, "oscillator"),
    "kama_10": ("momentum", ["close"], 15, "level"),
    "sma_20": ("trend", ["close"], 20, "level"),
    "sma_50": ("trend", ["close"], 50, "level"),
    "sma_200": ("trend", ["close"], 200, "level"),
    "ema_21": ("trend", ["close"], 21, "level"),
    "ema_50": ("trend", ["close"], 50, "level"),
    "wma_20": ("trend", ["close"], 20, "level"),
    "macd": ("trend", ["close"], 35, "oscillator"),
    "macd_signal": ("trend", ["close"], 35, "oscillator"),
    "adx_14": ("trend", ["high", "low", "close"], 28, "oscillator"),
    "aroon_up": ("trend", ["high", "low"], 25, "oscillator"),
    "aroon_down": ("trend", ["high", "low"], 25, "oscillator"),
    "cci_20": ("trend", ["high", "low", "close"], 20, "oscillator"),
    "dpo_20": ("trend", ["close"], 20, "oscillator"),
    "kst": ("trend", ["close"], 50, "oscillator"),
    "psar": ("trend", ["high", "low", "close"], 2, "level"),
    "stc": ("trend", ["close"], 50, "oscillator"),
    "trix": ("trend", ["close"], 45, "oscillator"),
    "vortex_pos": ("trend", ["high", "low", "close"], 14, "oscillator"),
    "atr_14": ("volatility", ["high", "low", "close"], 14, "level"),
    "bb_width": ("volatility", ["close"], 20, "level"),
    "bb_pct": ("volatility", ["close"], 20, "oscillator"),
    "donchian_width": ("volatility", ["high", "low"], 20, "level"),
    "keltner_width": ("volatility", ["high", "low", "close"], 20, "level"),
    "obv": ("volume", ["close", "volume"], 2, "level"),
    "cmf_20": ("volume", ["high", "low", "close", "volume"], 20, "oscillator"),
    "mfi_14": ("volume", ["high", "low", "close", "volume"], 14, "oscillator"),
    "force_13": ("volume", ["close", "volume"], 13, "oscillator"),
    "adi": ("volume", ["high", "low", "close", "volume"], 2, "level"),
    "eom": ("volume", ["high", "low", "volume"], 14, "oscillator"),
    "td_setup": ("cycle", ["close"], 13, "count"),
    "td_countdown": ("cycle", ["close", "high", "low"], 22, "count"),
    "pi_cycle": ("cycle", ["close"], 350, "flag"),
    "mayer_multiple": ("cycle", ["close"], 200, "level"),
    "weekly_band": ("cycle", ["close"], 147, "flag"),
    "funding_persist_high": ("positioning", ["funding"], 30, "count"),
    "funding_persist_low": ("positioning", ["funding"], 30, "count"),
    "oi_on_down_days": ("positioning", ["close", "oi"], 8, "level"),
    "liq_cascade": ("positioning", ["liq", "oi"], 30, "flag"),
    "breadth": ("breadth", ["breadth"], 1, "level"),
    "funding_dispersion": ("cross_venue", ["funding_dispersion"], 1, "level"),
    "dvol_level": ("options", ["dvol"], 1, "level"),
    "dvol_chg_7": ("options", ["dvol"], 8, "oscillator"),
    "dvol_pct_252": ("options", ["dvol"], 30, "oscillator"),
    "dvol_minus_rv30": ("options", ["dvol", "realized_vol"], 30, "level"),
    "atm_iv_7": ("options", ["atm_iv"], 1, "level"),
    "atm_iv_30": ("options", ["atm_iv"], 1, "level"),
    "atm_iv_90": ("options", ["atm_iv"], 1, "level"),
    "atm_term_slope": ("options", ["atm_iv"], 1, "level"),
    "atm_inversion": ("options", ["atm_iv"], 1, "flag"),
    "skew_25d_7": ("options", ["skew"], 1, "level"),
    "skew_25d_30": ("options", ["skew"], 1, "level"),
    "skew_25d_90": ("options", ["skew"], 1, "level"),
    "skew_chg_5": ("options", ["skew"], 6, "oscillator"),
    "skew_term_slope": ("options", ["skew"], 1, "level"),
    "risk_reversal_30": ("options", ["risk_reversal"], 1, "level"),
    "basis_venue": ("derivatives", ["basis"], 1, "level"),
    "basis_pct_252": ("derivatives", ["basis"], 30, "oscillator"),
    "perp_premium": ("derivatives", ["basis"], 1, "level"),
    "funding_oiw": ("derivatives", ["funding"], 1, "level"),
    "funding_oiw_avg_7": ("derivatives", ["funding"], 7, "level"),
    "funding_persist_high_oiw": ("derivatives", ["funding"], 30, "count"),
    "funding_persist_low_oiw": ("derivatives", ["funding"], 30, "count"),
    "funding_dispersion_oiw": ("derivatives", ["funding"], 1, "level"),
    "rv_7": ("derivatives", ["close"], 7, "level"),
    "rv_30": ("derivatives", ["close"], 30, "level"),
    "rv_ratio_7_30": ("derivatives", ["close"], 30, "level"),
    "vol_of_vol_30": ("derivatives", ["close"], 60, "level"),
}
META.update({f"{name}_{asset}": meta for name, meta in DERIVATIVES_META.items()
             for asset in ("btc", "eth")})


def _col(frame, name):
    return frame[name] if name in frame.columns else None


def _kst(close):
    """Know Sure Thing without the package's fill, which uses the full-sample mean.

    The packaged version fills the first bars with the mean of the whole series,
    so a price change years later moves the indicator at the start. Each rate of
    change here is left missing until its own window has elapsed.
    """
    total = None
    for roc, window, weight in ((10, 10, 1), (15, 10, 2), (20, 10, 3), (30, 15, 4)):
        change = close.pct_change(roc)
        smoothed = change.rolling(window).mean()
        total = smoothed * weight if total is None else total + smoothed * weight
    return 100 * total


def _packaged(frame):
    out = {}
    close, high, low = _col(frame, "close"), _col(frame, "high"), _col(frame, "low")
    vol = _col(frame, "volume")
    if close is not None:
        out["rsi_14"] = RSIIndicator(close, 14).rsi()
        out["roc_12"] = ROCIndicator(close, 12).roc()
        out["tsi"] = TSIIndicator(close).tsi()
        out["kama_10"] = KAMAIndicator(close, 10).kama()
        for window, name in ((20, "sma_20"), (50, "sma_50"), (200, "sma_200")):
            out[name] = SMAIndicator(close, window).sma_indicator()
        out["ema_21"] = EMAIndicator(close, 21).ema_indicator()
        out["ema_50"] = EMAIndicator(close, 50).ema_indicator()
        out["wma_20"] = WMAIndicator(close, 20).wma()
        macd = MACD(close)
        out["macd"] = macd.macd()
        out["macd_signal"] = macd.macd_signal()
        out["dpo_20"] = DPOIndicator(close, 20).dpo()
        out["kst"] = _kst(close)
        out["stc"] = STCIndicator(close).stc()
        out["trix"] = TRIXIndicator(close).trix()
        bb = BollingerBands(close, 20)
        out["bb_width"] = bb.bollinger_wband()
        out["bb_pct"] = bb.bollinger_pband()
    if close is not None and high is not None and low is not None:
        stoch = StochasticOscillator(high, low, close, 14, 3)
        out["stoch_k"] = stoch.stoch()
        out["williams_r"] = WilliamsRIndicator(high, low, close, 14).williams_r()
        out["adx_14"] = ADXIndicator(high, low, close, 14).adx()
        out["cci_20"] = CCIIndicator(high, low, close, 20).cci()
        out["psar"] = PSARIndicator(high, low, close).psar()
        out["vortex_pos"] = VortexIndicator(high, low, close, 14).vortex_indicator_pos()
        out["atr_14"] = AverageTrueRange(high, low, close, 14).average_true_range()
        out["keltner_width"] = KeltnerChannel(high, low, close, 20).keltner_channel_wband()
    if high is not None and low is not None:
        out["awesome"] = AwesomeOscillatorIndicator(high, low).awesome_oscillator()
        aroon = AroonIndicator(high, low, 25)
        out["aroon_up"] = aroon.aroon_up()
        out["aroon_down"] = aroon.aroon_down()
        out["donchian_width"] = DonchianChannel(high, low, close if close is not None else high, 20).donchian_channel_wband()
    if close is not None and vol is not None:
        out["obv"] = OnBalanceVolumeIndicator(close, vol).on_balance_volume()
        out["force_13"] = ForceIndexIndicator(close, vol, 13).force_index()
    if all(x is not None for x in (high, low, close, vol)):
        out["cmf_20"] = ChaikinMoneyFlowIndicator(high, low, close, vol, 20).chaikin_money_flow()
        out["mfi_14"] = MFIIndicator(high, low, close, vol, 14).money_flow_index()
        out["adi"] = AccDistIndexIndicator(high, low, close, vol).acc_dist_index()
    if all(x is not None for x in (high, low, vol)):
        out["eom"] = EaseOfMovementIndicator(high, low, vol, 14).ease_of_movement()
    return out


def td_sequential(close, high, low):
    """TD Sequential. Setup counts to 9, countdown to 13, both signed by direction.

    A sell setup is nine consecutive closes above the close four bars earlier; a
    buy setup is the mirror. The countdown starts after a completed setup and is
    cancelled by a close beyond the setup's extreme. The value on a bar is the
    running count, positive for a sell count and negative for a buy count, so a
    completed setup reads 9 or -9 and a completed countdown reads 13 or -13.
    """
    c = close.to_numpy(dtype=float)
    n = len(c)
    setup = np.zeros(n)
    sell = buy = 0
    for i in range(4, n):
        if np.isnan(c[i]) or np.isnan(c[i - 4]):
            sell = buy = 0
        elif c[i] > c[i - 4]:
            sell = sell + 1 if sell < 9 else 1
            buy = 0
        elif c[i] < c[i - 4]:
            buy = buy + 1 if buy < 9 else 1
            sell = 0
        else:
            sell = buy = 0
        setup[i] = sell if sell else -buy

    countdown = np.zeros(n)
    ref = c if high is None else high.to_numpy(dtype=float)
    ref_lo = c if low is None else low.to_numpy(dtype=float)
    direction = 0
    count = 0
    extreme = np.nan
    for i in range(2, n):
        if setup[i] == 9:
            direction, count, extreme = 1, 0, np.nanmin(c[max(0, i - 8):i + 1])
        elif setup[i] == -9:
            direction, count, extreme = -1, 0, np.nanmax(c[max(0, i - 8):i + 1])
        if direction == 1:
            if c[i] < extreme:
                direction = count = 0
            elif c[i] >= ref[i - 2]:
                count += 1
        elif direction == -1:
            if c[i] > extreme:
                direction = count = 0
            elif c[i] <= ref_lo[i - 2]:
                count += 1
        if count >= 13:
            countdown[i] = 13 * direction
            direction = count = 0
        else:
            countdown[i] = count * direction
    return pd.Series(setup, index=close.index), pd.Series(countdown, index=close.index)


def pi_cycle(close):
    """Flag the bar where the 111-day average crosses above twice the 350-day average."""
    fast = close.rolling(111).mean()
    slow = 2 * close.rolling(350).mean()
    cross = (fast > slow) & (fast.shift(1) <= slow.shift(1))
    return cross.astype(float).where(slow.notna())


def mayer_multiple(close):
    """Price divided by its 200-day average."""
    return close / close.rolling(200).mean()


def weekly_band(close):
    """Flag bars where price sits between the weekly 20-SMA and 21-EMA band.

    Weekly bars close on Sunday, so the band at bar t uses only weeks that have
    already closed. A daily or intraday frame is resampled; a frame that is
    already weekly is used as-is.
    """
    if isinstance(close.index, pd.DatetimeIndex) and len(close) > 1:
        step = close.index.to_series().diff().median()
        if step < pd.Timedelta(days=6):
            weekly = close.resample("W-SUN").last().dropna()
            sma = weekly.rolling(20).mean()
            ema = weekly.ewm(span=21, adjust=False).mean()
            band = pd.DataFrame({"lo": np.minimum(sma, ema), "hi": np.maximum(sma, ema)})
            band = band.shift(1).reindex(close.index, method="ffill")
            inside = (close >= band["lo"]) & (close <= band["hi"])
            return inside.astype(float)
    sma = close.rolling(20).mean()
    ema = close.ewm(span=21, adjust=False).mean()
    lo, hi = np.minimum(sma, ema), np.maximum(sma, ema)
    return ((close >= lo) & (close <= hi)).astype(float)


def funding_persistence(funding, pct=0.8, window=252):
    """Bars in a row beyond the trailing percentile. High and low counts separately."""
    hi = funding.rolling(window, min_periods=30).quantile(pct)
    lo = funding.rolling(window, min_periods=30).quantile(1 - pct)
    above = (funding > hi).to_numpy()
    below = (funding < lo).to_numpy()
    high = np.zeros(len(funding))
    low = np.zeros(len(funding))
    for i in range(len(funding)):
        high[i] = high[i - 1] + 1 if above[i] else 0
        low[i] = low[i - 1] + 1 if below[i] else 0
    return (pd.Series(high, index=funding.index), pd.Series(low, index=funding.index))


def oi_on_down_days(close, oi, window=7):
    """Change in open interest on down days minus the change on up days, over the window."""
    down = close.diff() < 0
    change = oi.diff()
    return (change.where(down, 0).rolling(window).sum()
            - change.where(~down, 0).rolling(window).sum())


def liq_cascade(liq, oi, window=90):
    """Flag a bar whose 3-day liquidations exceed the 95th percentile of their history."""
    share = liq.rolling(3).sum() / oi.replace(0, np.nan)
    bar = share.rolling(window, min_periods=30).quantile(0.95)
    return (share > bar).astype(float)


def indicators(frame):
    """Every indicator the frame can support, one column each.

    Columns the frame does not have the inputs for are absent rather than filled
    with nulls, so the sweep can see what was computable. Values use only data up
    to and including the bar they sit on; the caller lags them one bar before
    scoring.
    """
    out = _packaged(frame)
    close = _col(frame, "close")
    if close is not None:
        setup, countdown = td_sequential(close, _col(frame, "high"), _col(frame, "low"))
        out["td_setup"] = setup
        out["td_countdown"] = countdown
        out["pi_cycle"] = pi_cycle(close)
        out["mayer_multiple"] = mayer_multiple(close)
        out["weekly_band"] = weekly_band(close)
    funding = _col(frame, "funding")
    if funding is not None:
        high, low = funding_persistence(funding)
        out["funding_persist_high"] = high
        out["funding_persist_low"] = low
    if close is not None and _col(frame, "oi") is not None:
        out["oi_on_down_days"] = oi_on_down_days(close, frame["oi"])
    if _col(frame, "liq") is not None and _col(frame, "oi") is not None:
        out["liq_cascade"] = liq_cascade(frame["liq"], frame["oi"])
    if _col(frame, "breadth") is not None:
        out["breadth"] = frame["breadth"]
    if _col(frame, "funding_dispersion") is not None:
        out["funding_dispersion"] = frame["funding_dispersion"]
    for name in DERIVATIVES_META:
        for asset in ("btc", "eth"):
            column = f"{name}_{asset}"
            if _col(frame, column) is not None:
                out[column] = frame[column]
    return pd.DataFrame(out, index=frame.index)


def market_indicators():
    """The derivatives and options measures, one column per asset.

    Reads the raw store, so it is separate from indicators(frame), which only
    passes through columns the caller already has. A series the store does not
    hold is absent.
    """
    frame = market_measures()
    return indicators(frame) if len(frame.columns) else frame


def metadata():
    """One row per indicator: family, inputs, minimum history, kind."""
    return pd.DataFrame(
        [{"name": name, "family": fam, "inputs": ",".join(inp), "min_history": n, "kind": kind}
         for name, (fam, inp, n, kind) in META.items()]
    )
