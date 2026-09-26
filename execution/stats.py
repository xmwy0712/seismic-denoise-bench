"""P2.3 统计分析：配对置换检验 + Holm 校正 + 分层自助 CI + 宏平均。

**参数全部来自预注册件** `results/stats/preregistration.md`（**先落盘、后运行**）。
本脚本**只读** `results/metrics.csv`，不改任何输入，不实现融合。

配对置换检验：符号翻转（sign-flip），B = 10000，双侧，α = 0.05；
Holm 校正族 = 每个「指标 × 分层」内的 10 个方法对；
效应量 = 配对差的中位数；CI = 分层自助 95%（percentile），B = 10000；
随机种子显式注入：置换 20261001 / 自助 20261002。
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
METRICS = REPO / "results" / "metrics.csv"
OUT = REPO / "results" / "stats"
PREREG = OUT / "preregistration.md"

# ---------------- 预注册参数（**不得在此处另行改动**；与 preregistration.md 一致）----------------
B_PERM = 10_000
B_BOOT = 10_000
ALPHA = 0.05
SEED_PERM = 20261001
SEED_BOOT = 20261002

METRIC_COLS = [
    ("delta_snr_db", "ΔSNR", "higher"),
    ("lsig", "Lsig", "lower"),
    ("cna_db", "CNA", "higher"),
    ("event_timing_median_ms", "event_timing_median", "lower"),
    ("event_energy_median", "event_energy_median", "lower"),
]
STRATA = ["global", "model", "noise", "level", "f_main", "model_x_noise"]


def load_rows() -> list[dict]:
    with METRICS.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def parse_cid(cid: str) -> dict:
    p = cid.split("_")
    return {"model": p[0], "noise": p[1], "level": p[2], "f_main": p[3]}


def value_of(row: dict, col: str) -> float | None:
    v = row.get(col, "")
    if v in ("", "None", "NA", None):
        return None
    try:
        f = float(v)
    except ValueError:
        return None
    return f if np.isfinite(f) else None


def stratum_keys(meta: dict) -> dict[str, str]:
    return {
        "global": "global",
        "model": meta["model"],
        "noise": meta["noise"],
        "level": meta["level"],
        "f_main": meta["f_main"],
        "model_x_noise": f'{meta["model"]}_{meta["noise"]}',
    }


def holm(pvals: list[float]) -> list[float]:
    """Holm 逐步向下校正（**保序**返回，与输入同序）。"""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [1.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        val = (m - rank) * pvals[i]
        running = max(running, val)
        adj[i] = min(1.0, running)
    return adj


def perm_test(diffs: np.ndarray, rng: np.random.Generator) -> float:
    """符号翻转置换检验（双侧）。统计量 = 配对差均值。"""
    n = diffs.size
    if n == 0:
        return float("nan")
    obs = float(np.mean(diffs))
    signs = rng.integers(0, 2, size=(B_PERM, n), dtype=np.int8).astype(np.float64) * 2.0 - 1.0
    perm = (signs @ diffs) / n
    p = float((np.count_nonzero(np.abs(perm) >= abs(obs) - 1e-12) + 1) / (B_PERM + 1))
    return p


def boot_ci(vals: np.ndarray, rng: np.random.Generator, stat: str = "median") -> tuple[float, float]:
    """分层自助 95% CI（percentile）。stat = median | mean。"""
    n = vals.size
    if n == 0:
        return (float("nan"), float("nan"))
    idx = rng.integers(0, n, size=(B_BOOT, n))
    samples = vals[idx]
    boot = np.median(samples, axis=1) if stat == "median" else np.mean(samples, axis=1)
    return (float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5)))


def main() -> int:
    t0 = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)

    if not PREREG.exists():
        raise SystemExit("预注册件缺失 —— 必须先落盘 results/stats/preregistration.md")
    prereg_sha = hashlib.sha256(PREREG.read_bytes()).hexdigest().upper()

    rows = load_rows()
    methods = sorted({r["method"] for r in rows})
    pairs = list(itertools.combinations(methods, 2))
    for r in rows:
        r["_meta"] = parse_cid(r["config_id"])

    # 索引：(config_id, seed, method) -> row
    index: dict[tuple[str, int, str], dict] = {
        (r["config_id"], int(r["seed"]), r["method"]): r for r in rows
    }
    cells = sorted({(r["config_id"], int(r["seed"])) for r in rows})

    # 分层成员：stratum_name -> key -> {(config_id, seed)}
    strat_members: dict[str, dict[str, set]] = {s: {} for s in STRATA}
    for cid, seed in cells:
        meta = parse_cid(cid)
        for s, key in stratum_keys(meta).items():
            strat_members[s].setdefault(key, set()).add((cid, seed))

    rng_p = np.random.default_rng(SEED_PERM)
    rng_b = np.random.default_rng(SEED_BOOT)

    out_rows: list[dict] = []
    # **按「分层类型 × 分层键」逐格出表**：分层键总数 = 1+2+3+3+3+6 = 18
    # ⇒ 行数 = 10 对 × 5 指标 × 18 分层 = **900**（与预注册件公式一致）。
    # Holm 族 = 「本指标 × 本分层键」内的 10 个方法对。
    for col, label, direction in METRIC_COLS:
        for s in STRATA:
            for skey, members in sorted(strat_members[s].items()):
                recs: list[dict] = []
                raw: list[float] = []
                m_sorted = sorted(members)
                for (a, b) in pairs:
                    diffs: list[float] = []
                    for cid, seed in m_sorted:
                        ra = index.get((cid, seed, a))
                        rb = index.get((cid, seed, b))
                        if ra is None or rb is None:
                            continue
                        va, vb = value_of(ra, col), value_of(rb, col)
                        if va is None or vb is None:
                            continue
                        diffs.append(va - vb)
                    dv = np.asarray(diffs, dtype=np.float64)
                    n = int(dv.size)
                    if n == 0:
                        recs.append({"metric": label, "column": col, "direction": direction,
                                     "stratum": s, "stratum_key": skey,
                                     "method_a": a, "method_b": b, "n": 0,
                                     "median_diff": None, "ci_lo": None, "ci_hi": None,
                                     "p_raw": None, "p_holm": None})
                        raw.append(float("nan"))
                        continue
                    med = float(np.median(dv))
                    lo, hi = boot_ci(dv, rng_b, "median")
                    pv = perm_test(dv, rng_p)
                    raw.append(pv)
                    recs.append({"metric": label, "column": col, "direction": direction,
                                 "stratum": s, "stratum_key": skey,
                                 "method_a": a, "method_b": b, "n": n,
                                 "median_diff": med, "ci_lo": lo, "ci_hi": hi,
                                 "p_raw": pv, "p_holm": None})
                valid = [(i, pv) for i, pv in enumerate(raw) if not np.isnan(pv)]
                if valid:
                    adj = holm([pv for _, pv in valid])
                    for (i, _), pv in zip(valid, adj):
                        recs[i]["p_holm"] = pv
                out_rows.extend(recs)

    # ── 写出 pairwise.csv
    pw = OUT / "pairwise.csv"
    cols = ["metric", "column", "direction", "stratum", "stratum_key", "method_a", "method_b",
            "n", "median_diff", "ci_lo", "ci_hi", "p_raw", "p_holm"]
    with pw.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(out_rows)
    n_stratum_keys = sum(len(v) for v in strat_members.values())
    expected = len(pairs) * len(METRIC_COLS) * n_stratum_keys
    assert len(out_rows) == expected, f"行数 {len(out_rows)} != {expected}"

    # ── 宏平均（逐方法：中位与均值 + 自助 CI）
    macro: list[dict] = []
    for col, label, direction in METRIC_COLS:
        for m in methods:
            vals = np.array([value_of(r, col) for r in rows if r["method"] == m
                             and value_of(r, col) is not None], dtype=np.float64)
            if vals.size == 0:
                continue
            lo_m, hi_m = boot_ci(vals, rng_b, "median")
            lo_a, hi_a = boot_ci(vals, rng_b, "mean")
            macro.append({"metric": label, "method": m, "direction": direction,
                          "n": int(vals.size),
                          "median": float(np.median(vals)),
                          "median_ci_lo": lo_m, "median_ci_hi": hi_m,
                          "mean": float(np.mean(vals)),
                          "mean_ci_lo": lo_a, "mean_ci_hi": hi_a})
    with (OUT / "macro_average.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(macro[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(macro)

    elapsed = time.perf_counter() - t0
    (OUT / "manifest.json").write_text(json.dumps({
        "preregistration_sha256": prereg_sha,
        "metrics_csv_sha256": hashlib.sha256(METRICS.read_bytes()).hexdigest().upper(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),
        "B_perm": B_PERM, "B_boot": B_BOOT, "alpha": ALPHA,
        "seed_perm": SEED_PERM, "seed_boot": SEED_BOOT,
        "n_pairs": len(pairs), "n_metrics": len(METRIC_COLS), "n_strata_types": len(STRATA), "n_stratum_keys": n_stratum_keys,
        "pairwise_rows": len(out_rows), "expected_rows": expected,
        "elapsed_s": round(elapsed, 3),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"pairwise.csv 行数 = {len(out_rows)}（期望 {expected}）")
    print(f"macro_average.csv 行数 = {len(macro)}")
    print(f"耗时 = {elapsed:.2f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
