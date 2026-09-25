# 野外数据说明（P1.3）

> **数据来源**：Zenodo 公开数据集，**CC BY 4.0**。
> 本文件承载 CC BY 4.0 要求的**署名文本**与数据去向说明；许可登记见
> [`license-register.csv`](license-register.csv) 第 3.3 节。

---

## 1. 署名（CC BY 4.0 要求，使用时须保留）

> Dugan, B. (2023). *Seismic and Hydrostratigraphic Characterization of the
> Onshore-Offshore Freshwater Systems of Martha's Vineyard and Nantucket,
> Massachusetts, USA: Field Survey Report* [Data set]. Zenodo.
> https://doi.org/10.5281/zenodo.10407771 — licensed under **CC BY 4.0**.

- **DOI**：`10.5281/zenodo.10407771`
- **许可 id**：`cc-by-4.0`；许可原文：https://creativecommons.org/licenses/by/4.0/
- **创作人**：Dugan, Brandon（Colorado School of Mines；ORCID `0000-0002-2555-6430`）
- **发布年**：2023

## 2. 本仓库内的数据副本（不入 git）

| 项 | 值 |
| :--- | :--- |
| 目录 | `data/field/zenodo-mv/` |
| 文件 | `mv1001shots_subset8000.sgy`（Martha's Vineyard 测区）<br>`nan3001shots_subset8000.sgy`（Nantucket 测区） |
| 采集方式 | Zenodo 开放 API + HTTP Range **按道截取**（前 8000 条完整道） |
| 每文件字节 | 161,923,600 |
| 每文件 SHA256 | MV：`1CDD7E27D0D79A99178DE2E5DE392367E48050183CF40623AEC7E221A6ACB9E0`<br>NAN：`15DFA5DBC06850FC5631335D16B27C49D5774E9F98028FA229523B9C50714C66` |
| 几何 | 8000 道 × 5000 采样；`dt = 1 ms`；fmt=1（IBM 32-bit float）；单道 20240 B |
| 是否入库 | **否**（`data/**` 由 `.gitignore` 忽略；本仓库仅登记清单与校验值） |
| 再分发 | 依 CC BY 4.0 可再分发，**须保留上述署名** |

## 3. P1.3 选定的 3 个面板

| 面板 | 测区 | 道范围 | 时间窗 (ms) | 相干能量比 | 横向相干 | 事件数 | 倾角中位 |
| :--- | :--- | :--- | :--- | ---: | ---: | ---: | ---: |
| FP1 | NAN | [2000, 4000) | [0, 1000] | 0.3777 | 0.1309 | 1 | 82.17° |
| FP2 | MV | [4000, 6000) | [1000, 2000] | 0.3562 | 0.1787 | 3 | 84.98° |
| FP3 | MV | [2000, 4000) | [1000, 2000] | 0.3544 | 0.2058 | 0 | 84.91° |

**覆盖**：Martha's Vineyard **2** 个 + Nantucket **1** 个（满足"覆盖两个测区"）。
**选取规则**：严格按**事先冻结**的判据排序（相干能量比降序 → 横向相干降序 → 位置 tie-break），
**非事后挑选**；详见 [`../configs/field_panels_draft.yaml`](../configs/field_panels_draft.yaml)
的 `preregistered_criteria` 与 `selection_outcome`。

预览图（原始数据，**未做任何滤波**）：

- `docs/figures/p1_field_panel_1.png`
- `docs/figures/p1_field_panel_2.png`
- `docs/figures/p1_field_panel_3.png`

## 4. 时序约束合规声明（协议硬规则）

本阶段（P1.3）在选定 3 个面板的**全过程**中：

- **未运行任何去噪方法**——未执行滤波、f-k、反褶积、分解、低秩、深度学习等**任何方法**；
- **未参考任何去噪/滤波结果**（本仓库内当时也不存在此类结果）；
- 面板选择、事件窗与倾角**仅由原始数据导出**。

**可核验依据**：

1. P1.3 三个脚本（判据冻结 / 测量 / 选定）的**全部 import 行**经机械扫描，
   不含 `bench.methods`、`bench.fusion` 或任何 `coherence` 相关模块；
2. 使用到的全部算子为**原始数据统计量**：逐道 RMS、2D FFT 幅度谱、
   相邻道零延迟互相关、Hilbert 解析包络、独立结构张量取向角；
3. `data/field/zenodo-mv/*.sgy` 的 SHA256 与 P0.6-Am3 采集记录**逐字节一致**
   （即本阶段**只读**，未写入数据文件）。

> **注**：Hilbert 包络与结构张量属**原始数据上的描述性分析**（用于生成事件窗与倾角），
> 不构成"去噪方法"，亦不产生任何被方法消费的中间产物。
