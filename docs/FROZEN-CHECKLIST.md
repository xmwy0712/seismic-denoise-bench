# FROZEN-CHECKLIST.md —— P1.5 冻结清单逐项核对

> **配套文件**：[`configs/frozen.yaml`](../configs/frozen.yaml)（配置权威）。本清单与 yaml **逐项一致**。
> **依据**：`docs/task-sheets/P1.5-全量配置冻结-2026-10-04.md`
> SHA256 `61419E78BAFB5BBDC2833C4CD4ED4B9B5132559810189B15D9CC9C747013D488`（7771 B）

**冻结时间**：2026-09-26 10:56:56+08:00
**frozen.yaml**：30065 B，SHA256 `1695C1965D0F307E5CA55ABDA1B2206D1058F67DE4827770382602F2F2944A3F`

**自哈希说明（如实）**：`frozen.yaml` 的 SHA256 **不可内嵌于该文件自身**（写入即改变哈希）。
故记录于**本清单 + `execution-log.md` + annotated tag `config-frozen` 附注**三处，互相印证。

## 逐项核对（22 项）

| # | 冻结项 | yaml 键 | 内容要求 | 来源归档件 | SHA8 | 核对 |
| ---: | :--- | :--- | :--- | :--- | :--- | :---: |
| 1 | 合成配置矩阵 | `item_01_synthetic_matrix` | 54 配置（2 模型 × 3 噪声 × 3 档 × 3 主频）+ 种子 [101,202,303,404,505]，算式与总数写明 | P1.1-合成数据生成器完整版 | `A09EA0A8` | ✅ |
| 2 | 主模型参数 | `item_02_model_m1` | dt=0.002 / 64 道 / dx=10 m / 主频档 {15,25,40} Hz | P1.1-合成数据生成器完整版 | `A09EA0A8` | ✅ |
| 3 | 第二模型参数 | `item_03_model_m2` | dip_deg_range / curvature_range / 断层参数 / sparsity（P1.1 实现值） | P1.1-合成数据生成器完整版 | `A09EA0A8` | ✅ |
| 4 | 噪声强度档位（双口径） | `item_04_noise_levels` | 口径 (i) 目标输入 SNR（规范）+ 口径 (ii) amplitude_ratio（描述性）+ **实测标定表**；**N2 特例条款** | P1.2-Am3-验收通过与两处更正两项裁定 | `3A120A2E` | ✅ |
| 5 | 频散面波 | `item_05_dispersive_surface_wave` | v_model/v0/c/a/b/f_lo/f_hi/n_components=24 + dispersion_v_band_mps:[100,3000] | P1.1-Am1-频散物理合理性与报告口径 | `F7E0BB32` | ✅ |
| 6 | 掩码与事件窗 | `item_06_mask_and_event_window` | n_T 三元组（逐频点, half-up）+ event_mask 阈值 + 沿时间轴膨胀 + 距边界 ≥ ceil(n_T/2) + FP 回退阶梯 | P0.3-Am1-nT裁定与外部写入处置 | `2DD96C71` | ✅ |
| 7 | 数值约定 C1–C6 | `item_07_numeric_conventions_C1_C6` | snr_db 完美→+inf；x==s∧y==s→0.0（显式）；标志语义；零尺寸报错；掩码边界不环绕；锚定规则写死 | P0.3-Am3-代码同源判定与数值约定核定 | `5F2F160E` | ✅ |
| 8 | CNA 建基规则 | `item_08_cna_basis` | 分量基（线性 10 + 面波 2×24=48 维）、rank_tol=1e-8、**禁用抽样建基**（三条理由） | P1.2-Am2-CNA子空间张成阻断整改 | `3A0E0E8E` | ✅ |
| 9 | 野外面板 | `item_09_field_panels` | FP1/FP2/FP3（测区/道范围/时间窗/事件窗/倾角/实际 k_mad）+ 预览图引用 | P1.3-Am1-面板选定验收与网格数字再核 | `87A4FA6A` | ✅ |
| 10 | 融合保守度 3 档 | `item_10_fusion_conservativeness` | gamma 0.40 / 0.50 / 0.60，语义 w′=w(1−gamma·s) | P1.3-野外3面板选定 | `0EFEBA6B` | ✅ |
| 11 | 野外权重与统计规则 | `item_11_field_weights_and_stats` | 四项权重 30/25/25/20、配对置换检验、Holm 校正 | protocol-v5.md / README.md | `—` | ✅ |
| 12 | f-k 符号约定 | `item_12_fk_sign_convention` | 核 exp(−2πi(ft+kx)) → 脊线 k=−f/v（f>0 时 k<0） | P0.4-Am2-独立性判据与fk符号纠错 | `456AF58B` | ✅ |
| 13 | 证据等级（裁定 D） | `item_13_evidence_levels_ruling_D` | 核心事件证据 = 真值窗指标；复杂逐事件匹配一律辅助；匹配率须标注条件（1.0 / 0.731） | P1.2-Am3-验收通过与两处更正两项裁定 | `3A120A2E` | ✅ |
| 14 | CNA 定位声明（R16-d） | `item_14_cna_positioning` | 注入基目标型指标；子空间与注入参数同源；不得推断泛化 | P1.2-Am2-CNA子空间张成阻断整改 | `3A0E0E8E` | ✅ |
| 15 | 独立性与归属判据 | `item_15_independence_and_attribution` | 归属判据 a/b/c + 规则 15 四要件（引用 quarantine-register） | P0.4-Am2 + quarantine-register | `456AF58B` | ✅ |
| 16 | 环境依赖 | `item_16_environment` | Python 3.12.10、requirements.lock 全文、segyio 1.9.14 | P0.1R+P0.2-联合任务单 | `4559F626` | ✅ |
| 17 | 数据与许可 | `item_17_data_and_licenses` | Zenodo 10.5281/zenodo.10407771（CC BY 4.0 + 署名文本全文）、segyio LGPL-3.0 边界四条 | P0.6-Am3-Zenodo野外数据路径 | `11F5EB99` | ✅ |
| 18 | 检索边界声明 | `item_18_search_boundary` | 有界滚雪球边界 + 不构成查全证明 + Sandia 具名缺口 + 初筛仅 title + 竞争清单与 D1/D2/D3 | P1.4-Am1-竞争清单修订与两项披露 | `42A22F10` | ✅ |
| 19 | P2 判据修正记录 | `item_19_p2_criterion_record` | 原判据 0/40 无区分力 → 修正为相邻道相关系数（不参与面板质量判据，不追溯） | P1.3-Am2-秩谱实测与判定规则 | `558F2FEF` | ✅ |
| 20 | P3 连带风险 | `item_20_p3_connected_risk` | lateral_coherence 与 P2 同根因（近零基线 0.13–0.21）；**如实记录区分力有限**；P4 须先验证可区分性 | P1.5-全量配置冻结 | `61419E78` | ✅ |
| 21 | 仓库身份 | `item_21_repository_identity` | MIT，版权 Zhang Tao (张涛)；五 tag 体系 | P0.1-建仓落盘 | `5D665B37` | ✅ |
| 22 | 时间与哈希 | `item_22_time_and_hash` | 冻结时间、frozen.yaml 哈希、tag 指向 commit | P1.5-全量配置冻结 | `61419E78` | ✅ |

