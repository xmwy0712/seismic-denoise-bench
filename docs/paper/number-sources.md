# 论文数字来源对照表（draft-v1 + **draft-v2 增补**）

> **纪律**：初稿中**每一个数字**都必须能在此表找到来源产物与其 SHA256。
> **v2 增补**：下表末段为 P5.1（B 态修订）新增的来源行；v1 原有行**原样保留**。
> **禁止**使用未入册数字。

| 数字/量 | 值 | 来源产物 | SHA256 |
| :--- | :--- | :--- | :--- |
| 合成配置数 | 54（2 模型 × 3 噪声 × 3 档 × 3 主频） | `frozen-v2` | `1D4AF0389EDE2328015C09943536BD6B…` |
| 观测数 | 270（54 × 5 种子） | `frozen-v2` | `1D4AF0389EDE2328015C09943536BD6B…` |
| 方法数 | 5（滤波 2 / 变换阈值 1 / 分解 1 / 低秩 1） | `frozen-v2` | `1D4AF0389EDE2328015C09943536BD6B…` |
| 融合格数 | 1620（270 × 3 档 γ × 2 配对） | `fusion/metrics.csv` | `123B8E56893D1EE02094870D78BA42AE…` |
| 互补性行数 | 540（10 对 × 3 度量 × 18 分层键） | `complementarity.csv` | `AE0FF75F58F2E88D27F1751EF554BABE…` |
| M2 全局（选中对） | 0.500000 | `complementarity.csv` | `AE0FF75F58F2E88D27F1751EF554BABE…` |
| M2 全局（次名） | 0.200000 | `complementarity.csv` | `AE0FF75F58F2E88D27F1751EF554BABE…` |
| M2 零值对数 | 8/10 | `complementarity.csv` | `AE0FF75F58F2E88D27F1751EF554BABE…` |
| 选中对 M1（全 10 对最低） | 0.093807 | `complementarity.csv` | `AE0FF75F58F2E88D27F1751EF554BABE…` |
| ΔSNR 融合（主配对 γ=0.5） | 0.0588 dB | `fusion/metrics.csv` | `123B8E56893D1EE02094870D78BA42AE…` |
| ΔSNR 融合（次优 γ=0.5） | 2.5295 dB | `fusion/metrics.csv` | `123B8E56893D1EE02094870D78BA42AE…` |
| Lsig 融合（主配对 γ=0.5） | 0.020640 | `fusion/metrics.csv` | `123B8E56893D1EE02094870D78BA42AE…` |
| Lsig 融合（次优 γ=0.5） | 0.018103 | `fusion/metrics.csv` | `123B8E56893D1EE02094870D78BA42AE…` |
| ΔSNR 逐观测 oracle（上界） | 6.7033 dB | `metrics.csv` | `CD7499874B4A166E6B2737152D3B0C04…` |
| ΔSNR `fk_filter`（宏平均中位） | 0.9320 dB | `metrics.csv` | `CD7499874B4A166E6B2737152D3B0C04…` |
| Lsig `fk_filter`（宏平均中位） | 0.009706 | `metrics.csv` | `CD7499874B4A166E6B2737152D3B0C04…` |
| ΔSNR `fx_deconv`（宏平均中位） | 0.0000 dB | `metrics.csv` | `CD7499874B4A166E6B2737152D3B0C04…` |
| Lsig `fx_deconv`（宏平均中位） | 0.029151 | `metrics.csv` | `CD7499874B4A166E6B2737152D3B0C04…` |
| ΔSNR `wavelet_threshold`（宏平均中位） | 0.0422 dB | `metrics.csv` | `CD7499874B4A166E6B2737152D3B0C04…` |
| Lsig `wavelet_threshold`（宏平均中位） | 0.015129 | `metrics.csv` | `CD7499874B4A166E6B2737152D3B0C04…` |
| ΔSNR `ssa_decomposition`（宏平均中位） | 0.2101 dB | `metrics.csv` | `CD7499874B4A166E6B2737152D3B0C04…` |
| Lsig `ssa_decomposition`（宏平均中位） | 0.045928 | `metrics.csv` | `CD7499874B4A166E6B2737152D3B0C04…` |
| ΔSNR `svd_lowrank`（宏平均中位） | 0.9482 dB | `metrics.csv` | `CD7499874B4A166E6B2737152D3B0C04…` |
| Lsig `svd_lowrank`（宏平均中位） | 0.011218 | `metrics.csv` | `CD7499874B4A166E6B2737152D3B0C04…` |
| vs 最差单法 ΔSNR：中位差 / p_holm | +0.054257 / 0.134687 | `supplement_vs_worst.csv` | `FAB770718583E5A297AFB06538277FAE…` |
| vs 最差单法 Lsig：中位差 / p_holm | -0.017167 / 0.00019998 | `supplement_vs_worst.csv` | `FAB770718583E5A297AFB06538277FAE…` |
| 连续性可区分性：Q1/Q2/Q3 | +0.0503 / +0.0790 / +0.0838（阈值 0.1 / 0.05 / 0.1） | `continuity_verification.json` | `D618EDD892EBEDB28C32ABE4F519FCFB…` |
| 野外 FP1 融合 / 最佳单法（部分 U） | -2.2100 / +0.6953 | `u_scores_partial.csv` | `F2238A2AF5179B7E192FC2013BE76067…` |
| 野外 FP2 融合 / 最佳单法（部分 U） | -1.0791 / +0.6359 | `u_scores_partial.csv` | `F2238A2AF5179B7E192FC2013BE76067…` |
| 重归一化权重（振幅保持） | 0.4000 | `frozen-v2（原 30/75）` | `1D4AF0389EDE2328015C09943536BD6B…` |
| 重归一化权重（频谱残差） | 0.3333 | `frozen-v2（原 25/75）` | `1D4AF0389EDE2328015C09943536BD6B…` |
| 重归一化权重（盲评） | 0.2667 | `frozen-v2（原 20/75）` | `1D4AF0389EDE2328015C09943536BD6B…` |
| M1 全局（M2 次名对） | 0.575710 | `complementarity.csv` | `AE0FF75F58F2E88D27F1751EF554BABE…` |
| M2 分层：M1_N1 层（主配对） | 1.0000 | `complementarity.csv` | `AE0FF75F58F2E88D27F1751EF554BABE…` |
| M2 分层：model=M1 层 / noise=N3 层（主配对） | 0.0000 / 0.0000 | `complementarity.csv` | `AE0FF75F58F2E88D27F1751EF554BABE…` |
| M1 内积归一化（选中对） | ≈0.906 | `complementarity.csv` | `AE0FF75F58F2E88D27F1751EF554BABE…` |
| M2 零膨胀：8/10 对中位为 0 | 8/10 | `complementarity.csv` | `AE0FF75F58F2E88D27F1751EF554BABE…` |
| 连续性 Q1/Q2/Q3 判据阈值 | 0.1 / 0.05 / 0.1 | `continuity_verification.json` | `D618EDD892EBEDB28C32ABE4F519FCFB…` |
| 权重重归一化公式 | 30/25/20 ÷ 75 | `frozen-v2 item_11` | `1D4AF0389EDE2328015C09943536BD6B…` |
| γ 档（三档） | 0.4 / 0.5 / 0.6 | `fusion-rules.yaml` | `0C4D6BA3D2CA6C01E34D78A9550C4D0B…` |

