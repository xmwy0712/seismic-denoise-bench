"""方法 · F-X 预测反褶积（沿道方向的频率域预测滤波）。

机制族
------
中值/均值/预测滤波（经典）

用途与适用噪声
--------------
面向**相干噪声**的强基线备选（协议列举：f-k 滤波或 F-X 反褶积）；
对**随机噪声**亦有一定压制作用（不可预测分量被削弱）。

原理
----
在**每个时间频率切片**上，沿**道方向**相干同相轴是**可预测**的，而随机噪声不可预测。
对每个频率：以阶数 ``order`` 的前向自回归模型最小二乘拟合切片序列，用拟合值替换原值，
即可削弱不可预测成分。实现为**岭正则化最小二乘**（``eps`` 防止病态）。

实值输出保证：仅处理 ``f > 0`` 的频点，随后按厄米对称补齐 ``f < 0``。

关键参数
--------
``dt`` : 采样间隔（秒）
``order`` : AR 阶数（沿道方向）
``f_lo_hz`` / ``f_hi_hz`` : 处理频带
``eps`` : 岭正则系数

确定性
------
**确定性**（纯最小二乘线性代数）；不使用 ``rng``。
"""

from __future__ import annotations

import numpy as np

METHOD_NAME = "fx_deconv"
FAMILY = "中值/均值/预测滤波（经典）"
DETERMINISTIC = True

PARAMS_DEFAULT: dict = {
    "dt": 0.002,
    "order": 4,
    "f_lo_hz": 5.0,
    "f_hi_hz": 80.0,
    "eps": 1.0e-8,
}


def run(noisy: np.ndarray, params: dict | None, rng: np.random.Generator) -> np.ndarray:
    """F-X 预测反褶积。``rng`` 不使用（确定性方法，保留统一签名）。"""
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
    order = int(p["order"])
    f_lo = float(p["f_lo_hz"])
    f_hi = float(p["f_hi_hz"])
    eps = float(p["eps"])
    if order < 1:
        raise ValueError(f"order 须 >= 1，实测 {order}")
    if ntr <= order + 1:
        raise ValueError(f"道数 {ntr} 过少，无法拟合 order={order}")

    spec = np.fft.fft(a, axis=0)
    freqs = np.fft.fftfreq(ns, d=dt)
    out = spec.copy()

    for i in range(ns):
        fi = float(freqs[i])
        if not (f_lo <= fi <= f_hi):
            continue
        z = spec[i, :]
        m = ntr - order
        design = np.stack([z[order - k:ntr - k] for k in range(1, order + 1)], axis=1)
        target = z[order:ntr]
        gram = design.conj().T @ design + eps * np.eye(order)
        coef = np.linalg.solve(gram, design.conj().T @ target)
        z_new = z.copy()
        z_new[order:] = design @ coef
        out[i, :] = z_new
        # 厄米对称：保证实值输出
        mirror = (-i) % ns
        if mirror != i:
            out[mirror, :] = np.conj(z_new)

    return np.real(np.fft.ifft(out, axis=0))
