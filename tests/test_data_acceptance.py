"""P1.1 数据验收链：主频 / 视速度 / 频散 / 双实现 NMS / 种子有效性 / 第二模型非水平性。

验收项（P1.1 任务单第四节，容差即协议值，**不得放大**）
------------------------------------------------------
a) Ricker 主频回算 **≤5%**（沿用 P0.2 口径：FFT 零填充 ≥65536 点 + 峰值邻域抛物线插值）
b) 线性干扰视速度 f-k 回算 **≤10%**（沿用 P0.4；含无混叠前置校验）
c) **频散面波速度回算 ≤10%**（新）：在**预注册频率采样点**（≥5 点，覆盖频带两端与中部）
   回算 v(f)，取**中位相对误差** ≤10%
d) 无噪正演双实现 NMS **≤1e-6**（时域直接褶积 vs 频域乘积褶积；二者不得共享实现）
e) **种子有效性**（新，机械判据）：
   · 同配置 × 同种子，连续生成两次 → **逐字节相同**
   · 同配置 × 不同种子 → 输出**必须不同**
f) **第二模型非水平性验证**（新，机械判据）：
   以**与融合权重无关**的独立手段证明同相轴非水平
   （结构张量倾角分布的中位绝对值 > 阈值）

坐标与单位
----------
``dx`` 米、``dt`` 秒、``k`` **周/米**、``v`` 米/秒。

**f-k 脊的象限（重要，实现前须推导）**
干扰为 ``g(t, x) = W(t - x/v)``。二维傅里叶变换给出
``G(f, k) = W_hat(f) * delta(k + f / v)``，即能量脊为 **``k = -f / v``**。
因此 **``f > 0`` 时脊位于 ``k < 0``**，回算须在 **(f>0, k<0) 象限**搜索，
取 ``v = f / |k|``。（初版实现误在 ``k > 0`` 象限搜索，导致峰位跑到负频率折叠处；
已修正，详见 execution-log。）

**变换核约定（必要前提）**
上述符号在 ``numpy.fft.fft2`` 的核 **``exp(-2πi(f·t + k·x))``** 下成立。
**若改用 ``exp(-2πi(f·t - k·x))`` 的约定，则符号相反（``k = +f / v``）。**
**复现者须先确认所用变换核的符号。**
本约定的对称表述与完整推导见 ``src/bench/data/synthetic.py`` 中
``add_linear_coherent`` 的 docstring（两处互相引用，避免只读到一处而误判）。
"""

from __future__ import annotations

import numpy as np
import pytest

from bench.data.synthetic import (
    add_band_limited_noise,
    add_dispersive_surface_wave,
    add_linear_coherent,
    dispersion_velocity,
    estimate_dispersion_v,
    forward,
    forward_structure,
    input_snr_db,
    reflectivity,
    reflectivity_structure,
)
from bench.data.ricker import estimate_peak_frequency, ricker
from ref_forward import forward_frequency_domain, normalized_mean_square_error

# --- 预注册容差（协议值，不得放大）---------------------------------------------
TOL_F_PEAK = 0.05   # 主频回算相对误差上限
TOL_V_APP = 0.10    # 视速度回算相对误差上限
TOL_V_DISP = 0.10   # 频散速度**中位**相对误差上限
TOL_NMS = 1e-6      # 双实现归一化均方误差上限
# -----------------------------------------------------------------------------

N_FFT = 65536
DT = 0.002          # s
DX = 10.0           # m
F_MAINS = (15.0, 25.0, 40.0)
V_APPS = (800.0, 1500.0, 3000.0)
F_LINEAR = 30.0     # 线性干扰子波主频 (Hz)
N_SAMPLES = 512
N_TRACES = 64
SEED = 20260925

# --- 频散面波参数（P1.1 预注册；已做可分辨性扫描，见 execution-log）-------------
DISP_NS = 400
DISP_NTR = 64
DISP_F_LO, DISP_F_HI = 5.0, 25.0
DISP_V0, DISP_C = 500.0, 10.0        # v(f) = v0 + c·f
DISP_NCOMP = 24
# 预注册探测频率：覆盖频带两端与中部（共 7 点 ≥ 5）
DISP_PROBES = np.array([5.0, 8.0, 12.0, 15.0, 18.0, 22.0, 25.0])
DISP_A, DISP_B = 250.0, 0.5            # 幂律模型参数（必填，R15-b）
# R15-a：解析 v(f) 在预注册频带上必须落在该物理区间内（越界即 fail）
DISP_V_BAND_MPS = (100.0, 3000.0)


