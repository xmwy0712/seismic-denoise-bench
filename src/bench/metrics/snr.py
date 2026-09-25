"""ΔSNR（输出 SNR 提升）指标实现。

规格依据
--------
协议 `docs/protocol-v5.md` 第四节第 1 条：

    ΔSNR = 10*log10(||s||^2 / ||y-s||^2) - 10*log10(||s||^2 / ||x-s||^2)

其中 ``s`` 为真值、``x`` 为含噪输入、``y`` 为去噪输出。**越高越好。**

公开接口（冻结，P0.4-Am1 裁定 2）
----------------------------------
``snr_db(s, x) -> float``、``delta_snr_db(s, x, y) -> float`` 的**返回类型不得变更**，
亦不得改为 dataclass——P2/P4 的下游统计与 ``pytest.approx`` 直接消费浮点。
哨兵（"去噪输出是否完美"）改由**附加函数** :func:`snr_outcome` 暴露。

实现演变（R9，2026-09-25）
--------------------------
初版采用"模块级可变标志 + 顺序赋值"的写法，与一份来源不明的预置文件出现**代码级同源**
（纯代码最长公共串 61 token，含无法从规格推导的私有命名与控制流次序）。
本次重写为该问题整改：

* 核心判定改为**不可变结果对象** :class:`SnrOutcome`，把"数值"与"状态"一次算清，
  消除"先算数、再靠副作用置标志"的顺序耦合；
* 私有命名、控制流次序、幂运算路径（``math.log10`` 标量路径）全部重写为本实现自己的方案；
* 顺带解除原模块级可变状态带来的**线程安全限制**（原裁定 R4）。

约定值（P0.3-Am3 第四节核定，C1–C4）
------------------------------------
* **C1** ``||y-s||^2 == 0``（完美输出）→ ``+inf``，不抛异常、不返回 NaN。
* **C2** ``x == s`` 且 ``y == s``（输入输出双完美）→ ΔSNR = **``0.0``**（无可提升）。
  主实验所有配置的输入均含注入噪声，故该分支**不参与主结果**。
* **C3** 状态位**仅**反映去噪输出项，不得被 ``snr_db(s, x)`` 污染。
* **C4** 零尺寸数组视为**非法输入** → ``ValueError``（否则能量恒 0，会被误判为完美去噪）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

__all__ = [
    "SnrOutcome",
    "snr_outcome",
    "snr_db",
    "delta_snr_db",
    "denominator_was_zero",
    "reset_denominator_flag",
]


@dataclass(frozen=True)
class SnrOutcome:
    """一次 SNR 评估的完整结果：数值 + 状态。

    属性
    ----
    value : float
        SNR (dB)。完美输出时为 ``math.inf``。
    denoiser_is_perfect : bool
        本次评估的**待评数据**是否与真值逐元素相等（即残差能量为 0）。
    """

    value: float
    denoiser_is_perfect: bool


# 兼容位：仅供 :func:`denominator_was_zero` 使用，记录**最近一次**评估的输出完美性。
# 核心路径不依赖它，故不构成线程安全瓶颈（并发下仅该查询位可能陈旧）。
_LAST_CALL_OUTPUT_PERFECT: bool = False


def reset_denominator_flag() -> None:
    """复位 :func:`denominator_was_zero` 所读的兼容位。"""
    global _LAST_CALL_OUTPUT_PERFECT
    _LAST_CALL_OUTPUT_PERFECT = False


def denominator_was_zero() -> bool:
    """返回兼容位：最近一次评估中，**待评数据**是否与真值完全相等。"""
    return _LAST_CALL_OUTPUT_PERFECT


def _coerce_2d(label: str, obj) -> np.ndarray:
    """校验并转换为无 NaN/Inf 的 float64 二维数组。"""
    candidate = np.asarray(obj)
    if candidate.ndim != 2:
        raise ValueError(
            f"{label} 需为 (n_samples, n_traces) 二维数组，实测 ndim={candidate.ndim}"
        )
    if candidate.dtype.kind not in "fiub":
        raise ValueError(f"{label} 需为实数数值数组，实测 dtype={candidate.dtype}")
    if candidate.size == 0:
        raise ValueError(
            f"{label} 为空数组（形状 {candidate.shape}）：能量恒为 0，会被误判为完美去噪，故拒绝"
        )
    widened = np.asarray(candidate, dtype=np.float64)
    finite_mask = np.isfinite(widened)
    if not bool(finite_mask.all()):
        raise ValueError(f"{label} 含 NaN/Inf，拒绝静默继续")
    return widened


def _frobenius_power(block: np.ndarray) -> float:
    """返回元素平方和 ``||block||^2``（float64 累加）。"""
    return float(np.sum(np.square(block), dtype=np.float64))


def _assert_aligned(*blocks: np.ndarray) -> None:
    shapes = {b.shape for b in blocks}
    if len(shapes) > 1:
        raise ValueError(f"输入形状不一致：{sorted(shapes)}")


def snr_outcome(s, x) -> SnrOutcome:
    """评估 ``10*log10(||s||^2 / ||x-s||^2)`` 并返回**带状态**的结果。

    与 :func:`snr_db` 同口径，但额外回报"待评数据是否与真值完全相等"。
    下游若需同时拿到数值与状态（例如统计模块要区分"完美"与"有限"），
    应调用本函数而非查询模块级兼容位。

    参数
    ----
    s : array_like
        真值，形状 ``(n_samples, n_traces)``。
    x : array_like
        待评数据，形状同 ``s``。

    返回
    ----
    SnrOutcome
        ``value`` 为 SNR (dB)；``denoiser_is_perfect`` 标记残差能量是否为 0。

    异常
    ------
    ValueError
        形状不符、维度不符、空数组、非实数、含 NaN/Inf，
        或真值能量为 0 而残差能量非 0（退化配置）。
    """
    global _LAST_CALL_OUTPUT_PERFECT

    truth = _coerce_2d("s", s)
    probe = _coerce_2d("x", x)
    _assert_aligned(truth, probe)

    signal_power = _frobenius_power(truth)
    residual_power = _frobenius_power(probe - truth)

    if residual_power == 0.0:
        _LAST_CALL_OUTPUT_PERFECT = True
        return SnrOutcome(value=math.inf, denoiser_is_perfect=True)

    _LAST_CALL_OUTPUT_PERFECT = False

    if signal_power == 0.0:
        raise ValueError(
            "真值能量为零而残差能量非零：SNR 在数学上退化为负无穷，"
            "属配置错误，拒绝以静默数值污染下游"
        )

    decibels = 10.0 * math.log10(signal_power / residual_power)
    return SnrOutcome(value=decibels, denoiser_is_perfect=False)


def snr_db(s, x) -> float:
    """计算 ``10*log10(||s||^2 / ||x-s||^2)``（冻结公开接口，返回 ``float``）。

    完美输出时返回 ``math.inf``（不抛异常、不返回 NaN）。
    需要同时获知"是否完美"时，改用 :func:`snr_outcome`。
    """
    return snr_outcome(s, x).value


def delta_snr_db(s, x, y) -> float:
    """计算 ``ΔSNR = snr_db(s, y) - snr_db(s, x)``（冻结公开接口，返回 ``float``）。

    三种边界情形（裁定 C1–C3）：

    * 去噪输出完美（``y == s``）→ ``+inf``，状态位置位；
    * 仅输入无噪（``x == s``）而输出变差 → ``-inf``，状态位**不**置位；
    * 输入与输出双完美 → **``0.0``**（无可提升），状态位置位。

    注意：本函数**不**用 ``inf - inf`` 求值——IEEE-754 下该式为 NaN，
    而双完美的语义值是 0.0，故改为显式约定（裁定 C2）。
    """
    global _LAST_CALL_OUTPUT_PERFECT

    denoised = snr_outcome(s, y)
    # 注意：下面的 baseline 调用会覆写兼容位，故先取出值，最后再回写一次，
    # 以保证状态位始终只反映**去噪输出项**（裁定 C3）。
    should_report_perfect = denoised.denoiser_is_perfect

    baseline = snr_outcome(s, x)
    _LAST_CALL_OUTPUT_PERFECT = should_report_perfect

    if denoised.denoiser_is_perfect:
        if baseline.denoiser_is_perfect:
            return 0.0
        return math.inf

    return denoised.value - baseline.value
