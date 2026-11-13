import json

import pandas as pd

from regime_tester.indicators import META

frames = [pd.read_csv(f"results/sweeps/{name}")
          for name in ("2026-11-12_xs_vec.csv", "2026-11-13_xs_vec.csv")]
scored = pd.concat(frames, ignore_index=True).drop_duplicates("id")
scored["family"] = scored["measure"].map(lambda m: META.get(m, ("unknown",))[0])
usable = scored[(scored.below_minimum == False) & (scored.degenerate == False)]
print("usable", len(usable), "of", len(scored))
board = []
for family, group in usable.groupby("family"):
    order = group["t_newey_west"].abs().sort_values(ascending=False).index
    for _, row in group.reindex(order).head(5).iterrows():
        board.append({
            "family": family, "id": row["id"],
            "train_score": round(float(row["t_newey_west"]), 3),
            "n": int(row["n_independent"]), "status": "unconfirmed",
        })
json.dump({"as_of": "2026-11-13", "scored": int(len(scored)), "rows": board},
          open("results/sweeps/leaderboard_xs.json", "w"), indent=1)
for row in board:
    print(f"{row['family']:14} {row['train_score']:>8} n={row['n']:<5} {row['id']}")
