"""P3.2 阶段 2 · 融合统计（配对符号翻转置换 + Holm + 分层自助 CI）。

**参数全部取自** `results/fusion/stats_preregistration.md`（**先落盘、后统计**）。
**只读**输入；不写 `frozen*` / `results/metrics.csv` / 任何既有 y_hat。

用法::

    python execution/fusion_stats.py --out results/fusion/stats
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import itertools
import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
FUS = REPO / "results" / "fusion"
PRE = FUS / "stats_preregistration.md"

# ── 预注册参数（不得在此处另行改动）
B_PERM = 10_000
B_BOOT = 10_000
ALPHA = 0.05
SEED_PERM = 20261010
SEED_BOOT = 20261011
COMPARATORS = ("vs_method_i", "vs_method_j", "vs_best_single")
METRICS = [
    ("delta_snr_db", "ΔSNR", "higher"),
    ("lsig", "Lsig", "lower"),
    ("cna_db", "CNA", "higher"),
    ("event_timing_median_ms", "event_timing_median", "lower"),
    ("event_energy_median", "event_energy_median", "lower"),
]
STRATA = ("global", "model", "noise", "gamma")
GAMMAS = ("0.4", "0.5", "0.6")
METHODS5 = ("fk_filter", "fx_deconv", "wavelet_threshold", "ssa_decomposition", "svd_lowrank")


def val(row: dict, col: str):
    v = row.get(col, "")
    if v in ("", "None", "NA", None):
        return None
    try:
        f = float(v)
    except ValueError:
        return None
    return f if np.isfinite(f) else None


def holm(ps: list[float]) -> list[float]:
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    adj = [1.0] * m
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, (m - rank) * ps[i])
        adj[i] = min(1.0, run)
    return adj


def perm(d: np.ndarray, rng) -> float:
    n = d.size
    if n == 0:
        return float("nan")
    obs = float(np.mean(d))
    sg = rng.integers(0, 2, size=(B_PERM, n), dtype=np.int8).astype(np.float64) * 2 - 1
    pm = (sg @ d) / n
    return float((np.count_nonzero(np.abs(pm) >= abs(obs) - 1e-12) + 1) / (B_PERM + 1))


def bci(d: np.ndarray, rng) -> tuple[float, float]:
    n = d.size
    if n == 0:
        return (float("nan"), float("nan"))
    idx = rng.integers(0, n, size=(B_BOOT, n))
    b = np.median(d[idx], axis=1)
    return (float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5)))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="P3.2 融合统计（读 stats_preregistration.md 定死的参数）")
    ap.add_argument("--out", default="results/fusion/stats")
    a = ap.parse_args(argv)
    out = REPO / a.out
    out.mkdir(parents=True, exist_ok=True)

    if not PRE.exists():
        raise SystemExit("缺 results/fusion/stats_preregistration.md —— 必须先落盘")
    pre_sha = hashlib.sha256(PRE.read_bytes()).hexdigest().upper()

    frows = list(csv.DictReader((FUS / "metrics.csv").open(encoding="utf-8")))
    srows = list(csv.DictReader((REPO / "results" / "metrics.csv").open(encoding="utf-8")))
    t0 = time.perf_counter()

    # 单方法索引 + 逐观测「最优单法」（ΔSNR 最高者）
    sm = {(r["config_id"], int(r["seed"]), r["method"]): r for r in srows}
    best = {}
    for cid, seed in {(r["config_id"], int(r["seed"])) for r in srows}:
        cand = [(val(sm[(cid, seed, m)], "delta_snr_db"), m) for m in METHODS5
                if (cid, seed, m) in sm]
        cand = [(v, m) for v, m in cand if v is not None]
        if cand:
            best[(cid, seed)] = max(cand)[1]

    # 逐 (role, gamma) 分组
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in frows:
        groups.setdefault((r["role"], r["gamma"]), []).append(r)

    rng_p = np.random.default_rng(SEED_PERM)
    rng_b = np.random.default_rng(SEED_BOOT)
    rows: list[dict] = []

    for (role, gamma), grp in sorted(groups.items()):
        by_pair = {(r["config_id"], int(r["seed"])): r for r in grp}
        # 分层键
        keys: dict[str, set[str]] = {s: set() for s in STRATA}
        for r in grp:
            cid = r["config_id"]
            keys["global"].add("global")
            keys["model"].add(cid.split("_")[0])
            keys["noise"].add(cid.split("_")[1])
            keys["gamma"].add(gamma)
        for metric, label, direction in METRICS:
            for s in STRATA:
                for k in sorted(keys[s]):
                    # 该层内 (cid,seed) 集合
                    members = [(cid, sd) for (cid, sd) in by_pair
                               if (s == "global")
                               or (s == "model" and cid.split("_")[0] == k)
                               or (s == "noise" and cid.split("_")[1] == k)
                               or (s == "gamma" and gamma == k)]
                    recs, raw = [], []
                    for comp in COMPARATORS:
                        diffs = []
                        for cid, sd in sorted(members):
                            fr = by_pair.get((cid, sd))
                            if fr is None:
                                continue
                            fv = val(fr, metric)
                            if fv is None:
                                continue
                            if comp == "vs_method_i":
                                src = sm.get((cid, sd, fr["pair_i"]))
                            elif comp == "vs_method_j":
                                src = sm.get((cid, sd, fr["pair_j"]))
                            else:
                                bm = best.get((cid, sd))
                                src = sm.get((cid, sd, bm)) if bm else None
                            if src is None:
                                continue
                            sv = val(src, metric)
                            if sv is None:
                                continue
                            diffs.append(fv - sv)
                        d = np.asarray(diffs, dtype=np.float64)
                        if d.size == 0:
                            recs.append({"comparator": comp, "n": 0, "median_diff": None,
                                         "ci_lo": None, "ci_hi": None, "p_raw": None, "p_holm": None})
                            raw.append(float("nan"))
                            continue
                        lo, hi = bci(d, rng_b)
                        p = perm(d, rng_p)
                        raw.append(p)
                        recs.append({"comparator": comp, "n": int(d.size),
                                     "median_diff": float(np.median(d)),
                                     "ci_lo": lo, "ci_hi": hi, "p_raw": p, "p_holm": None})
                    valid = [(i, p) for i, p in enumerate(raw) if not np.isnan(p)]
                    if valid:
                        for (i, _), pv in zip(valid, holm([p for _, p in valid])):
                            recs[i]["p_holm"] = pv
                    for rec in recs:
                        rows.append({"role": role, "gamma": gamma, "metric": label,
                                     "column": metric, "direction": direction,
                                     "stratum": s, "stratum_key": k, **rec})

    # 期望行数（可推导）：每个 (role, gamma) 组内
    #   global(1) + model(2) + noise(3) + gamma(1) = **7 个分层键**
    # ⇒ 行数 = 组数 × 指标 5 × 7 × 比较对象 3
    keys_per_group = 1 + 2 + 3 + 1
    expected = len(groups) * len(METRICS) * keys_per_group * len(COMPARATORS)
    with (out / "pairwise.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader(); w.writerows(rows)

    sig = [r for r in rows if r["p_holm"] not in (None, "") and float(r["p_holm"]) < ALPHA]
    nvalid = [r for r in rows if r["p_holm"] not in (None, "")]
    summary = {
        "stats_preregistration_sha256": pre_sha,
        "fusion_metrics_sha256": hashlib.sha256((FUS / "metrics.csv").read_bytes()).hexdigest().upper(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),
        "B_perm": B_PERM, "B_boot": B_BOOT, "alpha": ALPHA,
        "seed_perm": SEED_PERM, "seed_boot": SEED_BOOT,
        "rows": len(rows), "expected_rows": expected,
        "n_significant_holm": len(sig), "n_valid": len(nvalid),
        "elapsed_s": round(time.perf_counter() - t0, 3),
    }
    with (out / "manifest.json").open("w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
