"""Ricker 子波生成与验收工具。

协议依据
--------
docs/protocol-v5.md 第七节：
    "Ricker 主频由频谱峰值回算，误差不超过设定值的 5%"

本模块提供：
  * :func:`ricker`                  —— 生成 Ricker 子波
  * :func:`estimate_peak_frequency` —— 由振幅谱峰值回算主频（验收用）

容差 5% 为**协议预注册值**，调用方不得放大。测试中的零填充 FFT（>=65536 点）与
抛物线插值仅用于把**测量**精度提高到远超判定阈值，不改变判定阈值本身。

归一化语义（P0.2 amendment，WorkBuddy 裁定采纳）
------------------------------------------------
本实现采用**解析归一化**：子波与连续解析式保持一致，在 ``tau = 0`` 处振幅精确为 1，
**不**把离散峰值强行拉到 1。

随之而来的推论（重要，供下游 Lsig / 事件窗生成参考）：

    当 ``n_samples`` 为偶数时，默认 ``t0 = (n_samples - 1) * dt / 2`` 落在两个
    样点**之间**，因而不存在样点恰好位于 ``tau = 0``，此时 ``max(w) < 1``。

    例：``f_main = 25 Hz, dt = 0.002 s, n_samples = 512`` 时
    ``max(w) = 0.98158934...``。

若需要精确取到峰值 1，应显式令 ``t0`` 与某个样点对齐（例如 ``t0 = k * dt``）。
"""

from __future__ import annotations

import numpy as np

__all__ = ["ricker", "estimate_peak_frequency"]


def ricker(
    f_main: float,
    dt: float,
    n_samples: int,
    t0: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """生成 Ricker（墨西哥帽）子波。

    参数
    ----
    f_main : float
        设定主频 (Hz)，必须为正。
    dt : float
        时间采样间隔 (s)，必须为正。
    n_samples : int
        时间采样点数，必须 >= 2。
    t0 : float | None
        子波峰值所在时刻 (s)。默认取时间轴中心 ``(n_samples - 1) * dt / 2``，
        使子波关于中心对称。

    返回
    ----
    (t, w) : tuple[numpy.ndarray, numpy.ndarray]
        ``t`` 为时间轴 (s)，``w`` 为 Ricker 子波振幅。

    公式
    ----
    令 ``tau = t - t0``、``a = pi * f_main``，则

        w(tau) = (1 - 2 * a^2 * tau^2) * exp(-a^2 * tau^2)

    该子波的解析振幅谱峰值位于 ``f = f_main``。
    """
    if not np.isfinite(f_main) or f_main <= 0:
        raise ValueError(f"f_main 必须为正有限值，收到 {f_main!r}")
    if not np.isfinite(dt) or dt <= 0:
        raise ValueError(f"dt 必须为正有限值，收到 {dt!r}")
    if not isinstance(n_samples, (int, np.integer)) or n_samples < 2:
        raise ValueError(f"n_samples 必须为 >= 2 的整数，收到 {n_samples!r}")

    t = np.arange(n_samples, dtype=np.float64) * dt
    if t0 is None:
        t0 = (n_samples - 1) * dt / 2.0
    tau = t - t0

    a2 = (np.pi * f_main) ** 2
    w = (1.0 - 2.0 * a2 * tau**2) * np.exp(-a2 * tau**2)
    return t, w


def estimate_peak_frequency(
    w: np.ndarray,
    dt: float,
    *,
    n_fft: int = 65536,
    interpolate: bool = True,
) -> float:
    """由振幅谱峰值回算子波主频。

    参数
    ----
    w : numpy.ndarray
        子波振幅序列。
    dt : float
        时间采样间隔 (s)。
    n_fft : int
        FFT 点数，默认 65536（零填充以提高频率分辨率）。
        频率分辨率 = 采样率 / n_fft。
    interpolate : bool
        是否对峰值邻域做三点抛物线插值以细化峰值位置，默认 True。

    返回
    ----
    float
        由频谱峰值回算的主频 (Hz)。

    备注
    ----
    零填充至 65536 点（或更多）是**必要**的：若 FFT 点数过少，
    频率分辨率 ``df = 1 / (n_fft * dt)`` 会很大（例如 512 点时 ``df ≈ 1 Hz``，
    101 点时 ``df ≈ 5 Hz``），量化误差可达 20%，会造成**假失败**。
    """
    w = np.asarray(w, dtype=np.float64)
    if w.ndim != 1 or w.size < 2:
        raise ValueError("w 必须是一维且长度 >= 2")
    if not np.isfinite(dt) or dt <= 0:
        raise ValueError(f"dt 必须为正有限值，收到 {dt!r}")
    if n_fft < max(w.size, 4):
        raise ValueError(f"n_fft ({n_fft}) 不得小于序列长度 ({w.size})")

    # 零填充 FFT
    spec = np.fft.rfft(w, n=n_fft)
    amp = np.abs(spec)
    freqs = np.fft.rfftfreq(n_fft, d=dt)

    k = int(np.argmax(amp))
    f_peak = float(freqs[k])

    if not interpolate or k == 0 or k == amp.size - 1:
        return f_peak

    # 三点抛物线插值（幅值域）
    y0, y1, y2 = float(amp[k - 1]), float(amp[k]), float(amp[k + 1])
    denom = y0 - 2.0 * y1 + y2
    if denom == 0.0:
        return f_peak
    delta = 0.5 * (y0 - y2) / denom
    if not np.isfinite(delta) or abs(delta) > 1.0:
        return f_peak
    df = 1.0 / (n_fft * dt)
    return f_peak + float(delta) * df
