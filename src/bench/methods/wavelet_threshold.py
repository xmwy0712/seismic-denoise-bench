"""方法 · 小波变换阈值去噪（多尺度细节系数软阈值）。

机制族
------
多尺度变换（小波/曲波/剪切波/contourlet）

用途与适用噪声
--------------
面向**随机噪声**（带限高斯）为主的通用去噪；对相干噪声效果有限。
依赖 **PyWavelets**（已在 requirements.lock：PyWavelets 1.10.0）。

原理
----
二维平稳小波分解后，对**细节系数**做**软阈值**（Donoho 通用阈值）：
``thr = mult * sigma * sqrt(2 ln N)``，其中 ``sigma`` 由最细尺度对角细节的
``median(|cD|) / 0.6745`` 稳健估计。低频近似系数保留不动。

关键参数
--------
``wavelet`` : 小波基（如 ``db4``）
``level`` : 分解层数（``None`` = 依信号长度自动取最大）
``mult`` : 阈值倍数（1.0 = 通用阈值）
``mode`` : 阈值函数（``soft`` / ``hard``）

确定性
------
**确定性**（小波分解与阈值均为确定性运算）；不使用 ``rng``。
"""

from __future__ import annotations

import numpy as np
import pywt

METHOD_NAME = "wavelet_threshold"
FAMILY = "多尺度变换（小波/曲波/剪切波/contourlet）"
DETERMINISTIC = True

PARAMS_DEFAULT: dict = {
    "wavelet": "db4",
    "level": None,
    "mult": 1.0,
    "mode": "soft",
}


def run(noisy: np.ndarray, params: dict | None, rng: np.random.Generator) -> np.ndarray:
    """小波阈值去噪。``rng`` 不使用（确定性方法，保留统一签名）。"""
    p = dict(PARAMS_DEFAULT)
    if params:
        p.update(params)

    a = np.asarray(noisy, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError(f"noisy 须为二维 (n_samples, n_traces)，实测 ndim={a.ndim}")
    if not np.all(np.isfinite(a)):
        raise ValueError("noisy 含非有限值")

    ns, ntr = a.shape
    wavelet = str(p["wavelet"])
    level = p["level"]
    mult = float(p["mult"])
    mode = str(p["mode"])
    if mode not in ("soft", "hard"):
        raise ValueError(f"mode 须为 soft/hard，实测 {mode!r}")

    coeffs = pywt.wavedec2(a, wavelet=wavelet, level=level, mode="symmetric")
    detail_finest = coeffs[-1][-1]                       # 最细尺度对角细节
    sigma = float(np.median(np.abs(detail_finest)) / 0.6745)
    thr = mult * sigma * float(np.sqrt(2.0 * np.log(max(a.size, 2))))

    new = [coeffs[0]]
    for detail in coeffs[1:]:
        new.append(tuple(pywt.threshold(c, thr, mode=mode) for c in detail))
    rec = pywt.waverec2(new, wavelet=wavelet, mode="symmetric")

    return np.asarray(rec, dtype=np.float64)[:ns, :ntr]