**逐项核对结论：22/22 全部在 `frozen.yaml` 中可查且注明来源。**

## 冻结前实测（本批）

| 项 | 结果 |
| :--- | :--- |
| 单观测时间 M1 | 1.366 ms（中位，预热后 15 次重复；min 1.206 / max 1.509） |
| 单观测时间 M2 | 29.449 ms（中位；min 16.397 / max 34.489） |
| **270 观测总时间** | **4.160 s**（135×1.366 + 135×29.449 ms） |
| 单观测峰值内存 | **2.004 MB**（上界，取两模型较大者；顺序执行） |
| 对照此前报告 | 8.6 / 21.3 ms / 5.7 s ⇒ **量级一致**；以本批实测为准 |
| 输入 SNR 标定表 | 实测 270 观测；N1/N3 与解析值一致；**N2 无档位** |
| 待定参数 | event_mask 阈值 = 0.5·max\|clean\|；rank_tol=1e-8；匹配器 40 ms / 2 道 |

## 冻结后变更规则（硬性）

1. **任何修改**都必须：**新版本文件 + 新 tag + 书面说明**；**禁止 amend**（红线）。
2. **缺项即视为未冻结**，P2 不得启动。
3. 禁止：实现融合或去噪方法；改动 `ricker.py` / `synthetic.py` / `snr.py` / `lsig.py` 已验收行为；装未列出的包。

## 流程位置

本清单 → WorkBuddy 终审（P1.6 逐项核对）→ **用户冻结确认（15 分钟，不可下放）** → P2 启动（云窗口 10-05 起）。
