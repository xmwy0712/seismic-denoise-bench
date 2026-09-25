"""P0.3 对拍验收测试：ΔSNR / Lsig 与闭式解析解对照。

对拍原则（任务单 P0.3）
-----------------------
**期望值必须来自闭式解析推导，写成字面常量**；禁止用被测代码自身计算期望值
——否则属自证，不构成验收。

容差为任务单预注册值，**不得放大**：
  * ``1e-12`` 档：A.1（ΔSNR 恒等）、B.1（Lsig 恒等）、B.2（Lsig 线性）
  * ``1e-10`` 档：A.2（ΔSNR 二分噪声）

本测试仅使用**确定性构造数组**，不引入随机数。

触发用例依据（P0.3-Am1 裁定 1）
--------------------------------
``n_T = math.floor(1/(f_main*dt) + 0.5)``（half-up）；40 Hz @ dt=2 ms 时
``1/(40*0.002)`` 恰为 **12.5**，须取 **13**（内建 ties-to-even 舍入会给 12，**禁止**）。
"""

from __future__ import annotations

import numpy as np
import pytest

from bench.metrics import (
    delta_snr_db,
    denominator_was_zero,
    dilation_length_samples,
    event_mask,
    lsig,
    reset_denominator_flag,
    snr_db,
)

# --- 预注册容差（不得放大）-----------------------------------------------------
TOL_STRICT = 1e-12
TOL_MEDIUM = 1e-10
# -----------------------------------------------------------------------------

# --- 解析解字面常量（禁止由被测代码计算）---------------------------------------
# A.2 推导：ΔSNR = 10*log10(4)
EXPECTED_DELTA_SNR_HALF_NOISE = 6.020599913279624
# A.1 推导：snr_db(s,x) - snr_db(s,x) ≡ 0
EXPECTED_DELTA_SNR_IDENTITY = 0.0
# B.1 推导：||M*0||^2 / ||Ms||^2 = 0
EXPECTED_LSIG_IDENTITY = 0.0
# B.2 推导：delta^2 = 0.1^2
EXPECTED_LSIG_LINEAR_DELTA_0P1 = 0.01
# -----------------------------------------------------------------------------

DT = 0.002  # s
F_MAINS = (15.0, 25.0, 40.0)


def _deterministic_arrays() -> tuple[np.ndarray, np.ndarray]:
    """确定性构造 (s, n)：s 真值、n 噪声。无随机数。

    ||s||^2 = 1+4+9+16+0.25+2.25 = 32.5
    ||n||^2 = 0.25+1+2.25+4+0.0625+0.5625 = 8.125
    """
    truth = np.array([[1.0, -2.0], [3.0, -4.0], [0.5, 1.5]], dtype=np.float64)
    noise = np.array([[0.5, 1.0], [-1.5, 2.0], [0.25, -0.75]], dtype=np.float64)
    return truth, noise


def _event_fixture(f_main: float = 25.0) -> tuple[np.ndarray, np.ndarray]:
    """构造带单一孤立事件的真值及其掩码（阈值 0.5）。"""
    truth = np.zeros((512, 4), dtype=np.float64)
    truth[256, :] = 10.0
    return truth, event_mask(truth, f_main=f_main, dt=DT, threshold=0.5)


# =============================================================================
# A. ΔSNR 闭式解
# =============================================================================
def test_A1_delta_snr_identity_is_zero() -> None:
    """A.1  ``y = x`` → ΔSNR = 0.0（容差 1e-12）。

    解析推导：``snr_db(s,x) - snr_db(s,x) ≡ 0``，与 s、x 取值无关。
    """
    truth, noise = _deterministic_arrays()
    noisy = truth + noise
    output = noisy  # 未去噪

    got = delta_snr_db(truth, noisy, output)

    assert got == pytest.approx(EXPECTED_DELTA_SNR_IDENTITY, abs=TOL_STRICT), (
        f"ΔSNR(y=x) 期望 {EXPECTED_DELTA_SNR_IDENTITY}，实测 {got!r}"
    )


