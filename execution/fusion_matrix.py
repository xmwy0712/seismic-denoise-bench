"""P3.2 阶段 2 · 融合运行器（**云上/本地同一份代码**）。

官方命令::

    python execution/fusion_matrix.py --out results/fusion

**硬约束**：融合函数 ``bench.fusion.fuse`` **只接收** ``(y_i, y_j, params)``；
真值 ``s`` **只用于指标计算**，**从不进入融合**。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from bench.data import synthetic as S                      # noqa: E402
from bench.data.ricker import ricker                       # noqa: E402
from bench.fusion import fuse                              # noqa: E402
from bench.metrics.lsig import event_mask, lsig            # noqa: E402
from bench.metrics.snr import delta_snr_db                 # noqa: E402
from bench.metrics.cna import build_subspace, cna_db       # noqa: E402
from bench.metrics.events import event_metrics             # noqa: E402

PAIRS = {
    "primary": ("fx_deconv", "wavelet_threshold"),
    "secondary": ("fx_deconv", "svd_lowrank"),
}
GAMMAS = (0.4, 0.5, 0.6)
FAILURE_RATE_STOP = 0.05
STRATA = ("global", "model", "noise", "gamma")


def sha256_of(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a, dtype=np.float64).tobytes()).hexdigest().upper()


def load_frozen_v2() -> dict:
    return yaml.safe_load((REPO / "configs" / "frozen-v2.yaml").read_text(encoding="utf-8"))


def build_configs(fz: dict) -> list[dict]:
    it01, it02, it03 = (fz["item_01_synthetic_matrix"], fz["item_02_model_m1"],
                        fz["item_03_model_m2"])
    it04, it05, sup = (fz["item_04_noise_levels"], fz["item_05_dispersive_surface_wave"],
                       fz["item_04_supplement"])
    acq = {"dt_s": it02["dt_s"], "dx_m": it02["dx_m"],
           "n_samples": it02["n_samples"], "n_traces": it02["n_traces"]}
    ratios = it04["criterion_ii_descriptive"]["values"]
    n2v = [800.0, 1500.0, 3000.0]
    noises = [{"id": "N1", "params": {"band_hz": list(sup["n1_band_limited_random"]["band_hz"])}},
              {"id": "N2", "params": {"f_main_hz": float(sup["n2_linear_coherent"]["f_main_hz"]),
                                      "v_app_m_s": n2v}},
              {"id": "N3", "params": {"v_model": it05["model"]["v_model"], "v0": it05["model"]["v0"],
                                      "c": it05["model"]["c"], "a": it05["model"]["a"],
                                      "b": it05["model"]["b"], "f_lo_hz": it05["frequency_band_hz"][0],
                                      "f_hi_hz": it05["frequency_band_hz"][1],
                                      "n_components": it05["n_components"]}}]
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


def make_observation(cfg: dict, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """重建 ``(s, x)`` —— 与 P2.2 全矩阵同源。``s`` 仅供指标；``x`` 供融合的 ``b`` 子分。"""
    acq = cfg["acq"]
    dt, dx, ns, ntr = (float(acq["dt_s"]), float(acq["dx_m"]),
                       int(acq["n_samples"]), int(acq["n_traces"]))
    _t, w = ricker(cfg["f_main"], dt, ns)
    rng = np.random.default_rng(seed)
    if cfg["model"]["id"] == "M1":
        mp = cfg["model"]["params"]
        refl = S.reflectivity(int(mp["n_layers"]), rng, sparsity=float(mp["sparsity"]))
        s = S.forward(refl, w, n_traces=ntr)[:ns, :]
    else:
        mp = dict(cfg["model"]["params"])
        for k in ("n_samples", "n_traces"):
            mp.pop(k, None)
        field = S.reflectivity_structure(rng=rng, n_samples=ns, n_traces=ntr, **mp)
        s = S.forward_structure(field, w, trace_stride=1)[:ns, :]
    nid, nrng = cfg["noise"]["id"], np.random.default_rng(seed + 90000)
    if nid == "N1":
        x = S.add_band_limited_noise(s, nrng, band=tuple(cfg["noise"]["params"]["band_hz"]),
                                     dt=dt, amplitude=float(cfg["level"]["amplitude_ratio"]))
    elif nid == "N2":
        p = cfg["noise"]["params"]
        x = S.add_linear_coherent(s, cfg["n2_v_app"] or p["v_app_m_s"][0], dt, dx, nrng,
                                  f_main=float(p["f_main_hz"]))
    else:
        p = cfg["noise"]["params"]
        x = S.add_dispersive_surface_wave(s, dt, dx, nrng, v_model=p["v_model"], v0=p["v0"],
                                          c=p["c"], a=p["a"], b=p["b"], f_lo=p["f_lo_hz"],
                                          f_hi=p["f_hi_hz"],
                                          amplitude=float(cfg["level"]["amplitude_ratio"]),
                                          n_components=int(p["n_components"]))
    return s, x


def config_id(cfg: dict) -> str:
    return f'{cfg["model"]["id"]}_{cfg["noise"]["id"]}_{cfg["level"]["id"]}_{int(cfg["f_main"])}Hz'


def time_windows(mask: np.ndarray) -> list[tuple[int, int]]:
    rows, wins, start = mask.any(axis=1), [], None
    for i, v in enumerate(rows):
        if v and start is None:
            start = i
        elif not v and start is not None:
            wins.append((start, i)); start = None
    if start is not None:
        wins.append((start, rows.size))
    return wins


def run(out_dir: Path, limit: int | None = None) -> dict:
    fz = load_frozen_v2()
    cfgs = build_configs(fz)
    seeds = [int(s) for s in fz["item_01_synthetic_matrix"]["seeds"]]
    dt = float(fz["item_02_model_m1"]["dt_s"])
    n_t_map = {r["f_main_hz"]: int(r["n_T_int"])
               for r in fz["item_06_mask_and_event_window"]["n_T_per_config"]}
    v_lo = fz["item_05_dispersive_surface_wave"]["dispersion_v_band_mps"][0]
    band = tuple(fz["item_05_dispersive_surface_wave"]["frequency_band_hz"])

    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    failures: list[dict] = []
    obs = [(c, s) for c in cfgs for s in seeds]
    if limit is not None:                       # 【验证专用】仅前 N 个观测
        obs = obs[:limit]
    total = len(obs) * len(PAIRS) * len(GAMMAS)
    done, t0 = 0, time.perf_counter()
    step = max(1, total // 10)

    for cfg, seed in obs:
        cid = config_id(cfg)
        if True:
            s, x = make_observation(cfg, seed)
            n_t = n_t_map[cfg["f_main"]]
            mask = event_mask(s, f_main=cfg["f_main"], dt=dt,
                              threshold=0.5 * float(np.max(np.abs(s))))
            wins = time_windows(mask)
            for role, (mi, mj) in PAIRS.items():
                fi = REPO / "results" / f"{cid}_{seed}_{mi}.npy"
                fj = REPO / "results" / f"{cid}_{seed}_{mj}.npy"
                if not (fi.exists() and fj.exists()):
                    failures.append({"config_id": cid, "seed": seed, "role": role,
                                     "error": "missing y_hat"})
                    done += len(GAMMAS)
                    continue
                yi, yj = np.load(fi), np.load(fj)
                for g in GAMMAS:
                    try:
                        yf = fuse(yi, yj, {"n_t": n_t, "gamma": g, "x": x,
                                           "v_lo_m_s": v_lo, "band_hz": band, "dt": dt})
                        if yf.shape != s.shape:
                            raise ValueError(f"形状 {yf.shape} != {s.shape}")
                        if not np.all(np.isfinite(yf)):
                            raise ValueError("含非有限值")
                        ds = delta_snr_db(s, x, yf)
                        lv = lsig(s, yf, mask)
                        res = yf - s
                        # CNA 口径与 P2.2 一致：**相干噪声分量** nc。
                        # N1 为带限**随机**噪声 ⇒ 无相干分量 ⇒ nc 置零 ⇒ CNA = N/A
                        # （不得把随机噪声当相干噪声算 CNA；否则 N1 会得到无意义的值）。
                        if cfg["noise"]["id"] == "N1":
                            nc = np.zeros_like(s)
                        else:
                            nc = x - s
                        sub = build_subspace([nc], rank_tol=1e-8) if float(np.sum(nc ** 2)) > 0 else None
                        cn = cna_db(nc, res, sub) if sub is not None else None
                        ev = event_metrics(s, yf, wins, dt=dt)
                        fn = f"{cid}_{seed}_{role}_g{g:.1f}.npy"
                        np.save(out_dir / fn, yf)
                        rows.append({
                            "config_id": cid, "seed": seed, "role": role, "gamma": g,
                            "pair_i": mi, "pair_j": mj,
                            "wall_time_ms": None, "y_fused_sha256": sha256_of(yf),
                            "y_fused_file": fn,
                            "delta_snr_db": ds, "lsig": lv, "cna_db": cn,
                            "n_event_windows": len(wins),
                            "event_timing_median_ms": getattr(ev, "timing_median_ms", None),
                            "event_energy_median": getattr(ev, "energy_median", None),
                            "x_missing": (not bool(getattr(fuse, "last_b_enabled", False))),
                        })
                    except Exception as exc:                     # noqa: BLE001
                        failures.append({"config_id": cid, "seed": seed, "role": role,
                                         "gamma": g, "error": f"{type(exc).__name__}: {exc}"})
                    done += 1
                    if done % step == 0:
                        print(f"[progress] {done}/{total} ({done/total:.0%}) "
                              f"elapsed={time.perf_counter()-t0:.1f}s failures={len(failures)}",
                              flush=True)

    rate = len(failures) / max(done, 1)
    summary = {"cells_attempted": done, "cells_ok": len(rows), "failures": len(failures),
               "failure_rate": round(rate, 6), "stop_threshold": FAILURE_RATE_STOP,
               "stop_flag": rate > FAILURE_RATE_STOP,
               "expected_rows": 270 * len(PAIRS) * len(GAMMAS),
               "pairs": {k: list(v) for k, v in PAIRS.items()},
               "gammas": list(GAMMAS), "elapsed_s": round(time.perf_counter() - t0, 3),
               "x_missing_any": any(r["x_missing"] for r in rows)}
    if rows:
        with (out_dir / "metrics.csv").open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
            w.writeheader(); w.writerows(rows)
    with (out_dir / "manifest.json").open("w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps({"summary": summary, "failures": failures}, ensure_ascii=False, indent=2))
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="P3.2 融合矩阵（官方命令：--out results/fusion）")
    ap.add_argument("--out", default="results/fusion")
    ap.add_argument("--limit", type=int, default=None,
                    help="【验证专用】仅前 N 个观测；**官方运行不得使用**")
    ap.add_argument("--methods", nargs="*",
                    help="【已废止】传入即报错（防选择性运行后门，同 P2.2-Am1 R-CLI）")
    a = ap.parse_args(argv)
    if a.methods is not None:
        raise SystemExit(
            "R-CLI 违规：`--methods` 已废止（同 P2.2-Am1 第四节）。\n"
            "官方运行: python execution/fusion_matrix.py --out results/fusion")
    s = run(Path(a.out), a.limit)
    print(json.dumps(s, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
