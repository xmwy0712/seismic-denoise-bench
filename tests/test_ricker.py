"""Ricker 子波验收测试。

协议依据
--------
docs/protocol-v5.md 第七节：
    "Ricker 主频由频谱峰值回算，误差不超过设定值的 5%"

本测试用「频谱峰值回算」的方式复现该验收条款。

测量方法
--------
FFT 零填充至 65536 点，频率分辨率 = (1/dt) / 65536。
对峰值邻域做三点抛物线插值细化峰值位置。
以上仅为提高**测量**精度；判定阈值恒为协议值 5%，不因测量精度提高而收紧或放宽。

关于采样与峰值位置
------------------
默认 ``t0 = (n_samples - 1) * dt / 2`` 使子波关于时间轴**中心对称**。
当 ``n_samples`` 为偶数时 t0 落在两个样点之间（例如 512 点时 t0 位于
第 255 与第 256 个样点之间），因此离散峰值由这两个样点**并列**取得，
且 ``max(w) < 1`` 属正常现象，不构成缺陷。需要精确取到 1 时，
应显式令 t0 与某个样点对齐（见 test_ricker_amplitude_normalization）。
"""

from __future__ import annotations

import numpy as np
import pytest

from bench.data.ricker import estimate_peak_frequency, ricker

# --- 冻结的测量参数（P0.2 定，后续如需更改必须另行留痕）---------------------------
N_FFT = 65536
TOL_REL = 0.05  # 协议预注册容差：5%
# -----------------------------------------------------------------------------

DT = 0.002  # s，合成观测常用采样间隔
N_SAMPLES = 512  # 偶数：峰值落在两样点之间
N_SAMPLES_ODD = 511  # 奇数：中心恰为一个样点

F_MAINS = (15.0, 25.0, 40.0)  # 合成观测常用主频档位 (Hz)


# ---------------------------------------------------------------------------
# 协议验收：主频回算误差 <= 5%
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("f_main", F_MAINS)
def test_ricker_peak_frequency_within_5pct(f_main: float) -> None:
    """主频由频谱峰值回算的相对误差不得超过 5%（协议第七条）。"""
    _t, w = ricker(f_main, DT, N_SAMPLES)
    f_est = estimate_peak_frequency(w, DT, n_fft=N_FFT, interpolate=True)
    rel_err = abs(f_est - f_main) / f_main

    assert rel_err <= TOL_REL, (
        f"设定主频 {f_main} Hz，回算主频 {f_est:.6f} Hz，"
        f"相对误差 {rel_err:.6%} > 阈值 {TOL_REL:.0%}"
    )


@pytest.mark.parametrize("f_main", F_MAINS)
def test_ricker_peak_frequency_odd_length_within_5pct(f_main: float) -> None:
    """奇数长度（中心恰为样点）下同样满足 5% 验收。"""
    _t, w = ricker(f_main, DT, N_SAMPLES_ODD)
    f_est = estimate_peak_frequency(w, DT, n_fft=N_FFT, interpolate=True)
    rel_err = abs(f_est - f_main) / f_main
    assert rel_err <= TOL_REL, f"{f_main} Hz -> {f_est:.6f} Hz, err={rel_err:.6%}"


# ---------------------------------------------------------------------------
# 波形健全性
# ---------------------------------------------------------------------------
def test_ricker_symmetry_and_peak() -> None:
    """子波应关于时间轴中心对称，且极大值由中心两样点并列取得。"""
    t, w = ricker(25.0, DT, N_SAMPLES)
    n = w.size
    np.testing.assert_allclose(w, w[::-1], rtol=0, atol=1e-12)

    peak_idx = np.flatnonzero(np.isclose(w, w.max(), rtol=0, atol=1e-15))
    assert list(peak_idx) == [n // 2 - 1, n // 2], peak_idx

    t0 = (n - 1) * DT / 2.0
    assert t0 == pytest.approx(0.5 * (t[n // 2 - 1] + t[n // 2]))


def test_ricker_peak_aligned_gives_unit_amplitude() -> None:
    """t0 与样点对齐时，峰值振幅应精确为 1（公式在 tau=0 处取 1）。"""
    n, k = 512, 100
    t, w = ricker(25.0, DT, n, t0=k * DT)
    assert float(w[k]) == pytest.approx(1.0, abs=1e-15)
    assert float(np.max(w)) == pytest.approx(1.0, abs=1e-15)
    # 极大值唯一
    assert int(np.argmax(w)) == k


def test_ricker_peak_amplitude_bounded_when_unaligned() -> None:
    """中心落在两样点之间时，峰值应 <= 1 且接近 1。"""
    _t, w = ricker(25.0, DT, N_SAMPLES)
    assert 0.0 < float(np.max(w)) <= 1.0
    assert float(np.max(w)) > 0.95


def test_ricker_zero_mean() -> None:
    """Ricker 子波理论均值为 0（离散近似下应极小）。"""
    _t, w = ricker(25.0, DT, N_SAMPLES)
    assert abs(float(np.mean(w))) < 1e-3


def test_ricker_odd_length_has_unique_center_sample() -> None:
    """奇数长度时，中心样点为唯一极大值且振幅为 1。"""
    t, w = ricker(25.0, DT, N_SAMPLES_ODD)
    k = int(np.argmax(w))
    assert k == N_SAMPLES_ODD // 2
    assert float(w[k]) == pytest.approx(1.0, abs=1e-15)
    assert t[k] == pytest.approx(k * DT)


def test_estimate_peak_frequency_linearity_in_f_main() -> None:
    """回算主频应随设定主频单调递增（辅助健全性检查）。"""
    ests = [
        estimate_peak_frequency(ricker(f, DT, N_SAMPLES)[1], DT, n_fft=N_FFT)
        for f in F_MAINS
    ]
    assert all(b > a for a, b in zip(ests, ests[1:])), ests
    for f, e in zip(F_MAINS, ests):
        assert abs(e - f) / f <= TOL_REL


def test_ricker_invalid_inputs() -> None:
    """非法输入应显式报错，而不是静默产生错误结果。"""
    with pytest.raises(ValueError):
        ricker(-1.0, DT, N_SAMPLES)
    with pytest.raises(ValueError):
        ricker(25.0, 0.0, N_SAMPLES)
    with pytest.raises(ValueError):
        ricker(25.0, DT, 1)