def test_A2_delta_snr_half_noise_is_ten_log10_4() -> None:
    """A.2  ``y = s + n/2`` → ΔSNR = 10*log10(4) = 6.020599913279624（容差 1e-10）。

    解析推导::

        ||y - s||^2 = ||n/2||^2 = ||n||^2 / 4
        ||x - s||^2 = ||n||^2
        ΔSNR = 10*log10(||s||^2 / (||n||^2/4)) - 10*log10(||s||^2 / ||n||^2)
             = 10*log10(4)

    ``||s||^2`` 在两式中约去，故结果与 s、n 的具体取值无关。
    """
    truth, noise = _deterministic_arrays()
    noisy = truth + noise
    output = truth + noise / 2.0

    got = delta_snr_db(truth, noisy, output)

    assert np.isfinite(got)
    assert got == pytest.approx(EXPECTED_DELTA_SNR_HALF_NOISE, abs=TOL_MEDIUM), (
        f"ΔSNR(y=s+n/2) 期望 {EXPECTED_DELTA_SNR_HALF_NOISE}，实测 {got!r}"
    )


def test_A3_perfect_denoise_is_pos_inf_not_nan_and_sets_flag() -> None:
    """A.3  ``y = s`` → ``+inf``，非 NaN，且内部标志已置（不抛异常）。

    解析推导：``||y-s||^2 = 0`` ⇒ ``snr_db(s,y) = +inf``；
    而 ``||x-s||^2 > 0`` ⇒ ``snr_db(s,x)`` 有限 ⇒ ΔSNR ``= +inf``。
    """
    truth, noise = _deterministic_arrays()
    noisy = truth + noise

    reset_denominator_flag()
    got = delta_snr_db(truth, noisy, truth)

    assert np.isposinf(got), f"期望 +inf，实测 {got!r}"
    assert not np.isnan(got), "结果不得为 NaN"
    assert denominator_was_zero() is True, "完美去噪时内部标志应已置位"


def test_A4_non_finite_input_raises_value_error() -> None:
    """含非有限值输入 → ``ValueError``（不得静默返回 NaN）。"""
    truth, noise = _deterministic_arrays()

    x_nan = truth + noise
    x_nan[0, 0] = np.nan
    with pytest.raises(ValueError):
        delta_snr_db(truth, x_nan, truth + noise / 2.0)

    y_inf = truth + noise / 2.0
    y_inf[1, 1] = np.inf
    with pytest.raises(ValueError):
        delta_snr_db(truth, truth + noise, y_inf)


def test_A5_snr_db_matches_hand_computed_value() -> None:
    """``snr_db`` 直接式与手算闭式值一致（容差 1e-10）。

    手算：``||s||^2 = 32.5``，``||n||^2 = 8.125``，
    ``10*log10(32.5/8.125) = 10*log10(4) = 6.020599913279624``。
    """
    truth, noise = _deterministic_arrays()
    noisy = truth + noise

    got = snr_db(truth, noisy)

    assert got == pytest.approx(EXPECTED_DELTA_SNR_HALF_NOISE, abs=TOL_MEDIUM), (
        f"snr_db 期望 {EXPECTED_DELTA_SNR_HALF_NOISE}，实测 {got!r}"
    )


def test_A6_shape_mismatch_and_bad_dtype_raise() -> None:
    """形状不符 / 非数值 / 非二维 → ``ValueError``。"""
    truth, noise = _deterministic_arrays()
    with pytest.raises(ValueError):
        snr_db(truth, np.zeros((4, 1)))
    with pytest.raises(ValueError):
        snr_db(truth[:, 0], truth[:, 0])  # 一维
    with pytest.raises(ValueError):
        snr_db(np.array([["a", "b"]]), np.array([["a", "b"]]))


def test_A7_zero_truth_energy_raises() -> None:
    """全零真值 + 非零噪声 → ``ValueError``（SNR 退化为 -inf，属配置错误）。"""
    truth = np.zeros((8, 2), dtype=np.float64)
    noisy = np.ones((8, 2), dtype=np.float64)
    with pytest.raises(ValueError):
        snr_db(truth, noisy)


