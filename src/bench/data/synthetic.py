"""合成数据生成器（P1.1 完整版）。

范围
----
本模块提供：

**主模型（水平层状）**
  * :func:`reflectivity`            —— 水平层状反射系数序列
  * :func:`forward`                 —— 褶积正演（**时域直接褶积**）

**第二模型（协议硬要求：不得仍是纯水平层状）**
  * :func:`reflectivity_structure`  —— 含**倾斜** + **弯曲（时变倾角）** + **断层**的反射系数场
  * :func:`forward_structure`       —— 上述模型的褶积正演（逐道）

**噪声（三类，协议规定）**
  * :func:`add_band_limited_noise`  —— 带限高斯随机噪声
  * :func:`add_linear_coherent`     —— 指定视速度的线性相干干扰
  * :func:`add_dispersive_surface_wave` —— **频散面波**（具明确 v(f) 关系）

**工具**
  * :func:`input_snr_db`            —— 输入 SNR（dB），用于强度档位的口径 (i)
  * :func:`estimate_dispersion_v`   —— 由 f-k 谱回算频散曲线 v(f)（验收 c）

随机性约定
----------
随机性一律通过**显式注入**的 ``rng``（``numpy.random.Generator``），
**禁止**模块级隐式全局种子——P1.5 需按"配置 × 种子"精确复现。

坐标与单位
----------
``t`` 秒；``dt`` 秒；``x`` 米；``dx`` 米；``k`` **周/米**；``v`` 米/秒。
数据形状统一 ``(n_samples, n_traces)`` = (时间, 道)。

变换核约定（重要，勿改）
------------------------
涉及 f-k 符号的结论一律基于 ``numpy.fft.fft2`` 的核 **``exp(-2πi(f·t + k·x))``**。
在该约定下，线性干扰 ``g(t,x) = W(t − x/v)`` 的能量脊为 **``k = −f/v``**（``f>0`` 时 ``k<0``）。
**若改用 ``exp(-2πi(f·t − k·x))`` 的约定，则符号相反。复现者须先确认核的符号。**
（依据 P0.4-Am2 R13 裁定；对称表述见 ``tests/test_data_acceptance.py`` 模块 docstring。）
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "reflectivity",
    "forward",
    "reflectivity_structure",
    "forward_structure",
    "add_band_limited_noise",
    "add_linear_coherent",
    "add_dispersive_surface_wave",
    "input_snr_db",
    "estimate_dispersion_v",
]


def _as_rng(rng: np.random.Generator) -> np.random.Generator:
    """校验注入的随机源类型（显式注入，禁止隐式全局种子）。"""
    if not isinstance(rng, np.random.Generator):
        raise TypeError(
            f"rng 必须是 numpy.random.Generator（显式注入），实测 {type(rng).__name__}"
        )
    return rng


# =============================================================================
# 主模型
# =============================================================================
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
        一维子波序列。
    n_traces : int
        输出道数，默认 1。

    返回
    ----
    numpy.ndarray
        形状 ``(n_samples, n_traces)``，``n_samples = len(refl) + len(wav) - 1``。
    """
    refl = np.asarray(reflectivity, dtype=np.float64).ravel()
    wav = np.asarray(wavelet, dtype=np.float64).ravel()
    if refl.size == 0 or wav.size == 0:
        raise ValueError("reflectivity 与 wavelet 均不得为空")
    if not isinstance(n_traces, (int, np.integer)) or n_traces < 1:
        raise ValueError(f"n_traces 须为 >= 1 的整数，实测 {n_traces!r}")

    single_trace = np.convolve(refl, wav, mode="full")
    return np.repeat(single_trace[:, np.newaxis], int(n_traces), axis=1)


