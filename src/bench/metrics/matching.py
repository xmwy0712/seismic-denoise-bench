"""自动事件匹配器（含 95% 预注册门限）。

协议依据
--------
`docs/protocol-v5.md` 第四节第 4 条：

    只有自动事件匹配在人工生成的已知事件测试集上达到至少 95% 正确匹配率时，
    才报告复杂的逐事件匹配指标；否则复杂匹配仅作辅助，核心事件证据固定使用
    真值窗到时和能量误差。

**容差先冻结、后测量（A2）**
-----------------------------
容差在**测量之前**写入 `docs/metrics-spec.md` 第 3.1 节并冻结：

| 参数 | 值 | 语义 |
| :--- | :--- | :--- |
| ``time_tol_ms`` | **40.0** | 到时差 ≤ 该值视为时间可匹配 |
| ``trace_tol`` | **2** | 道号差 ≤ 该值视为空间可匹配 |
| ``allow_one_to_many`` | **false** | 不允许一对多 |
| ``matching_rule`` | **greedy-nearest** | 按到时差升序贪心配对 |

若开发中调整过容差，须在 `docs/execution-log.md` 如实报告**调整序列与每次匹配率**，
**不得**只报最终一次结果。

**"正确匹配率"定义（A2-4）**：本模块采用 **F1** 作为门限判据口径
（理由：95% 门限须同时约束误配与漏配，单看精确率或召回率均可被单侧操纵）。
三个指标一并返回。

**降级路径**：未达 95% → 调用方按协议把复杂匹配降为辅助指标，
核心事件证据固定用真值窗指标；**不放宽门限**。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["MatchingTolerances", "MatchResult", "match_events", "PRE_REGISTERED_F1_THRESHOLD"]

# 协议明文门限（**不得放宽**）
PRE_REGISTERED_F1_THRESHOLD = 0.95


@dataclass(frozen=True)
class MatchingTolerances:
    """匹配容差（**测量前冻结**，见 docs/metrics-spec.md 第 3.1 节）。"""

    time_tol_ms: float = 40.0
    trace_tol: int = 2
    allow_one_to_many: bool = False


@dataclass
class MatchResult:
    """匹配结果与三项指标。"""

    n_truth: int
    n_detected: int
    n_matched: int
    precision: float
    recall: float
    f1: float
    pairs: list[tuple[int, int]] = field(default_factory=list)

    @property
    def meets_threshold(self) -> bool:
        """是否达到协议门限（以 **F1** 为准）。"""
        return self.f1 >= PRE_REGISTERED_F1_THRESHOLD


def match_events(
    truth_times_ms: np.ndarray,
    truth_traces: np.ndarray,
    detected_times_ms: np.ndarray,
    detected_traces: np.ndarray,
    tol: MatchingTolerances | None = None,
) -> MatchResult:
    """把检出事件与真值事件配对，返回精确率 / 召回率 / F1。

    匹配规则（**greedy-nearest**）：
      1. 枚举所有满足 ``|Δt| ≤ time_tol_ms`` 且 ``|Δtrace| ≤ trace_tol`` 的候选对；
      2. 按 ``|Δt|`` **升序**贪心配对；
      3. 已配对的事件（真值与检出）不再参与后续配对（``allow_one_to_many=False``）。

    参数
    ----
    truth_times_ms, detected_times_ms : numpy.ndarray
        到时（ms）。
    truth_traces, detected_traces : numpy.ndarray
        道号。
    tol : MatchingTolerances | None
        容差；``None`` 用冻结默认值。

    返回
    ----
    MatchResult
        ``precision = n_matched / n_detected``；
        ``recall = n_matched / n_truth``；``f1 = 2PR/(P+R)``（分母为 0 时按 0 处理）。
    """
    t = tol or MatchingTolerances()
    tt = np.asarray(truth_times_ms, dtype=np.float64).ravel()
    tr = np.asarray(truth_traces, dtype=np.float64).ravel()
    dt_ = np.asarray(detected_times_ms, dtype=np.float64).ravel()
    dr = np.asarray(detected_traces, dtype=np.float64).ravel()

    if tt.size != tr.size:
        raise ValueError("真值的到时与道号长度不一致")
    if dt_.size != dr.size:
        raise ValueError("检出的到时与道号长度不一致")
    for name, arr in (("truth_times_ms", tt), ("detected_times_ms", dt_)):
        if arr.size and not np.all(np.isfinite(arr)):
            raise ValueError(f"{name} 含非有限值")

    n_truth, n_detected = tt.size, dt_.size
    if n_truth == 0 or n_detected == 0:
        precision = 0.0 if n_detected > 0 else 0.0
        recall = 0.0 if n_truth > 0 else 0.0
        f1 = 0.0
        return MatchResult(n_truth, n_detected, 0, precision, recall, f1, [])

    # 候选对（满足容差）
    cands: list[tuple[float, int, int]] = []
    for i in range(n_truth):
        for j in range(n_detected):
            dt_val = abs(dt_[j] - tt[i])
            dtr_val = abs(dr[j] - tr[i])
            if dt_val <= t.time_tol_ms and dtr_val <= t.trace_tol:
                cands.append((dt_val, i, j))

    # 贪心：按时间差升序
    cands.sort(key=lambda c: c[0])
    used_t: set[int] = set()
    used_d: set[int] = set()
    pairs: list[tuple[int, int]] = []
    for _diff, i, j in cands:
        if t.allow_one_to_many:
            pairs.append((i, j))
            used_t.add(i)
            used_d.add(j)
        else:
            if i in used_t or j in used_d:
                continue
            pairs.append((i, j))
            used_t.add(i)
            used_d.add(j)

    n_matched = len(pairs)
    precision = n_matched / n_detected
    recall = n_matched / n_truth
    denom = precision + recall
    f1 = (2.0 * precision * recall / denom) if denom > 0 else 0.0
    return MatchResult(n_truth, n_detected, n_matched, precision, recall, f1, pairs)
