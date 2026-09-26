"""方法 · f-k 扇形滤波（频率-波数域视速度滤波）。

机制族
------
中值/均值/预测滤波（经典）

用途与适用噪声
--------------
面向**相干噪声**（线性干扰、频散面波）的**强基线**；协议强制保留的相干噪声基线之一。

原理
----
二维傅里叶变换后，视速度 ``|v| = |f| / |k|``。低视速度能量（地滚波/面波/线性干扰）
满足 ``|v| < v_cut``，在 (f,k) 平面被扇形区域隔离后**置零**，再反变换回时空域：

* 保号约定（与全仓一致）：核 ``exp(-2*pi*i*(f*t + k*x))``，脊线 ``k = -f/v``（f>0 时 k<0）。
  本滤波按 ``|v|`` 判据，故对符号不敏感，但**带宽与视速度判据的象限含义仍依赖该核**。
* ``f = 0``（直流）行**整体保留**，避免破坏均值。

关键参数
--------
``dt`` / ``dx`` : 采样间隔（秒 / 米）
``v_cut_m_s`` : 视速度下限；``|v| < v_cut`` 的频带能量被压制
``f_lo_hz`` / ``f_hi_hz`` : 保留频带

确定性
------
**确定性**（纯 FFT 与逐点掩码）；不使用 ``rng``。
"""

from __future__ import annotations

import numpy as np

METHOD_NAME = "fk_filter"
FAMILY = "中值/均值/预测滤波（经典）"
DETERMINISTIC = True

PARAMS_DEFAULT: dict = {
    "dt": 0.002,
    "dx": 10.0,
    "v_cut_m_s": 800.0,
    "f_lo_hz": 5.0,
    "f_hi_hz": 80.0,
}


def run(noisy: np.ndarray, params: dict | None, rng: np.random.Generator) -> np.ndarray:
    """f-k 扇形滤波。``rng`` 不使用（确定性方法，保留统一签名）。"""
    p = dict(PARAMS_DEFAULT)
    if params:
        p.update(params)

    a = np.asarray(noisy, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError(f"noisy 须为二维 (n_samples, n_traces)，实测 ndim={a.ndim}")
    if not np.all(np.isfinite(a)):
        raise ValueError("noisy 含非有限值")

    ns, ntr = a.shape
    dt = float(p["dt"])
    dx = float(p["dx"])
    v_cut = float(p["v_cut_m_s"])
    f_lo = float(p["f_lo_hz"])
    f_hi = float(p["f_hi_hz"])
    if v_cut <= 0.0:
        raise ValueError(f"v_cut_m_s 须为正，实测 {v_cut!r}")

    spectrum = np.fft.fft2(a)
    freqs = np.fft.fftfreq(ns, d=dt)[:, np.newaxis]
    wnums = np.fft.fftfreq(ntr, d=dx)[np.newaxis, :]

    with np.errstate(divide="ignore", invalid="ignore"):
        v_app = np.abs(freqs) / np.abs(wnums)

    in_band = (np.abs(freqs) >= f_lo) & (np.abs(freqs) <= f_hi)
    keep = in_band & np.isfinite(v_app) & (v_app >= v_cut)
    keep[0, :] = True                      # 直流行整体保留
    keep |= in_band & (wnums == 0.0)       # k=0 无有限视速度，按频带保留

    return np.real(np.fft.ifft2(spectrum * keep))
