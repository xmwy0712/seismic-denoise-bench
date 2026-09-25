# 竞争工作清单（P1.4）

> **协议要求**：对每篇「直接竞争工作」给出重叠点 / 差异点 / 新颖性收窄建议；**禁止隐瞒重叠**。

## 1. 滚雪球内的直接竞争工作

**结论：0 篇。**

逐轮统计（停止判据：连续两轮无新直接竞争工作）：

| 轮 | 种子数 | 新增题录 | 其中相关 | 新直接竞争 |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 32 | 143 | 40 | 0 |
| 2 | 16 | 229 | 91 | 0 |

触发停止判据：轮 1、轮 2 均无新直接竞争工作 ⇒ 连续两轮满足 ⇒ 停止。

## 2. 假阴性核验（这一步不可省）

「0 篇」是强结论，须证明**不是判据过严导致的漏检**。放宽为「域内词 + ≥1 竞争信号」后，
滚雪球新增条目中命中者 **8 条**，逐条判定：

| DOI | 年份 | 题名（截断） | 判定 |
| :--- | :--- | :--- | :--- |
| `10.1190/1.9781560802082` | 1998 | Comparison of Seismic Inversion Methods on a Single Real Data Set | **非竞争**：对比对象是**反演**方法，非去噪 |
| `10.1111/j.1365-246x.2009.04159.x` | 2009 | Comparison of stress-associated coda attenuation and intrinsic attenuation … | **非竞争**：衰减机制测量，非去噪 |
| `10.1190/1.2752175` | 2007 | Vp/Vs ratio versus differential stress … A comparison between rock models … | **非竞争**：岩石物理 |
| `10.1016/j.jappgeo.2016.11.003` | 2016 | Comparison between deterministic and statistical wavelet estimation … | **非竞争**：子波估计 |
| `10.1111/1365-2478.12158` | 2014 | Review Paper: outlook on the future of seismic imaging, Part III: JMI | **非竞争**：成像综述 |
| `10.1016/j.jappgeo.2026.106502` | 2026 | Physics-coherence-constrained hybrid swin-conv-Transformer … | **非竞争**：单方法（`hybrid` 指网络结构） |
| `10.1109/tgrs.2019.2954949` | 2019 | Seismic Signal Enhancement and Noise Suppression Using Structure-Adaptive … | **非竞争**：单方法 |
| `10.1109/tgrs.2021.3086317` | 2021 | Low-Frequency Seismic Noise Reduction Based on Deep Complex Reaction–Diffusion … | **非竞争**：单方法（`fusion` 指模型内部） |

⇒ 放宽后仍**无直接竞争工作**；「0 篇」不是判据假阴性。

## 3. 全语料宽扫（域内词 + ≥2 竞争信号）

命中 42 条，**逐条核验后全部为假阳性**：绝大多数是**土木/结构抗震**领域的
「seismic」歧义词（建筑抗震分析对比、核电站基准评估等），与本项目无重叠。

