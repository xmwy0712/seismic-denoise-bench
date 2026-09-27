"""P3.1 互补性量化（M1 误差正交性 / M2 局部互补 / M3 频带互补）。

**预注册纪律**：全部定义取自 `results/complementarity/preregistration.md`（**先落盘、后计算**）。
本模块**只读**输入（y_hat + 冻结观测重放 + `frozen-v2.yaml`），**不写**任何 y_hat / metrics.csv / frozen*。

**独立性（硬约束）**：本模块**不得导入** ``bench.fusion`` / ``bench.methods`` ——
互补性度量只依赖**误差与真值**，不依赖任何方法实现或融合实现。
由 ``tests/test_complementarity.py`` 的 import 行扫描守卫机械核验（含反证，规则 14）。

**确定性**：M1/M2/M3 全为**确定性**运算（无抽样 / 无置换 / 无自助），
「同输入两次运行逐字节相同」**由构造保证**。

用法::

    python src/bench/analysis/complementarity.py --out results/complementarity
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from bench.data import synthetic as S                      # noqa: E402
from bench.data.ricker import ricker                       # noqa: E402
from bench.metrics.lsig import dilation_length_samples, event_mask   # noqa: E402

METHODS = ("fk_filter", "fx_deconv", "wavelet_threshold", "ssa_decomposition", "svd_lowrank")
PAIRS = list(itertools.combinations(METHODS, 2))           # 10 对
BANDS_HZ = [(0.0, 5.0), (5.0, 15.0), (15.0, 25.0), (25.0, 40.0), (40.0, 250.0)]  # 预注册 5 带
IQR_MULT = 1.5                                             # 预注册（Tukey 惯用值）
STRATA = ("global", "model", "noise", "level", "f_main", "model_x_noise")


def sha256_of(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a, dtype=np.float64).tobytes()).hexdigest().upper()


def load_frozen_v2() -> dict:
    return yaml.safe_load((REPO / "configs" / "frozen-v2.yaml").read_text(encoding="utf-8"))


def build_configs(fz: dict) -> list[dict]:
    """按 frozen-v2 的轴展开 54 配置（**不依赖 execution/ 或 bench.methods**）。"""
    it01, it02, it03 = (fz["item_01_synthetic_matrix"], fz["item_02_model_m1"],
                        fz["item_03_model_m2"])
    it04, it05, sup = (fz["item_04_noise_levels"], fz["item_05_dispersive_surface_wave"],
                       fz["item_04_supplement"])
    acq = {"dt_s": it02["dt_s"], "dx_m": it02["dx_m"],
           "n_samples": it02["n_samples"], "n_traces": it02["n_traces"]}
    ratios = it04["criterion_ii_descriptive"]["values"]
    n2v = [800.0, 1500.0, 3000.0]
    n1p = {"band_hz": list(sup["n1_band_limited_random"]["band_hz"])}
    n2p = {"f_main_hz": float(sup["n2_linear_coherent"]["f_main_hz"]), "v_app_m_s": n2v}
    n3p = {"v_model": it05["model"]["v_model"], "v0": it05["model"]["v0"],
           "c": it05["model"]["c"], "a": it05["model"]["a"], "b": it05["model"]["b"],
           "f_lo_hz": it05["frequency_band_hz"][0], "f_hi_hz": it05["frequency_band_hz"][1],
           "n_components": it05["n_components"]}
    noises = [{"id": "N1", "params": n1p}, {"id": "N2", "params": n2p}, {"id": "N3", "params": n3p}]
    models = [{"id": it02["id"], "params": it02["params"]},
              {"id": it03["id"], "params": it03["params"]}]
    out = []
    for m in models:
        for nz in noises:
            for li, lv in enumerate(it01["axes"]["noise_levels"]):
                for fm in it01["axes"]["f_main_hz"]:
                    out.append({"model": m, "noise": nz,
                                "level": {"id": lv, "amplitude_ratio": ratios[lv]},
                                "f_main": float(fm), "acq": acq,
                                "n2_v_app": n2v[li] if nz["id"] == "N2" else None})
    return out


def clean_truth(cfg: dict, seed: int) -> np.ndarray:
    """冻结观测重放：**只求干净真值 s**（与 P2.2 全矩阵同源，逐字对齐）。"""
    acq = cfg["acq"]
    dt, ns, ntr = float(acq["dt_s"]), int(acq["n_samples"]), int(acq["n_traces"])
    _t, w = ricker(cfg["f_main"], dt, ns)
    rng = np.random.default_rng(seed)
    if cfg["model"]["id"] == "M1":
        mp = cfg["model"]["params"]
        refl = S.reflectivity(int(mp["n_layers"]), rng, sparsity=float(mp["sparsity"]))
        return S.forward(refl, w, n_traces=ntr)[:ns, :]
    mp = dict(cfg["model"]["params"])
    for k in ("n_samples", "n_traces"):
        mp.pop(k, None)
    field = S.reflectivity_structure(rng=rng, n_samples=ns, n_traces=ntr, **mp)
    return S.forward_structure(field, w, trace_stride=1)[:ns, :]


def config_id(cfg: dict) -> str:
    return f'{cfg["model"]["id"]}_{cfg["noise"]["id"]}_{cfg["level"]["id"]}_{int(cfg["f_main"])}Hz'


def window_starts(n_samples: int, n_t: int) -> list[int]:
    """窗长 = n_T，步长 = n_T // 2；起点满足 t0 + n_T <= n_samples（**不截断**）。"""
    stride = n_t // 2
    if stride < 1:
        stride = 1
    out, t0 = [], 0
    while t0 + n_t <= n_samples:
        out.append(t0)
        t0 += stride
    return out


