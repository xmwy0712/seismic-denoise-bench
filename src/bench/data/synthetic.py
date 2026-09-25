"""最小可用合成正演（P0.4 范围）。

范围界定（P0.4 任务 1）
----------------------
本单**只**实现：

* :func:`reflectivity` —— 水平层状反射系数序列
* :func:`forward`      —— 褶积正演（**时域直接褶积**）
* :func:`add_band_limited_noise`  —— 带限高斯随机噪声
* :func:`add_linear_coherent`     —— 指定视速度的线性相干干扰

**频散面波、第二合成模型、噪声强度档位、配置矩阵** 均留给 P1 完整版，本单不实现。

随机性约定
----------
随机性一律通过**显式注入**的 ``rng``（``numpy.random.Generator``）产生，
**禁止**模块级隐式全局种子——P1 需按"配置 × 种子"精确复现，隐式状态会破坏可复现性。

坐标与单位约定
--------------
* 时间 ``t``：秒 (s)；采样间隔 ``dt``：秒。
* 空间 ``x``：米 (m)；道间距 ``dx``：米。
* 波数 ``k``：**周/米**（cycles/m，非 rad/m）。
* 视速度 ``v_app``：米/秒 (m/s)。
* 数据形状统一为 ``(n_samples, n_traces)`` = (时间, 道)。

实现相对任务单的偏离（已在 execution-log 声明）
-----------------------------------------------
任务单给出的签名未包含"道数"与"子波主频"两个必要参数，故对
:func:`forward` 与 :func:`add_linear_coherent` 各增加**一个带默认值的仅关键字参数**
（``n_traces`` / ``f_main``）。默认值使任务单原始调用形式（两参数）依然可用，
且不改变任何既有语义。不引入模块级全局默认值。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "reflectivity",
    "forward",
    "add_band_limited_noise",
    "add_linear_coherent",
]


def _as_rng(rng: np.random.Generator) -> np.random.Generator:
    """校验注入的随机源类型（显式注入，禁止隐式全局种子）。"""
    if not isinstance(rng, np.random.Generator):
        raise TypeError(
            f"rng 必须是 numpy.random.Generator（显式注入），实测 {type(rng).__name__}"
        )
    return rng


def reflectivity(
    n_layers: int,
    rng: np.random.Generator,
    *,
    sparsity: float = 0.30,
) -> np.ndarray:
    """生成水平层状反射系数序列（一维）。

    实现：在 ``n_layers`` 个层界面上以 ``sparsity`` 的概率放置非零反射系数，
    幅度在 ``[-1, 1]`` 上均匀分布；其余界面为 0（无反射）。

    参数
    ----
    n_layers : int
        层界面数（序列长度），须 >= 1。
    rng : numpy.random.Generator
        显式注入的随机源。
    sparsity : float
        非零反射系数的比例，取值范围 ``(0, 1]``。

    返回
    ----
    numpy.ndarray
        形状 ``(n_layers,)`` 的 float64 一维序列。
    """
    _as_rng(rng)
    if not isinstance(n_layers, (int, np.integer)) or n_layers < 1:
        raise ValueError(f"n_layers 须为 >= 1 的整数，实测 {n_layers!r}")
    if not (0.0 < sparsity <= 1.0):
        raise ValueError(f"sparsity 须落在 (0, 1]，实测 {sparsity!r}")

    magnitudes = rng.uniform(-1.0, 1.0, size=int(n_layers))
    kept = rng.random(int(n_layers)) < sparsity
    return np.where(kept, magnitudes, 0.0).astype(np.float64)


def forward(
    reflectivity: np.ndarray,
    wavelet: np.ndarray,
    n_traces: int = 1,
) -> np.ndarray:
    """褶积正演（**时域直接褶积**路径），返回无噪合成剖面。

    对水平层状模型，各道结果相同（无横向变化）；本函数按 ``n_traces`` 复制列。

    参数
    ----
    reflectivity : numpy.ndarray
        一维反射系数序列（长度 = 层界数）。
    wavelet : numpy.ndarray
        一维子波序列（如 ``bench.data.ricker.ricker`` 的输出振幅）。
    n_traces : int
        输出道数，默认 1。

    返回
    ----
    numpy.ndarray
        形状 ``(n_samples, n_traces)``，其中
        ``n_samples = len(reflectivity) + len(wavelet) - 1``（``mode="full"`` 褶积）。
    """
    refl = np.asarray(reflectivity, dtype=np.float64).ravel()
    wav = np.asarray(wavelet, dtype=np.float64).ravel()
    if refl.size == 0 or wav.size == 0:
        raise ValueError("reflectivity 与 wavelet 均不得为空")
    if not isinstance(n_traces, (int, np.integer)) or n_traces < 1:
        raise ValueError(f"n_traces 须为 >= 1 的整数，实测 {n_traces!r}")

    single_trace = np.convolve(refl, wav, mode="full")
    return np.repeat(single_trace[:, np.newaxis], int(n_traces), axis=1)


def add_band_limited_noise(
    s: np.ndarray,
    rng: np.random.Generator,
    band: tuple[float, float],
    *,
    dt: float = 0.002,
    amplitude: float = 1.0,
) -> np.ndarray:
    """叠加**带限**高斯随机噪声（逐道独立）。

    实现：先产生白噪声，再在频域做矩形带通掩蔽（零相位，无滤波延迟），
    最后按原数据 RMS 归一化到指定幅度。

    参数
    ----
    s : numpy.ndarray
        干净数据，形状 ``(n_samples, n_traces)``。
    rng : numpy.random.Generator
        显式注入的随机源。
    band : tuple[float, float]
        ``(f_lo, f_hi)``，单位 Hz，须满足 ``0 <= f_lo < f_hi``。
    dt : float
        采样间隔 (s)。
    amplitude : float
        噪声幅度（相对干净数据 RMS 的倍率）。

    返回
    ----
    numpy.ndarray
        含噪数据，形状同 ``s``。
    """
    _as_rng(rng)
    arr = np.asarray(s, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"s 须为二维 (n_samples, n_traces)，实测 ndim={arr.ndim}")

    f_lo, f_hi = (float(band[0]), float(band[1]))
    if not (0.0 <= f_lo < f_hi):
        raise ValueError(f"band 须满足 0 <= f_lo < f_hi，实测 {band!r}")
    if dt <= 0:
        raise ValueError(f"dt 须为正，实测 {dt!r}")

    n_samples = arr.shape[0]
    n_fft = 1 << int(np.ceil(np.log2(max(n_samples, 2))))

    white = rng.standard_normal(size=arr.shape)
    spectrum = np.fft.rfft(white, n=n_fft, axis=0)
    freqs = np.fft.rfftfreq(n_fft, d=dt)
    in_band = (freqs >= f_lo) & (freqs <= f_hi)
    spectrum *= in_band[:, np.newaxis]
    colored = np.fft.irfft(spectrum, n=n_fft, axis=0)[:n_samples, :]

    reference = float(np.sqrt(np.mean(arr**2)))
    if reference > 0.0:
        current = float(np.sqrt(np.mean(colored**2)))
        if current > 0.0:
            colored *= (amplitude * reference) / current

    return arr + colored


def add_linear_coherent(
    s: np.ndarray,
    v_app: float,
    dt: float,
    dx: float,
    rng: np.random.Generator,
    *,
    f_main: float = 30.0,
) -> np.ndarray:
    """叠加**指定视速度的线性相干干扰**。

    干扰为沿空间线性时移的 Ricker 子波：

        g(t, x) = W(t - x / v_app)

    其 f-k 谱能量脊为 ``k = -f / v_app``（``f > 0`` 时 ``k < 0``），故回算取
    ``v = f_peak / |k_peak|``。

    **变换核约定（复现者必读）**
        本结论在 ``numpy.fft.fft2`` 的核 **``exp(-2πi(f·t + k·x))``**（两个负号）下成立：
        令 ``u = t - x / v_app``，指数化为 ``-2πi(f·u) - 2πi·x(f / v_app + k)``，
        故能量脊满足 ``f / v_app + k = 0``，即 **``k = -f / v_app``**。
        **若改用 ``exp(-2πi(f·t - k·x))`` 的约定，则符号相反（``k = +f / v_app``）。**
        **复现者须先确认所用变换核的符号**，再决定回算公式的符号。

        符号推导的完整记录见 ``tests/test_data_acceptance.py`` 的模块 docstring
        （该文件为同一约定的另一处表述，二者互相引用）。

    参数
    ----
    s : numpy.ndarray
        基础数据，形状 ``(n_samples, n_traces)``。
    v_app : float
        视速度 (m/s)，须为正。
    dt : float
        时间采样间隔 (s)。
    dx : float
        道间距 (m)。
    rng : numpy.random.Generator
        显式注入的随机源（仅用于整体幅度缩放，不改变 f-k 脊位置）。
    f_main : float
        干扰子波主频 (Hz)，默认 30.0。

    返回
    ----
    numpy.ndarray
        叠加干扰后的数据，形状同 ``s``。
    """
    _as_rng(rng)
    arr = np.asarray(s, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"s 须为二维 (n_samples, n_traces)，实测 ndim={arr.ndim}")
    for name, value in (("v_app", v_app), ("dt", dt), ("dx", dx), ("f_main", f_main)):
        if not np.isfinite(value) or value <= 0.0:
            raise ValueError(f"{name} 须为正有限值，实测 {value!r}")

    n_samples, n_traces = arr.shape
    time_axis = np.arange(n_samples, dtype=np.float64) * dt
    offset_axis = np.arange(n_traces, dtype=np.float64) * dx

    # 沿 (时间, 道) 的时移网格：tau = t - x / v
    tau = time_axis[:, np.newaxis] - offset_axis[np.newaxis, :] / float(v_app)

    scaled = (np.pi * float(f_main)) ** 2
    event = (1.0 - 2.0 * scaled * tau**2) * np.exp(-scaled * tau**2)

    # 幅度缩放走注入的 rng（线性幅度，不改变脊）
    magnitude = float(rng.uniform(0.5, 1.5))
    return arr + magnitude * event
