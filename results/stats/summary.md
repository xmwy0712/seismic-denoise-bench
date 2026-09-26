# P2.3 · 统计分析结果摘要

> **本文件只做描述性汇报。** 按预注册件第 8 条，**不得**下"哪个方法最好"这类**结论性判断**——
> 方法优劣的判定属 **P3 互补性分析与三态锁定**。本文件全部数值均**可机械复算**：
> 脚本 `execution/stats.py` + 输入 `results/metrics.csv` + 预注册参数。

## 0. 可复算性凭据（三方哈希）

| 项 | SHA256 |
| :--- | :--- |
| 输入 `results/metrics.csv` | `CD7499874B4A166E6B2737152D3B0C045232911D5D388DD46262406B11443933` |
| 预注册件 `results/stats/preregistration.md` | `174A25499ADB1525229C1F27BEEF4C221568EBA552ADF6B15B8831948FD682FD` |
| 统计脚本 `execution/stats.py` | `586D82C39B0A537B6CE325CCA2052CCA63EA5048CE0B495D7D2C95778113C5C5` |

- 置换 B = **10,000**（种子 **20261001**）；自助 B = **10,000**（种子 **20261002**）；α = **0.05**
- 配对 **10** 对 × 指标 **5** × 分层键 **18** = pairwise.csv **900** 行（公式核对一致）
- 统计运行耗时 **25.023 s**

## 1. 宏平均（逐方法，270 观测）

> **只读描述**：数值与区间如实呈现；**不含排序性判断**。

### 1.1 ΔSNR (dB, 越高越好)

| 方法 | n | 中位 | 中位 95% CI | 均值 | 均值 95% CI |
| :--- | ---: | ---: | :--- | ---: | :--- |
| `fk_filter` | 270 | 0.932 | [0.8762, 0.9714] | 3.99 | [3.336, 4.672] |
| `fx_deconv` | 270 | 1.917e-10 | [-1.132e-05, 0.01559] | 1.223 | [0.8648, 1.582] |
| `ssa_decomposition` | 270 | 0.2101 | [0.03947, 0.5905] | 0.6145 | [0.3229, 0.8902] |
| `svd_lowrank` | 270 | 0.9482 | [0.874, 2.451] | 4.487 | [3.59, 5.484] |
| `wavelet_threshold` | 270 | 0.04222 | [0.03877, 0.04327] | 0.8174 | [0.6856, 0.9519] |

### 1.2 Lsig (越低越好)

| 方法 | n | 中位 | 中位 95% CI | 均值 | 均值 95% CI |
| :--- | ---: | ---: | :--- | ---: | :--- |
| `fk_filter` | 270 | 0.009706 | [0.007993, 0.01115] | 0.02959 | [0.02359, 0.03626] |
| `fx_deconv` | 270 | 0.02915 | [0.02435, 0.03345] | 0.0503 | [0.04286, 0.05814] |
| `ssa_decomposition` | 270 | 0.04593 | [0.04013, 0.05386] | 0.08122 | [0.06952, 0.09337] |
| `svd_lowrank` | 270 | 0.01122 | [0.008907, 0.01424] | 0.0491 | [0.04022, 0.05856] |
| `wavelet_threshold` | 270 | 0.01513 | [0.01202, 0.01843] | 0.04439 | [0.03634, 0.05306] |

### 1.3 CNA (dB, 越高越好)

| 方法 | n | 中位 | 中位 95% CI | 均值 | 均值 95% CI |
| :--- | ---: | ---: | :--- | ---: | :--- |
| `fk_filter` | 180 | 14.69 | [4.029, 26.06] | 14.88 | [12.89, 16.93] |
| `fx_deconv` | 180 | 0.05713 | [0.04512, 0.07899] | 0.1407 | [0.1114, 0.1737] |
| `ssa_decomposition` | 180 | 2.08 | [1.741, 2.344] | 2.591 | [2.186, 3.073] |
| `svd_lowrank` | 180 | 6.775 | [3.328, 7.357] | 13.82 | [11.09, 16.75] |
| `wavelet_threshold` | 180 | 0.01818 | [1.35e-14, 0.03662] | 0.02062 | [0.01759, 0.02369] |

### 1.4 事件到时中位 (ms, 越低越好)

| 方法 | n | 中位 | 中位 95% CI | 均值 | 均值 95% CI |
| :--- | ---: | ---: | :--- | ---: | :--- |
| `fk_filter` | 270 | 0 | [0, 0] | 1.107 | [0.9074, 1.326] |
| `fx_deconv` | 270 | 0 | [0, 0] | 0.5481 | [0.3074, 0.9074] |
| `ssa_decomposition` | 270 | 2 | [2, 2] | 3.111 | [2.552, 3.73] |
| `svd_lowrank` | 270 | 0 | [0, 0] | 0.4 | [0.1704, 0.7705] |
| `wavelet_threshold` | 270 | 0 | [0, 0] | 0.6222 | [0.3852, 0.9889] |

