"""Independent re-implementation of TD Sequential (DeMark) from the stated definition.

Written WITHOUT reading harness3.py. Definition used (from the task):
  buy setup  : 9 consecutive bars with close < close 4 bars earlier; the count resets to 0 on any bar that
               fails; the 9th bar is the completion bar (flag buy9). Sell setup mirror with '>'.
  perfected  : close of bar 8 or 9 <= closes of bars 6 and 7  (closes only; no highs/lows in the panel), i.e.
               min(c8, c9) <= min(c6, c7). Flag buy9p on the completion bar. Sell mirror: max(c8,c9) >= max(c6,c7).
  countdown  : after a completed buy setup, count (not necessarily consecutive) bars with close <= close 2 bars
               earlier; the 13th completes (flag buy13) and the countdown goes inactive. An opposite completed
               setup cancels the countdown. A new same-direction setup completion restarts the countdown at 0.
               Sell countdown mirror with close >= close 2 bars earlier.

Two points the definition leaves open are exposed as switches so the comparison with harness3 can isolate them:
  countdown_from_bar9 : True  -> the setup completion bar (bar 9) itself may be countdown bar 1 (DeMark's rule);
                        False -> counting starts on the bar after completion.
  setup_reset_after_9 : False -> the setup count keeps running 10, 11, ... until the condition fails (DeMark; a run of
                                 18 consecutive bars gives ONE completion);
                        True  -> the count restarts at 1 after bar 9 (a run of 18 gives two completions).

NaN closes: every comparison with NaN is False, so a NaN bar resets both setup counts and is not a countdown bar.
Pass a dropna()'d series to reproduce 'gaps skipped' behaviour.
"""
import numpy as np
import pandas as pd


def td_sequential_independent(close, countdown_from_bar9=True, setup_reset_after_9=False):
    s = pd.Series(close).astype(float)
    c = s.to_numpy()
    n = len(c)
    buy_cnt = np.zeros(n, dtype=int)
    sell_cnt = np.zeros(n, dtype=int)
    buy_cd = np.zeros(n, dtype=int)
    sell_cd = np.zeros(n, dtype=int)
    buy9 = np.zeros(n, dtype=bool)
    sell9 = np.zeros(n, dtype=bool)
    buy9p = np.zeros(n, dtype=bool)
    sell9p = np.zeros(n, dtype=bool)
    buy13 = np.zeros(n, dtype=bool)
    sell13 = np.zeros(n, dtype=bool)

    bc = sc = 0                     # setup counts
    bcd_on = scd_on = False         # countdown active?
    bcd = scd = 0                   # countdown counts
    for i in range(n):
        # ---- setup counting ---------------------------------------------------------------------------
        if i >= 4 and c[i] < c[i - 4]:
            bc += 1
            sc = 0
        elif i >= 4 and c[i] > c[i - 4]:
            sc += 1
            bc = 0
        else:                       # equal, NaN, or not enough history: both reset
            bc = 0
            sc = 0
        if setup_reset_after_9:
            if bc > 9:
                bc = 1
            if sc > 9:
                sc = 1
        buy_cnt[i] = bc
        sell_cnt[i] = sc
        buy_done = bc == 9
        sell_done = sc == 9

        # ---- setup completion, perfection, countdown (re)start / cancel ---------------------------------
        if buy_done:
            buy9[i] = True
            # bars 6,7,8,9 of the setup are i-3, i-2, i-1, i
            if min(c[i - 1], c[i]) <= min(c[i - 3], c[i - 2]):
                buy9p[i] = True
            scd_on, scd = False, 0  # opposite countdown cancelled
            bcd_on, bcd = True, 0   # same-direction countdown restarts at 0
        if sell_done:
            sell9[i] = True
            if max(c[i - 1], c[i]) >= max(c[i - 3], c[i - 2]):
                sell9p[i] = True
            bcd_on, bcd = False, 0
            scd_on, scd = True, 0

        # ---- countdown counting -----------------------------------------------------------------------
        if bcd_on and i >= 2 and (countdown_from_bar9 or not buy_done):
            if c[i] <= c[i - 2]:
                bcd += 1
                if bcd == 13:
                    buy13[i] = True
                    bcd_on = False
        if scd_on and i >= 2 and (countdown_from_bar9 or not sell_done):
            if c[i] >= c[i - 2]:
                scd += 1
                if scd == 13:
                    sell13[i] = True
                    scd_on = False
        buy_cd[i] = bcd if (bcd_on or buy13[i]) else 0
        sell_cd[i] = scd if (scd_on or sell13[i]) else 0

    out = pd.DataFrame(
        {
            "buy_count": buy_cnt,
            "sell_count": sell_cnt,
            "buy_cd": buy_cd,
            "sell_cd": sell_cd,
            "buy9": buy9,
            "sell9": sell9,
            "buy9p": buy9p,
            "sell9p": sell9p,
            "buy13": buy13,
            "sell13": sell13,
        },
        index=s.index,
    )
    return out


def vectorized_setup_check(close):
    """Independent cross-check of the setup completions only (no loop): a buy9 at bar i means the 9 bars
    i-8..i all have close < close[-4] and bar i-9 does not (or does not exist / is NaN)."""
    s = pd.Series(close).astype(float)
    down = (s < s.shift(4)).to_numpy()
    up = (s > s.shift(4)).to_numpy()
    n = len(s)

    def run9(cond):
        # run length of consecutive True ending at each bar
        run = np.zeros(n, dtype=int)
        r = 0
        for i in range(n):
            r = r + 1 if cond[i] else 0
            run[i] = r
        return run

    rd, ru = run9(down), run9(up)
    return pd.DataFrame({"buy9": rd == 9, "sell9": ru == 9, "buy_run": rd, "sell_run": ru}, index=s.index)


if __name__ == "__main__":
    import os

    here = os.path.dirname(os.path.abspath(__file__))
    research = os.path.abspath(os.path.join(here, "..", ".."))
    d = pd.read_pickle(os.path.join(research, "data", "daily2.pkl"))
    for a in ("btc", "eth"):
        td = td_sequential_independent(d[a])
        chk = vectorized_setup_check(d[a])
        assert (td["buy9"] == chk["buy9"]).all() and (td["sell9"] == chk["sell9"]).all()
        print(a, {k: int(td[k].sum()) for k in ("buy9", "sell9", "buy9p", "sell9p", "buy13", "sell13")},
              "max buy run", int(chk["buy_run"].max()), "max sell run", int(chk["sell_run"].max()))
        td.to_csv(os.path.join(here, f"td_independent_{a}_daily.csv"))