def band_distribution(e: np.ndarray, dt: float) -> np.ndarray:
    """误差沿时间轴的功率谱按预注册 5 带求和 → 归一化分布（长度 5）。"""
    spec = np.abs(np.fft.rfft(e, axis=0)) ** 2
    freqs = np.fft.rfftfreq(e.shape[0], d=dt)
    energy = spec.sum(axis=1)
    d = np.zeros(len(BANDS_HZ), dtype=np.float64)
    for k, (lo, hi) in enumerate(BANDS_HZ):
        sel = (freqs >= lo) & (freqs < hi)
        d[k] = float(energy[sel].sum())
    tot = float(d.sum())
    return d / tot if tot > 0 else np.zeros_like(d)


def jsd_base2(p: np.ndarray, q: np.ndarray) -> float:
    """base-2 Jensen-Shannon 散度 ∈ [0, 1]。"""
    def kl(a, b):
        m = (a > 0) & (b > 0)
        return float(np.sum(a[m] * np.log2(a[m] / b[m])))
    m = 0.5 * (p + q)
    v = 0.5 * kl(p, m) + 0.5 * kl(q, m)
    return float(min(max(v, 0.0), 1.0))


def stratum_of(cid: str) -> dict[str, str]:
    p = cid.split("_")
    model, noise, level, fm = p[0], p[1], p[2], p[3].replace("Hz", "")
    return {"global": "global", "model": model, "noise": noise, "level": level,
            "f_main": fm, "model_x_noise": f"{model}_{noise}"}


def median_or_na(vals: list[float]) -> float | None:
    return float(np.median(vals)) if vals else None


