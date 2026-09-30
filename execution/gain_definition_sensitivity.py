"""P5.4 · WS1 追补：增益定义的**敏感性对照**（并列平均秩校正后的 Spearman）。

用途：WS1 报出的 M2 ρ = −0.5758 与签发方复算 −0.078 不一致，根因是**增益定义不同**。
本脚本在同一批数据上并列 5 种增益定义，并使用**并列平均秩**（scipy 口径）重算 Spearman，
产出 `results/fusion10/stats/gain_definition_sensitivity.csv`，供 draft-v5 并列写明。
"""

from __future__ import annotations

import csv
import io
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
METHODS = ("fk_filter", "fx_deconv", "wavelet_threshold", "ssa_decomposition", "svd_lowrank")


def avg_rank(x: np.ndarray) -> np.ndarray:
    """并列平均秩（与 scipy.stats.rankdata 默认口径一致）。"""
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(x.size, dtype=float)
    sorted_x = x[order]
    i = 0
    while i < x.size:
        j = i
        while j + 1 < x.size and sorted_x[j + 1] == sorted_x[i]:
            j += 1
        ranks[order[i:j + 1]] = 0.5 * (i + j) + 1.0
        i = j + 1
    return ranks


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    ra, rb = avg_rank(a), avg_rank(b)
    ra = ra - ra.mean()
    rb = rb - rb.mean()
    den = np.sqrt(np.sum(ra ** 2) * np.sum(rb ** 2))
    return float(np.sum(ra * rb) / den) if den > 0 else float("nan")


def main() -> int:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    single = defaultdict(dict)
    with (REPO / "results/metrics.csv").open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            single[r["method"]][(r["config_id"], r["seed"])] = float(r["delta_snr_db"])
    obs = sorted(next(iter(single.values())).keys())
    mv = {m: np.array([single[m][o] for o in obs]) for m in METHODS}
    best_fixed_name = max(METHODS, key=lambda m: float(np.median(mv[m])))
    bf = mv[best_fixed_name]
    oracle = np.array([max(single[m][o] for m in METHODS) for o in obs])

    fus = defaultdict(dict)
    with (REPO / "results/fusion10/metrics.csv").open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["kind"] == "fusion" and r["gamma"] == "0.5":
                fus[(r["pair_i"], r["pair_j"])][(r["config_id"], r["seed"])] = float(r["delta_snr_db"])

    comp = {}
    with (REPO / "results/complementarity10/complementarity10.csv").open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["stratum_key"] == "global":
                comp[(r["pair"], r["metric"])] = None if r["value"] == "" else float(r["value"])

    pairs = [f"{a}|{b}" for i, a in enumerate(METHODS) for b in METHODS[i + 1:]]
    gains = {p: {} for p in pairs}
    for p in pairs:
        a, b = p.split("|")
        y = np.array([fus[(a, b)][o] for o in obs])
        itsmax = np.maximum(mv[a], mv[b])
        gains[p] = {
            "A_median_own_dsnr": float(np.median(y)),
            "B_median_vs_best_fixed": float(np.median(y - bf)),
            "C_median_vs_better_member": float(np.median(y - itsmax)),
            "D_median_vs_oracle": float(np.median(y - oracle)),
            "E_mean_own_dsnr": float(np.mean(y)),
        }

    rows = []
    for name in ("A_median_own_dsnr", "B_median_vs_best_fixed", "C_median_vs_better_member",
                 "D_median_vs_oracle", "E_mean_own_dsnr"):
        gv = np.array([gains[p][name] for p in pairs])
        for met in ("M1", "M1_signed", "M2", "M3"):
            mvv = np.array([comp[(p, met)] for p in pairs], dtype=float)
            rows.append({"gain_definition": name, "metric": met, "n": 10,
                         "spearman_rho": round(spearman(mvv, gv), 6),
                         "gain_values": ";".join(f"{v:.6f}" for v in gv)})

    out = REPO / "results/fusion10/stats/gain_definition_sensitivity.csv"
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"  写出 {out.name}  {len(rows)} 行")
    print(f"  最优固定单法 = {best_fixed_name}")
    print()
    print(f"  {'增益定义':32} {'M1':>8} {'M1_signed':>10} {'M2':>8} {'M3':>8}")
    for name in ("A_median_own_dsnr", "B_median_vs_best_fixed", "C_median_vs_better_member",
                 "D_median_vs_oracle", "E_mean_own_dsnr"):
        r = {x["metric"]: x["spearman_rho"] for x in rows if x["gain_definition"] == name}
        print(f"  {name:32} {r['M1']:+8.4f} {r['M1_signed']:+10.4f} {r['M2']:+8.4f} {r['M3']:+8.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
