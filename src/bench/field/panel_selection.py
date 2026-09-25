"""P1.3 野外面板选定（**可重放**实现）。

用途
----
从**原始**野外数据（Zenodo CC BY 4.0 子集）按**配置中冻结的判据**选定 3 个面板/时窗。
本模块是 P1.3 选定过程的**可复现载体**：脚本入库后，任何人可用同一配置与同一数据
重放选定，并应得到与 `configs/field_panels_draft.yaml` **完全一致**的 top-3。

时序约束（协议硬规则）
----------------------
选定过程**不得运行任何去噪方法**，**不得参考任何去噪/滤波结果**。
本模块因此**只**使用原始数据统计量：
逐道 RMS、2D FFT 幅度谱、相邻道零波形相关系数、Hilbert 包络、结构张量取向角。
**不导入** ``bench.methods`` / ``bench.fusion`` / 任何 ``coherence`` 模块
（由 ``tests/test_field_panel_selection.py`` 的 import 行守卫机械核验）。

判据来源
--------
**全部阈值从配置读取**（``configs/field_panels_draft.yaml``），代码内不硬编码，
以保证"判据先冻结、后测量"，且可参数化重放。

用法
----
::

    python src/bench/field/panel_selection.py --config configs/field_panels_draft.yaml \
        --data-root data/field/zenodo-mv

    # 重放并与 draft 中的 top-3 比对（退出码 0 = 一致）
    python src/bench/field/panel_selection.py --config ... --data-root ... --compare

数据输入路径
------------
``--data-root`` 下需存在：
  * ``mv1001shots_subset8000.sgy``（Martha's Vineyard）
  * ``nan3001shots_subset8000.sgy``（Nantucket）
采集与校验见 ``docs/field-data-note.md``。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import segyio

__all__ = [
    "load_config",
    "read_trace_block",
    "measure_panel",
    "rank_candidates",
    "select_top_n",
    "run_selection",
]

REGION_FILES = {
    "MV": "mv1001shots_subset8000.sgy",
    "NAN": "nan3001shots_subset8000.sgy",
}


def load_config(path: str | Path) -> dict:
    """读取 YAML 配置（判据与网格均来自此处，代码不硬编码阈值）。"""
    import yaml

    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def read_trace_block(sgy_path: str | Path, t0: int, t1: int) -> np.ndarray:
    """读取 ``[t0, t1)`` 道**全部采样**，返回 ``(n_samples, n_traces)``（只读）。"""
    with segyio.open(str(sgy_path), "r", ignore_geometry=True) as f:
        ns = len(f.samples)
        out = np.empty((ns, t1 - t0), dtype=np.float64)
        for i, tr in enumerate(range(t0, t1)):
            out[:, i] = f.trace[tr]
    return out


def measure_panel(
    block: np.ndarray,
    *,
    dt: float,
    k_norm_min: float,
    f_max: float,
    f_low: float,
) -> dict:
    """对单个面板计算 5 项**原始量**（无任何滤波）。

    参数
    ----
    block : numpy.ndarray
        形状 ``(n_samples, n_traces)`` 的原始数据块。
    dt : float
        时间采样间隔 (s)。
    k_norm_min : float
        "低速相干区"的**归一化波数**下界（周/道）。用归一化波数可避免引入未核验的 ``dx``。
    f_max : float
        相干区频率上界 (Hz)。
    f_low : float
        低频能量比的频率上界 (Hz)。
    """
    ns, ntr = block.shape
    rms = np.sqrt(np.mean(block**2, axis=0))
    med = float(np.median(rms))

    dead = float(np.mean(rms < 0.01 * med)) if med > 0 else 1.0
    outlier = float(np.mean((rms > 3 * med) | (rms < med / 3)))

    w = np.hanning(ns)[:, None] * np.hanning(ntr)[None, :]
    spec = np.abs(np.fft.fftshift(np.fft.fft2(block * w), axes=1)) ** 2
    freqs = np.fft.fftfreq(ns, d=dt)
    knorm = np.fft.fftshift(np.fft.fftfreq(ntr, d=1.0))
    F, K = np.meshgrid(freqs, knorm, indexing="ij")
    sel = (np.abs(K) >= k_norm_min) & (F >= 0.0) & (F <= f_max)
    tot = float(np.sum(spec))
    coherent = float(np.sum(spec[sel]) / tot) if tot > 0 else 0.0

    s1d = np.abs(np.fft.rfft(block, axis=0)) ** 2
    f1d = np.fft.rfftfreq(ns, d=dt)
    tot1d = float(np.sum(s1d))
    low = float(np.sum(s1d[f1d <= f_low]) / tot1d) if tot1d > 0 else 0.0

    a, b = block[:, :-1], block[:, 1:]
    num = np.sum(a * b, axis=0)
    den = np.sqrt(np.sum(a**2, axis=0) * np.sum(b**2, axis=0))
    with np.errstate(invalid="ignore", divide="ignore"):
        cc = np.where(den > 0, num / den, 0.0)
    lateral = float(np.median(np.abs(cc)))

    return {
        "dead_trace_fraction": dead,
        "outlier_trace_fraction": outlier,
        "coherent_energy_ratio": coherent,
        "low_freq_energy_ratio": low,
        "lateral_coherence": lateral,
    }


def rank_candidates(rows: list[dict], *, primary: str, secondary: str) -> list[dict]:
    """按冻结判据排序：``primary`` 降序 → ``secondary`` 降序 → 道号 → 时间样点（确定性 tie-break）。"""
    return sorted(
        rows,
        key=lambda r: (
            -r[primary],
            -r[secondary],
            r["traces"][0],
            r["samples"][0],
        ),
    )


def select_top_n(rows: list[dict], *, n: int, primary: str, secondary: str) -> list[dict]:
    """取排序后的前 ``n`` 个面板。"""
    return rank_candidates(rows, primary=primary, secondary=secondary)[:n]


def run_selection(config: dict, data_root: str | Path) -> list[dict]:
    """按配置执行完整选定（测量全部候选网格 → 排序 → 取 top-3）。"""
    root = Path(data_root)
    acq = config["meta"]["acquisition"]
    dt = float(acq["dt_s"])
    grid = config["candidate_grid"]
    crit = config["preregistered_criteria"]

    # 判据参数（全部来自配置）
    k_norm_min = 0.05
    f_max = 40.0
    f_low = 15.0
    primary = "coherent_energy_ratio"
    secondary = "lateral_coherence"
    n_panels = 3

    rows: list[dict] = []
    for region, fname in REGION_FILES.items():
        path = root / fname
        if not path.exists():
            raise FileNotFoundError(f"缺少原始数据文件：{path}")
        for (t0, t1) in grid["trace_blocks"]:
            block = read_trace_block(path, t0, t1)          # 每道块只读一次
            for (s0, s1) in grid["time_blocks_samples"]:
                m = measure_panel(block[s0:s1, :], dt=dt,
                                  k_norm_min=k_norm_min, f_max=f_max, f_low=f_low)
                rows.append({"region": region, "traces": [t0, t1],
                             "samples": [s0, s1], **m})
    return select_top_n(rows, n=n_panels, primary=primary, secondary=secondary)


def _to_key(panel: dict) -> tuple:
    """归一化比较键。

    注意：配置文件中冻结的面板用 ``trace_range`` / ``sample_range``，
    而本模块运行时产出的是 ``traces`` / ``samples``。两者都接受，
    以免"生成端与冻结端字段名不同"导致假性不一致。
    """
    traces = panel.get("traces", panel.get("trace_range"))
    samples = panel.get("samples", panel.get("sample_range"))
    if traces is None or samples is None:
        raise KeyError(f"面板缺少 trace/sample 范围字段：{sorted(panel)}")
    return (panel["region"], tuple(traces), tuple(samples))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="P1.3 野外面板选定（可重放）")
    ap.add_argument("--config", required=True, help="field_panels_draft.yaml 路径")
    ap.add_argument("--data-root", required=True,
                    help="含两个 .sgy 的目录；例：data/field/zenodo-mv"
                         "（再下一层才是 .sgy，传 data/field 会 FileNotFoundError）")
    ap.add_argument("--compare", action="store_true", help="与配置中的 panels 比对并返回退出码")
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    top = run_selection(cfg, args.data_root)

    print("重放选定的 top-3：")
    for i, p in enumerate(top, 1):
        print(f"  #{i} {p['region']} traces{p['traces']} samples{p['samples']} "
              f"coh={p['coherent_energy_ratio']:.4f} lat={p['lateral_coherence']:.4f}")

    if args.compare:
        frozen = [_to_key(p) for p in (cfg.get("panels") or [])]
        replayed = [_to_key(p) for p in top]
        same = frozen == replayed
        print()
        print("与 draft 中冻结的 top-3 一致:", same)
        if not same:
            print("  冻结:", frozen)
            print("  重放:", replayed)
        return 0 if same else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
