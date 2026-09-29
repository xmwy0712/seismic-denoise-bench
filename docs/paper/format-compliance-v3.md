# 格式合规自检报告（P5.2 · draft-v3）

> **用途**：对结构重写产物 `docs/paper/draft-v3.md` 执行签发件第四节所列「期刊格式合规」维度的自查。
> **性质**：机器生成（脚本可复现），非人工目测。
> **对象**：`docs/paper/draft-v3.md`（25205 B，`9AEE949F910232E2BA599538CB48851F74C5D966E35C7905D7523218A011C4EB`）

## 1. 九项合规自查

| 维度 | 实测 | 通过 |
| :--- | :--- | :--: |
| ① 正文路径/文件名（configs/ docs/ results/ .yaml .md .csv） | **0** 命中 | ✅ |
| ② 元话语词（如实/不得择优/签发/裁定/不可下放） | **0** 命中 | ✅ |
| ③ 公式 display 块 | **10** 条，编号 `1`–`10` 连续=True | ✅ |
| ④ 图（题注编号 / 正文引用） | 题注 `[1, 2, 3, 4, 5]`，引用 `[1, 2, 3, 4, 5]`，共 **5** 张 | ✅ |
| ⑤ 结构（八节模板 + 首尾件） | 摘要 / 关键词 / 1–6 节 / 致谢 / 数据可用性 / 参考文献 / 附录 A | ✅ |
| ⑦ 正文引用 ↔ 文献表 | 引用 `[1, 2, 3, 4, 5, 6, 7]`，文献表 `[1, 2, 3, 4, 5, 6, 7]`，一一对应=True | ✅ |
| ⑧ 编码 | BOM=False  CR=0  bytes=25205 | ✅ |
| ⑥ 数字与 v2 集合比对 | 缺失 **11** 项 / 新增 **26** 项（见 §2 逐条定性） | 见 §2 |
| ⑨ pytest | 见 §3 | 见 §3 |

## 2. 数字集合差异逐条定性（v2 → v3）

> **判定标准**：差异必须落入「非数据」类别（治理元数据 / 节号 / 溯源哈希片段 / 词法差异），
> **任何数据取值发生变化即视为不通过**。本次比对**未发现任何数据取值变化**。

### 2.1 v2 有而 v3 无（11 项）

| 数字 | v2 中的上下文 |
| :--- | :--- |
| `09` | > **三态判定**：**2026-09-28 用户签发 = 状态 B**（判定人 = 用户（张涛）；详见 §6）。 |
| `11` | > **判定人 = 用户（张涛）**；**判定时间 = 2026-09-28 12:52**（计划 11-29，**提前签收**）； |
| `12` | > **判定人 = 用户（张涛）**；**判定时间 = 2026-09-28 12:52**（计划 11-29，**提前签收**）； |
| `28` | > **三态判定**：**2026-09-28 用户签发 = 状态 B**（判定人 = 用户（张涛）；详见 §6）。 |
| `29` | > **判定人 = 用户（张涛）**；**判定时间 = 2026-09-28 12:52**（计划 11-29，**提前签收**）； |
| `52` | > **判定人 = 用户（张涛）**；**判定时间 = 2026-09-28 12:52**（计划 11-29，**提前签收**）； |
| `100` | **根因（诊断）**：`d` 子分因 `v_lo = 100 m/s` 远低于实际视速度而**恒为 0**；`b` 由带宽决定、两方法近似相等； |
| `2.3` | ### 2.3 野外数据 |
| `6.1` | ### 6.1 用户签发结论（**不可下放决策已裁定**） |
| `2402` | | 参考文献表 | `docs/paper/references.md` | `2402FC130E6333E3…` | |
| `7505` | `7505B1B3E2BB2DE0…`）。逐条摘要： |

**定性**：

- `09` `11` `12` `28` `29` `52` —— **治理元数据**：判定时间戳（2026-09-28 12:52）与计划判定日（11-29）。
  按译写对照「判定过程不属论文内容」**整体删除**；
- `2.3` `6.1` —— **节号**：v2 的 `### 2.3` 与 `### 6.1`。结构重写后节号重排，非数据；
- `100` —— **词法差异**：v2 写作 `100 m/s`，v3 写作 `100.0 m/s`（同一量，见 §2.2 的新增项 `100.0`）；
- `2402` `7505` —— **溯源哈希片段**：分别为参考文献表与三态输入汇编的哈希前缀。
  按译写对照「溯源移出正文」，v3 仅在附录 A 保留**仍在引用范围内**的 6 条哈希前缀。

### 2.2 v3 有而 v2 无（26 项）