# =============================================================================
# a) Ricker 主频回算 ≤ 5%
# =============================================================================
@pytest.mark.parametrize("f_main", F_MAINS)
def test_a_ricker_peak_frequency_within_5pct(f_main: float) -> None:
    """主频由频谱峰值回算，相对误差 ≤ 5%。"""
    _t, w = ricker(f_main, DT, N_SAMPLES)
    f_estimate = estimate_peak_frequency(w, DT, n_fft=N_FFT, interpolate=True)
    relative_error = abs(f_estimate - f_main) / f_main

    assert relative_error <= TOL_F_PEAK, (
        f"设定 {f_main} Hz，回算 {f_estimate:.6f} Hz，相对误差 {relative_error:.6%}"
    )


# =============================================================================
# b) 线性干扰视速度回算 ≤ 10%
# =============================================================================
def _fk_peak_velocity(data: np.ndarray, dt: float, dx: float) -> tuple[float, float, float]:
    """由 2D f-k 谱能量峰回算视速度，返回 ``(f_peak, k_peak, v_estimate)``。

    搜索象限为 **``f > 0`` 且 ``k < 0``**：由 ``g(t,x) = W(t - x/v)`` 的二维谱
    ``G(f,k) = W_hat(f) * delta(k + f/v)`` 可知脊线为 ``k = -f/v``。
    回算取 ``v = f / |k|``。
    """
    n_samples, n_traces = data.shape
    window_t = np.hanning(n_samples)[:, np.newaxis]
    window_x = np.hanning(n_traces)[np.newaxis, :]
    spectrum = np.fft.fftshift(np.fft.fft2(data * window_t * window_x), axes=1)
    magnitude = np.abs(spectrum)

    freqs = np.fft.fftfreq(n_samples, d=dt)
    wavenumbers = np.fft.fftshift(np.fft.fftfreq(n_traces, d=dx))

    positive_f = freqs > 0.0
    negative_k = wavenumbers < 0.0
    magnitude_patch = magnitude[np.ix_(positive_f, negative_k)]
    freqs_pos = freqs[positive_f]
    wavenumbers_neg = wavenumbers[negative_k]

    flat_index = int(np.argmax(magnitude_patch))
    i_f, i_k = np.unravel_index(flat_index, magnitude_patch.shape)

    f_peak = float(freqs_pos[i_f])
    k_peak = float(wavenumbers_neg[i_k])

    if 0 < i_f < magnitude_patch.shape[0] - 1:
        y0, y1, y2 = (float(magnitude_patch[i_f - 1, i_k]),
                      float(magnitude_patch[i_f, i_k]),
                      float(magnitude_patch[i_f + 1, i_k]))
        denom = y0 - 2.0 * y1 + y2
        if denom != 0.0:
            delta = 0.5 * (y0 - y2) / denom
            if abs(delta) <= 1.0:
                f_peak += delta * abs(float(freqs[1] - freqs[0]))

    if 0 < i_k < magnitude_patch.shape[1] - 1:
        y0, y1, y2 = (float(magnitude_patch[i_f, i_k - 1]),
                      float(magnitude_patch[i_f, i_k]),
                      float(magnitude_patch[i_f, i_k + 1]))
        denom = y0 - 2.0 * y1 + y2
        if denom != 0.0:
            delta = 0.5 * (y0 - y2) / denom
            if abs(delta) <= 1.0:
                k_peak -= delta * abs(float(wavenumbers[1] - wavenumbers[0]))

    if k_peak >= 0.0:
        raise ValueError(
            f"f-k 峰落在非负波数（k_peak={k_peak}）：预期 k<0 分支，请检查象限与符号约定"
        )
    return f_peak, k_peak, f_peak / abs(k_peak)