### 1.5 事件能量中位 (越低越好)

| 方法 | n | 中位 | 中位 95% CI | 均值 | 均值 95% CI |
| :--- | ---: | ---: | :--- | ---: | :--- |
| `fk_filter` | 270 | 0.0108 | [0.00825, 0.01335] | 0.03525 | [0.02837, 0.04233] |
| `fx_deconv` | 270 | 0.039 | [0.03555, 0.04883] | 0.07305 | [0.06317, 0.08284] |
| `ssa_decomposition` | 270 | 0.0714 | [0.0555, 0.08164] | 0.1158 | [0.1011, 0.131] |
| `svd_lowrank` | 270 | 0.0152 | [0.01063, 0.02586] | 0.06111 | [0.05053, 0.07223] |
| `wavelet_threshold` | 270 | 0.01739 | [0.01205, 0.02165] | 0.04895 | [0.04011, 0.05815] |

## 2. 配对置换检验（Holm 校正后）—— 分层概览

> 显著性判据：**p_holm < 0.05**。下表为**逐分层键**的显著对数，仅作**计数描述**，
> **不对"哪个方法更好"作任何排序或推荐**。

| 指标 | 分层类型 | 分层键 | 对数(有效) | 显著对数(α=0.05) |
| :--- | :--- | :--- | ---: | ---: |
| ΔSNR | global | `global` | 10 | 8 |
| ΔSNR | model | `M1` | 10 | 10 |
| ΔSNR | model | `M2` | 10 | 10 |
| ΔSNR | noise | `N1` | 10 | 9 |
| ΔSNR | noise | `N2` | 10 | 6 |
| ΔSNR | noise | `N3` | 10 | 9 |
| ΔSNR | level | `L1` | 10 | 7 |
| ΔSNR | level | `L2` | 10 | 6 |
| ΔSNR | level | `L3` | 10 | 7 |
| ΔSNR | f_main | `15Hz` | 10 | 6 |
| ΔSNR | f_main | `25Hz` | 10 | 7 |
| ΔSNR | f_main | `40Hz` | 10 | 8 |
| ΔSNR | model_x_noise | `M1_N1` | 10 | 8 |
| ΔSNR | model_x_noise | `M1_N2` | 10 | 8 |
| ΔSNR | model_x_noise | `M1_N3` | 10 | 10 |
| ΔSNR | model_x_noise | `M2_N1` | 10 | 9 |
| ΔSNR | model_x_noise | `M2_N2` | 10 | 10 |
| ΔSNR | model_x_noise | `M2_N3` | 10 | 10 |
| Lsig | global | `global` | 10 | 9 |
| Lsig | model | `M1` | 10 | 8 |
| Lsig | model | `M2` | 10 | 7 |
| Lsig | noise | `N1` | 10 | 6 |
| Lsig | noise | `N2` | 10 | 9 |
| Lsig | noise | `N3` | 10 | 10 |
| Lsig | level | `L1` | 10 | 9 |
| Lsig | level | `L2` | 10 | 7 |
| Lsig | level | `L3` | 10 | 8 |
| Lsig | f_main | `15Hz` | 10 | 0 |
| Lsig | f_main | `25Hz` | 10 | 7 |
| Lsig | f_main | `40Hz` | 10 | 8 |
| Lsig | model_x_noise | `M1_N1` | 10 | 7 |
| Lsig | model_x_noise | `M1_N2` | 10 | 10 |
| Lsig | model_x_noise | `M1_N3` | 10 | 10 |
| Lsig | model_x_noise | `M2_N1` | 10 | 8 |
| Lsig | model_x_noise | `M2_N2` | 10 | 8 |
| Lsig | model_x_noise | `M2_N3` | 10 | 9 |
| CNA | global | `global` | 10 | 9 |
| CNA | model | `M1` | 10 | 9 |
| CNA | model | `M2` | 10 | 10 |
| CNA | noise | `N1` | 0 | 0 |
| CNA | noise | `N2` | 10 | 10 |
| CNA | noise | `N3` | 10 | 10 |
| CNA | level | `L1` | 10 | 9 |
| CNA | level | `L2` | 10 | 9 |
| CNA | level | `L3` | 10 | 9 |
| CNA | f_main | `15Hz` | 10 | 9 |
| CNA | f_main | `25Hz` | 10 | 9 |
| CNA | f_main | `40Hz` | 10 | 9 |
| CNA | model_x_noise | `M1_N1` | 0 | 0 |
| CNA | model_x_noise | `M1_N2` | 10 | 9 |
| CNA | model_x_noise | `M1_N3` | 10 | 9 |
| CNA | model_x_noise | `M2_N1` | 0 | 0 |
| CNA | model_x_noise | `M2_N2` | 10 | 10 |
| CNA | model_x_noise | `M2_N3` | 10 | 10 |
| event_timing_median | global | `global` | 10 | 8 |
| event_timing_median | model | `M1` | 10 | 4 |
| event_timing_median | model | `M2` | 10 | 7 |
| event_timing_median | noise | `N1` | 10 | 3 |
| event_timing_median | noise | `N2` | 10 | 7 |
| event_timing_median | noise | `N3` | 10 | 7 |
| event_timing_median | level | `L1` | 10 | 6 |
| event_timing_median | level | `L2` | 10 | 9 |
| event_timing_median | level | `L3` | 10 | 5 |
| event_timing_median | f_main | `15Hz` | 10 | 4 |
| event_timing_median | f_main | `25Hz` | 10 | 5 |
| event_timing_median | f_main | `40Hz` | 10 | 8 |
| event_timing_median | model_x_noise | `M1_N1` | 10 | 1 |
| event_timing_median | model_x_noise | `M1_N2` | 10 | 7 |
| event_timing_median | model_x_noise | `M1_N3` | 10 | 7 |
| event_timing_median | model_x_noise | `M2_N1` | 10 | 2 |
| event_timing_median | model_x_noise | `M2_N2` | 10 | 6 |
| event_timing_median | model_x_noise | `M2_N3` | 10 | 6 |
| event_energy_median | global | `global` | 10 | 10 |
| event_energy_median | model | `M1` | 10 | 9 |
| event_energy_median | model | `M2` | 10 | 8 |
| event_energy_median | noise | `N1` | 10 | 5 |
| event_energy_median | noise | `N2` | 10 | 9 |
| event_energy_median | noise | `N3` | 10 | 9 |
| event_energy_median | level | `L1` | 10 | 9 |
| event_energy_median | level | `L2` | 10 | 9 |
| event_energy_median | level | `L3` | 10 | 5 |
| event_energy_median | f_main | `15Hz` | 10 | 4 |
| event_energy_median | f_main | `25Hz` | 10 | 5 |
| event_energy_median | f_main | `40Hz` | 10 | 9 |
| event_energy_median | model_x_noise | `M1_N1` | 10 | 7 |
| event_energy_median | model_x_noise | `M1_N2` | 10 | 8 |
| event_energy_median | model_x_noise | `M1_N3` | 10 | 10 |
| event_energy_median | model_x_noise | `M2_N1` | 10 | 8 |
| event_energy_median | model_x_noise | `M2_N2` | 10 | 9 |
| event_energy_median | model_x_noise | `M2_N3` | 10 | 9 |

