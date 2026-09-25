"""事件级指标（真值事件窗内的到时误差与能量误差）。

协议依据
--------
`docs/protocol-v5.md` 第四节第 4 条：

    事件级指标预注册为真值事件窗内**包络峰值到时绝对误差**和**归一化窗内能量误差**。

实现要点
--------
* **到时**：对 ``y`` 与 ``s`` 各取 Hilbert 解析信号包络，在**真值事件窗**内分别取包络峰值位置，
  到时误差 = 二者之差的绝对值（单位 **ms**）；多事件时逐事件给出，并报告**中位数与最大值**。
* **归一化窗内能量误差**：``|E_y − E_s| / E_s``（窗内能量），逐事件给出，报中位与最大。
* **事件窗来源**：沿用**已冻结**的掩码规则（沿时间轴膨胀 ``n_T``、round-half-up）；
  本模块**不修改**该规则，只接受既有 ``event_mask`` 的输出或其等价窗口描述。

作用域（A3）
-----------
本模块与 `bench.data.synthetic` 的**两个模型无关**：它只依赖
``(s, y, 事件窗)``，故 M1/M2 均可计算。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["EventTiming", "event_peak_time_ms", "event_metrics"]


@dataclass(frozen=True)
class EventTiming:
    """单个事件的到时与能量误差。"""

    event_index: int
    trace_index: int
    t_truth_ms: float
    t_estimate_ms: float
    timing_error_ms: float
    energy_truth: float
    energy_estimate: float
    energy_rel_error: float


@dataclass
class EventMetricSummary:
    """多事件汇总。"""

    events: list[EventTiming] = field(default_factory=list)

    @property
    def timing_median_ms(self) -> float:
        return float(np.median([e.timing_error_ms for e in self.events])) if self.events else float("nan")

    @property
    def timing_max_ms(self) -> float:
        return float(np.max([e.timing_error_ms for e in self.events])) if self.events else float("nan")

    @property
    def energy_median(self) -> float:
        return float(np.median([e.energy_rel_error for e in self.events])) if self.events else float("nan")

    @property
    def energy_max(self) -> float:
        return float(np.max([e.energy_rel_error for e in self.events])) if self.events else float("nan")


def _envelope(signal: np.ndarray) -> np.ndarray:
    """解析信号包络 ``|hilbert(x)|``（沿时间轴 axis=0）。"""
    from scipy.signal import hilbert

    x = np.asarray(signal, dtype=np.float64)
    return np.abs(hilbert(x, axis=0))


def event_peak_time_ms(
    signal: np.ndarray,
    dt: float,
    window: tuple[int, int] | None = None,
) -> float:
    """在给定时间窗内取包络峰值位置（**毫秒**）。

    参数
    ----
    signal : numpy.ndarray
        一维时间序列（或二维，取列均值后再算）。
    dt : float
        采样间隔 (s)。
    window : (int, int) | None
        ``(start, stop)`` 样点区间（半开）；``None`` 表示全窗。

    返回
    ----
    float
        包络峰值所在时刻（ms）。
    """
    x = np.asarray(signal, dtype=np.float64)
    if x.ndim == 2:
        x = np.mean(x, axis=1)
    if x.ndim != 1 or x.size == 0:
        raise ValueError("signal 须为非空一维序列（或二维，逐道取均值）")
    if not np.isfinite(dt) or dt <= 0:
        raise ValueError(f"dt 须为正有限值，实测 {dt!r}")

    env = _envelope(x)
    if window is not None:
        lo, hi = int(window[0]), int(window[1])
        if lo < 0 or hi > env.size or lo >= hi:
            raise ValueError(f"window 非法：{(lo, hi)} vs 长度 {env.size}")
        seg = env[lo:hi]
        idx_local = int(np.argmax(seg))
        idx = lo + idx_local
    else:
        idx = int(np.argmax(env))
    return float(idx) * float(dt) * 1000.0


def event_metrics(
    s: np.ndarray,
    y: np.ndarray,
    windows: list[tuple[int, int]],
    dt: float,
) -> EventMetricSummary:
    """逐事件计算到时误差与归一化能量误差。

    参数
    ----
    s : numpy.ndarray
        真值，形状 ``(n_samples, n_traces)``。
    y : numpy.ndarray
        去噪输出，形状同 ``s``。
    windows : list[(int, int)]
        每个事件的**真值事件窗** ``(start, stop)``（半开区间，单位=样点）。
        **来源须为已冻结的掩码规则**（沿时间轴膨胀 ``n_T``、half-up）。
    dt : float
        采样间隔 (s)。

    返回
    ----
    EventMetricSummary
        含逐事件明细与汇总（中位/最大）。

    异常
    -----
    ValueError
        形状不符、含非有限值、窗口非法。
    """
    truth = np.asarray(s, dtype=np.float64)
    out = np.asarray(y, dtype=np.float64)
    if truth.shape != out.shape:
        raise ValueError(f"形状不一致：s={truth.shape}，y={out.shape}")
    if truth.ndim != 2:
        raise ValueError(f"s 须为二维，实测 ndim={truth.ndim}")
    if not np.all(np.isfinite(truth)) or not np.all(np.isfinite(out)):
        raise ValueError("输入含 NaN/Inf")

    summary = EventMetricSummary()
    for i, (lo, hi) in enumerate(windows):
        lo, hi = int(lo), int(hi)
        if lo < 0 or hi > truth.shape[0] or lo >= hi:
            raise ValueError(f"第 {i} 个事件窗非法：{(lo, hi)} vs 样本数 {truth.shape[0]}")

        seg_s = truth[lo:hi, :]
        seg_y = out[lo:hi, :]

        t_s = event_peak_time_ms(seg_s, dt, None)
        t_y = event_peak_time_ms(seg_y, dt, None)

        e_s = float(np.sum(seg_s**2))
        e_y = float(np.sum(seg_y**2))
        if e_s == 0.0:
            energy_rel = float("inf") if e_y > 0 else 0.0
        else:
            energy_rel = abs(e_y - e_s) / e_s

        summary.events.append(
            EventTiming(
                event_index=i,
                trace_index=-1,                     # 事件窗为时间窗，不指定单道
                t_truth_ms=t_s,
                t_estimate_ms=t_y,
                timing_error_ms=abs(t_y - t_s),
                energy_truth=e_s,
                energy_estimate=e_y,
                energy_rel_error=energy_rel,
            )
        )
    return summary
