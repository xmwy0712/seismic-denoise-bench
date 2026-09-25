"""P1.2 指标验收：CNA / 事件级指标 / 事件匹配器。

覆盖 P1.2 任务单与 P1.2-Am1 的 A1–A3 约束。

**期望值不得由被测代码自算**：本文件中的期望值均为**解析常量**或由
**独立于被测实现**的路径给出（详见各用例注释）。
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from bench.metrics.cna import (
    CnaOutcome,
    build_subspace,
    cna_db,
    cna_outcome,
    project_onto_subspace,
)
from bench.metrics.events import event_metrics, event_peak_time_ms
from bench.metrics.matching import (
    PRE_REGISTERED_F1_THRESHOLD,
    MatchingTolerances,
    match_events,
)
from bench.data.synthetic import add_dispersive_surface_wave, add_linear_coherent
from bench.data.ricker import ricker

DT, DX = 0.002, 10.0
SEED = 20261001

# ---------------------------------------------------------------------------
# 测试用模板参数（**来自冻结配置的等价取值**，与任何方法输出无关 —— A1-1）
# ---------------------------------------------------------------------------
TPL_NS, TPL_NTR = 256, 16
TPL_LIN_VAPP = 1500.0
TPL_LIN_FMAIN = 30.0
TPL_DISP_V_MODEL, TPL_DISP_V0, TPL_DISP_C = "linear", 500.0, 10.0
TPL_DISP_A, TPL_DISP_B = 250.0, 0.5
TPL_DISP_F_LO, TPL_DISP_F_HI = 5.0, 25.0


def _build_templates(seed: int = SEED) -> np.ndarray:
    """按冻结参数生成相干噪声模板（**只含相干噪声**，不含随机噪声/真值 —— A1-2）。"""
    base = np.zeros((TPL_NS, TPL_NTR), dtype=np.float64)
    rng = np.random.default_rng(seed)
    lin = add_linear_coherent(base, TPL_LIN_VAPP, DT, DX, rng, f_main=TPL_LIN_FMAIN)
    lin = lin - base                                  # 去掉零基线，只留干扰本身
    disp = add_dispersive_surface_wave(
        base, DT, DX, np.random.default_rng(seed + 1),
        v_model=TPL_DISP_V_MODEL, v0=TPL_DISP_V0, c=TPL_DISP_C,
        a=TPL_DISP_A, b=TPL_DISP_B,
        f_lo=TPL_DISP_F_LO, f_hi=TPL_DISP_F_HI,
        amplitude=1.0, n_components=12,
    )
    disp = disp - base
    return np.stack([lin, disp], axis=0)


# =============================================================================
# 一、CNA —— 先决验证（协议硬门禁）
# =============================================================================
def test_cna_prerequisite_recovery_error_within_5pct() -> None:
    """**先决验证（协议明文硬门禁）**：纯相干噪声的投影回收误差 ≤ 5%。

    构造：``y - s = nc``（无随机噪声、无信号残留）→ ``P_C(nc)`` 应几乎完全回收 ``nc``。
    回收误差定义：``||P_C(nc) - nc|| / ||nc||``。
    """
    templates = _build_templates()
    q = build_subspace(templates)

    nc = templates[0]                                  # 纯相干噪声
    proj = project_onto_subspace(nc, q)
    err = float(np.linalg.norm(proj - nc) / np.linalg.norm(nc))

    assert err <= 0.05, (
        f"投影回收误差 {err:.6%} > 5% → 子空间构造有 bug，不得进入主实验"
    )


def test_cna_prerequisite_holds_for_both_template_families() -> None:
    """两类模板（线性干扰、频散面波）的回收误差均 ≤ 5%。"""
    templates = _build_templates()
    q = build_subspace(templates)
    for i, name in enumerate(("linear_coherent", "dispersive_surface")):
        nc = templates[i]
        proj = project_onto_subspace(nc, q)
        err = float(np.linalg.norm(proj - nc) / np.linalg.norm(nc))
        assert err <= 0.05, f"{name} 回收误差 {err:.6%} > 5%"


def test_cna_prerequisite_holds_for_mixed_coherent_noise() -> None:
    """混合相干噪声（两类模板线性叠加）同样须回收 ≤ 5%。"""
    templates = _build_templates()
    q = build_subspace(templates)
    nc = templates[0] + 0.7 * templates[1]
    proj = project_onto_subspace(nc, q)
    err = float(np.linalg.norm(proj - nc) / np.linalg.norm(nc))
    assert err <= 0.05, f"混合相干噪声回收误差 {err:.6%} > 5%"


# =============================================================================
# 二、CNA —— 数值与边界
# =============================================================================
def test_cna_unprocessed_equals_zero_db_by_analytical_argument() -> None:
    """``y = x``（不处理）→ 残差即 ``nc`` 本身，故 ``‖nc‖²/‖P_C(nc)‖² ≈ 1`` → CNA ≈ 0 dB。

    解析论证：若残差完全落在子空间内，``‖P_C(nc)‖² ≈ ‖nc‖²``，故 CNA → 0 dB。
    """
    templates = _build_templates()
    q = build_subspace(templates)
    nc = templates[0]
    value = cna_db(nc, nc, q)
    assert abs(value) <= 0.05, f"未处理时 CNA 应为 ≈0 dB，实测 {value:.4f} dB"


def test_cna_perfect_denoise_returns_pos_inf_with_flag() -> None:
    """``y = s`` → 残差为 0 → CNA = ``+inf``（不 NaN），并置哨兵标志。"""
    templates = _build_templates()
    q = build_subspace(templates)
    nc = templates[0]
    zeros = np.zeros_like(nc)
    out = cna_outcome(nc, zeros, q)
    assert isinstance(out, CnaOutcome)
    assert out.value == math.inf
    assert not math.isnan(out.value)
    assert out.denoiser_left_no_residual is True


def test_cna_orthogonal_residual_yields_very_large_value() -> None:
    """残差与子空间近似正交（相干噪声已基本抑制）→ CNA 为**极大的有限值**。

    构造：取与子空间正交的残差（``nc`` 减去其投影）。

    **说明（如实记录断言口径的修正）**：初版断言 ``== inf`` 过严 —— 数值上
    ``‖P_C(orth)‖`` 不会精确为 0（`Q Qᵀ` 的浮点残差约 1e-14 量级），
    故 CNA 是 ~295 dB 的**大数**而非真正的 ``+inf``。
    这正是"该走哨兵分支"的信号偏弱时的实情：只有**残差恒为 0**（``y = s``）
    才触发 ``+inf``。本用例改为断言"极大值"，并另设一例验证真正的 0 残差走 ``+inf``。
    """
    templates = _build_templates()
    q = build_subspace(templates)
    nc = templates[0]
    orth = nc - project_onto_subspace(nc, q)
    out = cna_outcome(nc, orth, q)
    assert out.value > 200.0, f"近似正交残差应给出极大 CNA，实测 {out.value:.2f} dB"
    assert not math.isnan(out.value)


def test_cna_suppression_improves_with_partial_removal() -> None:
    """单调性：残差中相干成分越少，CNA 越高（用**解析构造的残差**对拍）。

    构造三档残差：``nc`` / ``0.5·nc`` / ``0.1·nc``。
    解析期望：CNA = ``10·log10(‖nc‖²/‖P_C(α·nc)‖²) = 10·log10(1/α²) = −20·log10(α)``。
    """
    templates = _build_templates()
    q = build_subspace(templates)
    nc = templates[0]
    for alpha in (1.0, 0.5, 0.1):
        got = cna_db(nc, alpha * nc, q)
        expected = -20.0 * math.log10(alpha)          # 独立解析式
        assert got == pytest.approx(expected, abs=0.05), (
            f"alpha={alpha}: 期望 {expected:.4f} dB，实测 {got:.4f} dB"
        )


def test_cna_zero_nc_energy_raises() -> None:
    """``nc`` 能量为 0 → ``ValueError``（配置错误，不得静默返回）。"""
    templates = _build_templates()
    q = build_subspace(templates)
    with pytest.raises(ValueError):
        cna_db(np.zeros_like(templates[0]), templates[0], q)


def test_cna_non_finite_input_raises() -> None:
    """含 NaN/Inf → ``ValueError``。"""
    templates = _build_templates()
    q = build_subspace(templates)
    bad = templates[0].copy()
    bad[0, 0] = np.nan
    with pytest.raises(ValueError):
        cna_db(bad, templates[0], q)
    bad2 = templates[0].copy()
    bad2[0, 0] = np.inf
    with pytest.raises(ValueError):
        cna_db(templates[0], bad2, q)


def test_subspace_is_orthonormal_and_rank_reported() -> None:
    """子空间基须列正交（``QᵀQ = I``）；秩不超过模板数。"""
    templates = _build_templates()
    q = build_subspace(templates)
    gram = q.T @ q
    np.testing.assert_allclose(gram, np.eye(q.shape[1]), rtol=0, atol=1e-10)
    assert q.shape[1] <= templates.shape[0]


def test_subspace_rank_tol_zero_keeps_all_resolvable_directions() -> None:
    """``rank_tol=0`` 时保留所有数值可分辨方向（秩 = 模板数，当模板线性无关）。"""
    templates = _build_templates()
    q0 = build_subspace(templates, rank_tol=0.0)
    assert q0.shape[1] == templates.shape[0]


def test_subspace_empty_templates_raises() -> None:
    """空模板集合 → ``ValueError``。"""
    with pytest.raises(ValueError):
        build_subspace(np.zeros((0, 8), dtype=np.float64))


# =============================================================================
# 三、事件级指标
# =============================================================================
def test_event_peak_time_zero_error_for_analytical_spike() -> None:
    """**解析对拍**：窗内单尖峰（真值到时精确可知）→ 到时误差 ≈ 0。

    构造：样点 ``k`` 处单位脉冲，``dt=2 ms`` → 真值到时 = ``k·dt``（解析可知）。
    """
    n = 128
    sig = np.zeros((n, 1), dtype=np.float64)
    k = 40
    sig[k, 0] = 1.0

    t_ms = event_peak_time_ms(sig, DT, (20, 60))
    expected_ms = k * DT * 1000.0
    assert t_ms == pytest.approx(expected_ms, abs=1e-9), (
        f"解析到时 {expected_ms} ms，实测 {t_ms} ms"
    )


def test_event_metrics_zero_when_output_equals_truth() -> None:
    """``y = s`` → 到时误差 0、能量误差 0。"""
    rng = np.random.default_rng(SEED)
    _t, wav = ricker(25.0, DT, 61)
    from bench.data.synthetic import forward, reflectivity

    refl = reflectivity(120, rng)
    s = forward(refl, wav, n_traces=1)
    windows = [(50, 90), (120, 170)]
    summ = event_metrics(s, s.copy(), windows, DT)
    assert len(summ.events) == 2
    for e in summ.events:
        assert e.timing_error_ms == pytest.approx(0.0, abs=1e-9)
        assert e.energy_rel_error == pytest.approx(0.0, abs=1e-12)


def test_event_metrics_energy_error_matches_analytical_scaling() -> None:
    """**解析对拍**：``y = 2s`` → 能量误差 = ``|4−1|/1 = 3``（解析值）。"""
    n = 200
    s = np.zeros((n, 1), dtype=np.float64)
    s[80:100, 0] = 1.0
    y = 2.0 * s
    summ = event_metrics(s, y, [(60, 120)], DT)
    assert summ.events[0].energy_rel_error == pytest.approx(3.0, abs=1e-12)


def test_event_metrics_timing_error_matches_analytical_shift() -> None:
    """**解析对拍**：``y`` 相对 ``s`` 平移 ``m`` 样点 → 到时误差 = ``m·dt``（ms）。"""
    shift = 5
    n = 256
    s = np.zeros((n, 1), dtype=np.float64)
    k = 100
    s[k, 0] = 1.0
    y = np.roll(s, shift, axis=0)
    # 窗避开边界，避免 roll 环绕影响
    summ = event_metrics(s, y, [(60, 160)], DT)
    expected_ms = shift * DT * 1000.0
    assert summ.events[0].timing_error_ms == pytest.approx(expected_ms, abs=1e-9)


def test_event_metrics_rejects_bad_window() -> None:
    """非法事件窗 → ``ValueError``。"""
    s = np.zeros((64, 1), dtype=np.float64)
    with pytest.raises(ValueError):
        event_metrics(s, s.copy(), [(50, 200)], DT)
    with pytest.raises(ValueError):
        event_metrics(s, s.copy(), [(-1, 10)], DT)


# =============================================================================
# 四、事件匹配器（A2：容差先冻结、后测量）
# =============================================================================
def _isolated_set() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """子集 `isolated`：事件间距 > 200 ms（远超容差）。"""
    t = np.array([100.0, 400.0, 700.0, 1000.0])
    x = np.array([5.0, 5.0, 5.0, 5.0])
    return t, x, t.copy(), x.copy()          # 检出 = 真值（理想检出）


def _near_neighbor_set() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """子集 `near_neighbor`：相邻间距 40–120 ms（容差 40 ms 的困难情形）。"""
    truth_t = np.array([100.0, 200.0, 280.0, 500.0])
    truth_x = np.array([3.0, 3.0, 4.0, 3.0])
    detected_t = truth_t + np.array([5.0, -8.0, 6.0, 3.0])   # 含微小抖动
    detected_x = truth_x.copy()
    return truth_t, truth_x, detected_t, detected_x


def _partial_overlap_set() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """子集 `partial_overlap`：相邻间距 < 40 ms（时间上部分重叠）。"""
    truth_t = np.array([100.0, 125.0, 300.0, 320.0])
    truth_x = np.array([2.0, 2.0, 6.0, 6.0])
    detected_t = truth_t + np.array([3.0, 2.0, -4.0, 5.0])
    detected_x = truth_x.copy()
    return truth_t, truth_x, detected_t, detected_x


def test_matcher_precision_recall_f1_on_isolated() -> None:
    """`isolated` 子集：理想检出 → P=R=F1=1.0。"""
    tt, tx, dt_, dx_ = _isolated_set()
    r = match_events(tt, tx, dt_, dx_)
    assert r.precision == pytest.approx(1.0)
    assert r.recall == pytest.approx(1.0)
    assert r.f1 == pytest.approx(1.0)
    assert r.meets_threshold


def test_matcher_handles_near_neighbor() -> None:
    """`near_neighbor` 子集：容差内抖动应被正确匹配。"""
    tt, tx, dt_, dx_ = _near_neighbor_set()
    r = match_events(tt, tx, dt_, dx_)
    assert r.n_matched == 4
    assert r.f1 == pytest.approx(1.0)


def test_matcher_handles_partial_overlap() -> None:
    """`partial_overlap` 子集：重叠情形下仍应匹配成功（间距 20–25 ms < 容差）。"""
    tt, tx, dt_, dx_ = _partial_overlap_set()
    r = match_events(tt, tx, dt_, dx_)
    assert r.n_matched == 4, f"重叠子集仅匹配 {r.n_matched}/4"


def test_matcher_penalises_false_positives() -> None:
    """误检（false positive）应降低精确率——证明指标非空转。"""
    tt = np.array([100.0, 400.0])
    tx = np.array([5.0, 5.0])
    dt_ = np.array([100.0, 400.0, 900.0])        # 第三个是误检
    dx_ = np.array([5.0, 5.0, 5.0])
    r = match_events(tt, tx, dt_, dx_)
    assert r.n_matched == 2
    assert r.precision == pytest.approx(2.0 / 3.0)
    assert r.recall == pytest.approx(1.0)
    assert not r.meets_threshold


def test_matcher_penalises_misses() -> None:
    """漏检（false negative）应降低召回率。"""
    tt = np.array([100.0, 400.0, 700.0])
    tx = np.array([5.0, 5.0, 5.0])
    dt_ = np.array([100.0, 400.0])               # 漏掉第三个
    dx_ = np.array([5.0, 5.0])
    r = match_events(tt, tx, dt_, dx_)
    assert r.n_matched == 2
    assert r.recall == pytest.approx(2.0 / 3.0)
    assert r.precision == pytest.approx(1.0)


def test_matcher_respects_frozen_tolerances() -> None:
    """容差**冻结值**被真正使用：超容差的候选不得配对。"""
    tol = MatchingTolerances()
    assert tol.time_tol_ms == 40.0, "容差与 metrics-spec.md 冻结值不符"
    assert tol.trace_tol == 2
    assert tol.allow_one_to_many is False

    # 时间超容差 → 不配对
    r = match_events(np.array([100.0]), np.array([5.0]),
                     np.array([160.0]), np.array([5.0]))
    assert r.n_matched == 0
    # 道号超容差 → 不配对
    r2 = match_events(np.array([100.0]), np.array([5.0]),
                      np.array([100.0]), np.array([9.0]))
    assert r2.n_matched == 0


def test_matcher_threshold_is_protocol_value() -> None:
    """门限为协议明文值 0.95，**未被放宽**。"""
    assert PRE_REGISTERED_F1_THRESHOLD == 0.95


def test_matcher_all_subsets_meet_95pct() -> None:
    """三个子集的 F1 均须 ≥ 95%（协议门限）。"""
    results = {}
    for name, builder in (
        ("isolated", _isolated_set),
        ("near_neighbor", _near_neighbor_set),
        ("partial_overlap", _partial_overlap_set),
    ):
        tt, tx, dt_, dx_ = builder()
        r = match_events(tt, tx, dt_, dx_)
        results[name] = r
        assert r.f1 >= PRE_REGISTERED_F1_THRESHOLD, (
            f"{name}: F1={r.f1:.4f} < {PRE_REGISTERED_F1_THRESHOLD}"
            f"（P={r.precision:.4f} R={r.recall:.4f}）"
        )


# =============================================================================
# 五、A3 独立性守卫（指标不得依赖被评对象）
# =============================================================================
def _import_lines(path) -> list[str]:
    import re
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()
            if re.match(r"^\s*(import|from)\s+", ln)]


def test_metrics_do_not_import_methods_or_fusion() -> None:
    """**A3 独立性守卫**：指标实现不得导入 methods / fusion / coherence 相关模块。"""
    from pathlib import Path
    pkg = Path(__file__).resolve().parent.parent / "src" / "bench" / "metrics"
    offenders: list[str] = []
    for f in sorted(pkg.glob("*.py")):
        for ln in _import_lines(f):
            if any(k in ln for k in ("methods", "fusion", "coherence")):
                offenders.append(f"{f.name}: {ln}")
    assert not offenders, f"指标实现导入了被评对象相关模块 → 独立性被破坏：{offenders}"


def test_metrics_test_file_does_not_import_methods_or_fusion() -> None:
    """同一守卫适用于本测试文件自身（只查 import 行，不查注释/文档串）。"""
    from pathlib import Path
    src = Path(__file__).read_text(encoding="utf-8")
    import re
    imports = [ln.strip() for ln in src.splitlines() if re.match(r"^\s*(import|from)\s+", ln)]
    offenders = [ln for ln in imports if any(k in ln for k in ("methods", "fusion", "coherence"))]
    assert not offenders, f"测试文件导入了被评对象相关模块：{offenders}"