| DOI | 年份 | 题名（截断） | 假阳性原因 |
| :--- | :--- | :--- | :--- |
| `10.2172/6402312` | 1980 | Best Estimate Method vs Evaluation Method: a comparison of two techniques in evaluating seismic | 地震（核）分析评估方法对比，非勘探去噪 |
| `10.1049/ip-f-1.1988.0045` | 1988 | Comparison of the seismic and ground probing radar methods in geological surveying | 地震与探地雷达勘探方法对比，非去噪对比 |
| `10.32920/ryerson.14648880.v1` | 2021 | Comparison of analysis techniques for the seismic evaluation of an 88-storey concrete building | 建筑抗震分析技术对比 |
| `10.32920/ryerson.14648880` | 2021 | Comparison of analysis techniques for the seismic evaluation of an 88-storey concrete building | （同上，重复 DOI 变体） |
| `10.1002/essoar.10512321.2` | 2022 | Quantitative evaluation of the lunar seismic scattering and comparison between the Earth, Mars, | 月震散射定量评估（预印本） |
| `10.1002/essoar.10512321.1` | 2022 | Quantitative evaluation of the lunar seismic scattering and comparison between the Earth, Mars, | （同上，预印本 v1） |
| `10.1029/2022je007558` | 2022 | Quantitative Evaluation of the Lunar Seismic Scattering and Comparison Between the Earth, Mars, | 月震散射定量评估，非去噪 |
| `10.21203/rs.3.rs-3824369/v1` | 2024 | Evaluation and Comparison of the Seismic Performance of Modern Concentrically Braces in the Nea | 建筑支撑抗震性能对比（预印本） |
| `10.1109/icassp.1977.1170156` |  | Comparison of seismic features extracted by digital signal processing techniques | 数字信号处理地震特征对比，非去噪 |
| `10.1190/1.9781560802082` | 1998 | Comparison of Seismic Inversion Methods on a Single Real Data Set | 域内词为歧义（土木/结构抗震）或为单方法论文 |
| `10.1115/1.1638388` | 2004 | Insights Gleaned From NRC-BNL Benchmark Evaluation of Seismic Analysis Methods for Non-Classica | 核电站抗震分析方法基准评估 |
| `10.1016/j.nucengdes.2003.06.019` | 2004 | A NRC-BNL benchmark evaluation of seismic analysis methods for non-classically damped coupled s | 同上（期刊版） |
| `10.4028/www.scientific.net/amm.204-208.2387` | 2012 | The Computational Analysis and Evaluation on the Seismic Response of Base Isolated Benchmark Bu | 隔震建筑抗震响应基准 |
| `10.1115/pvp2015-45721` | 2015 | Benchmark of Elastic Plastic Seismic Response Analysis and Fatigue Evaluation for Piping | 管道弹塑性抗震响应基准与疲劳评估 |
| `10.1190/ice2016-6260208.1` | 2016 | Weighted stacking of seismic AVO data using hybrid AB semblance and local similarity | AVO 加权叠加（混合 AB 似然与局部相似度），**单方法** |
| `10.1088/1742-2132/13/2/152` | 2016 | Weighted stacking of seismic AVO data using hybrid AB semblance and local similarity | 域内词为歧义（土木/结构抗震）或为单方法论文 |
| `10.1016/j.jappgeo.2016.11.003` | 2016 | Comparison between deterministic and statistical wavelet estimation methods through predictive  | 域内词为歧义（土木/结构抗震）或为单方法论文 |
| `10.1109/LGRS.2017.2695649` | 2017 | An Anisotropic Diffusion-Based Dynamic Combined Energy Model for Seismic Denoising | 域内词为歧义（土木/结构抗震）或为单方法论文 |
| `10.3997/2214-4609.201800239` | 2018 | Quantitative Quality Control: a Tool for Seismic Data Processing Monitoring and Comparison | 域内词为歧义（土木/结构抗震）或为单方法论文 |
| `10.3997/2214-4609.201801395` | 2018 | A Quantitative Comparison of Two Convolutional Neural Network Architectures - Seismic Data Inte | 域内词为歧义（土木/结构抗震）或为单方法论文 |

## 4. 最接近的已有工作与本项目边界（诚实披露）

| 最接近者 | 重叠点 | 差异点 |
| :--- | :--- | :--- |
| 单方法去噪论文（稀疏/低秩/DL/多尺度，见 `mechanism-table.md`） | 都以地震去噪为目标、都在合成或野外面板上评估 | 本项目**不提出新去噪方法**；目标是**同一数据上多方法的可比对照 + 互补性度量 + 保守融合边界** |
| 传统多方法对比论文（如 `10.1190/1.9781560802082` 类反演对比） | 同为「多方法对比」体裁 | 对比对象不同（反演 vs 去噪）；且本项目引入**正交化后的互补性判据**与**融合保守性上界** |
| 去噪综述 | 覆盖同样的方法族 | 综述不给**统一基准下的可复现实验**与**融合可行域**结论 |

**新颖性收窄建议（如实）**：
1. **不得**主张「首次对比多种地震去噪方法」——该体裁已存在（虽非同一数据/同一判据）。
2. 可主张的是：**同一野外数据集 + 预注册判据 + 正交化互补性度量 + 融合保守性上界**这一组合。
3. 风险：**检索有界**（见 `search-log.md` 覆盖限制），**不构成查全证明**；
   论文局限小节须承接，且**不得**写「未发现同类工作」这类无界断言，只能写「在本检索边界内未发现」。