**合计**：有效检验 **870** 个，Holm 后显著 **672** 个（占 77.2%）。

### 2.1 N1 层 CNA = N/A（与冻结件一致）

- CNA 共 **180** 行；其中 **N1 层 10 行全为 `NA`**
  （N1 为带限随机噪声，**无相干噪声分量** ⇒ CNA 不适用；与冻结件 item_08/item_14 一致）。
- CNA **非空**行 = **150**（N2 / N3 各分层）。

## 3. 图

| 图 | 文件 |
| :--- | :--- |
| 宏平均 ± 分层自助 95% CI | `fig_macro_average.png` |
| 分层 × 方法对 热图（Holm 后 −log10 p） | `fig_strata_heatmap.png` |

## 4. 报告纪律声明（**预注册承诺**）

1. 本摘要**只描述**，**不含**"谁最好"的结论性判断（判断属 P3）；
2. **18 个分层键全部进表**，含不显著与反向结果，**未选择性报告**；
3. 统计参数**先于运行落盘**于 `preregistration.md`，运行后**未作任何调整**；
4. 输入 `results/metrics.csv` **只读**，未修改；
5. 本单**未实现融合**（属 P3）。

## 5. 数据边界（如实）

- 本统计基于**合成数据**（M1/M2 × N1/N2/N3 × L1/L2/L3 × 15/25/40 Hz × 5 种子）；
- **跨域泛化未测**（DL 槽位按裁定 J 留空，见 `configs/methods_registry.yaml`）；
- 分层自助 CI 为**分层内**重抽，**不做跨层推断**；
- 多重校正族定义 = **每个「指标 × 分层键」内的 10 个方法对**；
- 本文件**不构成**任何野外适用性结论（野外评估属 P4）。

