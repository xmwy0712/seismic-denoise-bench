"""方法 · 截断 SVD 低秩逼近。

机制族
------
稀疏 / 低秩 / 矩阵分解（低秩类实现）

用途与适用噪声
--------------
面向**相干噪声**（强相干能量在低秩子空间占比高）与整体结构平滑；
作为低秩类代表方法。

原理
----
把整幅 ``(n_samples, n_traces)`` 数据矩阵做 SVD，保留前 ``rank`` 个奇异分量
（或按累计能量比 ``energy_frac`` 自动定秩），其余置零后重建。

关键参数
--------
``rank`` : 显式秩（整数）；为 ``None`` 时由 ``energy_frac`` 决定
``energy_frac`` : 累计奇异值能量占比阈值（``rank`` 为 ``None`` 时生效）

确定性
------
**确定性**（SVD 为确定性分解）；不使用 ``rng``。
"""

from __future__ import annotations

import numpy as np

METHOD_NAME = "svd_lowrank"
FAMILY = "稀疏 / 低秩 / 矩阵分解"
DETERMINISTIC = True

PARAMS_DEFAULT: dict = {
    "rank": None,
    "energy_frac": 0.95,
}


def run(noisy: np.ndarray, params: dict | None, rng: np.random.Generator) -> np.ndarray:
    """截断 SVD 低秩逼近。``rng`` 不使用（确定性方法，保留统一签名）。"""
    p = dict(PARAMS_DEFAULT)
    if params:
        p.update(params)

    a = np.asarray(noisy, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError(f"noisy 须为二维 (n_samples, n_traces)，实测 ndim={a.ndim}")
    if not np.all(np.isfinite(a)):
        raise ValueError("noisy 含非有限值")

    u, s, vt = np.linalg.svd(a, full_matrices=False)

    rank = p["rank"]
    if rank is None:
        energy = np.cumsum(s ** 2) / float(np.sum(s ** 2))
        k = int(np.searchsorted(energy, float(p["energy_frac"])) + 1)
    else:
        k = int(rank)
    k = max(1, min(k, s.size))

    return (u[:, :k] * s[:k]) @ vt[:k, :]