@pytest.mark.parametrize("v_app", V_APPS)
def test_b_linear_coherent_velocity_within_10pct(v_app: float) -> None:
    """线性干扰视速度由 f-k 峰值回算，相对误差 ≤ 10%。"""
    rng = np.random.default_rng(SEED)
    base = np.zeros((N_SAMPLES, N_TRACES), dtype=np.float64)
    data = add_linear_coherent(base, v_app, DT, DX, rng, f_main=F_LINEAR)

    f_peak, k_peak, v_estimate = _fk_peak_velocity(data, DT, DX)
    relative_error = abs(v_estimate - v_app) / v_app

    assert f_peak > 0.0, f"回算主频非正：{f_peak}"
    assert k_peak < 0.0, f"回算波数应为负（k = -f/v）：{k_peak}"
    assert relative_error <= TOL_V_APP, (
        f"设定 v_app={v_app} m/s，f_peak={f_peak:.4f} Hz，k_peak={k_peak:.6f} 周/m，"
        f"回算 {v_estimate:.2f} m/s，相对误差 {relative_error:.4%}"
    )


def test_b_prime_no_aliasing_for_chosen_velocities() -> None:
    """前提校验：所选三档视速度的干扰脊均落在无混叠区内。"""
    k_nyquist = 1.0 / (2.0 * DX)
    f_nyquist = 1.0 / (2.0 * DT)
    for v_app in V_APPS:
        k_ridge = F_LINEAR / v_app
        assert k_ridge < k_nyquist, (
            f"v_app={v_app} 的脊 k={k_ridge:.5f} 超出空间 Nyquist {k_nyquist:.5f}"
        )
    assert F_LINEAR < f_nyquist


# =============================================================================
# c) 频散面波速度回算 ≤ 10%（中位）
# =============================================================================
def _dispersion_dataset(seed: int = SEED, n_components: int = DISP_NCOMP) -> np.ndarray:
    """生成仅含频散面波的数据（零基础），供回算用。"""
    base = np.zeros((DISP_NS, DISP_NTR), dtype=np.float64)
    return add_dispersive_surface_wave(
        base, DT, DX, np.random.default_rng(seed),
        v_model="linear", v0=DISP_V0, c=DISP_C, a=DISP_A, b=DISP_B,
        f_lo=DISP_F_LO, f_hi=DISP_F_HI,
        amplitude=1.0, n_components=n_components,
    )


def test_c1_dispersion_model_formula_is_as_declared() -> None:
    """频散模型公式自检：``v(f) = v0 + c·f``（用**独立解析式**核对，非调用被测函数）。"""
    f = DISP_PROBES
    expected = DISP_V0 + DISP_C * f          # 独立写出的解析式
    got = dispersion_velocity(f, v_model="linear", v0=DISP_V0, c=DISP_C, a=DISP_A, b=DISP_B)
    np.testing.assert_allclose(got, expected, rtol=0, atol=1e-12)


def test_c2_dispersion_band_is_resolvable_no_alias() -> None:
    """前提校验：频散脊在整个频带上均落在 ``(dk, k_nyq)`` 之间（无混叠、可分辨）。"""
    dk = 1.0 / (DISP_NTR * DX)
    k_nyq = 1.0 / (2.0 * DX)
    k_min = DISP_F_LO / (DISP_V0 + DISP_C * DISP_F_HI)   # f 最小、v 最大 → k 最小
    k_max = DISP_F_HI / (DISP_V0 + DISP_C * DISP_F_LO)   # f 最大、v 最小 → k 最大
    assert k_min > dk, f"k_min={k_min:.6f} 未超过波数分辨率 dk={dk:.6f}"
    assert k_max < k_nyq, f"k_max={k_max:.6f} 超过空间 Nyquist k_nyq={k_nyq:.6f}"


def test_c3_dispersion_velocity_median_error_within_10pct() -> None:
    """频散面波速度回算：预注册频率点上 **中位**相对误差 ≤ 10%。"""
    data = _dispersion_dataset()
    v_estimate = estimate_dispersion_v(data, DT, DX, DISP_PROBES)
    v_truth = DISP_V0 + DISP_C * DISP_PROBES              # 独立解析式
    relative_errors = np.abs(v_estimate - v_truth) / v_truth
    median_error = float(np.median(relative_errors))

    assert median_error <= TOL_V_DISP, (
        f"预注册频率点 {DISP_PROBES.tolist()}；中位相对误差 {median_error:.4%} > {TOL_V_DISP:.0%}；"
        f"逐点误差={[f'{e:.4%}' for e in relative_errors]}；"
        f"v_est={[f'{v:.1f}' for v in v_estimate]}；v_true={[f'{v:.1f}' for v in v_truth]}"
    )


