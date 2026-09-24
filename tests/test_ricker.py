"""Ricker 子波验收测试。

协议依据
--------
docs/protocol-v5.md 第七节：
    "Ricker 主频由频谱峰值回算，误差不超过设定值的 5%"

任务单依据（归档件）
--------------------
`docs/task-sheets/P0.1R+P0.2-联合任务单-2026-09-24.md` 第二部分第 5 条 b 项
（SHA256 4559F626…A75AF）规定：

    f_main ∈ {15, 25, 40} Hz，dt = 0.002 s，**n = 101**，
    取 FFT 模峰对应频率，与 f_main 相对误差 ≤5%。
    实现要求：FFT 零填充至 ≥65536 点（否则 df≈5 Hz、量化误差可达 20%，
    会造成假失败），并对峰邻域做抛物线插值取亚 bin 精度。

本测试**保留 n = 101 的原始覆盖**，并额外覆盖 n = 511（奇数）与 n = 512（偶数），
后者与合成数据实际道长一致（P0.2 amendment，WorkBuddy 裁定采纳）。

关于采样与峰值位置
------------------
默认 ``t0 = (n_samples - 1) * dt / 2`` 使子波关于时间轴**中心对称**。
当 ``n_samples`` 为偶数时 t0 落在两个样点之间（例如 512 点时 t0 位于
第 255 与第 256 个样点之间），因此离散峰值由这两个样点**并列**取得，
且 ``max(w) < 1`` 属正常现象，不构成缺陷（见 ``ricker.py`` 模块 docstring）。
"""

from __future__ import annotations

import numpy as np
import pytest

from bench.data.ricker import estimate_peak_frequency, ricker

# --- 冻结的测量参数（P0.2 定，后续如需更改必须另行留痕）---------------------------
N_FFT = 65536
TOL_REL = 0.05  # 协议预注册容差：5%
# -----------------------------------------------------------------------------

DT = 0.002  # s，任务单规定

N_101 = 101  # 奇数：任务单原始规定长度
N_511 = 511  # 奇数
N_512 = 512  # 偶数：合成数据实际道长，峰值落在两样点之间

F_MAINS = (15.0, 25.0, 40.0)  # 任务单规定主频档位 (Hz)


# ---------------------------------------------------------------------------
# 协议验收：主频回算误差 <= 5%
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("f_main", F_MAINS)
def test_peak_freq_n101(f_main: float) -> None:
    """n = 101（任务单原始规定）主频回算误差 ≤ 5%。"""
    _t, w = ricker(f_main, DT, N_101)
    f_est = estimate_peak_frequency(w, DT, n_fft=N_FFT, interpolate=True)
    rel_err = abs(f_est - f_main) / f_main
    assert rel_err <= TOL_REL, (
        f"n=101 设定主频 {f_main} Hz，回算 {f_est:.6f} Hz，误差 {rel_err:.6%} > {TOL_REL:.0%}"
    )


@pytest.mark.parametrize("f_main", F_MAINS)
def test_peak_freq_n511_odd(f_main: float) -> None:
    """n = 511（奇数，中心恰为样点）主频回算误差 ≤ 5%。"""
    _t, w = ricker(f_main, DT, N_511)
    f_est = estimate_peak_frequency(w, DT, n_fft=N_FFT, interpolate=True)
    rel_err = abs(f_est - f_main) / f_main
    assert rel_err <= TOL_REL, f"n=511 {f_main} Hz -> {f_est:.6f} Hz, err={rel_err:.6%}"


@pytest.mark.parametrize("f_main", F_MAINS)
def test_peak_freq_n512_even(f_main: float) -> None:
    """n = 512（偶数，峰值落在两样点之间）主频回算误差 ≤ 5%。"""
    _t, w = ricker(f_main, DT, N_512)
    f_est = estimate_peak_frequency(w, DT, n_fft=N_FFT, interpolate=True)
    rel_err = abs(f_est - f_main) / f_main
    assert rel_err <= TOL_REL, f"n=512 {f_main} Hz -> {f_est:.6f} Hz, err={rel_err:.6%}"