## v2 增补来源（P5.1 · B 态修订）

> 以下行覆盖 **draft-v2 新增/改写句**中所用数字；v1 原有行全部保留不动。

| 数字/量 | 值 | 来源产物 | SHA256 |
| :--- | :--- | :--- | :--- |
| **三态判定结果** | **状态 B**（无伤害 / 未被最差单法击败 / 未超最优固定单法） | `P5.1-三态签收记录…-2026-09-29.md` | `58D627225AE10743DB173C4930720198…` |
| **判定人** | 用户（张涛） | 同上 | `58D627225AE10743DB173C4930720198…` |
| **判定时间** | 2026-09-28 12:52 | 同上 | `58D627225AE10743DB173C4930720198…` |
| **计划判定日** | 11-29（提前签收） | 同上 | `58D627225AE10743DB173C4930720198…` |
| 主频档 `f_main_hz` | 15.0 / 25.0 / 40.0 Hz | `frozen-v2.yaml` | `1D4AF0389EDE2328015C09943536BD6B…` |
| N2 视速度槽（L1/L2/L3） | 800 / 1500 / 3000 m/s | `frozen-v2.yaml` | `1D4AF0389EDE2328015C09943536BD6B…` |
| 鉴别子分权重（d / b / a） | 0.4 / 0.3 / 0.3 | `fusion-rules.yaml` | `0C4D6BA3D2CA6C01E34D78A9550C4D0B…` |
| d 子分视速度下限 `v_lo` | 100.0 m/s | `fusion-rules.yaml` | `0C4D6BA3D2CA6C01E34D78A9550C4D0B…` |
| M2 阈值倍数（Tukey IQR×1.5） | 1.5 | `complementarity/preregistration.md` | `3B552DB95499C2ABF97DD0A38A86A41E…` |
| 分层样本量 `n_obs` 范围 | 45–135 | `complementarity.csv` | `AE0FF75F58F2E88D27F1751EF554BABE…` |
| 度量值域（M1/M2/M3） | [0, 1] | `complementarity/preregistration.md` | `3B552DB95499C2ABF97DD0A38A86A41E…` |

> **说明**：判定元数据（状态 / 判定人 / 判定时间 / 计划日）来源为 P5.1 归档任务单原件，
> 路径 `docs/task-sheets/P5.1-三态签收记录与论文B态修订-2026-09-29.md`。

