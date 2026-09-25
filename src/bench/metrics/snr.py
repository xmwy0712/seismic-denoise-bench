"""ΔSNR（输出 SNR 提升）指标实现。

规格依据
--------
协议 `docs/protocol-v5.md` 第四节第 1 条：

    ΔSNR = 10*log10(||s||^2 / ||y-s||^2) - 10*log10(||s||^2 / ||x-s||^2)

其中 ``s`` 为真值、``x`` 为含噪输入、``y`` 为去噪输出。**越高越好。**
实现规格另见 `docs/task-sheets/P0.3-metrics与解析解对拍-2026-09-25.md` 任务 1。

输入与数值约定
--------------
* 输入为形状 ``(n_samples, n_traces)`` 的 ndarray，``float32`` / ``float64`` 均可；
  内部一律提升为 ``float64`` 再累加能量，避免低精度累加误差污染 1e-10 / 1e-12 级对拍。
* 输入含非有限值（NaN / Inf）→ 抛 ``ValueError``，**不**静默返回 NaN。
* 噪声能量 ``||y-s||^2 == 0``（完美去噪）→ 返回 ``+inf`` 并置内部标志，
  **不抛异常、不返回 NaN**。

本实现自行补充的裁定（规格未规定，已在审查与执行记录中声明）
------------------------------------------------------------
**R1（定值：输入与输出同时完美 → 0.0，而非 NaN）**
若 ``x == s`` 且 ``y == s``，则两项均为 ``+inf``。IEEE-754 下 ``inf - inf = NaN``，
但该场景的物理含义是"未产生任何改变"，故 ΔSNR **恰为 0.0**。
本实现在相减前显式处理"双完美"情形，返回 ``0.0``（并置标志），
从而既不违反"不得静默返回 NaN"，也避免误报为 ``+inf``。

**R2（定值：真值能量为 0 属配置错误 → ValueError）**
真值能量 ``||s||^2 == 0``（全零真值）而噪声能量非 0 时，SNR 在数学上退化为 ``-inf``。
本实现抛 ``ValueError``，视为配置错误。**已知副作用（如实声明）**：
若某配置的真值全域为零、输入含噪、输出完美去噪，则本函数会因输入项退化而抛错，
而非返回 ``+inf``。该场景在本研究的数据协议下不构成合法配置（真值为零则无信号可言），
故按配置错误处理；若下游确需支持，应显式短路而非放宽本函数。

**R3（定值：内部标志只反映"去噪输出是否完美"）**
规格把标志绑定在"``||y-s||^2 == 0``（完美去噪）"上，故标志**只**取输出去噪项，
不再对输入项做 ``or`` 合并——否则"输入本就无噪、输出反而变差"会被误标为发生过完美去噪。

**R4（已知限制：模块级标志非线程安全）**
规格要求"置内部标志"，故采用模块级变量。多线程/多进程并发调用时该标志会相互污染。
本研究的数据协议为**配置内串行**处理，不触发该问题；若将来引入并行跑道集，
应改为返回值携带状态（如命名元组），届时须重新走变更流程。
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "snr_db",
    "delta_snr_db",
    "denominator_was_zero",
    "reset_denominator_flag",
]

# 模块级标志：最近一次计算中，去噪输出的噪声能量是否为 0（即"完美去噪"）。
# 规格固定了返回类型为 float 且要求 "+inf 不抛异常"，故用独立标志传递该状态。
_LAST_DENOMINATOR_ZERO: bool = False


def reset_denominator_flag() -> None:
    """把内部标志复位为 ``False``。建议在每次断言前显式调用。"""
    global _LAST_DENOMINATOR_ZERO
    _LAST_DENOMINATOR_ZERO = False


def denominator_was_zero() -> bool:
    """返回内部标志：最近一次 ΔSNR 计算中，去噪输出是否为完美去噪。"""
    return _LAST_DENOMINATOR_ZERO


def _validate_2d(name: str, arr: np.ndarray) -> np.ndarray:
    """校验为二维、非空、数值、实值、无 NaN/Inf，并返回 float64 视图/副本。"""
    a = np.asarray(arr)
    if a.ndim != 2:
        raise ValueError(f"{name} 必须为二维数组 (n_samples, n_traces)，实测 ndim={a.ndim}")
    if a.size == 0:
        raise ValueError(
            f"{name} 为 0 元素数组（形状 {a.shape}）：能量恒为 0，"
            "会被误判为'完美去噪'，故拒绝"
        )
    if not np.issubdtype(a.dtype, np.number):
        raise ValueError(f"{name} 必须为数值数组，实测 dtype={a.dtype}")
    if np.iscomplexobj(a):
        raise ValueError(f"{name} 不得为复数数组，实测 dtype={a.dtype}")
    b = a.astype(np.float64, copy=False)
    if not np.all(np.isfinite(b)):
        raise ValueError(f"{name} 含非有限值 (NaN/Inf)，拒绝静默继续")
    return b


def _squared_norm(v: np.ndarray) -> float:
    """返回 Frobenius 范数平方 ||v||^2，以 float64 累加。"""
    return float(np.sum(v * v, dtype=np.float64))


def _require_same_shape(a: np.ndarray, b: np.ndarray, a_name: str, b_name: str) -> None:
    if a.shape != b.shape:
        raise ValueError(f"形状不一致：{a_name}={a.shape}，{b_name}={b.shape}")


def snr_db(s: np.ndarray, x: np.ndarray) -> float:
    """计算 ``10*log10(||s||^2 / ||x-s||^2)``。

    参数
    ----
    s : numpy.ndarray
        真值，形状 ``(n_samples, n_traces)``。
    x : numpy.ndarray
        待评估数据（含噪输入或去噪输出），形状同 ``s``。

    返回
    ----
    float
        SNR (dB)。若 ``||x-s||^2 == 0`` 则返回 ``+inf`` 并置内部标志。

    异常
    ----
    ValueError
        形状不符、空数组、非数值、复数、含非有限值，或真值能量为 0（且噪声能量非 0）。
    """
    global _LAST_DENOMINATOR_ZERO

    truth = _validate_2d("s", s)
    data = _validate_2d("x", x)
    _require_same_shape(truth, data, "s", "x")

    signal_energy = _squared_norm(truth)
    noise_energy = _squared_norm(data - truth)

    _LAST_DENOMINATOR_ZERO = False

    if noise_energy == 0.0:
        _LAST_DENOMINATOR_ZERO = True
        return float("inf")

    if signal_energy == 0.0:
        raise ValueError(
            "真值能量 ||s||^2 为 0 而噪声能量非 0：SNR 退化为 -inf，"
            "属配置错误，拒绝静默返回"
        )

    return float(10.0 * np.log10(signal_energy / noise_energy))


def delta_snr_db(s: np.ndarray, x: np.ndarray, y: np.ndarray) -> float:
    """计算 ``ΔSNR = snr_db(s, y) - snr_db(s, x)``。

    参数
    ----
    s : numpy.ndarray
        真值。
    x : numpy.ndarray
        含噪输入。
    y : numpy.ndarray
        去噪输出。

    返回
    ----
    float
        ΔSNR (dB)。三种边界情形的取值（见模块 docstring 裁定 R1）：

        * 仅输出完美（``y == s``）→ ``+inf``（**非 NaN**），标志置位；
        * 仅输入完美（``x == s``）→ ``-inf``（输出反而变差，数值上成立），标志不置位；
        * **输入与输出同时完美** → ``0.0``（未产生任何改变），标志置位。
    """
    global _LAST_DENOMINATOR_ZERO

    # --- 输出去噪项 ---
    _LAST_DENOMINATOR_ZERO = False
    snr_output = snr_db(s, y)
    output_is_perfect = _LAST_DENOMINATOR_ZERO

    # 输出去噪完美：仍需输入项以区分 "+inf" 与 "0.0"（双完美）。
    # 注意：此处不能无条件短路——若输入同样完美，正确值为 0.0 而非 +inf。
    _LAST_DENOMINATOR_ZERO = False
    try:
        snr_input = snr_db(s, x)
        input_is_perfect = _LAST_DENOMINATOR_ZERO
    except ValueError:
        if output_is_perfect:
            # 输出完美而输入项退化（真值能量为 0）：无法给出有意义的相对提升，
            # 依裁定 R2 仍按配置错误处理（不掩盖为 +inf）。
            raise
        raise

    # 标志只反映"去噪输出是否完美"（裁定 R3）
    _LAST_DENOMINATOR_ZERO = output_is_perfect

    if output_is_perfect and input_is_perfect:
        # 双完美：inf - inf 在 IEEE-754 下为 NaN，但语义上应为 0.0（裁定 R1）
        return 0.0

    return float(snr_output - snr_input)
