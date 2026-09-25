"""Lsig（真值事件窗归一化重建误差）与真值事件掩码实现。

规格依据
--------
协议 `docs/protocol-v5.md` 第四节第 2 条：

    Lsig = ||M(y-s)||^2 / ||M s||^2 ，**越低越好**。
    M 由干净真值按固定阈值生成后膨胀一个子波长度，生成规则在运行方法前冻结。

膨胀长度取整规则（**冻结参数**，见 P0.3-Am1 裁定 1）
----------------------------------------------------
::

    n_T = math.floor(1.0 / (f_main * dt) + 0.5)

即**真·四舍五入（half-up）**。15 / 25 / 40 Hz（dt = 0.002 s）对应
``n_T = 33 / 20 / 13``。

**为何不使用 ties-to-even 舍入**：40 Hz 时 ``1/(f*dt)`` 在 IEEE-754 双精度下
**恰好等于 12.5**（已实测：``repr`` 为 ``'12.5'``，``hex`` 为
``0x1.9000000000000p+3``，可精确表示）。Python 内建的 ties-to-even 舍入（以及 numpy 中
同语义的取整函数）会给 **12**；而 half-up 给 **13**。
banker's rounding 属 Python 实现细节，MATLAB / Fortran / Julia 复现者会得到 13，
两者冲突将导致**复现失败**；本项目核心主张即可复现，故规定 half-up。
（本模块内**不得**出现任何 ties-to-even 舍入调用，WorkBuddy 会做机械扫描。）

掩码语义
--------
1. **阈值检出**：``mask0 = |s| >= threshold``（含等号）。``threshold`` 为**显式参数**，
   本单不设默认值；具体数值由 **P1 冻结**（该值同属 Lsig 可复现的必要参数）。
2. **膨胀长度**：``n_T = floor(1/(f_main*dt) + 0.5)``，单位=样点。
3. **膨胀方向**：沿**时间轴（axis=0）**膨胀，**不作用于道方向（axis=1）**。
4. **锚定规则（本实现显式规定）**：长度为 ``n_T`` 的窗口以检出样点为中心，
   ``left = n_T // 2``（向早时间看）、``right = n_T - 1 - left``（向晚时间看）。
   该规则**显式写死不依赖任何库的默认锚点**，以保证跨平台、跨库实现一致。

**边界语义（如实声明，审查已知项）**
    数组端的窗口按"越界即不贡献"截断，**不做环绕（wrap）**。
    因此当事件位于数组边界附近（距边界小于 ``left`` 或 ``right`` 样点）时，
    掩码在时间轴上的支撑长度会**短于** ``n_T``。

    这是**掩码构造的固有性质**（任何非环绕膨胀皆如此），而非缺陷；
    只需保证验收断言中的尖峰位于数组内部（距边界 > ``n_T``/2），
    即可满足规格 C 的"支撑 ≈ n_T（±1 样点）"。
    **对 Lsig 数值的影响**：真值事件位于边界时，M 覆盖不足会低估分母
    ``||M s||^2``，从而**放大** Lsig。P1 冻结事件窗时应确保事件不贴边界。
"""

from __future__ import annotations

import math

import numpy as np

__all__ = ["dilation_length_samples", "event_mask", "lsig"]


def dilation_length_samples(f_main: float, dt: float) -> int:
    """返回冻结的膨胀长度（单位：样点）。

    ``n_T = floor(1.0 / (f_main * dt) + 0.5)`` —— half-up 取整。

    参数
    ----
    f_main : float
        子波主频 (Hz)，须为正有限值。
    dt : float
        时间采样间隔 (s)，须为正有限值。

    返回
    ----
    int
        膨胀长度 ``n_T``（样点），恒 ``>= 1``。
    """
    if not isinstance(f_main, (int, float, np.floating, np.integer)) or not np.isfinite(f_main):
        raise ValueError(f"f_main 必须为有限数值，实测 {f_main!r}")
    if not isinstance(dt, (int, float, np.floating, np.integer)) or not np.isfinite(dt):
        raise ValueError(f"dt 必须为有限数值，实测 {dt!r}")
    f_main = float(f_main)
    dt = float(dt)
    if f_main <= 0.0:
        raise ValueError(f"f_main 必须为正，实测 {f_main!r}")
    if dt <= 0.0:
        raise ValueError(f"dt 必须为正，实测 {dt!r}")

    n_samples_per_cycle = 1.0 / (f_main * dt)
    n_T = math.floor(n_samples_per_cycle + 0.5)
    if n_T < 1:
        raise ValueError(
            f"膨胀长度 n_T={n_T} < 1，参数不合理：f_main={f_main}, dt={dt}"
        )
    return int(n_T)


