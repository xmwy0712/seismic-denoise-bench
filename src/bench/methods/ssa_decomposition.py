"""方法 · 奇异谱分析（SSA，逐道轨迹矩阵分解重建）。

机制族
------
稀疏 / 低秩 / 矩阵分解（分解类实现）

用途与适用噪声
--------------
面向**随机噪声**与弱相干结构的通用分解去噪；对强相干干扰作用有限。

原理
----
对**每一条道**：以窗口 ``window_len`` 构造轨迹矩阵（trajectory matrix），
奇异值分解后仅保留前 ``n_components`` 个分量重建，再做**对角平均**（diagonal averaging）
还原为时间序列。低能量（多为噪声）分量被丢弃。

关键参数
--------
``window_len`` : 嵌入窗口长度（样点）
``n_components`` : 保留分量数

确定性
------
**确定性**（SVD 为确定性分解）；不使用 ``rng``。
"""

from __future__ import annotations

import numpy as np

METHOD_NAME = "ssa_decomposition"
FAMILY = "稀疏 / 低秩 / 矩阵分解"
DETERMINISTIC = True

PARAMS_DEFAULT: dict = {
    "window_len": 64,
    "n_components": 8,
}


def run(noisy: np.ndarray, params: dict | None, rng: np.random.Generator) -> np.ndarray:
    """逐道 SSA 重建。``rng`` 不使用（确定性方法，保留统一签名）。"""
    p = dict(PARAMS_DEFAULT)
    if params:
        p.update(params)

    a = np.asarray(noisy, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError(f"noisy 须为二维 (n_samples, n_traces)，实测 ndim={a.ndim}")
    if not np.all(np.isfinite(a)):
        raise ValueError("noisy 含非有限值")

    ns, ntr = a.shape
    win = int(p["window_len"])
    ncomp = int(p["n_components"])
    if not (2 <= win <= ns):
        raise ValueError(f"window_len 须在 [2, {ns}]，实测 {win}")
    if ncomp < 1:
        raise ValueError(f"n_components 须 >= 1，实测 {ncomp}")

    n_col = ns - win + 1
    out = np.empty_like(a)

    for j in range(ntr):
        series = a[:, j]
        traj = np.lib.stride_tricks.sliding_window_view(series, win)   # (n_col, win)
        u, s, vt = np.linalg.svd(traj, full_matrices=False)
        k = min(ncomp, s.size)
        approx = (u[:, :k] * s[:k]) @ vt[:k, :]

        rec = np.zeros(ns, dtype=np.float64)
        cnt = np.zeros(ns, dtype=np.float64)
        for i in range(win):
            rec[i:i + n_col] += approx[:, i]
            cnt[i:i + n_col] += 1.0
        out[:, j] = rec / cnt

    return out