def test_c4_dispersion_recall_stable_across_seeds() -> None:
    """跨种子稳健性：不同随机种子的中位误差均 ≤ 10%（防"单种子侥幸通过"）。"""
    for seed in (11, 22, 33):
        data = _dispersion_dataset(seed=seed)
        v_estimate = estimate_dispersion_v(data, DT, DX, DISP_PROBES)
        v_truth = DISP_V0 + DISP_C * DISP_PROBES
        median_error = float(np.median(np.abs(v_estimate - v_truth) / v_truth))
        assert median_error <= TOL_V_DISP, f"seed={seed} 中位误差 {median_error:.4%}"


# =============================================================================
# c-附加) R15-a · 频散解析式的物理合理性（堵"自洽即通过"的自证通道）
# =============================================================================
def test_c5_dispersion_truth_is_within_declared_physical_band() -> None:
    """**R15-a**：预注册频带上，解析 v(f) 必须落在声明的物理区间内。

    该断言把验收 c 从"自洽检验"升级为"自洽 + 物理"双重检验：
    即使估计器与解析式完全自洽，只要解析式本身不物理（如历史默认值
    ``v0=300, c=900`` 在 40 Hz 处给出 36 km/s），本项即 fail。
    """
    v_low, v_high = DISP_V_BAND_MPS
    v_at_probes = dispersion_velocity(
        DISP_PROBES, v_model="linear", v0=DISP_V0, c=DISP_C, a=DISP_A, b=DISP_B
    )
    vmin, vmax = float(np.min(v_at_probes)), float(np.max(v_at_probes))
    assert vmin >= v_low, f"解析 v(f) 最小 {vmin:.1f} m/s 低于物理下限 {v_low:.1f}"
    assert vmax <= v_high, f"解析 v(f) 最大 {vmax:.1f} m/s 超出物理上限 {v_high:.1f}"

    # 幂律模型同样须落在区间内
    v_pow = dispersion_velocity(
        DISP_PROBES, v_model="power", v0=DISP_V0, c=DISP_C, a=DISP_A, b=DISP_B
    )
    assert float(np.min(v_pow)) >= v_low, "幂律模型 v(f) 低于物理下限"
    assert float(np.max(v_pow)) <= v_high, "幂律模型 v(f) 超出物理上限"


def test_c6_legacy_placeholder_defaults_would_fail_the_physical_band() -> None:
    """**R15-a 反向演示**：历史上的占位参数（``v0=300, c=900``）**必定越界**。

    本用例证明该物理断言**不是空转**——若仍保留那两个默认值，验收会真的 fail。
    """
    v_low, v_high = DISP_V_BAND_MPS
    legacy = dispersion_velocity(
        np.array([5.0, 25.0, 40.0]),
        v_model="linear", v0=300.0, c=900.0, a=DISP_A, b=DISP_B,
    )
    assert float(np.max(legacy)) > v_high, (
        f"占位参数本应越界（40 Hz 处 36300 m/s > 上限 {v_high}），实测 max={float(np.max(legacy)):.1f}"
    )


def test_c7_dispersion_parameters_are_required_no_silent_defaults() -> None:
    """**R15-b**：频散参数**必填**——省略任一即 ``TypeError``，不得静默默认。

    这是"消除静默默认值"的机械判据：任何忘记传参的调用都会立刻报错，
    而不是产出不物理数据。
    """
    base = np.zeros((64, 16), dtype=np.float64)
    rng = np.random.default_rng(SEED)

    with pytest.raises(TypeError):
        add_dispersive_surface_wave(base, DT, DX, rng)  # type: ignore[call-arg]

    with pytest.raises(TypeError):
        add_dispersive_surface_wave(  # type: ignore[call-arg]
            base, DT, DX, rng, v_model="linear", v0=500.0, c=10.0,
            a=DISP_A, b=DISP_B, f_lo=5.0,
        )

    with pytest.raises(TypeError):
        dispersion_velocity(DISP_PROBES)  # type: ignore[call-arg]

    with pytest.raises(TypeError):
        dispersion_velocity(  # type: ignore[call-arg]
            DISP_PROBES, v_model="linear", v0=500.0, c=10.0,
        )


