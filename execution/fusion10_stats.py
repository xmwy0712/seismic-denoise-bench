"""P5.4 · WS1③：10 配对融合的**探索性**统计。

* 逐配对 vs {成员 i, 成员 j, 最优固定单法, 逐观测 oracle}：中位差 + 自助 95% CI + 配对符号翻转置换 p
* 度量（M1 / M1_signed / M2 / M3 全局值）与融合增益的 **Spearman 秩相关（n = 10）**

**定位**：本脚本属**事后扩展分析**（见 execution-log 的定位声明），
全部结果标注 `exploratory`，**不得进入主结论**（冻结件 `authorized_exploratory.must_not_enter_main_conclusion`）。
三个 gamma 档位**全部报告**（不选择性呈现）。
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
METHODS = ("fk_filter", "fx_deconv", "wavelet_threshold", "ssa_decomposition", "svd_lowrank")
GAMMAS = (0.4, 0.5, 0.6)
B_PERM, B_BOOT = 10000, 10000
SEED_PERM, SEED_BOOT = 20261015, 20261016


def _read(rel, keymap=None):
    with (REPO / rel).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def signflip_p(diff: np.ndarray, rng, stat=np.median) -> float:
    """配对符号翻转置换检验（two-sided），与 P3.2 同族。"""
    n = diff.size
    obs = abs(stat(diff))
    s = rng.choice(np.array([-1.0, 1.0]), size=(B_PERM, n))
    perm = np.abs(np.median(s * diff[None, :], axis=1))
    return float((np.count_nonzero(perm >= obs) + 1) / (B_PERM + 1))


def boot_ci(x: np.ndarray, rng, stat=np.median) -> tuple[float, float]:
    n = x.size
    idx = rng.integers(0, n, size=(B_BOOT, n))
    s = stat(x[idx], axis=1)
    return float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5))


def spearman(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """Spearman rho 与两侧 p（t 近似；n=10 属小样本，标注探索性）。"""
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean(); rb -= rb.mean()
    rho = float(np.sum(ra * rb) / np.sqrt(np.sum(ra ** 2) * np.sum(rb ** 2)))
    n = a.size
    if abs(rho) >= 1.0:
        return rho, 0.0
    t = rho * np.sqrt((n - 2) / max(1e-300, 1 - rho ** 2))
    # 双侧 p（学生 t，df = n-2），用不完全 beta 的级数近似
    from math import lgamma, log, exp
    df = n - 2

    def betacf(a, b, x):
        MAXIT, EPS, FPMIN = 200, 3e-16, 1e-300
        qab, qap, qam = a + b, a + 1.0, a - 1.0
        c, d = 1.0, 1.0 - qab * x / qap
        if abs(d) < FPMIN:
            d = FPMIN
        d = 1.0 / d
        h = d
        for mm in range(1, MAXIT + 1):
            m2 = 2 * mm
            aa = mm * (b - mm) * x / ((qam + m2) * (a + m2))
            d = 1.0 + aa * d
            if abs(d) < FPMIN:
                d = FPMIN
            c = 1.0 + aa / c
            if abs(c) < FPMIN:
                c = FPMIN
            d = 1.0 / d
            h *= d * c
            aa = -(a + mm) * (qab + mm) * x / ((a + m2) * (qap + m2))
            d = 1.0 + aa * d
            if abs(d) < FPMIN:
                d = FPMIN
            c = 1.0 + aa / c
            if abs(c) < FPMIN:
                c = FPMIN
            d = 1.0 / d
            de = d * c
            h *= de
            if abs(de - 1.0) < EPS:
                break
        return h

    def betai(a, b, x):
        if x <= 0:
            return 0.0
        if x >= 1:
            return 1.0
        bt = exp(lgamma(a + b) - lgamma(a) - lgamma(b) + a * log(x) + b * log(1 - x))
        if x < (a + 1) / (a + b + 2):
            return bt * betacf(a, b, x) / a
        return 1.0 - bt * betacf(b, a, 1 - x) / b

    p = betai(df / 2.0, 0.5, df / (df + t * t))
    return rho, float(min(max(p, 0.0), 1.0))


def run(out_dir: Path) -> dict:
    single = defaultdict(dict)
    for r in _read("results/metrics.csv"):
        single[r["method"]][(r["config_id"], r["seed"])] = float(r["delta_snr_db"])
    obs = sorted(next(iter(single.values())).keys())
    mvals = {m: np.array([single[m][o] for o in obs]) for m in METHODS}
    best_fixed_name = max(METHODS, key=lambda m: float(np.median(mvals[m])))
    best_fixed = mvals[best_fixed_name]
    oracle = np.array([max(single[m][o] for m in METHODS) for o in obs])

    fus = defaultdict(dict)
    for r in _read("results/fusion10/metrics.csv"):
        if r["kind"] != "fusion":
            continue
        fus[(r["pair_i"], r["pair_j"], float(r["gamma"]))][(r["config_id"], r["seed"])] = float(r["delta_snr_db"])

    rng_p, rng_b = np.random.default_rng(SEED_PERM), np.random.default_rng(SEED_BOOT)
    rows = []
    for (mi, mj, g), d in sorted(fus.items()):
        y = np.array([d[o] for o in obs])
        comps = {"vs_member_i": mvals[mi], "vs_member_j": mvals[mj],
                 f"vs_best_fixed({best_fixed_name})": best_fixed, "vs_oracle": oracle}
        for name, c in comps.items():
            diff = y - c
            lo, hi = boot_ci(diff, rng_b)
            rows.append({"exploratory": True, "pair_i": mi, "pair_j": mj, "gamma": g,
                         "comparator": name, "n": len(obs),
                         "median_diff_db": float(np.median(diff)),
                         "ci_lo": lo, "ci_hi": hi, "p_signflip": signflip_p(diff, rng_p)})

    # Spearman：度量全局值 vs 融合增益（n = 10，gamma = 0.5）
    comp10 = {}
    for r in _read("results/complementarity10/complementarity10.csv"):
        if r["stratum_key"] == "global":
            comp10[(r["pair"], r["metric"])] = (None if r["value"] == ""
                                                else float(r["value"]))
    pairs10 = [f"{a}|{b}" for i, a in enumerate(METHODS) for b in METHODS[i + 1:]]
    gain = {}
    for p in pairs10:
        a, b = p.split("|")
        xs = [fus[(a, b, 0.5)][o] for o in obs]
        gain[p] = float(np.median(xs))
    sp = []
    for metric in ("M1", "M1_signed", "M2", "M3"):
        mv = np.array([comp10[(p, metric)] for p in pairs10], dtype=float)
        gv = np.array([gain[p] for p in pairs10], dtype=float)
        rho, pv = spearman(mv, gv)
        sp.append({"exploratory": True, "metric": metric, "n": 10,
                   "spearman_rho": rho, "p_two_sided": pv,
                   "gain": "median delta_snr_db @ gamma=0.5"})

    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "pairwise.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader(); w.writerows(rows)
    with (out_dir / "spearman.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(sp[0].keys()), lineterminator="\n")
        w.writeheader(); w.writerows(sp)
    summary = {"exploratory": True, "rows_pairwise": len(rows), "rows_spearman": len(sp),
               "best_fixed_single_method": best_fixed_name,
               "perm_B": B_PERM, "boot_B": B_BOOT, "seeds": [SEED_PERM, SEED_BOOT],
               "gammas": list(GAMMAS), "oracle_is_upper_bound": True,
               "note": "post-hoc 扩展分析；不得进入主结论（冻结件 authorized_exploratory）"}
    with (out_dir / "summary.json").open("w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps({"summary": summary, "spearman": sp}, ensure_ascii=False, indent=2))
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="P5.4 WS1③ · 10 配对探索性统计")
    ap.add_argument("--out", default="results/fusion10/stats")
    a = ap.parse_args(argv)
    print(json.dumps(run(REPO / a.out), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
