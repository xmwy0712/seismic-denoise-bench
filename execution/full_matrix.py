"""P2.2 全矩阵运行器（本地/云端同一份代码；**云上不得改动**）。

用法
----
::

    python execution/full_matrix.py --out results --methods fk_filter
    python execution/full_matrix.py --out results --limit 1 --dry-run

纪律（对应 P2.2 任务单第三节）
------------------------------
* **顺序确定性**：按 config_matrix 轴顺序遍历（models → noise → levels → f_main → seeds）。
* **逐格登记**：config_id / seed / method / wall_time_ms / y_hat SHA256 / ΔSNR / Lsig / CNA / 事件级指标。
* **y_hat 本体**存 ``results/``（.npy），另写 ``manifest.csv``（SHA256 索引，缺件可检出）。
* **失败即记录并继续**：不得静默跳过、不得重试到成功；失败率 > 5% 触发停机标志。
* **不调参**：方法参数一律取 ``methods_registry.yaml`` 登记值；本运行器**不提供**任何调参入口。
* **不选方法（R-CLI，P2.2-Am1 第四节）**：``--methods`` 已**废止**（传入即报错退出）；
  方法集**恒为全集** ``METHODS``。官方运行命令**唯一**：
  ``python execution/full_matrix.py --out results``。
  理由：允许子集运行 = **选择性运行的后门**（只跑好看的方法 = 选择性报告），与禁止调参同类。
* **进度留痕**：每完成 1/10 打印一行（供 execution-log 抄录）。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from bench.data import synthetic as S          # noqa: E402
from bench.data.ricker import ricker           # noqa: E402
# **显式子模块导入**：包 __init__ 把 `lsig` 重导出为**函数**，会遮蔽同名子模块，
# 故不得用 `from bench.metrics import lsig as LSIG`（那会拿到函数）。
from bench.metrics.lsig import event_mask, lsig as lsig_value      # noqa: E402
from bench.metrics.snr import delta_snr_db                          # noqa: E402
from bench.metrics.cna import build_subspace, cna_db as cna_value   # noqa: E402
from bench.metrics.events import event_metrics                      # noqa: E402
from bench.methods import METHODS, load_method  # noqa: E402

FAILURE_RATE_STOP = 0.05          # 失败率 > 5% 停机报告


def sha256_of(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a, dtype=np.float64).tobytes()).hexdigest().upper()


def build_matrix(cfg: dict) -> list[dict]:
    """按 config_matrix 轴顺序展开 54 配置（不含种子）。"""
    acq = cfg["acquisition"]
    noise_levels = cfg["noise_levels"]
    n2_vapps = (cfg["matrix"]["param_slots"].get("n2_v_app_m_s") or [None])
    out: list[dict] = []
    for model in cfg["models"]:
        for noise in cfg["noise_types"]:
            # **N2 亦有 3 档**：其 level 槽位由 param_slots.n2_v_app_m_s 承担
            # （L1/L2/L3 依次对应 800/1500/3000）——见 configs/frozen.yaml item_01
            # 的 n2_level_slot_interpretation。故 N2 同样遍历 3 档 => 2x3x3x3 = 54 配置。
            for lv_idx, lv in enumerate(noise_levels):
                for f_main in cfg["wavelet"]["f_main_hz"]:
                    out.append({
                        "model": model, "noise": noise, "level": lv, "f_main": float(f_main),
                        "acq": acq,
                        "n2_v_app": (n2_vapps[lv_idx] if noise["id"] == "N2" else None),
                    })
    return out


def config_id(model_id: str, noise_id: str, level_id: str, f_main: float) -> str:
    return f"{model_id}_{noise_id}_{level_id}_{int(f_main)}Hz"


def make_observation(entry: dict, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """返回 (clean, noisy, nc)。nc = 注入的相干噪声分量（非相干噪声时为全零数组）。"""
    acq = entry["acq"]
    dt, dx, ns, ntr = float(acq["dt_s"]), float(acq["dx_m"]), int(acq["n_samples"]), int(acq["n_traces"])
    f_main = entry["f_main"]
    _t, w = ricker(f_main, dt, ns)
    rng = np.random.default_rng(seed)

    if entry["model"]["id"] == "M1":
        mp = entry["model"]["params"]
        refl = S.reflectivity(int(mp["n_layers"]), rng, sparsity=float(mp["sparsity"]))
        clean = S.forward(refl, w, n_traces=ntr)[:ns, :]
    else:
        # **尺寸键必须全部从登记参数中剔除**：M2 的 params 里同时含 `n_samples` 与
        # `n_traces`，若只剔除其中一个，再显式传同名关键字即 `got multiple values`
        # （Run 1 的 135 例失败即此因）。统一：登记参数只供**非尺寸**超参。
        mp = dict(entry["model"]["params"])
        for k in ("n_samples", "n_traces"):
            mp.pop(k, None)
        field = S.reflectivity_structure(rng=rng, n_samples=ns, n_traces=ntr, **mp)
        clean = S.forward_structure(field, w, trace_stride=1)[:ns, :]

    nid = entry["noise"]["id"]
    nrng = np.random.default_rng(seed + 90000)
    if nid == "N1":
        band = tuple(entry["noise"]["params"]["band_hz"])
        ratio = float(entry["level"]["amplitude_ratio"])
        noisy = S.add_band_limited_noise(clean, nrng, band=band, dt=dt, amplitude=ratio)
        nc = np.zeros_like(clean)
    elif nid == "N2":
        p = entry["noise"]["params"]
        v = entry["n2_v_app"] or p["v_app_m_s"][0]
        noisy = S.add_linear_coherent(clean, v, dt, dx, nrng, f_main=float(p["f_main_hz"]))
        nc = noisy - clean
    else:
        p = entry["noise"]["params"]
        ratio = float(entry["level"]["amplitude_ratio"])
        fz = yaml.safe_load((REPO / "configs" / "frozen.yaml").read_text(encoding="utf-8"))
        fm_ = fz["item_05_dispersive_surface_wave"]["model"]
        noisy = S.add_dispersive_surface_wave(
            clean, dt, dx, nrng, v_model=p["v_model"], v0=p["v0"], c=p["c"],
            a=float(fm_["a"]), b=float(fm_["b"]), f_lo=p["f_lo_hz"], f_hi=p["f_hi_hz"],
            amplitude=ratio, n_components=int(p["n_components"]))
        nc = noisy - clean
    return clean, noisy, nc


def time_windows_from_mask(mask: np.ndarray) -> list[tuple[int, int]]:
    """把布尔掩码压成**时间窗**列表（连续超阈行段），供事件级指标使用。"""
    rows = mask.any(axis=1)
    wins, start = [], None
    for i, v in enumerate(rows):
        if v and start is None:
            start = i
        elif not v and start is not None:
            wins.append((start, i))
            start = None
    if start is not None:
        wins.append((start, rows.size))
    return wins


def run_matrix(out_dir: Path, method_names: list[str], limit: int | None, dry_run: bool) -> dict:
    cfg = yaml.safe_load((REPO / "configs" / "config_matrix.yaml").read_text(encoding="utf-8"))
    reg = yaml.safe_load((REPO / "configs" / "methods_registry.yaml").read_text(encoding="utf-8"))
    reg_params = {m["name"]: {k: v["value"] for k, v in m["key_params"].items()}
                  for m in reg["methods"]}
    seeds = list(cfg["matrix"]["seeds"])
    entries = build_matrix(cfg)
    cells = [(e, s) for e in entries for s in seeds]
    if limit is not None:
        cells = cells[:limit]

    _prechecked: set[str] = set()

    # **预检（fail fast）**：在进入长循环前，每模型各构造一个观测。
    # Run 1 的教训：数据构造 bug 直到第 676 格（M2 首格）才暴露，白跑 200 s。
    for _e in entries:
        _mid = _e["model"]["id"]
        if _mid in _prechecked:
            continue
        make_observation(_e, seeds[0])
        _prechecked.add(_mid)
    print(f"[preflight] 预检通过：模型 {sorted(_prechecked)} 均可构造观测", flush=True)

    total = len(cells) * len(method_names)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    failures: list[dict] = []
    done = 0
    report_every = max(1, total // 10)
    t_start = time.perf_counter()

    for entry in entries:
        for seed in seeds:
            if limit is not None and (entry, seed) not in cells:
                continue
            cid = config_id(entry["model"]["id"], entry["noise"]["id"],
                            entry["level"]["id"] if entry["level"] else "NA", entry["f_main"])
            try:
                clean, noisy, nc = make_observation(entry, seed)
                mask = event_mask(clean, f_main=entry["f_main"], dt=float(entry["acq"]["dt_s"]),
                                       threshold=0.5 * float(np.max(np.abs(clean))))
                wins = time_windows_from_mask(mask)
                nc_energy = float(np.sum(nc ** 2))
                sub = build_subspace([nc], rank_tol=1e-8) if nc_energy > 0 else None
            except Exception as exc:                                   # noqa: BLE001
                failures.append({"config_id": cid, "seed": seed, "method": "<data>",
                                 "error": f"{type(exc).__name__}: {exc}"})
                done += len(method_names)
                continue

            for name in method_names:
                t0 = time.perf_counter()
                try:
                    mod = load_method(name)
                    params = dict(mod.PARAMS_DEFAULT)
                    params.update(reg_params.get(name, {}))       # 登记值覆盖默认（仍无调参入口）
                    y = mod.run(noisy, params, np.random.default_rng(seed))
                    dt_ms = (time.perf_counter() - t0) * 1000.0
                    if y.shape != noisy.shape:
                        raise ValueError(f"形状不一致 {y.shape} != {noisy.shape}")
                    if not np.all(np.isfinite(y)):
                        raise ValueError("输出含非有限值")
                    ds = delta_snr_db(clean, noisy, y)
                    lv = lsig_value(clean, y, mask)
                    res = y - clean
                    cn = (cna_value(nc, res, sub) if sub is not None else None)
                    ev = event_metrics(clean, y, wins, dt=float(entry["acq"]["dt_s"]))
                    fname = f"{cid}_{seed}_{name}.npy"
                    if not dry_run:
                        np.save(out_dir / fname, y)
                    rows.append({
                        "config_id": cid, "seed": seed, "method": name,
                        "wall_time_ms": round(dt_ms, 3), "y_hat_sha256": sha256_of(y),
                        "y_hat_file": (fname if not dry_run else ""),
                        "delta_snr_db": ds, "lsig": lv, "cna_db": cn,
                        "n_event_windows": len(wins),
                        "event_timing_median_ms": getattr(ev, "timing_median_ms", None),
                        "event_timing_max_ms": getattr(ev, "timing_max_ms", None),
                        "event_energy_median": getattr(ev, "energy_median", None),
                        "event_energy_max": getattr(ev, "energy_max", None),
                    })
                except Exception as exc:                               # noqa: BLE001
                    failures.append({"config_id": cid, "seed": seed, "method": name,
                                     "error": f"{type(exc).__name__}: {exc}"})
                done += 1
                if done % report_every == 0:
                    print(f"[progress] {done}/{total} cells "
                          f"({done/total:.0%}) elapsed={time.perf_counter()-t_start:.1f}s "
                          f"failures={len(failures)}", flush=True)

    rate = len(failures) / max(done, 1)
    summary = {
        "cells_attempted": done, "cells_ok": len(rows), "failures": len(failures),
        "failure_rate": round(rate, 6), "stop_threshold": FAILURE_RATE_STOP,
        "stop_flag": rate > FAILURE_RATE_STOP,
        "methods": method_names, "methods_source": "bench.methods.METHODS (全集，无子集入口)",
        "seeds": seeds, "entries": len(entries),
        "elapsed_s": round(time.perf_counter() - t_start, 3), "dry_run": dry_run,
    }
    if rows:
        with (out_dir / "metrics.csv").open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    (out_dir / "manifest.json").write_text(
        json.dumps({"summary": summary, "failures": failures}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    # **R-CLI（P2.2-Am1 第四节）：官方运行命令固定，无方法选择开关。**
    # `--methods` 已**移除** —— 允许子集运行 = 选择性运行的后门（只跑好看的方法 = 选择性报告），
    # 与"禁止调参"属同一类风险。**方法集恒为 METHDOS 全集。**
    ap = argparse.ArgumentParser(
        description="P2.2 全矩阵运行器（官方命令：python execution/full_matrix.py --out results）")
    ap.add_argument("--out", default="results")
    ap.add_argument("--limit", type=int, default=None,
                    help="【验证专用】仅前 N 个观测；官方运行禁用（守卫断言 metrics 行数即拦住）")
    ap.add_argument("--dry-run", action="store_true",
                    help="【验证专用】不落 y_hat 文件；官方运行禁用")
    ap.add_argument("--methods", nargs="*",
                    help="【已废止】传入即报错退出（保留此参数仅为给出明确报错，而非静默忽略）")
    a = ap.parse_args(argv)

    if a.methods is not None:
        raise SystemExit(
            "R-CLI 违规：`--methods` 已废止（P2.2-Am1 第四节）。\n"
            "  理由：允许子集运行 = 选择性运行的后门，与禁止调参同类风险。\n"
            "  官方运行命令：python execution/full_matrix.py --out results\n"
            f"  方法集恒为全集：{list(METHODS)}")

    s = run_matrix(Path(a.out), list(METHODS), a.limit, a.dry_run)
    print(json.dumps(s, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