# =============================================================================
# d) 双实现 NMS ≤ 1e-6
# =============================================================================
def test_d_forward_two_implementations_nms_within_1e_minus_6() -> None:
    """无噪正演：时域直接褶积 vs 频域乘积褶积，NMS ≤ 1e-6。"""
    rng = np.random.default_rng(SEED)
    refl = reflectivity(200, rng)
    _t, wav = ricker(25.0, DT, 101)

    time_domain = forward(refl, wav, n_traces=3)
    frequency_domain = forward_frequency_domain(refl, wav, n_traces=3)

    assert time_domain.shape == frequency_domain.shape
    nms = normalized_mean_square_error(time_domain, frequency_domain)
    assert nms <= TOL_NMS, f"双实现 NMS={nms:.3e} 超出 {TOL_NMS:.0e}"


def test_d2_structure_model_two_implementations_nms_within_1e_minus_6() -> None:
    """第二模型正演的同口径双实现校验（逐道）。"""
    rng = np.random.default_rng(SEED)
    field = reflectivity_structure(120, 8, rng)
    _t, wav = ricker(25.0, DT, 61)

    td = forward_structure(field, wav)
    ref = np.concatenate([forward_frequency_domain(field[:, i], wav, n_traces=1)
                          for i in range(field.shape[1])], axis=1)
    assert td.shape == ref.shape
    nms = normalized_mean_square_error(td, ref)
    assert nms <= TOL_NMS, f"第二模型双实现 NMS={nms:.3e}"


# =============================================================================
# e) 种子有效性（机械判据）
# =============================================================================
def test_e1_same_config_same_seed_is_byte_identical() -> None:
    """同配置 × 同种子，连续生成两次 → **逐字节相同**。"""
    a = reflectivity(64, np.random.default_rng(4321))
    b = reflectivity(64, np.random.default_rng(4321))
    assert a.tobytes() == b.tobytes(), "同种子两次生成结果不一致 → rng 未被正确使用"

    fa = reflectivity_structure(80, 8, np.random.default_rng(4321))
    fb = reflectivity_structure(80, 8, np.random.default_rng(4321))
    assert fa.tobytes() == fb.tobytes(), "结构模型同种子两次生成结果不一致"

    sa = add_band_limited_noise(np.zeros((64, 4)), np.random.default_rng(999),
                                band=(5.0, 60.0), dt=DT)
    sb = add_band_limited_noise(np.zeros((64, 4)), np.random.default_rng(999),
                                band=(5.0, 60.0), dt=DT)
    assert sa.tobytes() == sb.tobytes(), "带限噪声同种子两次生成结果不一致"


def test_e2_different_seeds_must_differ() -> None:
    """同配置 × 不同种子 → 输出**必须不同**（否则说明 rng 未真正参与）。"""
    a = reflectivity(64, np.random.default_rng(1))
    b = reflectivity(64, np.random.default_rng(2))
    assert a.tobytes() != b.tobytes(), "不同种子产生了相同输出 → 种子未生效"

    fa = reflectivity_structure(80, 8, np.random.default_rng(1))
    fb = reflectivity_structure(80, 8, np.random.default_rng(2))
    assert fa.tobytes() != fb.tobytes(), "结构模型不同种子产生了相同输出"

    na = add_band_limited_noise(np.zeros((64, 4)), np.random.default_rng(1),
                                band=(5.0, 60.0), dt=DT)
    nb = add_band_limited_noise(np.zeros((64, 4)), np.random.default_rng(2),
                                band=(5.0, 60.0), dt=DT)
    assert na.tobytes() != nb.tobytes(), "带限噪声不同种子产生了相同输出"


