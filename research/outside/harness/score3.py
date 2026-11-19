"""Pass 3 scoring: PREREG3.md families R1-R5. Writes results3/*.json and results3/REPORT.txt.

Usage: python score3.py [R1 R2 R3 R4 R5 ...]   (default: all)
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import harness as H  # noqa: E402
import harness2 as H2  # noqa: E402
import harness3 as H3  # noqa: E402

OUT = os.path.join(HERE, "results3")
os.makedirs(OUT, exist_ok=True)
REPORT = []
PASSES = []


def say(*parts):
    line = " ".join(str(p) for p in parts)
    print(line, flush=True)
    REPORT.append(line)


def save(name, obj):
    with open(os.path.join(OUT, name + ".json"), "w") as fh:
        json.dump(obj, fh, indent=1, default=str)


def note_passes(tag, res, kind):
    key = "horizons" if kind == "ret" else "windows"
    for k, e in res[key].items():
        if str(e["verdict"]).startswith("PASS"):
            PASSES.append(f"{tag} {kind} {k}: {e['verdict']}")


def ret(df, spec, asset, horizons, freq="1d", cond=None, episode_bar=30, tag=""):
    r = H2.event_test2(df, spec, asset, horizons=horizons, freq=freq, cond=cond, episode_bar=episode_bar)
    say(f"[{tag}] {asset} {spec}" + (f" AND {cond}" if cond else "") + f" ({freq})")
    say(H2.line2(r))
    note_passes(f"{tag} {asset} {spec}" + (f" AND {cond}" if cond else ""), r, "ret")
    return r


def risk(df, spec, asset, windows, freq="1d", cond=None, crash=-0.10, episode_bar=20, tag=""):
    r = H2.risk_test(df, spec, asset, windows=windows, freq=freq, cond=cond, crash=crash, episode_bar=episode_bar)
    say(f"[{tag}] RISK {asset} {spec}" + (f" AND {cond}" if cond else "") + f" ({freq}, crash {crash:+.0%})")
    say(H2.risk_line(r))
    for W, e in r["windows"].items():
        va = e["cell"].get("validation", {})
        if va.get("rv_flag") is not None:
            say(f"   W={W} fwd rv flag/all: " + " | ".join(
                f"{p[:3]} {e['cell'][p]['rv_flag']:.2f}/{e['cell'][p]['rv_all']:.2f}" for p in ("train", "validation", "test")
                if e["cell"].get(p, {}).get("rv_flag") is not None))
    note_passes(f"{tag} RISK {asset} {spec}" + (f" AND {cond}" if cond else ""), r, "risk")
    return r


# ---------------------------------------------------------------- data
def load_daily():
    d = pd.read_pickle(os.path.join(HERE, "data", "daily2.pkl"))
    for a in ("btc", "eth"):
        H3.td_columns(d, a)  # closes only: "perfected" uses closes of bars 6-9, see REPORT
        for s in (f"perp_funding_{a}", f"futures_oi_{a}", f"basis_{a}"):
            H3.state_columns(d, s, a)
            # post-hoc reported variant: hysteresis state on at pct>=0.8, off below 0.6
            p = H.pct_rank(d[s], 365, 180)
            on = np.zeros(len(p))
            state = False
            for i, v in enumerate(p.to_numpy()):
                if np.isnan(v):
                    state = False
                elif v >= 0.8:
                    state = True
                elif v < 0.6:
                    state = False
                on[i] = state
            onf = pd.Series(on.astype(bool), index=p.index)
            d[f"{s}_hyst_run"] = H3.days_in_state(onf)
            d[f"{s}_hyst_exit20"] = H3.exit_after(onf, 20)
            d[f"{s}_hyst_exit10"] = H3.exit_after(onf, 10)
    return d


def load_hourly():
    h = pd.read_pickle(os.path.join(HERE, "data", "hourly.pkl"))
    h4 = h.resample("4h").last()
    for a in ("btc", "eth"):
        for frame in (h, h4):
            px = frame[a].dropna()
            td = H3.td_sequential(px)  # gaps skipped: counts run over the available bars in sequence
            for k in td.columns:
                frame[f"td_{k}_{a}"] = td[k].reindex(frame.index).fillna(0.0)
    return h, h4


def three_day_frames(d):
    frames = []
    for anchor in (0, 1, 2):
        d3 = d.iloc[anchor::3].copy()
        for a in ("btc", "eth"):
            H3.td_columns(d3, a)
        frames.append((anchor, d3))
    return frames


# ---------------------------------------------------------------- families
R1_PRIM = {"perp_funding": "perp_funding_{a}", "futures_oi": "futures_oi_{a}", "perp_oi": "perp_oi_{a}",
           "basis": "basis_{a}", "lsr": "lsr_{A}"}


def R1(d):
    say("\n==== R1. Overheating as risk-on / continuation, 30-90 days ====")
    out = {}
    for a in ("btc", "eth"):
        for name, col in R1_PRIM.items():
            col = col.format(a=a, A=a.upper())
            if col not in d:
                say(f"[R1] {a} {col} missing")
                continue
            for thr in (0.8, 0.9):
                spec = (col, "pct365", "top", thr)
                out[f"{a}:{name}:{thr}:ret"] = ret(d, spec, a, (30, 60, 90), episode_bar=15, tag="R1")
                r30 = risk(d, spec, a, (30,), crash=-0.10, tag="R1")
                r69 = risk(d, spec, a, (60, 90), crash=-0.20, tag="R1")
                out[f"{a}:{name}:{thr}:risk"] = {"W30": r30, "W60_90": r69}
        spec = (f"perp_funding_{a}", "pct365", "top", 0.8)
        cond = (f"futures_oi_{a}", "pct365", "top", 0.8)
        out[f"{a}:pair:ret"] = ret(d, spec, a, (30, 60, 90), cond=cond, episode_bar=15, tag="R1")
        out[f"{a}:pair:risk"] = {"W30": risk(d, spec, a, (30,), cond=cond, crash=-0.10, tag="R1"),
                                 "W60_90": risk(d, spec, a, (60, 90), cond=cond, crash=-0.20, tag="R1")}
    save("R1_overheating_long_horizon", out)


def duration_table(d, series, a, run_col, buckets=((1, 10), (11, 30), (31, 60), (61, 100000)), W=30):
    px = H.price(d, a)
    run = d[run_col].shift(1)  # lag 1: the run length known at yesterday's close
    run = run.where(H.pct_rank(d[series], 365, 180).shift(1).notna())  # baseline only where the state is defined
    fwd = px.shift(-W) / px - 1
    mdd = H2.forward_mdd(px, W)
    table = {}
    for pname in H.PERIODS:
        r, y, m = (H2.slice_period(x, pname, "1d") for x in (run, fwd, mdd))
        ok = y.notna() & m.notna() & r.notna()
        r, y, m = r[ok], y[ok], m[ok]
        base_crash = float((m <= -0.10).mean()) if len(m) else None
        rows = {}
        for lo, hi in buckets:
            f = (r >= lo) & (r <= hi)
            n = int(f.sum())
            if n < 3:
                rows[f"{lo}-{hi if hi < 100000 else 'inf'}"] = {"n": n}
                continue
            t_ret, _ = H.nw_t(y.to_numpy(float), f.to_numpy(float), W)
            t_mdd, _ = H.nw_t(m.to_numpy(float), f.to_numpy(float), W)
            rows[f"{lo}-{hi if hi < 100000 else 'inf'}"] = {
                "n": n, "n_ind": H2.clusters(y[f].index, W, "1d"),
                "excess30": float(y[f].mean() - y.mean()), "t_ret": t_ret,
                "mdd_diff": float(m[f].mean() - m.mean()), "t_mdd": t_mdd,
                "crash_rate": float((m[f] <= -0.10).mean()), "crash_base": base_crash,
                "crash_lift": float((m[f] <= -0.10).mean() / base_crash) if base_crash else None,
            }
        table[pname] = rows
    # verdict: validation monotone (mdd_diff falling with duration) and >60 bucket worse than 1-10 in train and validation
    def mdd_of(p, key):
        return table.get(p, {}).get(key, {}).get("mdd_diff")
    keys = [f"{lo}-{hi if hi < 100000 else 'inf'}" for lo, hi in buckets]
    va = [mdd_of("validation", k) for k in keys]
    tr = [mdd_of("train", k) for k in keys]
    if any(v is None for v in va) or any(v is None for v in tr):
        verdict = "insufficient: a bucket has fewer than 3 days in train or validation"
    else:
        mono = all(va[i] >= va[i + 1] for i in range(len(va) - 1))
        worse = va[-1] < va[0] and tr[-1] < tr[0]
        n_last = (table["train"][keys[-1]].get("n_ind") or 0) + (table["validation"][keys[-1]].get("n_ind") or 0)
        if n_last < 10:
            verdict = f"insufficient: only {n_last} independent episodes in the longest-duration bucket"
        elif mono and worse:
            verdict = "PASS duration: drawdown worsens monotonically with time in state (validation) and late > early in train and validation"
        elif worse:
            verdict = "partial: late state worse than early in train and validation, but not monotone in validation"
        else:
            verdict = "rejected: no duration effect (late in state is not worse than early)"
    return {"series": series, "asset": a, "W": W, "table": table, "verdict": verdict}


def R2(d):
    say("\n==== R2. Duration of the crowded state (30-day forward return and drawdown by days-in-state) ====")
    out = {}
    for a in ("btc", "eth"):
        for s in (f"perp_funding_{a}", f"futures_oi_{a}", f"basis_{a}"):
            for variant, run_col in (("consecutive", f"{s}_hi_run"), ("hysteresis(post-hoc)", f"{s}_hyst_run")):
                res = duration_table(d, s, a, run_col)
                out[f"{a}:{s}:{variant}"] = res
                say(f"[R2] {a} {s} [{variant}] -> {res['verdict']}")
                for p in ("train", "validation", "test"):
                    cells = []
                    for k, r in res["table"].get(p, {}).items():
                        if "mdd_diff" in r:
                            cells.append(f"{k}: n={r['n']}/{r['n_ind']} ex30 {r['excess30'] * 100:+.1f}% mdd {r['mdd_diff'] * 100:+.1f}% (t {r['t_mdd']:.1f}) crash x{(r['crash_lift'] or 0):.2f}")
                        else:
                            cells.append(f"{k}: n={r['n']}")
                    say(f"   {p[:3]}: " + " | ".join(cells))
                if variant.startswith("PASS"):
                    PASSES.append(f"R2 {a} {s} {variant}: {res['verdict']}")
                elif res["verdict"].startswith("PASS"):
                    PASSES.append(f"R2 {a} {s} {variant}: {res['verdict']}")
    save("R2_duration", out)


def R3(d):
    say("\n==== R3. Exit from a crowded state ====")
    out = {}
    for a in ("btc", "eth"):
        for s in (f"perp_funding_{a}", f"futures_oi_{a}", f"basis_{a}"):
            for col, hyp in ((f"{s}_hi_exit20", "down"), (f"{s}_hi_exit40", "down"), (f"{s}_lo_exit20", "up"), (f"{s}_lo_exit40", "up"),
                             (f"{s}_hyst_exit20", "down (post-hoc variant)"), (f"{s}_hyst_exit10", "down (post-hoc variant)")):
                n = int(d[col].sum())
                say(f"[R3] {a} {col}: {n} events total, hypothesis {hyp}")
                if n < 6:
                    continue
                spec = (col, "raw", "top", 1)
                out[f"{a}:{col}:ret"] = ret(d, spec, a, (10, 20, 30), episode_bar=15, tag="R3")
                out[f"{a}:{col}:risk"] = risk(d, spec, a, (10, 20, 30), crash=-0.10, episode_bar=15, tag="R3")
    save("R3_exit", out)


TD_FLAGS = (("buy9", +1), ("sell9", -1), ("buy9p", +1), ("sell9p", -1), ("buy13", +1), ("sell13", -1))


def td_family(frames, freq, horizons, windows, label, episode_bar_ret=30, episode_bar_risk=20):
    out = {}
    sign_table = []
    for fname, frame in frames:
        for a in ("btc", "eth"):
            for flag, hyp in TD_FLAGS:
                col = f"td_{flag}_{a}"
                n = int(frame[col].sum())
                spec = (col, "raw", "top", 1)
                say(f"[R4 {label}{fname}] {a} {flag}: {n} completions, hypothesis {'+' if hyp > 0 else '-'}")
                if n < 6:
                    continue
                r = ret(frame, spec, a, horizons, freq=freq, episode_bar=episode_bar_ret, tag=f"R4 {label}{fname}")
                k = risk(frame, spec, a, windows, freq=freq, crash=-0.10, episode_bar=episode_bar_risk, tag=f"R4 {label}{fname}")
                out[f"{fname}:{a}:{flag}"] = {"ret": r, "risk": k}
                for hz, e in r["horizons"].items():
                    for p in ("train", "validation", "test"):
                        ex = e["cell"].get(p, {}).get("excess")
                        if ex is not None:
                            sign_table.append({"frame": str(fname), "asset": a, "flag": flag, "h": hz, "period": p,
                                               "excess": ex, "t": e["cell"][p]["t_nw"], "n_ind": e["cell"][p]["n_ind"],
                                               "consistent": bool(np.sign(ex) == hyp)})
    st = pd.DataFrame(sign_table)
    if len(st):
        agg = st.groupby(["flag", "period"]).agg(cells=("consistent", "size"), consistent=("consistent", "sum"),
                                                 mean_t_signed=("t", lambda x: float(np.mean(x))))
        say(f"[R4 {label}] share of cell-horizons whose excess sign matches the DeMark hypothesis:")
        say(agg.to_string())
        pooled = st.assign(signed_t=lambda x: x["t"] * x["flag"].map(dict(TD_FLAGS)))
        say(f"[R4 {label}] mean hypothesis-signed t by period: " + ", ".join(
            f"{p} {pooled[pooled.period == p]['signed_t'].mean():+.2f} (n={int((pooled.period == p).sum())})" for p in ("train", "validation", "test")))
    out["_sign_table"] = sign_table
    return out


def setup_count_table(d):
    say("[R4 info] daily forward 10-day excess return by TD setup count (train+validation pooled, lag 1)")
    rows = {}
    for a in ("btc", "eth"):
        px = H.price(d, a)
        fwd = px.shift(-10) / px - 1
        setup = d[f"td_setup_{a}"].shift(1)
        m = (d.index <= "2025-12-31")
        fwd_m, setup_m = fwd[m], setup[m]
        base = fwd_m.mean()
        parts = []
        for k in list(range(-9, 0)) + list(range(1, 10)):
            f = setup_m == k
            if f.sum() >= 10:
                parts.append(f"{k:+d}:{(fwd_m[f].mean() - base) * 100:+.1f}%({int(f.sum())})")
                rows[f"{a}:{k}"] = {"n": int(f.sum()), "excess10": float(fwd_m[f].mean() - base)}
        say(f"   {a}: " + " ".join(parts))
    return rows


def R4(d, h, h4):
    say("\n==== R4. TD Sequential ====")
    say("note: daily/3D 'perfected' uses closes (no highs/lows in the panel): close of bar 8 or 9 at/below closes of bars 6 and 7")
    out = {}
    out["1d"] = td_family([("", d)], "1d", (1, 3, 5, 10, 20), (10, 20, 30), "1D")
    out["3d"] = td_family([(f"a{k}", f) for k, f in three_day_frames(d)], "3d", (1, 3, 5, 10, 20), (15, 30), "3D-")
    out["4h"] = td_family([("", h4)], "4h", (4, 12, 24, 72), (4, 12), "4H", episode_bar_ret=30, episode_bar_risk=20)
    out["1h"] = td_family([("", h)], "1h", (4, 12, 24, 72), (1, 3), "1H", episode_bar_ret=30, episode_bar_risk=20)
    out["setup_counts"] = setup_count_table(d)
    save("R4_td_sequential", out)


def R5(d):
    say("\n==== R5. Long horizons for the near misses ====")
    out = {}
    for a in ("btc", "eth"):
        for thr in (0.1, 0.2):
            out[f"{a}:funding_bottom:{thr}"] = ret(d, (f"perp_funding_{a}", "pct365", "bottom", thr), a, (30, 60, 90), episode_bar=15, tag="R5")
        for thr in (0.1, 0.2):
            out[f"{a}:ivrv_bottom:{thr}"] = ret(d, (f"ivrv30_{a}", "pct365", "bottom", thr), a, (30, 60), episode_bar=15, tag="R5")
        for thr in (0.8, 0.9):
            out[f"{a}:skew30_top:{thr}:ret"] = ret(d, (f"skew_30_{a}", "pct365", "top", thr), a, (30, 60, 90), episode_bar=15, tag="R5")
            out[f"{a}:skew30_top:{thr}:risk"] = risk(d, (f"skew_30_{a}", "pct365", "top", thr), a, (30, 60), crash=-0.10, tag="R5")
    say("(lsr top at 30/60/90 is scored in R1)")
    save("R5_long_horizon_near_misses", out)


if __name__ == "__main__":
    want = sys.argv[1:] or ["R1", "R2", "R3", "R4", "R5"]
    d = load_daily()
    say(f"daily panel {d.index[0].date()}..{d.index[-1].date()} rows {len(d)}")
    if "R1" in want:
        R1(d)
    if "R2" in want:
        R2(d)
    if "R3" in want:
        R3(d)
    if "R4" in want:
        h, h4 = load_hourly()
        say(f"hourly {h.index[0]}..{h.index[-1]} rows {len(h)}; 4h rows {len(h4)}")
        R4(d, h, h4)
    if "R5" in want:
        R5(d)
    say("\n==== PASSES (any verdict starting with PASS) ====")
    for p in PASSES:
        say(p)
    if not PASSES:
        say("none")
    with open(os.path.join(OUT, "REPORT_" + "_".join(want) + ".txt"), "w") as fh:
        fh.write("\n".join(REPORT))
