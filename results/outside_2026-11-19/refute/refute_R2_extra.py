"""Extra refutations for R2 (ETH futures_oi duration): leave-one-episode-out, lag=2, equal-episode weighting, and the
mechanism check 'a USD-OI run ends when price drops' (how do long runs end?). Writes R2_refute_extra.{json,txt}."""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import harness as H  # noqa: E402
import harness2 as H2  # noqa: E402
from refute_R2_oi_duration import runs_for, spans, dur_table, keys_of, fmt_table  # noqa: E402

LINES = []


def say(*p):
    s = " ".join(str(x) for x in p)
    print(s, flush=True)
    LINES.append(s)


def late_stats(run_raw, px, pname, T=60, W=30, lag=1, drop_span=None):
    run = run_raw.shift(lag)
    mdd = H2.forward_mdd(px, W)
    r, m = (H2.slice_period(x, pname, "1d") for x in (run, mdd))
    ok = r.notna() & m.notna()
    r, m = r[ok], m[ok]
    f = r > T
    if drop_span is not None:
        s, e = drop_span
        keep = ~((m.index >= s) & (m.index <= e))
        f, m = f[keep], m[keep]
    if f.sum() < 3:
        return {"n": int(f.sum())}
    t, _ = H.nw_t(m.to_numpy(float), f.to_numpy(float), W)
    return {"n": int(f.sum()), "n_ind": H2.clusters(m[f].index, W, "1d"), "mdd_diff": float(m[f].mean() - m.mean()), "t": t,
            "crash_lift": float((m[f] <= -0.10).mean() / (m <= -0.10).mean())}


