"""P3.2 阶段 2 · 融合实现（**依冻结的 `configs/fusion-rules.yaml`**）。

冻结依据
--------
* `configs/fusion-rules.yaml`（annotated tag `fusion-rules-frozen`）
* `results/fusion/preregistration.md`（含条件 1 失效模式 #2、条件 2 的 `x` 语义）

**硬约束（本模块的生命线）**
----------------------------
* 公开接口为 :func:`fuse`，签名为 ``fuse(y_i, y_j, params) -> np.ndarray``。
  **禁止**出现 ``clean`` / ``s`` / ``mask`` / ``truth`` 形参。
* 本模块**不得导入** ``bench.methods``（方法实现）或 ``bench.data.synthetic``（**真值生成器**）。
* 由 ``tests/test_fusion_independence.py`` 的 **AST 级**守卫机械核验（含反证，规则 14）。

**STFT/ISTFT**：**自实现**（Hann 窗、步长 ``n_T//2``、不截断、逆变换逐样点除以窗累计和）
—— 口径与 P3.1 窗格严格一致；不使用 ``scipy.signal.stft``（其边界语义不符预注册）。

**确定性**：无随机成分 ⇒ 逐字节可复现由构造保证。
"""

from __future__ import annotations

from typing import Any

import numpy as np

__all__ = ["fuse", "PARAMS_DEFAULT", "S_SUBWEIGHTS", "P_COHERENCE_POWER"]

#: ``w_i = C_i ** p``（预注册 `w_definition.weight`）
P_COHERENCE_POWER = 2

#: ``s`` 的三个子分权重（预注册 `s_definition.subscores`）
S_SUBWEIGHTS = {"d": 0.4, "b": 0.3, "a": 0.3}

#: 非真值参数默认值（`x` 由调用方在 **官方运行** 时传入）
PARAMS_DEFAULT: dict[str, Any] = {
    "dt": 0.002,
    "n_t": 20,                    # 膨胀长度 n_T（逐观测传入）
    "gamma": 0.5,                 # 三档之一（0.4 / 0.5 / 0.6）
    "v_lo_m_s": 100.0,            # 冻结 item_05.dispersion_v_band_mps 下限
    "band_hz": (5.0, 25.0),       # 冻结 item_05.frequency_band_hz
    "eps": 1.0e-12,
    "x": None,                    # 含噪输入（**共享输入、非真值**）；缺失 ⇒ b = 0 并须标注
}


