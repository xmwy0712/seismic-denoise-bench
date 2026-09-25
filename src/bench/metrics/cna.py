"""CNA（相干噪声抑制指标）实现。

协议依据
--------
`docs/protocol-v5.md` 第四节第 3 条：

    CNA = 10*log10( ||nc||^2 / ||P_C(y - s)||^2 )   **越高越好**

其中 ``nc`` 为**已知注入的相干噪声**；``P_C`` 是向**预先由注入线性干扰与频散面波模板
构成之子空间**的**最小二乘投影**。

⚠️ **CNA 为「注入基目标型」指标（A1 声明，按 R16-d 改写；见 `docs/metrics-spec.md` §1.1）**

    CNA 为**注入基目标型**指标：其子空间由**注入所用的分量基**构成，
    衡量对**该注入成分**的抑制；**不代表对任意相干噪声的普适评价**。

**子空间与注入参数同源**——这正是该指标的定义方式（不是缺陷）；
但正因如此，**不得据此推断方法对未见噪声的泛化能力**。

子空间构造（R16-a：**分量基精确张成**，禁用抽样建基）
------------------------------------------------------
由生成器**导出注入所用的分量基**，子空间直接由该基构造：

1. **线性干扰**：``bench.data.synthetic.linear_coherent_basis``
   —— 家族唯一随机量是整体幅度 ⇒ 每组 ``(v_app, f_main)`` **1 维**；
   覆盖注册的 ``v_app × f_main`` 并另加注入实际使用的那一组。
2. **频散面波**：``bench.data.synthetic.dispersion_component_basis``
   —— 由 ``A_i·sin(2πf_iτ_i + φ_i) = (A_i cos φ_i)·sin(2πf_iτ_i) + (A_i sin φ_i)·cos(2πf_iτ_i)``
   可知**每分量 2 维**（sin/cos）⇒ 共 **2·n_components 维**；
   频率轴规则与注入实现**完全一致**。
3. 基按列展平为 ``T``（``n_features × n_basis``），对 ``T`` 做 SVD，
   保留奇异值 ≥ ``rank_tol·σ_max`` 的**左奇异向量 ``U``**（**列空间由 ``U`` 给出**）构成正交基 ``Q``；
4. 投影 ``P_C(v) = Q Qᵀ v``。

**为何禁用抽样建基**：频散面波家族维数 = 2·n_components；实测抽 1 / 5 / 20 个
**随机实现**建基时，另一新实现的回收误差中位为 **98.93% / 86.54% / 50.98%**（不收敛）；
改用分量基后降至 **~1e-15**。

**秩/截断规则**：``rank_tol`` 为**冻结参数**（P1.5 冻结）。本模块默认候选值 ``1e-8``
（几乎不截断，保留全部数值可分辨方向）。

A1 硬约束
---------
* **模板只含相干噪声成分**：不含随机噪声、不含真值信号；
* **与任何方法输出无关**：模板参数只来自冻结配置；构造路径**不读取**方法输出或结果文件；
* 由 ``tests/test_metrics_independence.py`` 机械检查保证。

边界情形（沿用 P0.3-Am3 C1–C6 约定）
------------------------------------
* ``y = s``（完全去噪）→ ``P_C(0) = 0`` → CNA = **``+inf``** 并置哨兵标志（同 C1）；
* ``y = x``（不处理）→ 返回有限值，量级与"未抑制相干噪声"一致；
* ``nc`` 能量为 0 → ``ValueError``（配置错误）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

__all__ = ["CnaOutcome", "build_subspace", "project_onto_subspace", "cna_db", "cna_outcome"]

# 秩截断候选值（**P1.5 冻结**）
DEFAULT_RANK_TOL = 1e-8

# 哨兵标志（与 snr.py 的约定同类：核心路径不写全局状态，仅兼容位）
_LAST_WAS_PERFECT: bool = False


@dataclass(frozen=True)
class CnaOutcome:
    """CNA 评估结果：数值 + 状态。"""

    value: float
    denoiser_left_no_residual: bool


def _validate_2d(name: str, arr) -> np.ndarray:
    a = np.asarray(arr)
    if a.ndim != 2:
        raise ValueError(f"{name} 必须为二维数组，实测 ndim={a.ndim}")
    if a.size == 0:
        raise ValueError(f"{name} 为 0 元素数组")
    if not np.issubdtype(a.dtype, np.number):
        raise ValueError(f"{name} 必须为数值数组，实测 dtype={a.dtype}")
    if np.iscomplexobj(a):
        raise ValueError(f"{name} 不得为复数数组")
    b = a.astype(np.float64, copy=False)
    if not np.all(np.isfinite(b)):
        raise ValueError(f"{name} 含 NaN/Inf，拒绝静默继续")
    return b


def _frobenius_power(a: np.ndarray) -> float:
    return float(np.sum(np.square(a), dtype=np.float64))


def build_subspace(
    templates: list[np.ndarray] | np.ndarray,
    *,
    rank_tol: float = DEFAULT_RANK_TOL,
) -> np.ndarray:
    """由**相干噪声模板**构造正交基 ``Q``（列正交）。

    参数
    ----
    templates : list[np.ndarray] | numpy.ndarray
        模板集合。三种接受形式：
        (a) ``(n_templates, n_samples, n_traces)`` 三维数组；
        (b) ``(n_features, n_templates)`` 已展平矩阵（列为模板）；
        (c) ``(n_templates, n_features)`` 矩阵（行为模板，自动转置）。
        二维时的歧义按「列数 <= 行数 ⇒ 列为模板」消解。
    rank_tol : float
        奇异值相对截断阈值（**冻结参数候选**）：保留 ``σ >= rank_tol * σ_max`` 的方向。

    返回
    ----
    numpy.ndarray
        形状 ``(n_features, rank)`` 的列正交基。

    异常
    ----
    ValueError
        模板为空、形状不一致、含非有限值，或全部奇异值退化（子空间为空）。
    """
    if not np.isfinite(rank_tol) or rank_tol < 0.0:
        raise ValueError(f"rank_tol 须为非负有限值，实测 {rank_tol!r}")

    arr = np.asarray(templates, dtype=np.float64)
    if arr.ndim == 3:
        # 每个切片 (n_samples, n_traces) 是一个模板；展平后按列堆叠
        n_tpl = arr.shape[0]
        mat = arr.reshape(n_tpl, -1).T                      # (n_features, n_templates)
    elif arr.ndim == 2:
        # 歧义消解：若列数远小于行数，按"每列一个模板"处理；否则按"每行一个模板"处理
        if arr.shape[1] <= arr.shape[0]:
            mat = arr                                       # (n_features, n_templates)
        else:
            mat = arr.T                                     # 行是模板 -> 转置
    else:
        raise ValueError(f"templates 须为 2D（已展平）或 3D（模板集合），实测 ndim={arr.ndim}")

    if mat.size == 0:
        raise ValueError("模板集合为空，无法构造子空间")
    if not np.all(np.isfinite(mat)):
        raise ValueError("模板含 NaN/Inf")

    # SVD：mat = U S Vt。
    # **关键**：模板子空间是 U 的前 rank 列（它们落在**特征空间** R^{n_features}）；
    # Vt 的行只落在"模板编号"空间 R^{n_templates}，列数 = 模板数，**不是**特征空间的基。
    # 早期实现误用 Vt 作基，导致 Q 的维数只有"模板数"（2），project 时维度不匹配。
    u, s, _vt = np.linalg.svd(mat, full_matrices=False)
    if s.size == 0 or s[0] <= 0.0:
        raise ValueError("模板全部为零向量，子空间为空")

    keep = s >= (rank_tol * s[0])
    if not np.any(keep):
        raise ValueError("按 rank_tol 截断后子空间为空（请放宽 rank_tol 或检查模板）")

    q = u[:, keep]                                           # (n_features, rank)
    # 数值再正交化，确保 Q^T Q = I
    q, _r = np.linalg.qr(q)
    return q


def project_onto_subspace(v: np.ndarray, q: np.ndarray) -> np.ndarray:
    """最小二乘投影 ``P_C(v) = Q Qᵀ v``（把 v 展平后投影并还原形状）。"""
    x = np.asarray(v, dtype=np.float64)
    shape = x.shape
    flat = x.reshape(-1)
    if q.shape[0] != flat.size:
        raise ValueError(
            f"维度不匹配：子空间基 {q.shape[0]} 维 vs 数据 {flat.size} 维"
        )
    coef = q.T @ flat
    return (q @ coef).reshape(shape)


def cna_outcome(
    nc: np.ndarray,
    y_minus_s: np.ndarray,
    q: np.ndarray,
) -> CnaOutcome:
    """计算 CNA 并返回**带状态**的结果。

    参数
    ----
    nc : numpy.ndarray
        已知注入的**相干噪声** ``nc``（形状 ``(n_samples, n_traces)``）。
    y_minus_s : numpy.ndarray
        残差 ``y − s``，形状同 ``nc``。
    q : numpy.ndarray
        子空间正交基（由 :func:`build_subspace` 得到，**须来自冻结配置的模板**）。

    返回
    ----
    CnaOutcome
        ``value`` 为 CNA (dB)；``denoiser_left_no_residual`` 标记残差是否为零。

    异常
    -----
    ValueError
        形状不符、含非有限值、``nc`` 能量为 0（配置错误）。
    """
    global _LAST_WAS_PERFECT

    noise = _validate_2d("nc", nc)
    residual = _validate_2d("y_minus_s", y_minus_s)
    if noise.shape != residual.shape:
        raise ValueError(f"形状不一致：nc={noise.shape}，y-s={residual.shape}")

    nc_power = _frobenius_power(noise)
    if nc_power == 0.0:
        raise ValueError("已知相干噪声 nc 能量为 0：CNA 退化，属配置错误")

    if _frobenius_power(residual) == 0.0:
        _LAST_WAS_PERFECT = True
        return CnaOutcome(value=math.inf, denoiser_left_no_residual=True)

    _LAST_WAS_PERFECT = False
    proj = project_onto_subspace(residual, q)
    proj_power = _frobenius_power(proj)
    if proj_power == 0.0:
        # 残差与子空间正交 → 相干噪声已被完全抑制
        return CnaOutcome(value=math.inf, denoiser_left_no_residual=False)

    return CnaOutcome(
        value=10.0 * math.log10(nc_power / proj_power),
        denoiser_left_no_residual=False,
    )


def cna_db(nc: np.ndarray, y_minus_s: np.ndarray, q: np.ndarray) -> float:
    """CNA（dB）的薄封装，返回纯 ``float``（冻结公开接口）。"""
    return cna_outcome(nc, y_minus_s, q).value