def main():
    d = pd.read_pickle(os.path.join(ROOT, "data", "daily2.pkl"))
    out = {}
    for a in ("eth", "btc"):
        px = H.price(d, a)
        oi = d[f"futures_oi_{a}"]
        for variant in ("consecutive", "hysteresis"):
            rr = runs_for(oi, variant)
            tag = f"{a}:{variant}"
            # ---- leave-one-episode-out on the validation >60 bucket
            run = rr.shift(1)
            mdd = H2.forward_mdd(px, 30)
            r, m = (H2.slice_period(x, "validation", "1d") for x in (run, mdd))
            ok = r.notna() & m.notna()
            flag = (r > 60) & ok
            sp = spans(flag)
            full = late_stats(rr, px, "validation")
            say(f"[LOO] {tag} validation >60: full mdd_diff {full['mdd_diff'] * 100:+.1f} (t {full['t']:.1f}) n={full['n']}/{full['n_ind']}")
            loo = {"full": full}
            per_ep = []
            for s, e, n in sp:
                st = late_stats(rr, px, "validation", drop_span=(s, e))
                ep_mean = float(m.loc[s:e].mean() - m[ok].mean())
                ep_crash = float((m.loc[s:e] <= -0.10).mean())
                per_ep.append({"span": f"{s.date()}..{e.date()}", "n": int(n), "ep_mdd_diff": ep_mean, "ep_crash_share": ep_crash})
                loo[f"drop {s.date()}..{e.date()}"] = st
                say(f"      drop {s.date()}..{e.date()} (n={n}, that span's own mdd_diff {ep_mean * 100:+.1f}, share mdd<=-10% {ep_crash:.2f}) -> "
                    + (f"mdd_diff {st['mdd_diff'] * 100:+.1f} (t {st['t']:.1f}) n={st['n']}/{st['n_ind']}" if "mdd_diff" in st else f"n={st['n']}"))
            eqw = float(np.mean([x["ep_mdd_diff"] for x in per_ep])) if per_ep else None
            say(f"      equal-episode-weighted mdd_diff of the >60 bucket (validation): {eqw * 100:+.1f} over {len(per_ep)} spans; "
                f"spans with mdd_diff<0: {sum(1 for x in per_ep if x['ep_mdd_diff'] < 0)}/{len(per_ep)}")
            loo["per_episode"] = per_ep
            loo["equal_weight_mdd_diff"] = eqw
            # train equal weight
            r_t, m_t = (H2.slice_period(x, "train", "1d") for x in (run, mdd))
            ok_t = r_t.notna() & m_t.notna()
            sp_t = spans((r_t > 60) & ok_t)
            per_t = [{"span": f"{s.date()}..{e.date()}", "n": int(n), "ep_mdd_diff": float(m_t.loc[s:e].mean() - m_t[ok_t].mean())} for s, e, n in sp_t]
            say(f"      train spans: " + "; ".join(f"{x['span']} (n={x['n']}) {x['ep_mdd_diff'] * 100:+.1f}" for x in per_t)
                + f" | equal-weight {np.mean([x['ep_mdd_diff'] for x in per_t]) * 100:+.1f}" if per_t else "      train: no spans")
            loo["train_per_episode"] = per_t
            out[f"{tag}:loo"] = loo
            # ---- lag 2
            l2 = {p: late_stats(rr, px, p, lag=2) for p in ("train", "validation")}
            say(f"[lag2] {tag} >60: " + " | ".join(f"{p[:3]} mdd_diff {v['mdd_diff'] * 100:+.1f} (t {v['t']:.1f}) n={v['n']}/{v['n_ind']}" if "mdd_diff" in v else f"{p[:3]} n={v['n']}" for p, v in l2.items()))
            out[f"{tag}:lag2"] = l2
            # ---- how do runs end? For every run >= 30 days: price change over the last 10 days of the run, and over
            # the 10 days after the end, and the OI pct level at the end.
            p365 = H.pct_rank(oi, 365, 180)
            ends = []
            v = rr.to_numpy()
            idx = rr.index
            i = 0
            while i < len(v):
                if v[i] >= 1 and (i == 0 or v[i - 1] == 0):
                    j = i
                    while j + 1 < len(v) and v[j + 1] >= 1:
                        j += 1
                    L = int(v[j])
                    if L >= 30 and j + 10 < len(v):
                        end = idx[j]
                        ret_last10 = float(px.iloc[j] / px.iloc[j - 10] - 1)
                        ret_next10 = float(px.iloc[j + 10] / px.iloc[j] - 1)
                        ret_next30 = float(px.iloc[min(j + 30, len(v) - 1)] / px.iloc[j] - 1)
                        oi_chg10 = float(oi.iloc[j + 1] / oi.iloc[j - 9] - 1) if not np.isnan(oi.iloc[j + 1]) else np.nan
                        coin_chg10 = float((oi.iloc[j + 1] / px.iloc[j + 1]) / (oi.iloc[j - 9] / px.iloc[j - 9]) - 1) if not np.isnan(oi.iloc[j + 1]) else np.nan
                        pname = next((p for p in H.PERIODS if len(H2.slice_period(pd.Series([1], index=[end]), p, "1d"))), None)
                        ends.append({"run": f"{idx[i].date()}..{end.date()}", "len": L, "period": pname,
                                     "px_ret_last10": ret_last10, "px_ret_next10": ret_next10, "px_ret_next30": ret_next30,
                                     "usd_oi_chg_last10_to_exit": oi_chg10, "coin_oi_chg_last10_to_exit": coin_chg10,
                                     "pct_at_exit": float(p365.iloc[j + 1]) if not np.isnan(p365.iloc[j + 1]) else None})
                    i = j + 1
                else:
                    i += 1
            say(f"[run-ends] {tag}: runs >= 30d: {len(ends)}; price return over the last 10 days of the run (to the exit day):")
            for e in ends:
                say(f"      {e['run']} ({e['len']}d, {e['period']}): px last10 {e['px_ret_last10'] * 100:+.1f}%, next10 {e['px_ret_next10'] * 100:+.1f}%, next30 {e['px_ret_next30'] * 100:+.1f}% | "
                    f"USD OI chg {e['usd_oi_chg_last10_to_exit'] * 100:+.1f}%, coin OI chg {e['coin_oi_chg_last10_to_exit'] * 100:+.1f}%")
            if ends:
                neg = sum(1 for e in ends if e["px_ret_last10"] < -0.05)
                say(f"      runs ending with a >5% price fall over the preceding 10 days: {neg}/{len(ends)}; mean last-10 return {np.mean([e['px_ret_last10'] for e in ends]) * 100:+.1f}%; "
                    f"mean next-30 return {np.mean([e['px_ret_next30'] for e in ends]) * 100:+.1f}%")
            out[f"{tag}:run_ends"] = ends
        # ---- co-movement of USD-OI percentile and price
        p365 = H.pct_rank(oi, 365, 180)
        dp = p365.diff()
        rpx = px.pct_change()
        both = dp.notna() & rpx.notna()
        c = float(np.corrcoef(dp[both], rpx[both])[0, 1])
        big_down = rpx <= -0.05
        say(f"[co-move] {a}: corr(daily change in OI pct365, daily price return) = {c:.2f}; mean OI-pct change on days with price <= -5%: {dp[big_down & both].mean():+.3f} (n={int((big_down & both).sum())}) vs all days {dp[both].mean():+.4f}")
        out[f"{a}:comove"] = {"corr": c, "mean_dpct_on_big_down": float(dp[big_down & both].mean()), "n_big_down": int((big_down & both).sum())}

    with open(os.path.join(HERE, "R2_refute_extra.json"), "w") as fh:
        json.dump(out, fh, indent=1, default=str)
    with open(os.path.join(HERE, "R2_refute_extra.txt"), "w") as fh:
        fh.write("\n".join(LINES))


if __name__ == "__main__":
    main()