def test_A9_double_perfect_returns_zero_not_nan() -> None:
    """``x == s`` 且 ``y == s`` → ΔSNR = 0.0（**非 NaN**），且标志置位。

    解析推导：两项的噪声能量均为 0 ⇒ 两项均取 ``+inf``；
    IEEE-754 下 ``inf - inf = NaN``，但物理含义是"未产生任何改变"，
    故 ΔSNR **恰为 0.0**（本实现裁定 R1）。

    本用例为跨模型审查发现项（agy 报告不符点 2）的回归测试。
    """
    truth = np.ones((16, 3), dtype=np.float64)
    reset_denominator_flag()

    got = delta_snr_db(truth, truth.copy(), truth.copy())

    assert not np.isnan(got), "不得返回 NaN（inf - inf 的默认结果）"
    assert got == pytest.approx(EXPECTED_DELTA_SNR_IDENTITY, abs=TOL_STRICT), (
        f"双完美应得 {EXPECTED_DELTA_SNR_IDENTITY}，实测 {got!r}"
    )
    assert denominator_was_zero() is True, "去噪输出完美，标志应置位"


def test_A10_input_perfect_only_yields_neg_inf_and_flag_not_set() -> None:
    """仅输入完美（``x == s``）而输出变差 → ``-inf``，且标志**不**置位。

    解析推导：``snr_db(s,x) = +inf``、``snr_db(s,y)`` 有限 ⇒ ``-inf``。
    标志按规格只绑定"``||y-s||^2 == 0``（完美去噪）"，故此处不得置位。

    本用例为跨模型审查发现项（agy 报告不符点 3）的回归测试。
    """
    truth = np.ones((16, 3), dtype=np.float64)
    noisy_output = truth + 1.0  # 输出反而变差

    reset_denominator_flag()
    got = delta_snr_db(truth, truth.copy(), noisy_output)

    assert np.isneginf(got), f"期望 -inf，实测 {got!r}"
    assert denominator_was_zero() is False, (
        "标志只反映去噪输出是否完美；输入完美不应置位（裁定 R3）"
    )


def test_A11_empty_array_raises() -> None:
    """0 元素数组 → ``ValueError``（否则能量恒为 0 会被误判为完美去噪）。

    本用例为跨模型审查发现项（agy 报告其它问题 4）的回归测试。
    """
    empty = np.zeros((0, 4), dtype=np.float64)
    with pytest.raises(ValueError):
        snr_db(empty, empty)
    with pytest.raises(ValueError):
        delta_snr_db(empty, empty, empty)


def test_A8_float32_input_is_promoted_and_matches_float64() -> None:
    """``float32`` 输入内部提升为 ``float64``；同值下结果与 ``float64`` 一致。"""
    truth64, noise64 = _deterministic_arrays()
    truth32 = truth64.astype(np.float32)
    noise32 = noise64.astype(np.float32)

    got32 = delta_snr_db(truth32, truth32 + noise32, truth32 + noise32 / 2.0)
    got64 = delta_snr_db(truth64, truth64 + noise64, truth64 + noise64 / 2.0)

    assert got32 == pytest.approx(got64, abs=1e-6)


# =============================================================================
# B. Lsig 闭式解
# =============================================================================
def test_B1_lsig_identity_is_zero() -> None:
    """B.1  ``y = s`` → Lsig = 0.0（容差 1e-12）。

    解析推导：``||M(y-s)||^2 = ||M·0||^2 = 0`` ⇒ ``Lsig = 0 / ||Ms||^2 = 0``
    （分母非零由 fixture 保证）。
    """
    truth, mask = _event_fixture()
    output = truth.copy()

    got = lsig(truth, output, mask)

    assert got == pytest.approx(EXPECTED_LSIG_IDENTITY, abs=TOL_STRICT), (
        f"Lsig(y=s) 期望 {EXPECTED_LSIG_IDENTITY}，实测 {got!r}"
    )