# =============================================================================
# 第二模型：倾斜 + 弯曲 + 断层（协议硬要求：不得仍是纯水平层状）
# =============================================================================
def reflectivity_structure(
    n_samples: int,
    n_traces: int,
    rng: np.random.Generator,
    *,
    n_events: int = 6,
    dip_deg_range: tuple[float, float] = (-18.0, 18.0),
    curvature_range: tuple[float, float] = (-0.35, 0.35),
    fault_trace_fraction: float = 0.5,
    fault_throw_samples: float = 25.0,
    lateral_velocity_gradient: float = 0.0,
    sparsity: float = 0.55,
) -> np.ndarray:
    """生成含**倾斜 + 弯曲（时变倾角）+ 断层**的反射系数场 ``(n_samples, n_traces)``。

    构造
    ----
    对第 ``j`` 个反射界面，其上覆界面的双程时间随道号变化：

        t_j(x) = t0_j + p_j · x + q_j · x² + Δt_fault · H(x − x_f)

    其中（``x`` 为归一化道号 ``0..1``）：

    * ``t0_j``      —— 界面零偏移距时间（随机，按序递增以避免交叉）
    * ``p_j``       —— **倾斜**项，由 ``dip_deg_range`` 采样（角度→斜率按名义速度换算）
    * ``q_j``       —— **弯曲**项（时变倾角），由 ``curvature_range`` 采样
    * ``Δt_fault``  —— **断层**断距（样点），在 ``x_f`` 处阶跃
    * ``H``         —— Heaviside 阶跃函数

    另可叠加 **横向速度变化**（``lateral_velocity_gradient``）：使有效时间轴沿道方向线性拉伸，
    与断层**至少其一**（协议要求"，建议都实现"——本实现**两者皆有**，断层默认开启、
    梯度默认 0 但可按配置启用）。

    每个界面沿其轨迹放置带限子波形状的反射系数：对第 ``j`` 界面，将 ``w(t − t_j(x))``
    按 ``sparsity`` 概率缩放后累加到对应位置。

    参数
    ----
    n_samples, n_traces : int
        输出形状。
    rng : numpy.random.Generator
        显式注入的随机源。
    n_events : int
        反射界面数（>= 3 才有意义）。
    dip_deg_range : (float, float)
        **倾斜**角范围（度）。
    curvature_range : (float, float)
        **弯曲**系数范围（归一化到 ``[0,1]`` 道号后的二次项系数，单位=样点）。
    fault_trace_fraction : float
        断层所在归一化道号位置 ``x_f ∈ (0,1)``。
    fault_throw_samples : float
        断层**断距**（样点）。
    lateral_velocity_gradient : float
        横向速度梯度（相对量／归一化道号）。``0`` 表示关闭。
    sparsity : float
        界面保留概率（每次采样决定该界面是否赋非零反射系数）。

    返回
    ----
    numpy.ndarray
        形状 ``(n_samples, n_traces)`` 的 float64 反射系数场。
    """
    _as_rng(rng)
    if n_samples < 8 or n_traces < 8:
        raise ValueError("n_samples 与 n_traces 均须 >= 8")
    if n_events < 3:
        raise ValueError(f"n_events 须 >= 3（需容纳倾斜/弯曲/断层），实测 {n_events!r}")
    if not (0.0 < fault_trace_fraction < 1.0):
        raise ValueError(f"fault_trace_fraction 须落在 (0,1)，实测 {fault_trace_fraction!r}")
    if not (0.0 < sparsity <= 1.0):
        raise ValueError(f"sparsity 须落在 (0,1]，实测 {sparsity!r}")

    xn = np.linspace(0.0, 1.0, int(n_traces))          # 归一化道号
    field = np.zeros((int(n_samples), int(n_traces)), dtype=np.float64)

    # 名义速度→斜率换算：dip(度) 在归一化道上映射为 "总时间跨度/道数" 的尺度
    nominal_vel = 2000.0  # m/s，仅用于把角度换算为时间斜率
    trace_len_m = 25.0    # m，名义道间距（与 dx 解耦，此处只用其比例）

    # 预生成界面零偏移距时间（单调递增，避免界面交叉）
    base_times = np.sort(rng.uniform(0.08, 0.88, size=int(n_events))) * n_samples
    faults_enabled = fault_throw_samples != 0.0

    for j in range(int(n_events)):
        # 该界面是否赋非零系数
        if rng.random() >= sparsity:
            continue

        dip_deg = float(rng.uniform(*dip_deg_range))
        curv = float(rng.uniform(*curvature_range))
        amp = float(rng.uniform(-1.0, 1.0))

        # 角度 → 归一化道号上的线性斜率（样点/归一化道号）
        slope = np.tan(np.deg2rad(dip_deg)) * (n_samples / max(n_events, 1)) * 0.5

        t_of_x = (
            base_times[j]
            + slope * xn
            + curv * (xn**2) * n_samples * 0.25
        )

        # 横向速度变化：沿道方向线性拉伸时间轴
        if lateral_velocity_gradient != 0.0:
            t_of_x = t_of_x * (1.0 + lateral_velocity_gradient * xn)

        # 断层：在 x_f 处阶跃
        if faults_enabled:
            t_of_x = t_of_x + fault_throw_samples * (xn >= fault_trace_fraction)

        # 沿轨迹放置反射系数（用高斯包络近似子波主瓣，宽度随样点尺度）
        width = 2.5
        for i in range(int(n_traces)):
            center = t_of_x[i]
            lo = int(max(0, np.floor(center - 4 * width)))
            hi = int(min(int(n_samples), np.ceil(center + 4 * width) + 1))
            if hi <= lo:
                continue
            idx = np.arange(lo, hi, dtype=np.float64)
            field[lo:hi, i] += amp * np.exp(-0.5 * ((idx - center) / width) ** 2)

    return field