def test_e3_seed_listed_explicitly_in_config() -> None:
    """配置矩阵须**显式列出**每个种子（禁止写"随机种子"而不给值）。"""
    from pathlib import Path
    cfg = Path(__file__).resolve().parent.parent / "configs" / "config_matrix.yaml"
    assert cfg.exists(), "未找到 configs/config_matrix.yaml"
    text = cfg.read_text(encoding="utf-8")
    assert "seeds" in text, "配置矩阵缺少 seeds 键"
    import re
    numbers = re.findall(r"^\s*-\s*(\d+)\s*$", text, re.M)
    assert len(numbers) >= 5, (
        f"配置矩阵显式列出的种子数 {len(numbers)} < 5（须每配置 ≥5 个且显式给出数值）"
    )


# =============================================================================
# f) 第二模型非水平性（独立结构张量，与融合权重无关）
# =============================================================================
def median_abs_dip_deg(image: np.ndarray) -> float:
    """用**独立实现**的结构张量估计局部倾角，返回倾角绝对值的中位数（度）。

    **独立性声明**：本函数为验收专用的一次性实现，**不共享**任何融合模块
    （``src/bench/fusion/``）中"局部相干度/结构张量"的代码与参数族；
    仅使用 numpy 的 ``gradient`` 与逐点 2×2 张量取向公式。

    数学依据
    --------
    设图像为 ``f(t, x)``，局部事件可写成 ``f = g(t - s·x)``（``s`` 为样点/道 的斜率）。
    则 ``g_t = g'``、``g_x = -s·g'``。结构张量
    ``J = [[<g_t²>, <g_t g_x>], [<g_t g_x>, <g_x²>]] = <g'²>·[[1, -s], [-s, s²]]``。
    其取向角（标准公式）::

        theta = 0.5 * atan2(2·J_tx, J_tt - J_xx) = -atan(s)

    故 ``|theta|`` 即为该处同相轴的倾角（度），与斜率单调对应且对振幅缩放不变。

    统计口径：仅统计**有能量**的位置（结构张量范数 ≥ 60 分位），避免平坦区的数值噪声主导中位数。
    """
    img = np.asarray(image, dtype=np.float64)
    if img.ndim != 2:
        raise ValueError("image 须为二维")

    gt, gx = np.gradient(img)   # axis0 = 时间(纵向 t)，axis1 = 道(横向 x)

    # 窗平滑：用 scipy.ndimage.uniform_filter（矩形窗均值，边界为 nearest）。
    # 注：scipy 已在项目依赖清单内（P0.2 起）。早期曾用自写积分图，
    # 该实现存在边界与索引错位，已废弃（见 execution-log）。
    from scipy.ndimage import uniform_filter

    def smooth(a: np.ndarray, r: int = 3) -> np.ndarray:
        return uniform_filter(a, size=2 * r + 1, mode="nearest")

    j_tt = smooth(gt * gt)
    j_xx = smooth(gx * gx)
    j_tx = smooth(gt * gx)

    # 标准结构张量取向角：0.5·atan2(2·J_tx, J_tt − J_xx)
    theta = 0.5 * np.arctan2(2.0 * j_tx, j_tt - j_xx)
    dip = np.abs(np.degrees(theta))

    energy = np.sqrt(j_tt * j_tt + 2.0 * j_tx * j_tx + j_xx * j_xx)
    if not np.any(energy > 0.0):
        return 0.0
    thr = np.percentile(energy, 60)
    sel = energy >= thr
    if not np.any(sel):
        sel = np.ones_like(energy, dtype=bool)
    return float(np.median(dip[sel]))


def test_f1_second_model_is_not_horizontal() -> None:
    """第二模型同相轴**非水平**：独立结构张量的倾角中位绝对值 > 阈值。"""
    rng = np.random.default_rng(SEED)
    field = reflectivity_structure(
        300, 64, rng,
        dip_deg_range=(-18.0, 18.0),
        curvature_range=(-0.35, 0.35),
        fault_throw_samples=25.0,
    )
    dip = median_abs_dip_deg(field)
    assert dip > DIP_THRESHOLD_DEG, (
        f"第二模型倾角中位绝对值 {dip:.2f}° 未超过阈值 {DIP_THRESHOLD_DEG}° → 可能退化为水平层状"
    )