def _frames(n_samples: int, n_t: int) -> list[int]:
    """窗起点：窗长 ``n_t``、步长 ``n_t // 2``、满足 ``t0 + n_t <= n_samples``（**不截断**）。"""
    stride = max(1, n_t // 2)
    out, t0 = [], 0
    while t0 + n_t <= n_samples:
        out.append(t0)
        t0 += stride
    return out


def _stft(y: np.ndarray, n_t: int) -> tuple[list[int], np.ndarray]:
    """自实现 STFT：Hann 窗、步长 ``n_t // 2``、**不截断**。

    返回 ``(starts, Z)``，``Z`` 形状 ``(n_freq, n_frame, n_trace)``，复数。
    """
    ns, ntr = y.shape
    starts = _frames(ns, n_t)
    nfft = 1 << int(np.ceil(np.log2(n_t)))
    nf = nfft // 2 + 1
    win = np.hanning(n_t)[:, None]
    Z = np.zeros((nf, len(starts), ntr), dtype=np.complex128)
    for b, t0 in enumerate(starts):
        blk = y[t0:t0 + n_t, :] * win
        Z[:, b, :] = np.fft.rfft(blk, n=nfft, axis=0)
    return starts, Z


def _istft(Z: np.ndarray, starts: list[int], n_samples: int, n_t: int) -> np.ndarray:
    """自实现逆 STFT：Hann 重叠相加，**逐样点除以窗函数累计和**。"""
    nf, nfr, ntr = Z.shape
    nfft = (nf - 1) * 2
    win = np.hanning(n_t)[:, None]
    acc = np.zeros((n_samples, ntr), dtype=np.float64)
    wsum = np.zeros((n_samples, 1), dtype=np.float64)
    for b, t0 in enumerate(starts):
        blk = np.fft.irfft(Z[:, b, :], n=nfft, axis=0)[:n_t, :]
        acc[t0:t0 + n_t, :] += blk * win
        wsum[t0:t0 + n_t, :] += win ** 2
    return acc / np.maximum(wsum, 1e-12)


def _lateral_coherence(z: np.ndarray) -> np.ndarray:
    """横向相干度 ``C(τ, f, j)``（**只用该方法自身的输出**）。

    ``C = |Σ_{j'∈N(j)} Z(j')·conj(Z(j'+1))| / (Σ|Z(j')|² · Σ|Z(j'+1)|²)^{1/2}``，
    ``N(j) = {j-1, j, j+1} ∩ [0, n_trace-1]``。
    """
    nf, nt, ntr = z.shape
    if ntr < 2:
        return np.zeros((nf, nt, ntr), dtype=np.float64)
    a = z[:, :, :-1]
    b = z[:, :, 1:]
    num = np.abs(a * np.conj(b))
    da = np.abs(a) ** 2
    db = np.abs(b) ** 2
    pair = num / np.sqrt(np.maximum(da * db, 0.0) + 1e-300)     # (nf, nt, ntr-1)

    out = np.zeros((nf, nt, ntr), dtype=np.float64)
    for j in range(ntr):
        vals = []
        for jj in (j - 1, j):
            if 0 <= jj < ntr - 1:
                vals.append(pair[:, :, jj])
        if vals:
            out[:, :, j] = np.mean(np.stack(vals, axis=0), axis=0)
    return np.clip(out, 0.0, 1.0)


def _block_dip_linearity(y: np.ndarray, n_frame: int, n_t: int, dt: float,
                         dx: float, v_lo: float) -> np.ndarray:
    """逐**块**（窗长 ``n_t``，步长 ``n_t//2``）的视倾角与线性度子分 ``d ∈ [0,1]``。

    该块输出做 2D FFT → 能量峰 → ``v_app = |f| / |k|``；
    ``d = clip((v_lo − v_app) / v_lo, 0, 1)``（``v_app ≥ v_lo`` ⇒ 0）。
    """
    ns, ntr = y.shape
    stride = max(1, n_t // 2)
    out = np.zeros(n_frame, dtype=np.float64)
    win_t = np.hanning(n_t)[:, None]
    win_x = np.hanning(ntr)[None, :]
    for b in range(n_frame):
        t0 = b * stride
        blk = y[t0:t0 + n_t, :]
        if blk.shape[0] < n_t:
            out[b] = 0.0
            continue
        spec = np.abs(np.fft.fftshift(np.fft.fft2(blk * win_t * win_x), axes=1))
        i_f, i_k = np.unravel_index(int(np.argmax(spec)), spec.shape)
        freqs = np.fft.fftfreq(n_t, d=dt)
        knums = np.fft.fftshift(np.fft.fftfreq(ntr, d=dx))
        f_pk, k_pk = float(freqs[i_f]), float(knums[i_k])
        tot = float(spec.sum())
        lin = float(spec[i_f, i_k] / tot) if tot > 0 else 0.0
        if abs(k_pk) < 1e-12 or abs(f_pk) < 1e-12:
            v_app = np.inf
        else:
            v_app = abs(f_pk) / abs(k_pk)
        d_val = float(np.clip((v_lo - v_app) / v_lo, 0.0, 1.0))
        if lin > 0.5:                       # 预注册：线性度 > 0.5 亦判为低速线性干扰
            d_val = max(d_val, 1.0)
        out[b] = d_val
    return out


def _block_band_fraction(err: np.ndarray, n_frame: int, n_t: int, dt: float,
                         band: tuple[float, float]) -> np.ndarray:
    """逐块误差在冻结频散带内的能量占比 ``b ∈ [0,1]``（``err = y_i − x``，``x`` **非真值**）。"""
    ns, ntr = err.shape
    stride = max(1, n_t // 2)
    freqs = np.fft.rfftfreq(n_t, d=dt)
    sel = (freqs >= band[0]) & (freqs <= band[1])
    out = np.zeros(n_frame, dtype=np.float64)
    for b in range(n_frame):
        t0 = b * stride
        blk = err[t0:t0 + n_t, :]
        if blk.shape[0] < n_t:
            continue
        p = np.abs(np.fft.rfft(blk, axis=0)) ** 2
        tot = float(p.sum())
        out[b] = float(p[sel, :].sum() / tot) if tot > 0 else 0.0
    return np.clip(out, 0.0, 1.0)


def _local_similarity_a(zi: np.ndarray, zj: np.ndarray) -> np.ndarray:
    """跨方法一致性子分 ``a = 1 − |⟨Z_i, Z_j⟩| / (‖Z_i‖‖Z_j‖)``（**局部，逐系数**）。

    在该时频点的**道邻域** ``{j-1, j, j+1}`` 内计算内积（预注册 `a_cross_method_consistency`）。
    """
    nf, nt, ntr = zi.shape
    a = np.zeros((nf, nt, ntr), dtype=np.float64)
    for j in range(ntr):
        lo, hi = max(0, j - 1), min(ntr, j + 2)
        vi, vj = zi[:, :, lo:hi], zj[:, :, lo:hi]
        num = np.abs(np.sum(vi * np.conj(vj), axis=2))
        den = np.sqrt(np.sum(np.abs(vi) ** 2, axis=2) * np.sum(np.abs(vj) ** 2, axis=2))
        with np.errstate(divide="ignore", invalid="ignore"):
            sim = np.where(den > 0, num / den, 0.0)
        a[:, :, j] = 1.0 - np.clip(sim, 0.0, 1.0)
    return np.clip(a, 0.0, 1.0)


def fuse(y_i: np.ndarray, y_j: np.ndarray, params: dict | None = None) -> np.ndarray:
    """两方法融合（**签名不含真值**）。

    参数
    ----
    y_i, y_j : 两方法的输出，形状 ``(n_samples, n_traces)``。
    params : 非真值参数；**官方运行传 ``x``（共享含噪输入，非真值）**。

    返回
    ----
    融合输出，形状同输入。

    边界
    ----
    ``w_i′ + w_j′ ≤ 0``（双方均被完全抑制）⇒ **退化为等权** ``ν = 0.5``（预注册）。
    """
    p = dict(PARAMS_DEFAULT)
    if params:
        p.update(params)

    a_arr = np.asarray(y_i, dtype=np.float64)
    b_arr = np.asarray(y_j, dtype=np.float64)
    if a_arr.ndim != 2 or b_arr.ndim != 2 or a_arr.shape != b_arr.shape:
        raise ValueError(f"y_i/y_j 须同形二维，实测 {a_arr.shape} 与 {b_arr.shape}")
    if not (np.all(np.isfinite(a_arr)) and np.all(np.isfinite(b_arr))):
        raise ValueError("输入含非有限值")

    ns, ntr = a_arr.shape
    dt = float(p["dt"])
    dx = 10.0
    n_t = int(p["n_t"])
    gamma = float(p["gamma"])
    v_lo = float(p["v_lo_m_s"])
    band = tuple(p["band_hz"])
    eps = float(p["eps"])
    x_in = p.get("x", None)

    starts, zi = _stft(a_arr, n_t)
    _s2, zj = _stft(b_arr, n_t)
    nf, nfr = zi.shape[0], zi.shape[1]

    # ---- w_i = C_i ** p（只用自身输出）
    wi = _lateral_coherence(zi) ** P_COHERENCE_POWER
    wj = _lateral_coherence(zj) ** P_COHERENCE_POWER

    # ---- s_i = clip(0.4 d + 0.3 b + 0.3 a, 0, 1)
    di = _block_dip_linearity(a_arr, nfr, n_t, dt, dx, v_lo)
    dj = _block_dip_linearity(b_arr, nfr, n_t, dt, dx, v_lo)
    if x_in is not None:
        x_arr = np.asarray(x_in, dtype=np.float64)
        ei, ej = a_arr - x_arr, b_arr - x_arr
        bi = _block_band_fraction(ei, nfr, n_t, dt, band)
        bj = _block_band_fraction(ej, nfr, n_t, dt, band)
        b_used = True
    else:                                   # 条件 2：缺失 ⇒ b = 0 且调用方须标注
        bi = np.zeros(nfr, dtype=np.float64)
        bj = np.zeros(nfr, dtype=np.float64)
        b_used = False
    ai = _local_similarity_a(zi, zj)
    aj = _local_similarity_a(zj, zi)

    # 块级子分广播到时频帧（帧与块同 hop ⇒ 一一对应）
    def _s_of(d_blk, b_blk, a_cf):
        """块级子分 d/b 广播到 (nf, nfr, 1)，与逐系数的 a (nf, nfr, ntr) 相加。

        **维度说明**：`d`（视倾角/线性度）与 `b`（频带占比）是**逐块**量 ⇒ 在同一帧内
        对所有道取同值；`a`（跨方法一致性）是**逐系数**量 ⇒ 逐道不同。
        二者相加必须显式对齐到 (nf, nfr, ntr)。
        """
        n = min(nfr, d_blk.size)
        db = np.zeros(nfr, dtype=np.float64); db[:n] = d_blk[:n]
        bb = np.zeros(nfr, dtype=np.float64); bb[:n] = b_blk[:n]
        d_cf = db[None, :, None]            # (1, nfr, 1) -> 广播到 (nf, nfr, ntr)
        b_cf = bb[None, :, None]
        return np.clip(S_SUBWEIGHTS["d"] * d_cf + S_SUBWEIGHTS["b"] * b_cf
                       + S_SUBWEIGHTS["a"] * a_cf, 0.0, 1.0)

    si = _s_of(di, bi, ai)
    sj = _s_of(dj, bj, aj)

    # ---- w' = w (1 - gamma s)
    wpi = wi * (1.0 - gamma * si)
    wpj = wj * (1.0 - gamma * sj)

    # ---- 逐系数归一化（含退化规则）
    tot = wpi + wpj
    degen = tot <= 0.0
    nu_i = np.where(degen, 0.5, wpi / np.where(degen, 1.0, tot + eps))
    nu_j = np.where(degen, 0.5, wpj / np.where(degen, 1.0, tot + eps))

    zf = nu_i * zi + nu_j * zj

    # ---- 逆 STFT（自实现 Hann OLA + 逐样点窗累计和归一化）
    out = _istft(zf, starts, ns, n_t)
    if not np.all(np.isfinite(out)):
        raise ValueError("融合输出含非有限值")

    # 附注：b 是否启用（供运行脚本写入 metrics.csv 的 x_missing 标注）
    fuse.last_b_enabled = bool(b_used)          # type: ignore[attr-defined]
    return out
