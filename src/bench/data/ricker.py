"""Ricker 子波生成与验收工具。

协议依据
--------
docs/protocol-v5.md 第七节：
    "Ricker 主频由频谱峰值回算，误差不超过设定值的 5%"

本模块提供：
  * :func:`ricker`                  —— 生成 Ricker 子波
  * :func:`estimate_peak_frequency` —— 由振幅谱峰值回算主频（验收用）

容差 5% 为**协议预注册值**，调用方不得放大。测试中的 65536 点 FFT 与抛物线
插值仅用于把**测量**精度提高到远超判定阈值，不改变判定阈值本身。
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
    """
    w = np.asarray(w, dtype=np.float64)
    if w.ndim != 1 or w.size < 2:
        raise ValueError("w 必须是一维且长度 >= 2")
    if not np.isfinite(dt) or dt <= 0:
        raise ValueError(f"dt 必须为正有限值，收到 {dt!r}")
    if n_fft < max(w.size, 4):
        raise ValueError(f"n_fft ({n_fft}) 不得小于序列长度 ({w.size})")

    # 零填充 FFT；子波较短，先去除均值不必要（Ricker 理论均值为 0）
    spec = np.fft.rfft(w, n=n_fft)
    amp = np.abs(spec)
    freqs = np.fft.rfftfreq(n_fft, d=dt)

    k = int(np.argmax(amp))
    f_peak = float(freqs[k])

    if not interpolate or k == 0 or k == amp.size - 1:
        return f_peak

    # 三点抛物线插值（log 幅值域不可用于零点附近，故在幅值域做）
    y0, y1, y2 = float(amp[k - 1]), float(amp[k]), float(amp[k + 1])
    denom = y0 - 2.0 * y1 + y2
    if denom == 0.0:
        return f_peak
    delta = 0.5 * (y0 - y2) / denom
    if not np.isfinite(delta) or abs(delta) > 1.0:
        return f_peak
    df = 1.0 / (n_fft * dt)
    return f_peak + float(delta) * df