def test_B2_lsig_linear_scaling_is_delta_squared() -> None:
    """B.2  ``y = s + δs``（δ=0.1）→ Lsig = δ² = 0.01（容差 1e-12）。

    解析推导::

        M(y-s) = M(δs) = δ·Ms
        ||M(δs)||^2 = δ² ||Ms||^2
        Lsig = δ² ||Ms||^2 / ||Ms||^2 = δ² = 0.01

    结论与掩码形状、阈值取值**无关**（只要 ``||Ms||^2 ≠ 0``）。
    """
    truth, mask = _event_fixture()
    delta = 0.1
    output = truth + delta * truth

    got = lsig(truth, output, mask)

    assert got == pytest.approx(EXPECTED_LSIG_LINEAR_DELTA_0P1, abs=TOL_STRICT), (
        f"Lsig(y=s+0.1s) 期望 {EXPECTED_LSIG_LINEAR_DELTA_0P1}，实测 {got!r}"
    )


def test_B3_lsig_zero_denominator_raises() -> None:
    """``||M s||^2 == 0`` → ``ValueError``（不得返回 inf / NaN 掩盖）。"""
    truth = np.zeros((64, 2), dtype=np.float64)
    output = truth + 1.0
    mask = np.zeros_like(truth, dtype=bool)  # 全 False
    with pytest.raises(ValueError):
        lsig(truth, output, mask)


def test_B4_lsig_rejects_non_bool_mask_and_shape_mismatch() -> None:
    """掩码必须为布尔、形状须一致；否则显式报错。"""
    truth, mask = _event_fixture()
    with pytest.raises(ValueError):
        lsig(truth, truth.copy(), mask.astype(np.int64))
    with pytest.raises(ValueError):
        lsig(truth, truth[:-1].copy(), mask)
    with pytest.raises(ValueError):
        lsig(truth, truth.copy(), mask[:-1])


# =============================================================================
# C. 掩码语义
# =============================================================================
def test_C1_freezing_rule_half_up_at_tie() -> None:
    """C.1（冻结规则触发用例）``1/(40*0.002)`` 恰为 ``12.5`` → ``n_T == 13``。

    Am1 裁定 1 要求：断言 ``repr(1.0/(40.0*0.002)) == '12.5'`` 且 ``n_T == 13``；
    Python 内建 ties-to-even 舍入会给出 12，本项目**禁止**该舍入方式。
    """
    assert repr(1.0 / (40.0 * 0.002)) == "12.5", (
        f"前提不成立：repr(1/(40*0.002)) = {repr(1.0/(40.0*0.002))!r}，应为 '12.5'"
    )
    assert dilation_length_samples(40.0, DT) == 13, "half-up 应给 13（ties-to-even 会给 12）"


def test_C2_dilation_lengths_all_frequencies() -> None:
    """C.2 逐主频实测 ``n_T``（dt = 2 ms，half-up）。

    解析推导（Am1 裁定 1）：``1/(15*0.002) = 33.333…`` → 33；
    ``1/(25*0.002) = 20.0`` → 20；``1/(40*0.002) = 12.5`` → **13**（half-up）。
    """
    assert dilation_length_samples(15.0, DT) == 33
    assert dilation_length_samples(25.0, DT) == 20
    assert dilation_length_samples(40.0, DT) == 13


def test_C3_mask_time_extent_equals_n_T_within_one_sample() -> None:
    """C.3 单孤立尖峰：掩码沿时间轴的支撑长度 ≈ ``n_T``（±1 样点，取整所致）。

    依据原单任务 2.C：``断言掩码沿时间轴的长度 = 尖峰支撑 + n_T（±1 样点）``。
    """
    for f_main in F_MAINS:
        n_T = dilation_length_samples(f_main, DT)
        truth = np.zeros((512, 3), dtype=np.float64)
        truth[256, :] = 10.0
        mask = event_mask(truth, f_main=f_main, dt=DT, threshold=0.5)

        rows = np.flatnonzero(mask[:, 0])
        extent = int(rows[-1] - rows[0] + 1)
        assert abs(extent - n_T) <= 1, (
            f"f_main={f_main}: 期望支撑≈n_T={n_T}，实测 {extent}"
        )


def test_C4_mask_does_not_expand_along_trace_axis() -> None:
    """C.4 掩码在道方向不扩张：所有道列完全一致（全道同时有事件时）。"""
    for f_main in F_MAINS:
        truth = np.zeros((256, 5), dtype=np.float64)
        truth[128, :] = 10.0
        mask = event_mask(truth, f_main=f_main, dt=DT, threshold=0.5)
        for column in range(1, mask.shape[1]):
            assert np.array_equal(mask[:, 0], mask[:, column]), (
                f"f_main={f_main}: 第 {column} 道与第 0 道掩码不一致 → 道方向发生扩张"
            )