def run(out_dir: Path) -> dict:
    fz = load_frozen_v2()
    dt = float(fz["item_02_model_m1"]["dt_s"])
    cfgs = build_configs(fz)
    seeds = [int(s) for s in fz["item_01_synthetic_matrix"]["seeds"]]
    obs = [(config_id(c), s, c) for c in cfgs for s in seeds]
    assert len(obs) == 270, f"观测数须为 270，实测 {len(obs)}"

    # ── Pass 1：逐观测逐方法缓存（误差范数 / 窗级 Lsig / 可评估性 / 频带分布）
    cache: dict[tuple[str, int], dict] = {}
    for cid, seed, cfg in obs:
        s = clean_truth(cfg, seed)
        n_t = dilation_length_samples(cfg["f_main"], dt)
        mask = event_mask(s, f_main=cfg["f_main"], dt=dt, threshold=0.5 * float(np.max(np.abs(s))))
        starts = window_starts(s.shape[0], n_t)
        rec: dict = {"s": s, "n_t": n_t, "starts": starts, "methods": {}}
        for m in METHODS:
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
                                 "band": band_distribution(e, dt)}
        cache[(cid, seed)] = rec

    # ── 池化阈值：每对的 d_w 在全部观测的全部可评估窗上汇总（预注册）
    thresholds: dict[tuple[str, str], float] = {}
    for (a, b) in PAIRS:
        pool = []
        for key, rec in cache.items():
            la, lb = rec["methods"][a]["lsig_w"], rec["methods"][b]["lsig_w"]
            ok = rec["methods"][a]["evaluable"] & rec["methods"][b]["evaluable"]
            d = (la - lb)[ok]
            d = d[np.isfinite(d)]
            if d.size:
                pool.append(d)
        if pool:
            allv = np.concatenate(pool)
            q1, q3 = np.percentile(allv, [25.0, 75.0])
            thresholds[(a, b)] = float(IQR_MULT * (q3 - q1))
        else:
            thresholds[(a, b)] = float("nan")

    # ── Pass 2：逐观测逐对计算 M1/M2/M3
    per_obs: dict[tuple[str, str], dict[str, list[float]]] = {
        p: {"M1": [], "M2": [], "M3": []} for p in PAIRS}
    obs_index: dict[tuple[str, str], list[tuple[str, int, dict[str, str]]]] = {
        p: [] for p in PAIRS}
    for (cid, seed), rec in cache.items():
        st = stratum_of(cid)
        for (a, b) in PAIRS:
            ea, eb = rec["methods"][a], rec["methods"][b]
            na, nb = ea["norm"], eb["norm"]
            m1 = np.nan if (na == 0.0 or nb == 0.0) else \
                1.0 - abs(float(np.sum(ea["e"] * eb["e"]))) / (na * nb)
            la, lb = ea["lsig_w"], eb["lsig_w"]
            ok = ea["evaluable"] & eb["evaluable"] & np.isfinite(la) & np.isfinite(lb)
            thr = thresholds[(a, b)]
            if ok.sum() == 0 or not np.isfinite(thr):
                m2 = np.nan
            else:
                d = np.abs(la[ok] - lb[ok])
                m2 = float(np.count_nonzero(d > thr) / ok.sum())
            pa, pb = ea["band"], eb["band"]
            m3 = np.nan if (pa.sum() == 0.0 or pb.sum() == 0.0) else jsd_base2(pa, pb)
            per_obs[(a, b)]["M1"].append(m1)
            per_obs[(a, b)]["M2"].append(m2)
            per_obs[(a, b)]["M3"].append(m3)
            obs_index[(a, b)].append((cid, seed, st))

    # ── 聚合：10 对 × 3 度量 × 18 分层键 = 540 行
    rows: list[dict] = []
    for (a, b) in PAIRS:
        st_list = obs_index[(a, b)]
        keys: dict[str, set[str]] = {s: set() for s in STRATA}
        for _cid, _seed, st in st_list:
            for s in STRATA:
                keys[s].add(st[s])
        for metric in ("M1", "M2", "M3"):
            vals = per_obs[(a, b)][metric]
            for s in STRATA:
                for k in sorted(keys[s]):
                    sub = [v for v, (_c, _sd, stt) in zip(vals, st_list) if stt[s] == k]
                    sub = [v for v in sub if np.isfinite(v)]
                    rows.append({"pair": f"{a}|{b}", "method_a": a, "method_b": b,
                                 "metric": metric, "stratum": s, "stratum_key": k,
                                 "n_obs": len(sub), "value": median_or_na(sub)})
    n_keys = sum(len(v) for v in
                 ({s: {st[s] for *_x, st in obs_index[PAIRS[0]]} for s in STRATA}).values())
    expected = len(PAIRS) * 3 * n_keys
    assert len(rows) == expected, f"行数 {len(rows)} != {expected}"

    # ── 配对选择（**机械、可重放**，预注册第 5.2 条）
    glob = {(r["method_a"], r["method_b"]): r for r in rows
            if r["metric"] == "M2" and r["stratum"] == "global"}
    m1g = {(r["method_a"], r["method_b"]): r for r in rows
           if r["metric"] == "M1" and r["stratum"] == "global"}
    def val(d, p):
        v = d[p]["value"]
        return float("-inf") if v in ("", None) else float(v)
    best_m2 = max(val(glob, p) for p in PAIRS)
    cand = [p for p in PAIRS if abs(val(glob, p) - best_m2) < 1e-9]
    tie_path = ["primary: max global M2 median"]
    if len(cand) > 1:
        tie_path.append(f"tie on M2 among {len(cand)} pairs -> M1")
        best_m1 = max(val(m1g, p) for p in cand)
        cand = [p for p in cand if abs(val(m1g, p) - best_m1) < 1e-9]
    if len(cand) > 1:
        tie_path.append(f"tie on M1 among {len(cand)} pairs -> lexicographic method name")
        cand = [min(cand, key=lambda p: (p[0], p[1]))]
    chosen = cand[0] if cand else PAIRS[0]

    mx_keys = sorted({r["stratum_key"] for r in rows
                      if r["metric"] == "M2" and r["stratum"] == "model_x_noise"})
    agree = 0
    per_layer = {}
    for k in mx_keys:
        d = {(r["method_a"], r["method_b"]): r for r in rows
             if r["metric"] == "M2" and r["stratum"] == "model_x_noise" and r["stratum_key"] == k}
        if not d:
            continue
        bk = max(val(d, p) for p in PAIRS)
        top = [p for p in PAIRS if abs(val(d, p) - bk) < 1e-9]
        per_layer[k] = {"top_pairs": [f"{x[0]}|{x[1]}" for x in top], "value": bk}
        if chosen in top:
            agree += 1

    # ── 写出
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "complementarity.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    prereg = out_dir / "preregistration.md"
    sel = {
        "preregistration_sha256": hashlib.sha256(prereg.read_bytes()).hexdigest().upper(),
        "rule": "M2 global median max; tie -> M1; tie -> lexicographic",
        "tie_resolution_path": tie_path,
        "chosen_pair": [chosen[0], chosen[1]],
        "chosen_m2_global": val(glob, chosen),
        "chosen_m1_global": val(m1g, chosen),
        "ranking_by_m2_global": [{"pair": f"{p[0]}|{p[1]}", "M2": val(glob, p), "M1": val(m1g, p)}
                                 for p in sorted(PAIRS, key=lambda p: -val(glob, p))],
        "thresholds_tau_ij": {f"{a}|{b}": thresholds[(a, b)] for (a, b) in PAIRS},
        "robustness_model_x_noise": {
            "chosen_is_top_in": f"{agree}/{len(mx_keys)}",
            "per_layer": per_layer,
            "note": "分层仅作描述，**不改变选择**（预注册 5.2-4）",
        },
        "determinism": "no random component (deterministic by construction)",
        "rows": len(rows), "expected_rows": expected, "stratum_keys": n_keys,
    }
    # **显式 LF**：`Path.write_text` 在 Windows 会把 \n 翻成 \r\n，破坏仓库纯 LF 约定。
    with (out_dir / "pair_selection.json").open("w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(sel, ensure_ascii=False, indent=2))
    return sel


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="P3.1 互补性量化（只读输入；不实现融合）")
    ap.add_argument("--out", default="results/complementarity")
    a = ap.parse_args(argv)
    sel = run(Path(a.out))
    print(json.dumps({k: sel[k] for k in ("chosen_pair", "chosen_m2_global", "rows",
                                          "expected_rows", "stratum_keys",
                                          "robustness_model_x_noise")},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
