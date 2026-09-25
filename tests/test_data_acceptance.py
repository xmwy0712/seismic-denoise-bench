"""P0.4 数据验收链：主频回算 / 视速度回算 / 双实现 NMS。

三项验收门（P0.4 任务 3，**协议值，不得放大**）
----------------------------------------------
a) **Ricker 主频回算 ≤ 5%**：沿用 P0.2 测量口径（FFT 零填充 ≥65536 点 +
   峰值邻域三点抛物线插值），对 ``f_main ∈ {15, 25, 40} Hz`` 各测一次。
b) **线性干扰视速度回算 ≤ 10%**：2D f-k 谱能量峰 ``(f, k)`` → ``v = f / k``；
   至少三档视速度各测一次。
c) **无噪正演双实现 NMS ≤ 1e-6**：时域直接褶积 vs 频域乘积褶积。

坐标与单位（b 项）
------------------
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

避开混叠区：空间 Nyquist 波数 ``k_nyq = 1/(2·dx)``。本用例取 ``dx = 5 m``
→ ``k_nyq = 0.1`` 周/米；``f_main = 30 Hz``；三档视速度对应脊 ``k = 30/v``
分别为 0.0375 / 0.02 / 0.01，均远小于 ``k_nyq``，无空间混叠。
时间上 ``f_main = 30 Hz << f_nyq = 250 Hz``，无时间混叠。

随机性：全部经显式 ``np.random.default_rng(seed)`` 注入，种子固定。
"""

from __future__ import annotations

import numpy as np
import pytest

from bench.data.synthetic import (
    add_band_limited_noise,
    add_linear_coherent,
    forward,
    reflectivity,
)
from bench.data.ricker import estimate_peak_frequency, ricker
from ref_forward import forward_frequency_domain, normalized_mean_square_error

# --- 预注册容差（协议值，不得放大）---------------------------------------------
TOL_F_PEAK = 0.05  # 主频回算相对误差上限
TOL_V_APP = 0.10  # 视速度回算相对误差上限
TOL_NMS = 1e-6  # 双实现归一化均方误差上限
# -----------------------------------------------------------------------------

N_FFT = 65536
DT = 0.002  # s
DX = 5.0  # m
F_MAINS = (15.0, 25.0, 40.0)
V_APPS = (800.0, 1500.0, 3000.0)
F_LINEAR = 30.0  # 线性干扰子波主频 (Hz)
N_SAMPLES = 512
N_TRACES = 64
SEED = 20260925


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
    spectrum = np.fft.fftshift(
        np.fft.fft2(data * window_t * window_x), axes=1
    )
    magnitude = np.abs(spectrum)

    freqs = np.fft.fftfreq(n_samples, d=dt)  # 周/秒
    wavenumbers = np.fft.fftshift(np.fft.fftfreq(n_traces, d=dx))  # 周/米

    positive_f = freqs > 0.0
    negative_k = wavenumbers < 0.0
    magnitude_patch = magnitude[np.ix_(positive_f, negative_k)]
    freqs_pos = freqs[positive_f]
    wavenumbers_neg = wavenumbers[negative_k]

    # 说明：由 G(f,k) = W_hat(f) * delta(k + f/v) 得脊线 k = -f/v，
    # 故 f>0 的物理有意义分支落在 k<0。（实数据谱共轭对称，k>0 分支 equivalente 镜像。）
    flat_index = int(np.argmax(magnitude_patch))
    i_f, i_k = np.unravel_index(flat_index, magnitude_patch.shape)

    f_peak = float(freqs_pos[i_f])
    k_peak = float(wavenumbers_neg[i_k])

    # 沿 f 轴抛物线细化
    if 0 < i_f < magnitude_patch.shape[0] - 1:
        y0, y1, y2 = (float(magnitude_patch[i_f - 1, i_k]),
                      float(magnitude_patch[i_f, i_k]),
                      float(magnitude_patch[i_f + 1, i_k]))
        denom = y0 - 2.0 * y1 + y2
        if denom != 0.0:
            delta = 0.5 * (y0 - y2) / denom
            if abs(delta) <= 1.0:
                df = abs(float(freqs[1] - freqs[0]))
                f_peak += delta * df

    # 沿 k 轴抛物线细化
    if 0 < i_k < magnitude_patch.shape[1] - 1:
        y0, y1, y2 = (float(magnitude_patch[i_f, i_k - 1]),
                      float(magnitude_patch[i_f, i_k]),
                      float(magnitude_patch[i_f, i_k + 1]))
        denom = y0 - 2.0 * y1 + y2
        if denom != 0.0:
            delta = 0.5 * (y0 - y2) / denom
            if abs(delta) <= 1.0:
                dk = abs(float(wavenumbers[1] - wavenumbers[0]))
                k_peak -= delta * dk

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
# c) 双实现 NMS ≤ 1e-6
# =============================================================================
def test_c_forward_two_implementations_nms_within_1e_minus_6() -> None:
    """无噪正演：时域直接褶积 vs 频域乘积褶积，NMS ≤ 1e-6。"""
    rng = np.random.default_rng(SEED)
    refl = reflectivity(200, rng)
    _t, wav = ricker(25.0, DT, 101)

    time_domain = forward(refl, wav, n_traces=3)
    frequency_domain = forward_frequency_domain(refl, wav, n_traces=3)

    assert time_domain.shape == frequency_domain.shape
    nms = normalized_mean_square_error(time_domain, frequency_domain)
    assert nms <= TOL_NMS, f"双实现 NMS={nms:.3e} 超出 {TOL_NMS:.0e}"


# =============================================================================
# 辅助：显式 rng 注入与形状约定
# =============================================================================
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
    """同一显式种子必须逐元素复现（P1 逐配置固定种子的前提）。"""
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
