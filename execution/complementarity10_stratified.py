"""P5.8 · WS2②：互补性阈值口径的**直接检验** —— 逐噪声类型层内 IQR 重选。

**预注册声明（运行前冻结，随本脚本一并提交并打 tag）**
------------------------------------------------------
问题：`results/complementarity/pair_selection.json` 的配对选择用**全局池化**的
`IQR×1.5` 阈值（`fx_deconv|wavelet_threshold` τ = 0.03946529906544755）。
该池化是否制造了「主配对居首」的伪影？

处置：**只改阈值口径** —— M2 的 `τ_ij` 由全局池化改为**逐噪声类型层内**分别池化
（N1 / N2 / N3 各自把所有观测的 `|Δ Lsig_w|` 合并后算 `IQR×1.5`）。
其余**一律不变**：M1 / M1_signed / M3 定义、观测集合（270）、层键（18）、
选择规则（max global M2 median → tie → M1 → lexicographic）。

判读（**两个方向都接受，如实报告**）
------------------------------------
* 主配对 `fx_deconv|wavelet_threshold` **仍居首** ⇒ 池化未制造伪影，回到「系统性占优」解释；
* 主配对**不再居首** ⇒ 池化伪影坐实，按新首位配对报告并如实披露。

自证门（自带反证）
------------------
`--mode pooled` 的 M1 / M1_signed / M2 / M3 **必须**与既有
`results/complementarity10/complementarity10.csv` **逐值一致**（tol = 1e-12）。
不一致 ⇒ `cross_ok = False` 且**退出码非零**。这一门同时反证：本脚本复现了口径未变时的既有结果。

**独立性**：同原模块，**不导入** `bench.fusion` / `bench.methods`。
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
PTOL = 1e-12
NOISE_KEYS = ("N1", "N2", "N3")


def _load_module():
    p = REPO / "src" / "bench" / "analysis" / "complementarity.py"
    spec = importlib.util.spec_from_file_location("compl_mod", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


C = _load_module()


def _build_cache() -> dict:
    """逐观测逐方法缓存（与 `complementarity10.py` 同法，保证可比）。"""
    fz = C.load_frozen_v2()
    dt = float(fz["item_02_model_m1"]["dt_s"])
    cfgs = C.build_configs(fz)
    seeds = [int(s) for s in fz["item_01_synthetic_matrix"]["seeds"]]
    obs = [(C.config_id(c), s, c) for c in cfgs for s in seeds]
    assert len(obs) == 270, f"观测数须为 270，实测 {len(obs)}"

    cache: dict = {}
    for cid, seed, cfg in obs:
        s = C.clean_truth(cfg, seed)
        n_t = C.dilation_length_samples(cfg["f_main"], dt)
        mask = C.event_mask(s, f_main=cfg["f_main"], dt=dt,
                            threshold=0.5 * float(np.max(np.abs(s))))
        starts = C.window_starts(s.shape[0], n_t)
        rec = {"methods": {}}
        for m in C.METHODS:
            f = REPO / "results" / f"{cid}_{seed}_{m}.npy"
            if not f.exists():
                raise FileNotFoundError(f"缺 y_hat：{f}")
            y = np.load(f)
            e = y - s
            ne = float(np.linalg.norm(e))
            lw, ev = [], []
            for t0 in starts:
                mw = mask[t0:t0 + n_t, :]
                den = float(np.linalg.norm(s[t0:t0 + n_t, :][mw]))
                if den <= 0.0:
                    lw.append(np.nan)
                    ev.append(False)
                    continue
                num = float(np.linalg.norm(e[t0:t0 + n_t, :][mw]))
                lw.append(num / den)
                ev.append(True)
            rec["methods"][m] = {"e": e, "norm": ne,
                                 "lsig_w": np.asarray(lw, dtype=np.float64),
                                 "evaluable": np.asarray(ev, dtype=bool),
                                 "band": C.band_distribution(e, dt)}
        cache[(cid, seed)] = rec
    return cache


def _deltas(cache: dict) -> dict:
    """逐观测逐对的 `|Δ Lsig_w|` 可用值（未取绝对值前带符号）。"""
    dob: dict = {}
    for (cid, seed), rec in cache.items():
        for (a, b) in C.PAIRS:
            ea, eb = rec["methods"][a], rec["methods"][b]
            la, lb = ea["lsig_w"], eb["lsig_w"]
            ok = ea["evaluable"] & eb["evaluable"] & np.isfinite(la) & np.isfinite(lb)
            dob[(cid, seed, a, b)] = (la - lb)[ok]
    return dob


def _thresholds(dob: dict) -> tuple[dict, dict, dict]:
    thr_pool, thr_strat, iqr = {}, {}, {}
    for (a, b) in C.PAIRS:
        allv = [d for (c_, s_, aa, bb), d in dob.items() if (aa, bb) == (a, b) and d.size]
        v = np.concatenate(allv)
        q1, q3 = np.percentile(v, [25.0, 75.0])
        thr_pool[(a, b)] = float(C.IQR_MULT * (q3 - q1))
        iqr[(a, b, "pooled")] = float(q3 - q1)
        for nt in NOISE_KEYS:
            sub = [d for (c_, s_, aa, bb), d in dob.items()
                   if (aa, bb) == (a, b) and C.stratum_of(c_)["noise"] == nt and d.size]
            vn = np.concatenate(sub)
            q1n, q3n = np.percentile(vn, [25.0, 75.0])
            thr_strat[(a, b, nt)] = float(C.IQR_MULT * (q3n - q1n))
            iqr[(a, b, nt)] = float(q3n - q1n)
    return thr_pool, thr_strat, iqr


def _rows(cache: dict, dob: dict, thr_pool: dict, thr_strat: dict, mode: str) -> list[dict]:
    """按给定阈值口径重算 M1/M1_signed/M2/M3 与分层中位值。"""
    per_obs = {p: {m: [] for m in ("M1", "M1_signed", "M2", "M3")} for p in C.PAIRS}
    obs_index = {p: [] for p in C.PAIRS}
    for (cid, seed), rec in cache.items():
        st = C.stratum_of(cid)
        for (a, b) in C.PAIRS:
            ea, eb = rec["methods"][a], rec["methods"][b]
            na, nb = ea["norm"], eb["norm"]
            ip = float(np.sum(ea["e"] * eb["e"]))
            if na == 0.0 or nb == 0.0:
                m1 = m1s = np.nan
            else:
                m1 = 1.0 - abs(ip) / (na * nb)
                m1s = 1.0 - ip / (na * nb)
            d = np.abs(dob[(cid, seed, a, b)])
            if mode == "pooled":
                thr = thr_pool[(a, b)]
            else:
                thr = thr_strat[(a, b, st["noise"])]
            m2 = np.nan if d.size == 0 else float(np.count_nonzero(d > thr) / d.size)
            pa, pb = ea["band"], eb["band"]
            m3 = np.nan if (pa.sum() == 0.0 or pb.sum() == 0.0) else C.jsd_base2(pa, pb)
            per_obs[(a, b)]["M1"].append(m1)
            per_obs[(a, b)]["M1_signed"].append(m1s)
            per_obs[(a, b)]["M2"].append(m2)
            per_obs[(a, b)]["M3"].append(m3)
            obs_index[(a, b)].append((cid, seed, st))

    rows: list[dict] = []
    for (a, b) in C.PAIRS:
        st_list = obs_index[(a, b)]
        keys = {s: set() for s in C.STRATA}
        for _c, _sd, st in st_list:
            for s in C.STRATA:
                keys[s].add(st[s])
        for metric in ("M1", "M1_signed", "M2", "M3"):
            vals = per_obs[(a, b)][metric]
            for s in C.STRATA:
                for k in sorted(keys[s]):
                    sub = [v for v, (_c, _sd, stt) in zip(vals, st_list) if stt[s] == k]
                    sub = [v for v in sub if np.isfinite(v)]
                    rows.append({"pair": f"{a}|{b}", "method_a": a, "method_b": b,
                                 "metric": metric, "stratum": s, "stratum_key": k,
                                 "n_obs": len(sub), "value": C.median_or_na(sub)})
    return rows


def _select(rows: list[dict]) -> dict:
    """原规则重选（逐行照搬 `complementarity.py` L258-276）。"""
    glob = {(r["method_a"], r["method_b"]): r for r in rows
            if r["metric"] == "M2" and r["stratum"] == "global"}
    m1g = {(r["method_a"], r["method_b"]): r for r in rows
           if r["metric"] == "M1" and r["stratum"] == "global"}

    def val(d, p):
        v = d[p]["value"]
        return float("-inf") if v in ("", None) else float(v)

    best_m2 = max(val(glob, p) for p in C.PAIRS)
    cand = [p for p in C.PAIRS if abs(val(glob, p) - best_m2) < 1e-9]
    tie_path = ["primary: max global M2 median"]
    if len(cand) > 1:
        tie_path.append(f"tie on M2 among {len(cand)} pairs -> M1")
        best_m1 = max(val(m1g, p) for p in cand)
        cand = [p for p in cand if abs(val(m1g, p) - best_m1) < 1e-9]
    if len(cand) > 1:
        tie_path.append(f"tie on M1 among {len(cand)} pairs -> lexicographic method name")
        cand = [min(cand, key=lambda p: (p[0], p[1]))]
    chosen = cand[0] if cand else C.PAIRS[0]
    return {"chosen_pair": [chosen[0], chosen[1]],
            "chosen_m2_global": val(glob, chosen),
            "chosen_m1_global": val(m1g, chosen),
            "tie_resolution_path": tie_path,
            "ranking_by_m2_global": [{"pair": f"{p[0]}|{p[1]}", "M2": val(glob, p), "M1": val(m1g, p)}
                                     for p in sorted(C.PAIRS, key=lambda p: -val(glob, p))]}


def _cross_check(rows: list[dict]) -> tuple[int, list[dict]]:
    old = {}
    with (REPO / "results/complementarity10/complementarity10.csv").open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            old[(r["pair"], r["metric"], r["stratum"], r["stratum_key"])] = (
                r["n_obs"], None if r["value"] == "" else float(r["value"]))
    mismatch, checked = [], 0
    for r in rows:
        key = (r["pair"], r["metric"], r["stratum"], r["stratum_key"])
        if key not in old:
            mismatch.append({"key": list(key), "reason": "既有 CSV 缺该键"})
            continue
        on, ov = old[key]
        checked += 1
        nv = r["value"]
        if str(r["n_obs"]) != str(on):
            mismatch.append({"key": list(key), "reason": f"n_obs {on} -> {r['n_obs']}"})
        elif (ov is None) != (nv is None):
            mismatch.append({"key": list(key), "reason": f"空值性不一致 old={ov} new={nv}"})
        elif ov is not None and abs(ov - nv) > PTOL:
            mismatch.append({"key": list(key), "reason": f"值 {ov!r} -> {nv!r}"})
    return checked, mismatch


def run(out_dir: Path) -> dict:
    cache = _build_cache()
    dob = _deltas(cache)
    thr_pool, thr_strat, iqr = _thresholds(dob)

    rows_pool = _rows(cache, dob, thr_pool, thr_strat, "pooled")
    rows_strat = _rows(cache, dob, thr_pool, thr_strat, "stratified")

    checked, mismatch = _cross_check(rows_pool)
    sel_pool = _select(rows_pool)
    sel_strat = _select(rows_strat)

    fp = ("fx_deconv", "wavelet_threshold")
    still_top = tuple(sel_strat["chosen_pair"]) == fp
    summary = {
        "question": "全局池化 IQR 阈值是否制造了主配对居首的伪影？",
        "rule": "M2 global median max; tie -> M1; tie -> lexicographic（与既有完全一致）",
        "changed": "仅 M2 的 τ_ij 口径：全局池化 -> 逐噪声类型层内池化",
        "thresholds_pooled": {f"{a}|{b}": v for (a, b), v in thr_pool.items()},
        "thresholds_stratified": {f"{a}|{b}|{nt}": v for (a, b, nt), v in thr_strat.items()},
        "iqr": {f"{a}|{b}|{k}": v for (a, b, k), v in iqr.items()},
        "selection_pooled": sel_pool,
        "selection_stratified": sel_strat,
        "primary_pair": list(fp),
        "primary_pair_still_top": bool(still_top),
        "verdict": ("池化未制造伪影 —— 回到「系统性占优」解释" if still_top
                    else "池化伪影坐实 —— 主配对不再居首"),
        "self_check": {"mode_pooled_vs_existing": {"checked": checked,
                                                   "mismatches": len(mismatch),
                                                   "cross_ok": (checked > 0 and not mismatch),
                                                   "detail": mismatch[:10]}},
        "rows": len(rows_strat),
        "note": "两个方向都接受；本结论只改阈值口径，其余口径完全不变",
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "complementarity10_stratified.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows_strat[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows_strat)
    with (out_dir / "reselection.json").open("w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="P5.8 WS2② · 层内 IQR 阈值重选检验")
    ap.add_argument("--out", default="results/complementarity10_stratified")
    a = ap.parse_args(argv)
    s = run(REPO / a.out)
    sc = s["self_check"]["mode_pooled_vs_existing"]
    print(json.dumps({"primary_pair_still_top": s["primary_pair_still_top"],
                      "verdict": s["verdict"],
                      "chosen_stratified": s["selection_stratified"]["chosen_pair"],
                      "self_check": sc}, ensure_ascii=False, indent=2))
    return 0 if sc["cross_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