def test_zeropad_is_necessary() -> None:
    """零填充的必要性：点数过少时频率量化误差会显著增大。

    n_fft = 101 时 df ≈ 5 Hz，40 Hz 档位的量化误差可达 ~12%；
    零填充到 65536 后误差降至 1e-6 % 量级。本测试锁定该结论。
    """
    _t, w = ricker(40.0, DT, N_101)
    f_coarse = estimate_peak_frequency(w, DT, n_fft=128, interpolate=False)
    f_fine = estimate_peak_frequency(w, DT, n_fft=N_FFT, interpolate=True)
    err_coarse = abs(f_coarse - 40.0) / 40.0
    err_fine = abs(f_fine - 40.0) / 40.0
    assert err_coarse > err_fine
    assert err_fine <= TOL_REL


# ---------------------------------------------------------------------------
# 波形健全性
# ---------------------------------------------------------------------------
def test_ricker_symmetry_and_peak() -> None:
    """子波应关于时间轴中心对称，且极大值由中心两样点并列取得（偶数 n）。"""
    t, w = ricker(25.0, DT, N_512)
    n = w.size
    np.testing.assert_allclose(w, w[::-1], rtol=0, atol=1e-12)

    peak_idx = np.flatnonzero(np.isclose(w, w.max(), rtol=0, atol=1e-15))
    assert list(peak_idx) == [n // 2 - 1, n // 2], peak_idx

    t0 = (n - 1) * DT / 2.0
    assert t0 == pytest.approx(0.5 * (t[n // 2 - 1] + t[n // 2]))


def test_ricker_odd_length_has_unique_center_sample() -> None:
    """奇数长度时，中心样点为唯一极大值且振幅为 1（解析归一化）。"""
    t, w = ricker(25.0, DT, N_101)
    k = int(np.argmax(w))
    assert k == N_101 // 2
    assert float(w[k]) == pytest.approx(1.0, abs=1e-15)
    assert t[k] == pytest.approx(k * DT)


def test_ricker_peak_aligned_gives_unit_amplitude() -> None:
    """t0 与样点对齐时，峰值振幅应精确为 1（解析归一化）。"""
    n, k = 512, 100
    _t, w = ricker(25.0, DT, n, t0=k * DT)
    assert float(w[k]) == pytest.approx(1.0, abs=1e-15)
    assert float(np.max(w)) == pytest.approx(1.0, abs=1e-15)
    assert int(np.argmax(w)) == k


def test_ricker_peak_amplitude_bounded_when_unaligned() -> None:
    """偶数 n 时无样点落在 tau=0，故 max(w) < 1（R8 amendment 的推论）。"""
    _t, w = ricker(25.0, DT, N_512)
    mx = float(np.max(w))
    assert 0.0 < mx < 1.0
    assert mx == pytest.approx(0.98158934, abs=1e-8)  # R8 裁定记载的参考值


def test_ricker_zero_mean() -> None:
    """Ricker 子波理论均值为 0（离散近似下应极小）。"""
    _t, w = ricker(25.0, DT, N_512)
    assert abs(float(np.mean(w))) < 1e-3


def test_estimate_peak_frequency_linearity_in_f_main() -> None:
    """回算主频应随设定主频单调递增（辅助健全性检查）。"""
    ests = [
        estimate_peak_frequency(ricker(f, DT, N_101)[1], DT, n_fft=N_FFT)
        for f in F_MAINS
    ]
    assert all(b > a for a, b in zip(ests, ests[1:])), ests
    for f, e in zip(F_MAINS, ests):
        assert abs(e - f) / f <= TOL_REL


def test_ricker_invalid_inputs() -> None:
    """非法输入应显式报错，而不是静默产生错误结果。"""
    with pytest.raises(ValueError):
        ricker(-1.0, DT, N_101)
    with pytest.raises(ValueError):
        ricker(25.0, 0.0, N_101)
    with pytest.raises(ValueError):
        ricker(25.0, DT, 1)