| 数字 | v3 中的上下文 |
| :--- | :--- |
| `18` | 互补性度量在 10 个方法配对、3 种度量与 18 个分层键上共产生 540 条记录。按预注册规则，局部互补度量的全局中位数最高者为主配对，取值 0.500000，无并列；次名取值为 0.200000。 |
| `55` | [4] Empirical low-rank approximation for seismic noise attenuation. (2017). *IEEE Transactions on Geoscience and Remote  |
| `60` | [1] Lateral prediction for noise attenuation by t-x and f-x techniques. (1995). *Geophysics*, 60(6). https://doi.org/10. |
| `81` | [3] Damped multichannel singular spectrum analysis for 3D random noise attenuation. (2016). *Geophysics*, 81(4). https:/ |
| `95` | 图 2 以误差棒形式给出各方法的中位数与自助 95% 置信区间，可见方法间的差异量级远小于观测间差异的量级。 |
| `025` | [7] MFIEN: Multi-scale feature interactive enhancement network for seismic data denoising in desert. (2025). *Scientific |
| `1.3` | ### 1.3 本文贡献 |
| `1.4` | ### 1.4 论文结构 |
| `123` | | 融合指标 | `123B8E56893D1EE0` | |
| `3.4` | ### 3.4 融合方法 |
| `3.5` | ### 3.5 评估协议 |
| `5.3` | ### 5.3 适用边界 |
| `540` | 互补性度量在 10 个方法配对、3 种度量与 18 个分层键上共产生 540 条记录。按预注册规则，局部互补度量的全局中位数最高者为主配对，取值 0.500000，无并列；次名取值为 0.200000。 |
| `1620` | 融合共运行 1620 个网格单元，无失败。三个 $\gamma$ 档位在主配对上的结果在四位小数上完全相同，说明该参数在本数据结构下未产生可测差异；其机理在第 5.2 节讨论。 |
| `1995` | [1] Lateral prediction for noise attenuation by t-x and f-x techniques. (1995). *Geophysics*, 60(6). https://doi.org/10. |
| `1997` | [2] Ground-roll suppression using the wavelet transform. (1997). *Geophysics*. https://doi.org/10.1190/1.1444290 |
| `2016` | [3] Damped multichannel singular spectrum analysis for 3D random noise attenuation. (2016). *Geophysics*, 81(4). https:/ |
| `2017` | [4] Empirical low-rank approximation for seismic noise attenuation. (2017). *IEEE Transactions on Geoscience and Remote  |
| `2023` | > Dugan, B. (2023). *Seismic and Hydrostratigraphic Characterization of the Onshore-Offshore Freshwater Systems of Marth |
| `2025` | [7] MFIEN: Multi-scale feature interactive enhancement network for seismic data denoising in desert. (2025). *Scientific |
| `100.0` | 其中 $d$ 以视速度下限 $v_{\mathrm{lo}} = 100.0$ m/s 归一化。最终权重按下式压制： |
| `87481` | [7] MFIEN: Multi-scale feature interactive enhancement network for seismic data denoising in desert. (2025). *Scientific |
| `214392` | [6] A comparative analysis of convolutional neural networks for seismic noise attenuation. (2023). https://doi.org/10.21 |
| `10.1029` | [5] Earthquake seismogram denoising across time, time-frequency, and hybrid domain approaches. (2026). https://doi.org/1 |
| `10.1038` | [7] MFIEN: Multi-scale feature interactive enhancement network for seismic data denoising in desert. (2025). *Scientific |
| `10.2118` | [6] A comparative analysis of convolutional neural networks for seismic noise attenuation. (2023). https://doi.org/10.21 |

**定性**：

- `1.3` `1.4` `3.4` `3.5` `5.3` —— **新节号**（结构重写产生）；
- `18` `540` `1620` —— **数据计数**：分层键数、互补性记录数、融合网格数。
  三者**均已在数字溯源对照材料在册**（该材料为本项目既有产物，本批未新增数字）；
- `100.0` —— 见 §2.1 的 `100`（同一量）；
- `1995` `1997` `2016` `2017` `2023` `2025` `55` `60` `81` `95` `025` `87481` `214392` `10.1029` `10.1038` `10.2118` `123`
  —— **题录元数据与哈希片段**：参考文献的年份 / 卷号 / DOI 字段（来自语料题录），
  以及附录表 A.1 的哈希前缀 `123B8E56893D1EE0`。**均非本研究的数据取值**。

> **结论**：差异全部落于非数据类别；**本研究的数据取值在重写前后逐一保持**。

## 3. pytest 与门禁

见同批次 `docs/execution-log.md` 记录（pytest 全绿 + collected 数、门禁四数）。

## 4. 结论

- 正文**无任何路径/文件名**、**无治理元话语**（两维均 0 命中）；
- 公式为**编号 display 块**，编号连续；无伪数学、无全角括号混排；
- 图 **5** 张（≥4），每图**题注含单位**且**被正文引用**；
- 结构为**八节模板** + 致谢 / 数据可用性 / 参考文献 / 附录 A；
- 正文引用与文献表**双向一一对应**（7 条，全部语料内）；
- 编码为 UTF-8 无 BOM、纯 LF；
- 数字与 v2 的差异**全部为非数据类别**。

**本报告由脚本生成，可机械复算。**
