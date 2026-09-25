"""哨兵语义测试（P0.4-Am1 裁定 2 的新增要求）。

背景
----
R9 把 `snr.py` 的内部机制从"模块级可变标志"改为"不可变结果对象"
（:class:`~bench.metrics.snr.SnrOutcome`），以消除与来源不明预置文件的代码级同源，
并顺带解除原模块级可变状态带来的线程安全限制。

**公开接口未变**：`snr_db` / `delta_snr_db` 仍返回 `float`（下游统计与
`pytest.approx` 直接消费浮点）。哨兵语义改由**附加函数** `snr_outcome` 暴露。

本文件即验证该哨兵语义。
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from bench.metrics import SnrOutcome, delta_snr_db, snr_db, snr_outcome


def _truth_and_noise() -> tuple[np.ndarray, np.ndarray]:
    """确定性构造（无随机数）。真值能量非零、噪声能量非零。"""
    truth = np.array([[1.0, -2.0], [3.0, -4.0], [0.5, 1.5]], dtype=np.float64)
    noise = np.array([[0.5, 1.0], [-1.5, 2.0], [0.25, -0.75]], dtype=np.float64)
    return truth, noise


# ---------------------------------------------------------------------------
# 哨兵：完美输出
# ---------------------------------------------------------------------------
def test_sentinel_perfect_output_flags_true_and_value_is_inf() -> None:
    """完美输出（``y == s``）→ ``denoiser_is_perfect is True`` 且 ``value == math.inf``。"""
    truth, _noise = _truth_and_noise()

    outcome = snr_outcome(truth, truth.copy())

    assert isinstance(outcome, SnrOutcome)
    assert outcome.denoiser_is_perfect is True
    assert outcome.value == math.inf
    assert not math.isnan(outcome.value)


def test_sentinel_non_perfect_output_flags_false() -> None:
    """非完美输出 → ``denoiser_is_perfect is False``，``value`` 有限。"""
    truth, noise = _truth_and_noise()

    outcome = snr_outcome(truth, truth + noise)

    assert outcome.denoiser_is_perfect is False
    assert math.isfinite(outcome.value)


def test_sentinel_is_frozen_dataclass() -> None:
    """结果对象不可变（防止下游意外改写状态）。"""
    truth, noise = _truth_and_noise()
    outcome = snr_outcome(truth, truth + noise)

    with pytest.raises(Exception):
        outcome.value = 0.0  # type: ignore[misc]


def test_public_snr_db_is_thin_wrapper_over_outcome() -> None:
    """``snr_db`` 返回类型为 ``float``，且与 ``snr_outcome(...).value`` 一致。"""
    truth, noise = _truth_and_noise()
    probe = truth + noise

    value = snr_db(truth, probe)

    assert type(value) is float
    assert value == snr_outcome(truth, probe).value


# ---------------------------------------------------------------------------
# 双完美：ΔSNR = 0.0 且状态可查
# ---------------------------------------------------------------------------
def test_double_perfect_delta_is_zero_and_state_inspectable() -> None:
    """``x == s`` 且 ``y == s`` → ΔSNR = ``0.0``，且状态可经附加函数查询。"""
    truth, _noise = _truth_and_noise()

    delta = delta_snr_db(truth, truth.copy(), truth.copy())

    assert delta == 0.0
    assert type(delta) is float
    # 状态可查：输出的去噪项为完美
    assert snr_outcome(truth, truth.copy()).denoiser_is_perfect is True


def test_double_perfect_is_not_nan() -> None:
    """双完美不得退化为 NaN（IEEE-754 下 ``inf - inf`` 即为 NaN，须显式约定）。"""
    truth, _noise = _truth_and_noise()

    delta = delta_snr_db(truth, truth.copy(), truth.copy())

    assert not math.isnan(delta)


def test_perfect_output_only_returns_pos_inf() -> None:
    """仅输出完美 → ``+inf``（非 NaN）。"""
    truth, noise = _truth_and_noise()

    delta = delta_snr_db(truth, truth + noise, truth.copy())

    assert delta == math.inf
    assert not math.isnan(delta)


def test_perfect_input_only_returns_neg_inf() -> None:
    """仅输入无噪而输出变差 → ``-inf``。"""
    truth, _noise = _truth_and_noise()

    delta = delta_snr_db(truth, truth.copy(), truth + 1.0)

    assert delta == -math.inf


# ---------------------------------------------------------------------------
# 公开签名冻结（P0.4-Am1 裁定 2）
# ---------------------------------------------------------------------------
def test_public_signatures_return_plain_floats() -> None:
    """公开函数必须返回**纯 float**，不得返回 dataclass/数组（下游直接消费浮点）。"""
    truth, noise = _truth_and_noise()

    assert type(snr_db(truth, truth + noise)) is float
    assert type(delta_snr_db(truth, truth + noise, truth + noise / 2.0)) is float