def test_C5_single_trace_event_does_not_leak_to_other_traces() -> None:
    """C.5 仅第 0 道有事件时，其余道不得被污染（道方向不扩张的强判据）。"""
    truth = np.zeros((256, 4), dtype=np.float64)
    truth[128, 0] = 10.0
    mask = event_mask(truth, f_main=25.0, dt=DT, threshold=0.5)

    assert mask[:, 0].any(), "第 0 道应检出事件"
    assert not mask[:, 1:].any(), "其余道不应被胀出事件（道方向不得扩张）"


def test_C6_threshold_is_inclusive_and_explicit() -> None:
    """C.6 阈值语义为 ``|s| >= threshold``（含等号），且 threshold 为显式参数。"""
    truth = np.zeros((64, 2), dtype=np.float64)
    truth[32, :] = 0.5
    mask_at_threshold = event_mask(truth, f_main=25.0, dt=DT, threshold=0.5)
    assert mask_at_threshold[32, 0], "|s| == threshold 应被检出（含等号）"

    mask_above = event_mask(truth, f_main=25.0, dt=DT, threshold=0.5000001)
    assert not mask_above[32, 0], "略高于 threshold 时应不检出"


def test_C8_boundary_event_mask_is_truncated_documented_behaviour() -> None:
    """C.8 边界语义（已知项，如实固定）：贴边事件掩码支撑 < ``n_T``，不环绕。

    任何非环绕膨胀在数组端都会截断，属掩码构造的固有性质。
    本用例把该行为**固定为已知语义**，防止将来被误当回归。
    中间位置的事件不受影响（见 C.3）。
    """
    n_T = dilation_length_samples(25.0, DT)  # = 20

    top = np.zeros((100, 2), dtype=np.float64)
    top[0, :] = 10.0
    mask_top = event_mask(top, f_main=25.0, dt=DT, threshold=0.5)
    rows_top = np.flatnonzero(mask_top[:, 0])
    assert int(rows_top[-1] - rows_top[0] + 1) < n_T, "顶部贴边应被截断（文档化行为）"
    assert rows_top[0] == 0, "顶部贴边时掩码应起始于第 0 样点"

    bottom = np.zeros((100, 2), dtype=np.float64)
    bottom[99, :] = 10.0
    mask_bottom = event_mask(bottom, f_main=25.0, dt=DT, threshold=0.5)
    rows_bottom = np.flatnonzero(mask_bottom[:, 0])
    assert int(rows_bottom[-1] - rows_bottom[0] + 1) < n_T, "底部贴边应被截断（文档化行为）"
    assert rows_bottom[-1] == 99, "底部贴边时掩码应终止于末样点"


def test_C9_mask_accepts_bool_dtype_via_kind() -> None:
    """C.9 布尔判定用 ``dtype.kind``，标准 bool 掩码应被接受。

    本用例为跨模型审查发现项（agy 报告其它问题 3）的回归测试。
    """
    truth, mask = _event_fixture()
    assert mask.dtype.kind == "b"
    value = lsig(truth, truth.copy(), mask)
    assert value == pytest.approx(EXPECTED_LSIG_IDENTITY, abs=TOL_STRICT)

    # 非布尔必须被拒
    with pytest.raises(ValueError):
        lsig(truth, truth.copy(), mask.astype(np.int8))


def test_C7_dilation_length_rejects_invalid_parameters() -> None:
    """非法参数显式报错（不得静默产生错误结果）。"""
    with pytest.raises(ValueError):
        dilation_length_samples(0.0, DT)
    with pytest.raises(ValueError):
        dilation_length_samples(-15.0, DT)
    with pytest.raises(ValueError):
        dilation_length_samples(15.0, 0.0)
    with pytest.raises(ValueError):
        dilation_length_samples(float("nan"), DT)
    with pytest.raises(ValueError):
        # f_main 极大 → 1/(f*dt) → 0 → n_T < 1（f*dt > 2 即触发）
        dilation_length_samples(1e6, DT)