def forward_structure(
    reflectivity_field: np.ndarray,
    wavelet: np.ndarray,
    *,
    trace_stride: int = 1,
) -> np.ndarray:
    """对**第二模型**的反射系数场逐道做褶积正演（时域直接褶积）。

    ``trace_stride`` 用于**时间轴方向**的降采样（模拟粗采样），默认 1（不降采样）。
    空间方向不做抽道，保持与 ``reflectivity_field`` 相同道数。

    参数
    ----
    reflectivity_field : numpy.ndarray
        形状 ``(n_samples, n_traces)`` 的反射系数场。
    wavelet : numpy.ndarray
        一维子波序列。
    trace_stride : int
        时间轴降采样步长（>=1）。

    返回
    ----
    numpy.ndarray
        形状 ``(n_samples + len(wav) - 1, n_traces)`` 的无噪剖面。
    """
    refl = np.asarray(reflectivity_field, dtype=np.float64)
    wav = np.asarray(wavelet, dtype=np.float64).ravel()
    if refl.ndim != 2:
        raise ValueError(f"reflectivity_field 须为二维，实测 ndim={refl.ndim}")
    if wav.size == 0:
        raise ValueError("wavelet 不得为空")
    if not isinstance(trace_stride, (int, np.integer)) or trace_stride < 1:
        raise ValueError(f"trace_stride 须为 >= 1 的整数，实测 {trace_stride!r}")

    r = refl[:: int(trace_stride), :] if trace_stride > 1 else refl
    out_len = r.shape[0] + wav.size - 1
    out = np.empty((out_len, r.shape[1]), dtype=np.float64)
    for i in range(r.shape[1]):
        out[:, i] = np.convolve(r[:, i], wav, mode="full")
    return out


# =============================================================================
# 噪声一：带限高斯随机噪声
# =============================================================================
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


# =============================================================================
# 噪声二：指定视速度的线性相干干扰
# =============================================================================
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

    tau = time_axis[:, np.newaxis] - offset_axis[np.newaxis, :] / float(v_app)

    scaled = (np.pi * float(f_main)) ** 2
    event = (1.0 - 2.0 * scaled * tau**2) * np.exp(-scaled * tau**2)

    magnitude = float(rng.uniform(0.5, 1.5))
    return arr + magnitude * event


