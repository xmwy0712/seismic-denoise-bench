# 预注册 · 互补性阈值口径的直接检验（P5.8 · WS2②）

> **状态**：**运行前冻结**。本文件与 `execution/complementarity10_stratified.py` 一并**独立提交并打 tag**，
> 之后才运行检验。**运行后不得修改本文件**；如口径需变，另立新文件并重走该流程。

## 一、问题

`results/complementarity/pair_selection.json` 的配对选择使用**全局池化**的 `IQR×1.5` 阈值
（主配对 `fx_deconv|wavelet_threshold` 的 τ = `0.03946529906544755`）。
审稿人指出：该池化把三类噪声的 `|Δ Lsig_w|` 合并成一个分位基准，
**可能制造了「主配对居首」的伪影**。

## 二、处置（只改一处）

把 M2 的逐对阈值 `τ_ij` 由

* **原口径**：全部观测合并后取 `IQR×1.5`（全局池化）

改为

* **新口径**：**逐噪声类型层内**分别合并后取 `IQR×1.5`（N1 / N2 / N3 各一套 τ）。

**其余一律不变**：M1 / M1_signed / M3 的定义、观测集合（270）、分层键（18）、
选择规则（max global M2 median → tie → M1 → tie → lexicographic）、配对集合（10 对）。

## 三、判读（**两个方向都接受，如实报告**）

| 结果 | 解释 |
| :--- | :--- |
| 主配对 `fx_deconv|wavelet_threshold` **仍居首** | 池化未制造伪影 ⇒ 回到「系统性占优」解释 |
| 主配对**不再居首** | 池化伪影坐实 ⇒ 按新首位配对报告并如实披露 |

**不预设期望，不调口径迎合结论。**

## 四、自证门（自带反证）

以 `--mode pooled` 复现既有口径，其 M1 / M1_signed / M2 / M3 必须与
`results/complementarity10/complementarity10.csv` **逐值一致**（tol = 1e-12）。
不一致 ⇒ `cross_ok = False`，**退出码非零**，检验作废。
该门反证：本脚本在口径不变时**确实复现**了既有结果，故口径改变带来的差异可归因于该改变本身。

## 五、产物

| 文件 | 内容 |
| :--- | :--- |
| `results/complementarity10_stratified/complementarity10_stratified.csv` | 层内口径下的 10 对 × 4 度量 × 18 层键 |
| `results/complementarity10_stratified/reselection.json` | 两套阈值、两套排序、重选结果与判读 |
| `docs/execution-log.md` | 追加式记录（含 WS1 排查两问） |

**独立性**：不导入 `bench.fusion` / `bench.methods`（同原模块）。