def test_f2_horizontal_model_is_contrastingly_flat() -> None:
    """对照：主模型（水平层状）的倾角中位绝对值应**显著低于**第二模型。

    该对照用于证明 f1 的判据确实在区分"水平"与"非水平"，而非恒真。
    """
    rng = np.random.default_rng(SEED)
    refl = reflectivity(300, rng)
    _t, wav = ricker(25.0, DT, 61)
    flat = forward(refl, wav, n_traces=64)

    dip_flat = median_abs_dip_deg(flat)

    rng2 = np.random.default_rng(SEED)
    field = reflectivity_structure(300, 64, rng2,
                                   dip_deg_range=(-18.0, 18.0),
                                   curvature_range=(-0.35, 0.35))
    dip_struct = median_abs_dip_deg(field)

    assert dip_flat < dip_struct, (
        f"水平模型倾角({dip_flat:.2f}°) 未低于第二模型({dip_struct:.2f}°) → 判据区分力不足"
    )


def test_f3_structure_tensor_is_independent_of_fusion_module() -> None:
    """独立性机械检查：验收用的结构张量实现**不得**导入融合模块。

    做法：读取本测试文件源码，仅扫描 **import 语句**，断言其**未**导入
    ``bench.fusion`` 或任何融合侧实现（不扫描注释/docstring——本文件在**声明**独立性时
    会提到该模块名，那是文字而非导入）。
    """
    import re
    from pathlib import Path
    src = Path(__file__).read_text(encoding="utf-8")
    imports = [ln.strip() for ln in src.splitlines()
               if re.match(r"^\s*(import|from)\s+", ln)]
    offenders = [ln for ln in imports if "fusion" in ln or "coherence" in ln]
    assert not offenders, f"验收测试导入了融合侧实现 → 独立性被破坏：{offenders}"


# =============================================================================
# 辅助：形状约定与显式 rng 注入
# =============================================================================
DIP_THRESHOLD_DEG = 3.0   # 第二模型非水平性阈值（写死于此处，见 execution-log）


def test_synthetic_shapes_and_rng_injection() -> None:
    """形状约定为 (n_samples, n_traces)，且 rng 必须显式注入。"""
    rng = np.random.default_rng(SEED)
    refl = reflectivity(128, rng)
    assert refl.shape == (128,)

    _t, wav = ricker(25.0, DT, 101)
    section = forward(refl, wav, n_traces=5)
    assert section.ndim == 2
    assert section.shape == (128 + 101 - 1, 5)

    noisy = add_band_limited_noise(section, rng, band=(5.0, 80.0), dt=DT)
    assert noisy.shape == section.shape

    with pytest.raises(TypeError):
        reflectivity(16, np.random.RandomState(0))  # type: ignore[arg-type]


def test_synthetic_reproducible_with_fixed_seed() -> None:
    """同一显式种子必须逐元素复现（P1.5 逐配置固定种子的前提）。"""
    first = reflectivity(64, np.random.default_rng(SEED))
    second = reflectivity(64, np.random.default_rng(SEED))
    np.testing.assert_array_equal(first, second)


def test_band_limited_noise_stays_in_band() -> None:
    """带限噪声的能量应集中在指定频带内。"""
    rng = np.random.default_rng(SEED)
    base = np.zeros((N_SAMPLES, 8), dtype=np.float64)
    noisy = add_band_limited_noise(base, rng, band=(10.0, 60.0), dt=DT)

    spectrum = np.abs(np.fft.rfft(noisy[:, 0]))
    freqs = np.fft.rfftfreq(N_SAMPLES, d=DT)
    in_band_energy = float(np.sum(spectrum[(freqs >= 10.0) & (freqs <= 60.0)] ** 2))
    total_energy = float(np.sum(spectrum**2))
    assert total_energy > 0.0
    assert in_band_energy / total_energy > 0.99, "带外能量占比过高，带限未生效"


def test_input_snr_db_matches_definition() -> None:
    """``input_snr_db`` 与解析定义一致（独立手算）。"""
    clean = np.array([[1.0, -2.0], [3.0, -4.0]], dtype=np.float64)
    noise = np.array([[0.5, 1.0], [-1.5, 2.0]], dtype=np.float64)
    got = input_snr_db(clean, clean + noise)
    expected = 10.0 * np.log10(float(np.sum(clean**2)) / float(np.sum(noise**2)))
    assert got == pytest.approx(expected, abs=1e-12)
