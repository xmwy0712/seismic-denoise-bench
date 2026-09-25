"""独立参考实现：**频域乘积褶积**路径的正演。

用途（P0.4 任务 2）
------------------
对被测实现 :func:`bench.data.synthetic.forward`（**时域直接褶积**）作独立交叉验证：
两条数值路径算同一物理量，断言归一化均方误差 ``NMS <= 1e-6``。

**硬要求**：本文件与 ``synthetic.py`` **不得共享任何实现代码**（禁止复制改名）。
二者共享的仅是"褶积"这一数学定义本身——此处以频域乘法表达，彼处以时域求和表达。

本文件不定义测试用例，故按 P0.4-Am1 裁定 1 的清单守卫规则，
须登记在 ``tests/_auxiliary.tsv`` 中（**不**使用代码内豁免名单）。

长度约定
--------
时域 ``mode="full"`` 褶积的输出长度为 ``n_refl + n_wav - 1``。
频域路径使用 ``n_fft >= n_refl + n_wav - 1``，相乘后取前 ``n_refl + n_wav - 1`` 点，
以避免循环卷积污染。
"""

from __future__ import annotations

import numpy as np

__all__ = ["forward_frequency_domain", "normalized_mean_square_error"]


def forward_frequency_domain(
    reflectivity: np.ndarray,
    wavelet: np.ndarray,
    n_traces: int = 1,
) -> np.ndarray:
    """用**频域乘积**实现褶积正演（独立于 ``synthetic.forward`` 的数值路径）。

    参数
    ----
    reflectivity : numpy.ndarray
        一维反射系数序列。
    wavelet : numpy.ndarray
        一维子波序列。
    n_traces : int
        输出道数，默认 1。

    返回
    ----
    numpy.ndarray
        形状 ``(n_refl + n_wav - 1, n_traces)`` 的 float64 数组。
    """
    refl = np.asarray(reflectivity, dtype=np.float64).reshape(-1)
    wav = np.asarray(wavelet, dtype=np.float64).reshape(-1)
    if refl.size == 0 or wav.size == 0:
        raise ValueError("输入序列不得为空")
    if n_traces < 1:
        raise ValueError("n_traces 须 >= 1")

    target_len = refl.size + wav.size - 1
    n_fft = 1
    while n_fft < target_len:
        n_fft <<= 1

    product = np.fft.rfft(refl, n=n_fft) * np.fft.rfft(wav, n=n_fft)
    trace = np.fft.irfft(product, n=n_fft)[:target_len]
    return np.tile(trace[:, None], (1, int(n_traces)))


def normalized_mean_square_error(reference: np.ndarray, test: np.ndarray) -> float:
    """归一化均方误差 ``NMS = ||test - reference||^2 / ||reference||^2``。

    两条路径若数值等价，该值应在浮点误差量级（约 ``1e-30``），远低于 ``1e-6`` 验收门。
    """
    ref = np.asarray(reference, dtype=np.float64)
    tst = np.asarray(test, dtype=np.float64)
    if ref.shape != tst.shape:
        raise ValueError(f"形状不一致：reference={ref.shape}，test={tst.shape}")
    denom = float(np.sum(ref * ref))
    if denom == 0.0:
        raise ValueError("参考解能量为 0，无法归一化")
    diff = tst - ref
    return float(np.sum(diff * diff) / denom)
