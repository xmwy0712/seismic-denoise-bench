"""P4 野外「同相轴连续性」指标（**独立于融合**，不共享代码与参数）。

设计依据
--------
* `frozen-v2.item_11`：野外指标含「同相轴连续性」，且 **LP 与融合局部相干度不得共享代码与参数**；
* `frozen-v2.item_20`（**P1.5 义务**）：P3 的 `lateral_coherence` 与 P2 **同根因** ——
  同为**沿道轴的零延迟相关量**，实测**近零基线**（top-3 仅 0.13–0.21，逐道中位 0.0575）
  ⇒ 该量在本数据上**不表达几何质量**。**P4 不得继承同一缺陷**。

本模块的**关键区别**：连续性是**沿局部倾角（dip-guided）**计算的，**不是零延迟**相关。
零延迟相关在倾斜同相轴上天然偏低（同相轴在相邻道间**有时间位移**）；
沿倾角对齐后再相关，才可能反映真实同相轴连续性。

**独立性**：本模块**不得导入** ``bench.fusion``（防与融合权重共享实现）；
由 ``tests/test_field_continuity.py`` 的 AST 守卫核验（含反证）。
"""

from __future__ import annotations

import numpy as np

__all__ = ["local_dip", "continuity_field", "continuity_per_trace"]

#: 结构张量平滑尺度（样点）—— 冻结参数候选，验证通过后随 P4 记录
SMOOTH_SIGMA = (3.0, 1.5)


def _gaussian_kernel(sigma: float) -> np.ndarray:
    n = max(1, int(3 * sigma))
    x = np.arange(-n, n + 1, dtype=np.float64)
    k = np.exp(-(x ** 2) / (2 * sigma ** 2))
    return k / k.sum()


def _smooth(a: np.ndarray, st: float, sx: float) -> np.ndarray:
    kt, kx = _gaussian_kernel(st), _gaussian_kernel(sx)
    out = a
    # 沿时间轴
    out = np.apply_along_axis(lambda v: np.convolve(v, kt, mode="same"), 0, out)
    # 沿道轴
    out = np.apply_along_axis(lambda v: np.convolve(v, kx, mode="same"), 1, out)
    return out


def local_dip(data: np.ndarray) -> np.ndarray:
    """结构张量局部倾角（**样点/道**，即相邻道之间的时间位移）。

    返回形状同 ``data``；正值表示同相轴随道号增大而向晚时间倾斜。
    """
    a = np.asarray(data, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError("data 须为二维 (n_samples, n_traces)")
    gt = np.gradient(a, axis=0)
    gx = np.gradient(a, axis=1)
    st, sx = SMOOTH_SIGMA
    jtt = _smooth(gt * gt, st, sx)
    jxx = _smooth(gx * gx, st, sx)
    jtx = _smooth(gt * gx, st, sx)
    # 结构张量主方向 → 倾角（沿道方向的斜率 dt/dx）
    theta = 0.5 * np.arctan2(2.0 * jtx, (jtt - jxx))
    # 转成「相邻道时间位移」：tan(theta) 给出 dt/dx 的斜率量级
    return np.tan(theta)


def _shift_trace(v: np.ndarray, d: float) -> np.ndarray:
    """按 ``d`` 样点重采样一条道（线性插值，边界取端值）。"""
    n = v.size
    idx = np.arange(n, dtype=np.float64) + d
    idx = np.clip(idx, 0.0, n - 1.0)
    i0 = np.floor(idx).astype(int)
    i1 = np.minimum(i0 + 1, n - 1)
    w = idx - i0
    return v[i0] * (1.0 - w) + v[i1] * w


def continuity_per_trace(data: np.ndarray, *, half_win: int = 32) -> np.ndarray:
    """逐道连续性：与左右邻居**沿局部倾角对齐后**的归一化相关，取窗内中位。

    返回长度 ``n_traces``；每条道只与其**紧邻**道比较（``j±1``），
    对齐量取该道两侧倾角的平均（结构张量给出）。
    """
    a = np.asarray(data, dtype=np.float64)
    ns, ntr = a.shape
    dip = local_dip(a)
    out = np.full(ntr, np.nan, dtype=np.float64)
    for j in range(ntr):
        vals = []
        for jj in (j - 1, j + 1):
            if not (0 <= jj < ntr):
                continue
            d = float(np.median(dip[:, j]) ) if jj > j else -float(np.median(dip[:, jj]))
            v1, v2 = a[:, j], _shift_trace(a[:, jj], -d)
            # 滑窗归一化相关，取中位（稳健）
            cs = []
            step = max(1, half_win // 2)
            for t0 in range(0, ns - 2 * half_win + 1, step):
                s1 = v1[t0:t0 + 2 * half_win]
                s2 = v2[t0:t0 + 2 * half_win]
                n1 = np.linalg.norm(s1)
                n2 = np.linalg.norm(s2)
                if n1 > 0 and n2 > 0:
                    cs.append(float(np.dot(s1, s2) / (n1 * n2)))
            if cs:
                vals.append(float(np.median(cs)))
        if vals:
            out[j] = float(np.mean(vals))
    return out


def continuity_field(data: np.ndarray) -> float:
    """面板级连续性 = 逐道连续性的**中位数**（稳健，抗离群道）。"""
    c = continuity_per_trace(data)
    c = c[np.isfinite(c)]
    if c.size == 0:
        raise ValueError("无可评估道")
    return float(np.median(c))