## v5 增补来源（P5.4 · WS2 新增表格与数值）

> 覆盖 draft-v5 相对 draft-v4 **新增的全部数值**；v4 及更早的来源行全部保留不动。

| 数字/量 | 值 | 来源产物 | SHA256 |
| :--- | :--- | :--- | :--- |
| v5 · 配置描述表（振幅比例与实测输入 SNR） | 0.30 / 0.60 / 1.00；10.46 / 4.44 / 0.00 dB；800 / 1500 / 3000 m/s | `configs/frozen-v2.yaml` + `docs/metrics-spec.md` | `FB63E2112C2984578BAB38EAA427F6D3…` |
| v5 · 参数表（登记默认值） | 800.0 / 5.0 / 80.0 / 4 / 1e-08 / db4 / 1.0 / 64 / 8 / 0.95 | `configs/methods_registry.yaml` | `5DA2959BBE4C2C7BFB7667EF3E45A4AB…` |
| v5 · 配对清单表（10 对 M1/M2 全局中位） | 0.741185 / 0.093807 / 0.575710 / 0.500000 / 0.200000 等 | `results/complementarity10/complementarity10.csv` | `507DEEBE81A36AD2EEF37EA2DBAEEED0…` |
| v5 · 配对清单表（10 对融合 ΔSNR 中位） | 4.1515 / 0.0588 / 2.5295 等 | `results/fusion10/metrics.csv` | `E8147D0D4702F063D6DE21B20DEF6149…` |
| v5 · 秩相关表（5 定义 × 4 度量） | +0.8303 / −0.3114 / +0.6727 / −0.0779 等 | `results/fusion10/stats/gain_definition_sensitivity.csv` | `812FBB051725E57D3B5807C5DF92426A…` |
| v5 · CNA 与事件级表 | 14.6916 / 2.0804 / 6.7747 / 0.1101 / 2.8370 等 | `results/metrics.csv` + `results/fusion/metrics.csv` | `CD7499874B4A166E6B2737152D3B0C04…` |
| v5 · 主配对池化阈值 | 0.0394653 | `results/complementarity10/run_manifest.json` | `080D2A2156F94B9B0C57740D05B24512…` |
| v5 · 成员补表（单法 ΔSNR/Lsig） | 0.0000 / 0.0422 / 0.029151 / 0.015129 / 0.011218 | `results/metrics.csv` | `CD7499874B4A166E6B2737152D3B0C04…` |

## v6 增补来源（P5.5 · 新分析）

> 覆盖 draft-v6 相对 draft-v5 新增的数值；此前来源行全部保留不动。

| 数字/量 | 值 | 来源产物 | SHA256 |
| :--- | :--- | :--- | :--- |
| v6 · 分工表（方法 × 噪声类型中位） | 0.8528 / 5.5231 / 2.4351 / 3.3458 / 0.8715；-0.1709 / -0.1028 / -0.0000 / 0.3020 / 4.4591；12.4354 / -0.0393 / 0.0422 / -0.0323 / 0.7927 | `results/metrics.csv` | `CD7499874B4A166E6B2737152D3B0C04…` |
| v6 · 消融对照表（等权 / 纯 C² / 完整） | 4.1465 / 4.1465 / 4.1515 / 0.0050 / 0.0252 等 | `results/fusion_ablation/metrics.csv` + `results/fusion10/metrics.csv` | `1BDE916F4FF0C73B6B254F683E083BBB…` |
| v6 · 种子外验证表 | 5.5231→5.5730 / 4.4591→2.0195 / 12.4354→12.1630；量级比 1.009 / 0.453 / 0.978 | `results/validation/metrics.csv` + `results/validation/validation_manifest.json` | `37B7042B296481C740621B51C6E4A5BF…` |
| v6 · 样本外验证判据与规则 | N1→fx_deconv / N2→svd_lowrank / N3→fk_filter；判据 1 组内第一、判据 2 量级≥0.5× | `results/validation/preregistration.md` | `2C593C40286A544E7F4F01A82009275B…` |
| v6 · 附录 B 各提交哈希 | afffc32 / ff60ac5 / 866989c / 37590f9 | git 历史（可 `git show <hash>` 核验） | `37590F908D25EADCD468FDD3546E9188…` |
### v6 · 野外重跑（A1）

| 数字/量 | 值 | 来源产物 | SHA256 |
| :--- | :--- | :--- | :--- |
| v6 · 野外三配对原始指标表 | -4.5336 / 0.19939 / 1.2099 / 0.6974 / +2.0835 / 0.71220 / 2.0143 / 0.2992 / -6.0569 / 0.44160 / 2.5260 / 0.2013 / -3.5899 / 0.13804 / -5.3283 / 0.13587 / -5.4667 / 0.47916 等 | `results/field2/field_pair_metrics.csv` | `E5882B408223A027E43A1FC2361DE869…` |