def _dilate_along_time_axis(mask0: np.ndarray, n_T: int) -> np.ndarray:
    """沿 axis=0 膨胀 ``n_T`` 个样点；axis=1 宽度恒为 1（不作用于道方向）。

    显式实现（不使用任何库的默认结构元素锚点），以保证跨平台结果一致。
    采用**切片视图原址或运算**，无逐次大数组分配。
    边界处按"越界即不贡献"截断，不发生环绕。
    """
    n_rows = mask0.shape[0]
    left = n_T // 2
    right = n_T - 1 - left

    out = np.array(mask0, dtype=bool, copy=True)

    for offset in range(-left, right + 1):
        if offset == 0:
            continue
        # 目标区间 [dst_lo, dst_hi) 与源区间 [src_lo, src_hi) 同长错位 offset
        dst_lo = max(0, offset)
        dst_hi = min(n_rows, n_rows + offset)
        if dst_lo >= dst_hi:
            continue
        src_lo = dst_lo - offset
        src_hi = dst_hi - offset
        out[dst_lo:dst_hi] |= mask0[src_lo:src_hi]

    return out


def event_mask(
    s: np.ndarray,
    f_main: float,
    dt: float,
    threshold: float,
) -> np.ndarray:
    """由干净真值生成真值事件掩码 ``M``。

    步骤：``|s| >= threshold`` 二值化 → 沿时间轴（axis=0）膨胀 ``n_T`` 样点。

    参数
    ----
    s : numpy.ndarray
        干净真值，形状 ``(n_samples, n_traces)``。
    f_main : float
        子波主频 (Hz)。
    dt : float
        时间采样间隔 (s)。
    threshold : float
        振幅绝对值阈值（**显式参数**；数值由 P1 冻结）。

    返回
    ----
    numpy.ndarray
        布尔掩码，形状同 ``s``。

    异常
    ----
    ValueError
        ``s`` 非二维 / 空 / 非数值 / 复数 / 含非有限值，或 ``threshold`` 非有限值。
    """
    if not isinstance(threshold, (int, float, np.floating, np.integer)) or not np.isfinite(
        threshold
    ):
        raise ValueError(f"threshold 必须为有限数值，实测 {threshold!r}")

    arr = np.asarray(s)
    if arr.ndim != 2:
        raise ValueError(f"s 必须为二维数组 (n_samples, n_traces)，实测 ndim={arr.ndim}")
    if arr.size == 0:
        raise ValueError(f"s 为 0 元素数组（形状 {arr.shape}），拒绝生成掩码")
    if not np.issubdtype(arr.dtype, np.number):
        raise ValueError(f"s 必须为数值数组，实测 dtype={arr.dtype}")
    if np.iscomplexobj(arr):
        raise ValueError(f"s 不得为复数数组，实测 dtype={arr.dtype}")

    truth = arr.astype(np.float64, copy=False)
    if not np.all(np.isfinite(truth)):
        raise ValueError("s 含非有限值 (NaN/Inf)，拒绝生成掩码")

    n_T = dilation_length_samples(f_main, dt)
    detected = np.abs(truth) >= threshold
    return _dilate_along_time_axis(detected, n_T)


def lsig(s: np.ndarray, y: np.ndarray, mask: np.ndarray) -> float:
    """计算 ``||M(y-s)||^2 / ||M s||^2``。

    参数
    ----
    s : numpy.ndarray
        干净真值。
    y : numpy.ndarray
        去噪输出，形状同 ``s``。
    mask : numpy.ndarray
        布尔掩码，形状同 ``s``。

    返回
    ----
    float
        Lsig，越低越好。

    异常
    ----
    ValueError
        形状不符、``mask`` 非布尔、空数组、含非有限值，或 ``||M s||^2 == 0``
        （分母为零属配置 / 掩码错误，**不得**返回 inf 或 NaN 掩盖）。
    """
    truth = np.asarray(s)
    output = np.asarray(y)
    m = np.asarray(mask)

    if truth.ndim != 2:
        raise ValueError(f"s 必须为二维数组，实测 ndim={truth.ndim}")
    if truth.size == 0:
        raise ValueError(f"s 为 0 元素数组（形状 {truth.shape}）, 拒绝计算")
    if truth.shape != output.shape:
        raise ValueError(f"形状不一致：s={truth.shape}，y={output.shape}")
    if truth.shape != m.shape:
        raise ValueError(f"掩码形状不一致：s={truth.shape}，mask={m.shape}")
    # 用 dtype.kind 判布尔（兼容 numpy 各版本与不同布尔来源）
    if m.dtype.kind != "b":
        raise ValueError(f"mask 必须为布尔数组，实测 dtype={m.dtype}")

    truth64 = truth.astype(np.float64, copy=False)
    output64 = output.astype(np.float64, copy=False)
    if not np.all(np.isfinite(truth64)):
        raise ValueError("s 含非有限值 (NaN/Inf)")
    if not np.all(np.isfinite(output64)):
        raise ValueError("y 含非有限值 (NaN/Inf)")

    residual = output64 - truth64

    numerator = float(np.sum((residual * residual)[m], dtype=np.float64))
    denominator = float(np.sum((truth64 * truth64)[m], dtype=np.float64))

    if denominator == 0.0:
        raise ValueError(
            "||M s||^2 为 0（掩码内无真值能量）：属配置 / 掩码错误，"
            "拒绝返回 inf 或 NaN 掩盖"
        )

    return numerator / denominator
