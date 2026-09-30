"""P5.4 · WS1：10 配对全跑 + 两消融（**事后扩展；规则冻结一字不改**）。

官方命令::

    python execution/fusion10_matrix.py --mode both --out10 results/fusion10 \
        --out-ab results/fusion_ablation

硬约束
------
* **规则不改**：全部调用 `bench.fusion.fuse`（冻结实现），参数与 P3.2 官方运行**逐项一致**。
* **确定性交叉核验**：主配对与稳健性对照共 1620 格的 `y_fused_sha256`
  必须与 `results/fusion/metrics.csv` **逐格一致**；不一致 ⇒ 汇总里 `cross_check_ok=False`。
* 消融复用**同一实现**的 `_stft/_istft/_lateral_coherence`（同一代码路径，仅去掉相应项）。
* 真值 `s` 只用于指标计算，**从不进入融合**。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "execution"))

import fusion_matrix as FM                                    # noqa: E402  复用观测构造（同源）
from bench.fusion import fuse                                  # noqa: E402
from bench.fusion.fusion import (_istft, _lateral_coherence,    # noqa: E402
                                 _stft, P_COHERENCE_POWER)
from bench.metrics.lsig import event_mask, lsig                # noqa: E402
from bench.metrics.snr import delta_snr_db                     # noqa: E402
from bench.metrics.cna import build_subspace, cna_db           # noqa: E402
from bench.metrics.events import event_metrics                 # noqa: E402

METHODS = ("fk_filter", "fx_deconv", "wavelet_threshold", "ssa_decomposition", "svd_lowrank")
PAIRS10 = list(itertools.combinations(METHODS, 2))             # C(5,2) = 10
GAMMAS = (0.4, 0.5, 0.6)
PREREG_ROLE = {("fx_deconv", "wavelet_threshold"): "primary",
               ("fx_deconv", "svd_lowrank"): "secondary"}
KINDS = ("fusion", "ablation_equal", "ablation_c2")


def sha256_of(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a, dtype=np.float64).tobytes()).hexdigest().upper()


def fuse_equal(y_i: np.ndarray, y_j: np.ndarray, n_t: int) -> np.ndarray:
    """消融①：等权平均（STFT 域 nu = 0.5，复用同一正逆变换）。"""
    starts, zi = _stft(y_i, n_t)
    _s, zj = _stft(y_j, n_t)
    return _istft(0.5 * zi + 0.5 * zj, starts, y_i.shape[0], n_t)


def fuse_c2(y_i: np.ndarray, y_j: np.ndarray, n_t: int) -> np.ndarray:
    """消融②：纯 C² 加权（**去掉 (1-gamma*s) 压制项**），退化规则同冻结件。"""
    starts, zi = _stft(y_i, n_t)
    _s, zj = _stft(y_j, n_t)
    wi = _lateral_coherence(zi) ** P_COHERENCE_POWER
    wj = _lateral_coherence(zj) ** P_COHERENCE_POWER
    tot = wi + wj
    degen = tot <= 0.0
    nu_i = np.where(degen, 0.5, wi / np.where(degen, 1.0, tot + 1e-12))
    nu_j = np.where(degen, 0.5, wj / np.where(degen, 1.0, tot + 1e-12))
    return _istft(nu_i * zi + nu_j * zj, starts, y_i.shape[0], n_t)


def load_prereg_hashes() -> dict:
    out = {}
    p = REPO / "results" / "fusion" / "metrics.csv"
    with p.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            out[(r["config_id"], r["seed"], r["role"], r["gamma"])] = r["y_fused_sha256"]
    return out


def run(mode: str, out10: Path, out_ab: Path, limit: int | None = None) -> dict:
    fz = FM.load_frozen_v2()
    cfgs = FM.build_configs(fz)
    seeds = [int(s) for s in fz["item_01_synthetic_matrix"]["seeds"]]
    dt = float(fz["item_02_model_m1"]["dt_s"])
    n_t_map = {r["f_main_hz"]: int(r["n_T_int"])
               for r in fz["item_06_mask_and_event_window"]["n_T_per_config"]}
    v_lo = fz["item_05_dispersive_surface_wave"]["dispersion_v_band_mps"][0]
    band = tuple(fz["item_05_dispersive_surface_wave"]["frequency_band_hz"])

    obs = [(c, s) for c in cfgs for s in seeds]
    if limit is not None:
        obs = obs[:limit]
    prereg = load_prereg_hashes() if mode in ("ten", "both") else {}

    rows, failures = [], []
    cross_mismatch, cross_checked = [], 0
    t0 = time.perf_counter()
    total = len(obs) * len(PAIRS10) * (len(GAMMAS) if mode in ("ten", "both") else 2)
    done, step = 0, max(1, total // 10)

    for cfg, seed in obs:
        cid = FM.config_id(cfg)
        s, x = FM.make_observation(cfg, seed)
        n_t = n_t_map[cfg["f_main"]]
        mask = event_mask(s, f_main=cfg["f_main"], dt=dt,
                          threshold=0.5 * float(np.max(np.abs(s))))
        wins = FM.time_windows(mask)
        ys = {}
        for m in METHODS:
            f = REPO / "results" / f"{cid}_{seed}_{m}.npy"
            if not f.exists():
                failures.append({"config_id": cid, "seed": seed, "method": m,
                                 "error": "missing y_hat"})
                continue
            ys[m] = np.load(f)
        if len(ys) != len(METHODS):
            done += len(PAIRS10) * len(GAMMAS)
            continue

        nc = np.zeros_like(s) if cfg["noise"]["id"] == "N1" else (x - s)
        sub = build_subspace([nc], rank_tol=1e-8) if float(np.sum(nc ** 2)) > 0 else None

        for (mi, mj) in PAIRS10:
            yi, yj = ys[mi], ys[mj]
            role = PREREG_ROLE.get((mi, mj), "")
            tasks = []
            if mode in ("ten", "both"):
                tasks += [("fusion", g) for g in GAMMAS]
            if mode in ("ablation", "both"):
                tasks += [("ablation_equal", None), ("ablation_c2", None)]
            for kind, g in tasks:
                try:
                    if kind == "fusion":
                        yf = fuse(yi, yj, {"n_t": n_t, "gamma": g, "x": x,
                                           "v_lo_m_s": v_lo, "band_hz": band, "dt": dt})
                        b_used = bool(getattr(fuse, "last_b_enabled", False))
                    elif kind == "ablation_equal":
                        yf = fuse_equal(yi, yj, n_t)
                        b_used = None
                    else:
                        yf = fuse_c2(yi, yj, n_t)
                        b_used = None
                    if yf.shape != s.shape:
                        raise ValueError(f"形状 {yf.shape} != {s.shape}")
                    if not np.all(np.isfinite(yf)):
                        raise ValueError("含非有限值")
                    ds = delta_snr_db(s, x, yf)
                    lv = lsig(s, yf, mask)
                    cn = cna_db(nc, yf - s, sub) if sub is not None else None
                    ev = event_metrics(s, yf, wins, dt=dt)
                    h = sha256_of(yf)
                    if kind == "fusion" and role:
                        cross_checked += 1
                        k = (cid, str(seed), role, str(g))
                        exp = prereg.get(k)
                        if exp is not None and exp != h:
                            cross_mismatch.append({"key": k, "expected": exp, "got": h})
                    outdir = out10 if kind == "fusion" else out_ab
                    outdir.mkdir(parents=True, exist_ok=True)
                    fn = (f"{cid}_{seed}_{mi}-{mj}_g{g:.1f}.npy" if kind == "fusion"
                          else f"{cid}_{seed}_{mi}-{mj}_{kind}.npy")
                    np.save(outdir / fn, yf)
                    rows.append({"kind": kind, "config_id": cid, "seed": seed,
                                 "role": role, "gamma": ("" if g is None else g),
                                 "pair_i": mi, "pair_j": mj,
                                 "y_sha256": h, "y_file": fn,
                                 "delta_snr_db": ds, "lsig": lv, "cna_db": cn,
                                 "n_event_windows": len(wins),
                                 "event_timing_median_ms": getattr(ev, "timing_median_ms", None),
                                 "event_energy_median": getattr(ev, "energy_median", None),
                                 "x_missing": (None if b_used is None else (not b_used))})
                except Exception as exc:                          # noqa: BLE001
                    failures.append({"config_id": cid, "seed": seed, "pair": [mi, mj],
                                     "kind": kind, "gamma": g,
                                     "error": f"{type(exc).__name__}: {exc}"})
                done += 1
                if done % step == 0:
                    print(f"[progress] {done}/{total} ({done/total:.0%}) "
                          f"elapsed={time.perf_counter()-t0:.1f}s fails={len(failures)}",
                          flush=True)

    for outdir in {out10, out_ab}:
        sub_rows = [r for r in rows if (r["kind"] == "fusion") == (outdir == out10)]
        if sub_rows:
            with (outdir / "metrics.csv").open("w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(sub_rows[0].keys()), lineterminator="\n")
                w.writeheader()
                w.writerows(sub_rows)
    summary = {
        "mode": mode, "cells": done, "rows": len(rows), "failures": len(failures),
        "elapsed_s": round(time.perf_counter() - t0, 3),
        "pairs": [list(p) for p in PAIRS10], "gammas": list(GAMMAS),
        "cross_check_cells": cross_checked,
        "cross_check_mismatches": len(cross_mismatch),
        "cross_check_ok": (cross_checked > 0 and not cross_mismatch) if mode in ("ten", "both") else None,
        "cross_check_detail": cross_mismatch[:5],
        "expected_cells": {"ten": 270 * 10 * 3, "ablation": 270 * 10 * 2},
    }
    for outdir in {out10, out_ab}:
        outdir.mkdir(parents=True, exist_ok=True)
        with (outdir / "run_manifest.json").open("w", encoding="utf-8", newline="") as fh:
            fh.write(json.dumps({"summary": summary, "failures": failures},
                                ensure_ascii=False, indent=2))
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="P5.4 WS1 · 10 配对 + 消融")
    ap.add_argument("--mode", choices=("ten", "ablation", "both"), default="both")
    ap.add_argument("--out10", default="results/fusion10")
    ap.add_argument("--out-ab", default="results/fusion_ablation")
    ap.add_argument("--limit", type=int, default=None,
                    help="【验证专用】仅前 N 个观测；官方运行不得使用")
    a = ap.parse_args(argv)
    s = run(a.mode, REPO / a.out10, REPO / a.out_ab, a.limit)
    print(json.dumps(s, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