# =============================================================================
# 噪声三：频散面波（具明确 v(f) 关系）
# =============================================================================
def add_dispersive_surface_wave(
    s: np.ndarray,
    dt: float,
    dx: float,
    rng: np.random.Generator,
    *,
    v_model: str = "linear",
    v0: float = 300.0,
    c: float = 900.0,
    a: float = 250.0,
    b: float = 0.5,
    f_lo: float = 5.0,
    f_hi: float = 40.0,
    amplitude: float = 1.0,
    n_components: int = 24,
) -> np.ndarray:
    """叠加**频散面波**（速度—频率关系 :math:`v(f)` 明确）。

    **速度—频率关系（两种模型，由 ``v_model`` 选择）**

    * ``"linear"``： :math:`v(f) = v_0 + c \\cdot f`
    * ``"power"`` ： :math:`v(f) = a \\cdot f^{b}`

    其中 :math:`f` 单位 Hz、:math:`v` 单位 m/s。

    实现：把面波写成**有限个频率分量的叠加**（``n_components`` 个，等间隔覆盖
    ``[f_lo, f_hi]``）。每个分量 ``f_i`` 以其相速度 :math:`v(f_i)` 沿空间线性时移：

        w_i(t, x) = A_i · sin(2π f_i (t − x / v(f_i)) + φ_i)

    幅度 ``A_i`` 随机（模拟各模态能量起伏），相位 ``φ_i`` 随机。
    该构造保证 f-k 谱上每个分量落在 ``k = −f_i / v(f_i)``（同 ``add_linear_coherent`` 的核约定），
    因此**逐频率回算 v(f) 是可行的**（见 :func:`estimate_dispersion_v`）。

    参数
    ----
    s : numpy.ndarray
        基础数据，形状 ``(n_samples, n_traces)``。
    dt, dx : float
        采样间隔 (s) / 道间距 (m)。
    rng : numpy.random.Generator
        显式注入的随机源。
    v_model : str
        ``"linear"`` 或 ``"power"``。
    v0, c : float
        线性模型参数（m/s, m/s/Hz）。
    a, b : float
        幂律模型参数（m/s, 无量纲）。
    f_lo, f_hi : float
        频率带 (Hz)，须 ``0 < f_lo < f_hi``。
    amplitude : float
        整体幅度（相对基础数据 RMS 的倍率）。
    n_components : int
        频率分量数（>= 3）。

    返回
    ----
    numpy.ndarray
        叠加面波后的数据，形状同 ``s``。
    """
    _as_rng(rng)
    arr = np.asarray(s, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"s 须为二维 (n_samples, n_traces)，实测 ndim={arr.ndim}")
    if v_model not in ("linear", "power"):
        raise ValueError(f"v_model 须为 'linear' 或 'power'，实测 {v_model!r}")
    if not (0.0 < f_lo < f_hi):
        raise ValueError(f"须满足 0 < f_lo < f_hi，实测 {(f_lo, f_hi)!r}")
    if n_components < 3:
        raise ValueError(f"n_components 须 >= 3，实测 {n_components!r}")
    if v_model == "linear" and (v0 <= 0.0 or c <= 0.0):
        raise ValueError(f"线性模型须 v0>0 且 c>0，实测 {(v0, c)!r}")
    if v_model == "power" and (a <= 0.0 or b <= 0.0):
        raise ValueError(f"幂律模型须 a>0 且 b>0，实测 {(a, b)!r}")

    n_samples, n_traces = arr.shape
    t = np.arange(n_samples, dtype=np.float64) * dt
    x = np.arange(n_traces, dtype=np.float64) * dx

    freq_axis = np.linspace(f_lo, f_hi, int(n_components))
    wave = np.zeros_like(arr)
    for f in freq_axis:
        v = (v0 + c * f) if v_model == "linear" else (a * f**b)
        tau = t[:, np.newaxis] - x[np.newaxis, :] / v
        phase = float(rng.uniform(0.0, 2.0 * np.pi))
        amp_i = float(rng.uniform(0.5, 1.0))
        wave += amp_i * np.sin(2.0 * np.pi * f * tau + phase)

    reference = float(np.sqrt(np.mean(arr**2)))
    denom = float(np.sqrt(np.mean(wave**2)))
    if denom > 0.0 and reference > 0.0:
        wave *= (amplitude * reference) / denom

    return arr + wave


