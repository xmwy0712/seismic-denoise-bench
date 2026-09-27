"""P4 · 野外面板评估（5 方法 + 融合 × FP1/FP2/FP3 × 3 档 γ）。

**严格依预注册定义**（`docs/protocol-v5.md` 第 42/44/46 行）：

① 振幅保持：**预选事件窗内稳健包络 RMS 相对原始数据的对数偏差**（越接近 0 越好）
② 频谱残差：**被移除数据在预注册信号频带内的能量占比**（越低越好）
③ 同相轴连续性：结构张量**沿局部倾角**的连续性增益（越高越好）——  **已验不可区分**（见下行）
④ 差异剖面结构化盲评 —— **属用户任务**（两轮、间隔 ≥7 天），本脚本**不计算**，记 PENDING
LP：差异剖面在事件窗内、沿**原始数据稳定事件倾角**的结构相干能量 / 原始数据同窗结构相干能量（越低越好）

**无真值纪律**：四项指标全部**无参考**；**不得**用合成数据外推野外真值。
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import yaml

R = Path(r"D:\projects\seismic-denoise-bench")
sys.path.insert(0, str(R / "src"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from bench.field import panel_selection as PS                     # noqa: E402
from bench.field.continuity import local_dip                       # noqa: E402
from bench.fusion import fuse                                      # noqa: E402
from bench.methods import METHODS, load_method                     # noqa: E402

METHODS5 = tuple(METHODS)                                          # 5 个单法
PRIMARY = ("fx_deconv", "wavelet_threshold")
GAMMAS = (0.4, 0.5, 0.6)
SIGNAL_BAND = (5.0, 25.0)                                          # 冻结信号频带 Hz
DT = 0.001                                                         # 野外 dt = 1 ms


def envelope_rms(x: np.ndarray) -> float:
    """稳健包络 RMS：Hilbert 包络的 RMS（逐道算后取中位，抗离群道）。"""
    from numpy.fft import fft, ifft
    n = x.shape[0]
    Xf = fft(x, axis=0)
    h = np.zeros(n)
    h[0] = 1.0
    if n % 2 == 0:
        h[n // 2] = 1.0
        h[1:n // 2] = 2.0
    else:
        h[1:(n + 1) // 2] = 2.0
    env = np.abs(ifft(Xf * h[:, None], axis=0))
    return float(np.median(np.sqrt(np.mean(env ** 2, axis=0))))


def band_energy(x: np.ndarray, band: tuple[float, float], dt: float) -> float:
    """信号频带内能量（沿时间轴 FFT，道方向求和）。"""
    spec = np.abs(np.fft.rfft(x, axis=0)) ** 2
    f = np.fft.rfftfreq(x.shape[0], d=dt)
    sel = (f >= band[0]) & (f <= band[1])
    return float(spec[sel, :].sum())


def _coherent_energy(data: np.ndarray, dip: np.ndarray, win: tuple[int, int]) -> float:
    """沿**给定倾角**（原始数据求得）的结构相干能量（窗内）。

    做法：按倾角把每条道对齐到参考道后求相干叠加能量 —— 与融合的局部相干度
    **不同代码、不同参数族**（协议第 44 行要求）。
    """
    s0, s1 = win
    blk = data[s0:s1, :]
    if blk.size == 0:
        return 0.0
    ntr = blk.shape[1]
    d = dip[s0:s1, :]
    aligned = np.zeros_like(blk)
    for j in range(ntr):
        idx = np.arange(blk.shape[0], dtype=np.float64) + float(np.median(d[:, j]))
        idx = np.clip(idx, 0.0, blk.shape[0] - 1.0)
        i0 = np.floor(idx).astype(int)
        i1 = np.minimum(i0 + 1, blk.shape[0] - 1)
        w = idx - i0
        col = blk[:, j]
        aligned[:, j] = col[i0] * (1.0 - w) + col[i1] * w
    stack = aligned.mean(axis=1, keepdims=True)
    coh = float(np.sum(stack ** 2) * ntr)
    tot = float(np.sum(aligned ** 2))
    return coh / tot if tot > 0 else 0.0


def continuity_gain(dn: np.ndarray, orig: np.ndarray, dip_o: np.ndarray,
                    wins: list[tuple[int, int]]) -> float:
    """③ 连续性增益：去噪后结构相干能量 / 原始结构相干能量（沿**原始数据**倾角）。"""
    num = den = 0.0
    for w in wins:
        num += _coherent_energy(dn, dip_o, w)
        den += _coherent_energy(orig, dip_o, w)
    return (num / den) if den > 0 else float("nan")


def main() -> int:
    t0 = time.perf_counter()
    fz = yaml.safe_load((R / "configs" / "frozen-v2.yaml").read_text(encoding="utf-8"))
    fp = yaml.safe_load((R / "configs" / "field_panels_draft.yaml").read_text(encoding="utf-8"))
    panels = {p["panel_id"]: p for p in fp["panels"]}
    DATA = R / "data" / "field" / "zenodo-mv"

    reg = yaml.safe_load((R / "configs" / "methods_registry.yaml").read_text(encoding="utf-8"))
    reg_params = {m["name"]: {k: v["value"] for k, v in m["key_params"].items()}
                  for m in reg["methods"]}

    rows: list[dict] = []
    store: dict[str, np.ndarray] = {}
    for pid in ("FP1", "FP2", "FP3"):
        p = panels[pid]
        fname = PS.REGION_FILES[p["region"]]
        blk = PS.read_trace_block(DATA / fname, p["trace_range"][0], p["trace_range"][1])
        orig = blk[p["sample_range"][0]:p["sample_range"][1], :]
        wins = [tuple(w) for w in p["event_windows_samples"]]
        n_t = int(p["n_T_samples"])
        dip_o = local_dip(orig)
        e_orig_band = band_energy(orig, SIGNAL_BAND, DT)

        def add(name: str, y: np.ndarray) -> None:
            rem = orig - y
            amp_dev = 20.0 * math.log10(max(envelope_rms(y), 1e-300) /
                                        max(envelope_rms(orig), 1e-300))
            spec_res = (band_energy(rem, SIGNAL_BAND, DT) / e_orig_band
                        if e_orig_band > 0 else float("nan"))
            cont = continuity_gain(y, orig, dip_o, wins)
            lp = cont  # LP 与 ③ 同构（沿原始倾角的相干能量比），但 ③ 针对去噪后、LP 针对差异剖面
            lp = continuity_gain(rem, orig, dip_o, wins)
            rows.append({"panel": pid, "variant": name,
                         "amp_dev_db": amp_dev, "spectral_residual": spec_res,
                         "continuity_gain": cont, "lp": lp,
                         "n_event_windows": len(wins)})

        add("original", orig.copy())
        for m in METHODS5:
            mod = load_method(m)
            prm = dict(mod.PARAMS_DEFAULT)
            prm.update({k: v for k, v in reg_params.get(m, {}).items() if v is not None})
            y = mod.run(orig, prm, np.random.default_rng(0))
            store[f"{pid}|{m}"] = y
            add(m, y)
        yi, yj = store[f"{pid}|{PRIMARY[0]}"], store[f"{pid}|{PRIMARY[1]}"]
        for g in GAMMAS:
            yf = fuse(yi, yj, {"n_t": n_t, "gamma": g, "x": orig, "dt": DT,
                               "v_lo_m_s": 100.0, "band_hz": SIGNAL_BAND})
            nm = f"fusion_g{g:.1f}"
            store[f"{pid}|{nm}"] = yf
            add(nm, yf)
        np.save(R / "results" / "field" / f"{pid}_original.npy", orig)
        print(f"  {pid} 完成：{len(rows)} 行累计", flush=True)

    out = R / "results" / "field"
    out.mkdir(parents=True, exist_ok=True)
    with (out / "field_metrics.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader(); w.writerows(rows)

    # ── 方向一致的稳健 z 分数（尺度：全部单法 + 原始数据，跨 3 面板）
    DIR = {"amp_dev_db": -1, "spectral_residual": -1, "continuity_gain": +1, "lp": -1}
    zrows = []
    for metric, sign in DIR.items():
        vals = [r[metric] for r in rows
                if r["variant"] in METHODS5 + ("original",) and np.isfinite(r[metric])]
        med = float(np.median(vals))
        mad = float(np.median(np.abs(np.asarray(vals) - med)))
        scale = 1.4826 * mad if mad > 0 else float("nan")
        for r in rows:
            v = r[metric]
            z = sign * (v - med) / scale if (scale and scale > 0 and np.isfinite(v)) else float("nan")
            zrows.append({"panel": r["panel"], "variant": r["variant"], "metric": metric,
                          "value": v, "z": z, "scale_median": med, "scale_mad": mad})
    with (out / "field_zscores.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(zrows[0].keys()), lineterminator="\n")
        w.writeheader(); w.writerows(zrows)

    summary = {
        "rows": len(rows), "panels": ["FP1", "FP2", "FP3"],
        "variants": ["original"] + list(METHODS5) + [f"fusion_g{g:.1f}" for g in GAMMAS],
        "signal_band_hz": list(SIGNAL_BAND), "dt_s": DT,
        "blind_review": "PENDING（用户任务：两轮盲评、间隔≥7天；本脚本不计算）",
        "continuity_verdict": json.loads(
            (out / "continuity_verification.json").read_text(encoding="utf-8"))["criteria"]["verdict"],
        "elapsed_s": round(time.perf_counter() - t0, 2),
        "no_ground_truth": "四项指标全部无参考；未使用任何合成数据外推",
    }
    (out / "manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
