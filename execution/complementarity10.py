"""P5.4 · WS1③：互补性度量更正与重算（10 配对 × 4 度量 → results/complementarity10/）。

* **M1**（无符号，预注册原样）：`1 - |<e_i,e_j>| / (‖e_i‖‖e_j‖)`
* **M1_signed**（本批**新增**，分析性质）：`1 - <e_i,e_j> / (‖e_i‖‖e_j‖)`
  —— 依据：反相关误差对取平均更有利，取绝对值会把"有利/不利"混为一谈。
* **M2**（预注册原样，**不修正**）：池化 `IQR×1.5` 阈值下 `|Δ Lsig_w|` 超阈窗占比；**不区分方向**。
* **M3**（= 预注册与实现口径：**真 JS**，`m=(p+q)/2`）：本脚本**照实重算**，用于与既有值对齐核验。

**交叉核验（硬门）**：M1/M2/M3 三度量 × 10 对 × 18 分层键 = **540 值**，必须与既有
`results/complementarity/complementarity.csv` **逐值完全一致**；不一致 ⇒ 打印并置 `cross_ok=False`。

**独立性**：同原模块，**不导入** `bench.fusion` / `bench.methods`。
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import itertools
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))


def _load_module():
    p = REPO / "src" / "bench" / "analysis" / "complementarity.py"
    spec = importlib.util.spec_from_file_location("compl_mod", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


C = _load_module()
PTOL = 1e-12


def run(out_dir: Path) -> dict:
    fz = C.load_frozen_v2()
    dt = float(fz["item_02_model_m1"]["dt_s"])
    cfgs = C.build_configs(fz)
    seeds = [int(s) for s in fz["item_01_synthetic_matrix"]["seeds"]]
    obs = [(C.config_id(c), s, c) for c in cfgs for s in seeds]
    assert len(obs) == 270, f"观测数须为 270，实测 {len(obs)}"

    # Pass 1：逐观测逐方法缓存
    cache = {}
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
                    lw.append(np.nan); ev.append(False); continue
                num = float(np.linalg.norm(e[t0:t0 + n_t, :][mw]))
                lw.append(num / den); ev.append(True)
            rec["methods"][m] = {"e": e, "norm": ne,
                                 "lsig_w": np.asarray(lw, dtype=np.float64),
                                 "evaluable": np.asarray(ev, dtype=bool),
                                 "band": C.band_distribution(e, dt)}
        cache[(cid, seed)] = rec

    # 池化阈值（同预注册：每对固定常数）
    thresholds = {}
    for (a, b) in C.PAIRS:
        pool = []
        for rec in cache.values():
            la, lb = rec["methods"][a]["lsig_w"], rec["methods"][b]["lsig_w"]
            ok = rec["methods"][a]["evaluable"] & rec["methods"][b]["evaluable"]
            d = (la - lb)[ok]
            d = d[np.isfinite(d)]
            if d.size:
                pool.append(d)
        if pool:
            allv = np.concatenate(pool)
            q1, q3 = np.percentile(allv, [25.0, 75.0])
            thresholds[(a, b)] = float(C.IQR_MULT * (q3 - q1))
        else:
            thresholds[(a, b)] = float("nan")

    # Pass 2：逐观测逐对计算
    METRICS = ("M1", "M1_signed", "M2", "M3")
    per_obs = {p: {m: [] for m in METRICS} for p in C.PAIRS}
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
            la, lb = ea["lsig_w"], eb["lsig_w"]
            ok = ea["evaluable"] & eb["evaluable"] & np.isfinite(la) & np.isfinite(lb)
            thr = thresholds[(a, b)]
            if ok.sum() == 0 or not np.isfinite(thr):
                m2 = np.nan
            else:
                d = np.abs(la[ok] - lb[ok])
                m2 = float(np.count_nonzero(d > thr) / ok.sum())
            pa, pb = ea["band"], eb["band"]
            m3 = np.nan if (pa.sum() == 0.0 or pb.sum() == 0.0) else C.jsd_base2(pa, pb)
            per_obs[(a, b)]["M1"].append(m1)
            per_obs[(a, b)]["M1_signed"].append(m1s)
            per_obs[(a, b)]["M2"].append(m2)
            per_obs[(a, b)]["M3"].append(m3)
            obs_index[(a, b)].append((cid, seed, st))

    rows = []
    for (a, b) in C.PAIRS:
        st_list = obs_index[(a, b)]
        keys = {s: set() for s in C.STRATA}
        for _c, _sd, st in st_list:
            for s in C.STRATA:
                keys[s].add(st[s])
        for metric in METRICS:
            vals = per_obs[(a, b)][metric]
            for s in C.STRATA:
                for k in sorted(keys[s]):
                    sub = [v for v, (_c, _sd, stt) in zip(vals, st_list) if stt[s] == k]
                    sub = [v for v in sub if np.isfinite(v)]
                    rows.append({"pair": f"{a}|{b}", "method_a": a, "method_b": b,
                                 "metric": metric, "stratum": s, "stratum_key": k,
                                 "n_obs": len(sub), "value": C.median_or_na(sub)})

    # 交叉核验：与既有 CSV 逐值比对（M1/M2/M3）
    old = {}
    with (REPO / "results/complementarity/complementarity.csv").open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            old[(r["pair"], r["metric"], r["stratum"], r["stratum_key"])] = (
                r["n_obs"], None if r["value"] == "" else float(r["value"]))
    mismatch, checked = [], 0
    for r in rows:
        if r["metric"] not in ("M1", "M2", "M3"):
            continue
        key = (r["pair"], r["metric"], r["stratum"], r["stratum_key"])
        if key not in old:
            mismatch.append({"key": key, "reason": "既有 CSV 缺该键"})
            continue
        on, ov = old[key]
        checked += 1
        nv = r["value"]
        if str(r["n_obs"]) != str(on):
            mismatch.append({"key": key, "reason": f"n_obs {on} -> {r['n_obs']}"})
        elif (ov is None) != (nv is None):
            mismatch.append({"key": key, "reason": f"空值性不一致 old={ov} new={nv}"})
        elif ov is not None and abs(ov - nv) > PTOL:
            mismatch.append({"key": key, "reason": f"值 {ov!r} -> {nv!r}"})

    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "complementarity10.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader(); w.writerows(rows)
    summary = {"rows": len(rows), "expected_rows": len(C.PAIRS) * len(METRICS) * 18,
               "metrics": list(METRICS), "cross_checked": checked,
               "cross_mismatches": len(mismatch), "cross_ok": (checked > 0 and not mismatch),
               "cross_detail": mismatch[:10],
               "thresholds": {f"{a}|{b}": v for (a, b), v in thresholds.items()},
               "note": "M1/M2/M3 为预注册口径照实重算（M3 = 真 JS）；M1_signed 为本批新增的分析性质量"}
    with (out_dir / "run_manifest.json").open("w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="P5.4 WS1③ · 互补性 10 配对重算")
    ap.add_argument("--out", default="results/complementarity10")
    a = ap.parse_args(argv)
    s = run(REPO / a.out)
    print(json.dumps(s, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