def dispersion_velocity(
    f: np.ndarray | float,
    *,
    v_model: str = "linear",
    v0: float = 300.0,
    c: float = 900.0,
    a: float = 250.0,
    b: float = 0.5,
) -> np.ndarray:
    """按给定模型返回 :math:`v(f)`（m/s）。用于生成与验收的**同一公式**。

    注意：验收测试中的**期望值必须由本函数之外的解析式独立写出**
    （见 ``tests/test_data_acceptance.py`` 中硬编码的解析常量），
    以免自证。
    """
    f_arr = np.asarray(f, dtype=np.float64)
    if v_model == "linear":
        return v0 + c * f_arr
    if v_model == "power":
        return a * np.power(f_arr, b)
    raise ValueError(f"未知 v_model：{v_model!r}")


# =============================================================================
# 工具
# =============================================================================
def input_snr_db(clean: np.ndarray, noisy: np.ndarray) -> float:
    """输入 SNR（dB） = ``10·log10(||s||² / ||n||²)``，``n = noisy − clean``。

    用于"噪声强度档位"的**口径 (i)：目标输入 SNR**。
    """
    s = np.asarray(clean, dtype=np.float64)
    y = np.asarray(noisy, dtype=np.float64)
    if s.shape != y.shape:
        raise ValueError(f"形状不一致：clean={s.shape}，noisy={y.shape}")
    num = float(np.sum(s * s))
    den = float(np.sum((y - s) ** 2))
    if den == 0.0:
        return float("inf")
    if num == 0.0:
        raise ValueError("干净数据能量为 0，SNR 退化")
    return 10.0 * float(np.log10(num / den))


def estimate_dispersion_v(
    data: np.ndarray,
    dt: float,
    dx: float,
    probe_freqs: np.ndarray,
) -> np.ndarray:
    """由 f-k 谱回算**各探测频率处**的相速度 ``v(f)``（验收 c 用）。

    方法：对每个探测频率 ``f_p``，在 f-k 幅度谱中取 ``f ≈ f_p`` 的**切片**，
    在 ``k < 0`` 半平面（依本模块「变换核约定」）找峰，得 ``k_p``，
    返回 ``v = f_p / |k_p|``。

    参数
    ----
    data : numpy.ndarray
        形状 ``(n_samples, n_traces)``。
    dt, dx : float
        采样间隔 (s) / 道间距 (m)。
    probe_freqs : numpy.ndarray
        探测频率 (Hz)，一维。

    返回
    ----
    numpy.ndarray
        与 ``probe_freqs`` 等长的 ``v`` 数组 (m/s)。
    """
    arr = np.asarray(data, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"data 须为二维，实测 ndim={arr.ndim}")
    freqs_in = np.asarray(probe_freqs, dtype=np.float64).ravel()
    if freqs_in.size == 0:
        raise ValueError("probe_freqs 不得为空")

    n_samples, n_traces = arr.shape
    window_t = np.hanning(n_samples)[:, np.newaxis]
    window_x = np.hanning(n_traces)[np.newaxis, :]
    spec = np.abs(np.fft.fftshift(np.fft.fft2(arr * window_t * window_x), axes=1))

    f_axis = np.fft.fftfreq(n_samples, d=dt)
    k_axis = np.fft.fftshift(np.fft.fftfreq(n_traces, d=dx))

    # 依变换核约定：f>0 时脊在 k<0
    f_ok = f_axis > 0.0
    k_ok = k_axis < 0.0
    sub = spec[np.ix_(f_ok, k_ok)]
    f_sub = f_axis[f_ok]
    k_sub = k_axis[k_ok]

    v_out = np.empty(freqs_in.size, dtype=np.float64)
    for i, fp in enumerate(freqs_in):
        j = int(np.argmin(np.abs(f_sub - fp)))
        col = sub[j, :]
        m = int(np.argmax(col))
        k_peak = float(k_sub[m])
        if k_peak == 0.0:
            raise ValueError(f"f={fp} Hz 处峰落在零波数，无法回算速度")
        v_out[i] = float(fp) / abs(k_peak)
    return v_out
