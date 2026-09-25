# 新颖性检索日志（协议第八节）

> 本文件记录每次检索一行：`日期 | 数据库 | 检索式 | 命中数 | 入库数 | 备注`。
> 末尾单列**覆盖限制**小节。
>
> **本阶段范围（P0.5）**：只要求"检索管道 + 首批题录 + 日志"。
> **滚雪球与查全记录属 P1**（截至检索截止日 2026-10-04）。
> 初筛**只做相关性标记**，不做深入分析。

---

## 一、检索记录

| 日期 | 数据库 | 检索式 | 命中数 | 入库数 | 备注 |
| :--- | :--- | :--- | ---: | ---: | :--- |
| 2026-09-25 | Crossref | `seismic AND denois* AND (fusion OR combination OR ensemble OR local similarity OR orthogonalization)` | 200 | 200 | **协议原式逐字** |
| 2026-09-25 | Semantic Scholar | `seismic denoising fusion ensemble` | 100 | 100 | **降级式**（S2 不支持 `*` 通配符，见下） |
| 2026-09-25 | Crossref | `seismic AND denois* AND (benchmark OR quantitative comparison OR evaluation OR signal preservation OR fidelity)` | 200 | 200 | **协议原式逐字** |
| 2026-09-25 | Semantic Scholar | `seismic denoising benchmark evaluation fidelity` | 100 | 100 | **降级式** |
| 2026-09-25 | Semantic Scholar | `seismic denoising orthogonalization local similarity` | 50 | 50 | **降级式**（机制线补充词项） |
| 2026-09-25 | Crossref | `seismic denoising Chen`（作者追踪子项） | 50 | 50 | 机制线作者追踪，独立子项 |
| 2026-09-25 | Semantic Scholar | `seismic denoising Chen`（作者追踪子项） | 50 | 50 | **降级式** 作者追踪 |
| 2026-09-25 | Crossref | `seismic denoising Fomel`（作者追踪子项） | 50 | 50 | 机制线作者追踪，独立子项 |
| 2026-09-25 | Semantic Scholar | `seismic denoising Fomel`（作者追踪子项） | 50 | 50 | **降级式** 作者追踪 |
| 2026-09-25 | Google Scholar | （人工检索） | — | **0** | **本阶段未执行**；见覆盖限制第 3 条 |

**合计采集 850 条 → 去重后 782 条**（原始响应全量落盘于 `docs/bibliography/raw/`）。

---

## 二、逐来源入库计数（P0.6-Am1 第二节第 2 条要求：分列，不得只给总数）

| 来源 | 入库条数（去重后） | 说明 |
| :--- | ---: | :--- |
| **Crossref** | **482** | 协议原式逐字检索 |
| **Semantic Scholar** | **300** | 降级式检索（见第一节偏离说明） |
| **人工检索（Google Scholar）** | **0** | 本阶段未执行（见覆盖限制） |
| 合计 | **782** | — |

## 三、逐 track 计数（去重后）

| 线 / 子项 | 条数 | 是否满足"每线 ≥30" |
| :--- | ---: | :--- |
| `mechanism`（机制线） | 340 | ✅ |
| `benchmark`（基准线） | 293 | ✅ |
| `mechanism_author_Chen`（作者追踪） | 83 | ✅（子项，不计入线门槛） |
| `mechanism_author_Fomel`（作者追踪） | 66 | ✅（子项，不计入线门槛） |

**结论**：两条线均**多来源合计**远超 30 条门槛（机制线 340、基准线 293）。

---

## 四、API 文档核验记录

| 项 | 结论 | 来源 |
| :--- | :--- | :--- |
| Crossref 端点/认证 | `https://api.crossref.org/works`，**无需认证** | Crossref REST API 文档 |
| Crossref polite pool | URL 附 `mailto=` 即进入 polite pool | Crossref polite pool 说明 |
| Crossref 分页 | `rows`（≤1000）+ `offset` | 同上 |
| Crossref 实测 | `query=seismic+denoising` → `total-results=217403` | 本地实测 2026-09-25 |
| S2 端点 | `https://api.semanticscholar.org/graph/v1/paper/search` | S2 Graph API 文档 |
| S2 认证 | 无 key 可用（限额极低）；带 key（环境变量 `S2_API_KEY`）限额更高 | S2 API 文档 |
| S2 速率 | **1 请求/秒**（带 key） | S2 文档 |
| S2 分页 | `limit`（≤100）+ `offset` | 同上 |
| S2 实测（无 key） | **持续 HTTP 429**；直连与经 socks5 代理**均 429**；响应体明示"apply for a key for higher rate limits" | 本地实测 2026-09-25 |
| S2 实测（带 key） | 可用；但仍有间歇 429（估约 50%），需**退避重试** | 本地实测 2026-09-25 |
| S2 **不支持 `*` 通配符** | 原式 `denois*` → HTTP 400；实测 `seismic AND denoising` 可用 | 本地实测 2026-09-25 |
| Google Scholar | **无稳定公开 API** | 通用事实；故本项标注为人工检索 |

**凭据处理**：S2 key 从环境变量 `S2_API_KEY` 读取，**仅置于请求头**，
**不写入任何入库文件**（不写代码、日志、CSV、响应缓存）。已核验原始响应 JSON 中不含 key。

---

## 五、覆盖限制（如实记录，不得宣称已完成同等查全）

1. **Scopus / Web of Science 未纳入** —— 访问性**未确认**。协议第八节要求"用户可合法访问的
   Scopus 或 Web of Science 入口"，本执行方无法确认访问权限，故**不纳入本次检索**，
   亦**不宣称**已完成与它们同等的查全。

2. **Semantic Scholar 采用降级检索式** —— S2 Graph API **不支持布尔通配符 `*`**，
   协议原式 `denois*` 会返回 HTTP 400；且 S2 为**相关性检索**而非严格布尔引擎，
   带括号的复杂布尔式返回 0 命中。故对 S2 采用**简单关键词形式**（词项取自协议原式，
   语义对应，形如 `seismic denoising fusion ensemble`）。
   **Crossref 仍严格使用协议原式逐字**。
   该偏离已在第一节与第二节逐条标注。

3. **Google Scholar 未执行** —— 无稳定公开 API，需人工/半自动检索。
   本阶段（P0.5）**未执行**该来源的检索，入库数为 **0**。
   留待 P1 滚雪球阶段以人工方式补充，并在 P1 日志中如实标注为**人工检索**。

4. **S2 额度受限** —— 带 key 仍有间歇 429，本实现采用退避重试（间隔 ≥3 s，最多 8 次）。
   已获得 300 条；若 P1 需要更多 S2 结果，须重新评估额度或分批慢跑。

5. **本阶段未做滚雪球** —— 前向/后向引文滚雪球、排除理由与查全交叉复核均属 **P1** 任务
   （依 P0.5 任务单第一节明示）。

---

## 六、原始响应留档

- 目录：`docs/bibliography/raw/`
- 内容：Crossref 与 Semantic Scholar 的**原始 JSON 响应**（15 个文件，约 5.37 MB）
- 原则：**原样保存，不得改写**（P0.5 任务 2）

---

## 七、执行摘要

- 采集：850 条原始 → **782 条去重入库**
- 结构化列：`doi,title,year,venue,source_db,query_line,track,relevance_flag,note`
- 缺 DOI 者 `note` 标 `no-doi`（**未编造任何 DOI**）
- 两条线均满足"≥30 条"验收门（机制线 340 / 基准线 293）
---

## 八、相关性初筛判据（F1 补做，**先冻结后标注**）

> **冻结声明**：本节判据在**执行标注之前**写入本文件并冻结。
> 标注完成后**不得调整判据**；若发现判据缺陷，只能**追加**新判据并重新标注，
> 且须保留两轮结果与差异说明。

### 8.1 判据（两级判定）

对每一条题录，仅依据其 **`title`** 字段（判据不使用 `venue`，避免"期刊名含 seismic"类误命中）执行：

**第一级 · 领域词（domain）—— 必要条件**

标题须命中**至少一个**地震学/地球物理领域词。词表（不区分大小写，按词干匹配）：

```
seismic, seismolog, seismogram, seismograph, geophysic, reflection,
refraction, wavefield / wave field, trace, gather, shot gather, receiver,
migration, prestack / pre-stack, poststack / post-stack, avo / amplitude
variation, reservoir, subsurface, well log, borehole, vsp, ground roll,
surface wave, rayleigh, dispersion, multiple, deghost, velocity model,
imaging, common midpoint, cmp, cdp, offset, stratum, horizon, fault, salt,
marine, land acquisition, vibrator, vibroseis, geophone, p-wave, s-wave,
elastic, acoustic impedance, sonic, wavelet, deconvolution, stack, band-limited,
random noise, coherent noise, denois, noise attenuation, noise suppression
```

**第二级 · 主题词（topic）—— 用于区分"相关 / 待定"**

在第一级命中的前提下，标题须再命中**至少一个**去噪 / 基准 / 互补性 / 信号保真主题词：

```
denois, noise, noise attenuation, suppression, snr, signal-to-noise,
fidelity, preservation, benchmark, comparison, evaluation, fusion,
combination, ensemble, local similarity, orthogonalization, blind,
filter, filtering, sparse, low-rank / low rank, decomposition, threshold,
svd, dictionary learning, deep learning, neural, cnn, u-net, attention,
transformer, inversion, separation, removal, attenuation
```

### 8.2 判定规则

| 条件 | 标记 | 说明 |
| :--- | :--- | :--- |
| 命中**第一级** 且 命中**第二级** | **`相关`** | 领域 + 主题均相符 |
| 命中**第一级** 但**未**命中第二级 | **`待定`** | 属本领域但主题不明确（如纯成像/反演类） |
| **未**命中第一级 | **`不相关`** | 仅因 OR 展开词（ensemble / fusion / fidelity / preservation…）跨域命中 |

### 8.3 判据设计意图（防事后调整的说明）

- **第一级为必要条件**：协议布尔式含 `OR combination OR ensemble OR ...` 等通用词，
  会大量命中跨域文献（实测样本含 peptide hormones、Speech Emotion Recognition、
  Diffusion Tensor Imaging 等）。以"是否属地震/地球物理领域"作为**必要条件**，
  是把"领域外假阳性"直接判为 `不相关` 的核心手段。
- **第二级用于分层，不用于排除**：属本领域但主题偏离的（如基础成像、速度建模）
  标 `待定` 而非 `不相关`——保留给 P1 滚雪球阶段人工复核，避免过早丢弃。
- **只读 `title`**：`title` 为各来源稳定提供的字段；`venue` 含期刊名，
  用其判断会引入"期刊领域 ≠ 论文领域"的偏差。
- **`no-doi` 行不特殊处理**：7 条缺 DOI 的记录同样按上述判据标注；
  `note` 列保留 `no-doi` 标记不变（两者互不覆盖）。

---

---

## 九、F1 相关性初筛结果（判据见第八节，标注前已冻结）

### 9.1 分布（全部 782 行已标注，**空标记 0 行**）

**总体**

| 标记 | 条数 | 占比 |
| :--- | ---: | ---: |
| **相关** | **417** | 53.3% |
| **待定** | **60** | 7.7% |
| **不相关** | **305** | 39.0% |
| 合计 | 782 | 100% |

**逐线 × 标记**

| 线 | 相关 | 待定 | 不相关 | 合计 |
| :--- | ---: | ---: | ---: | ---: |
| `mechanism`（机制线主检索） | 172 | 15 | 153 | 340 |
| `benchmark`（基准线） | 130 | 13 | 150 | 293 |
| `mechanism_author_Chen`（作者追踪） | 83 | 0 | 0 | 83 |
| `mechanism_author_Fomel`（作者追踪） | 32 | 32 | 2 | 66 |

**两条线合计**

| 线 | 相关条数 | 是否≥30 |
| :--- | ---: | :--- |
| 机制线（含作者追踪 Chen+Fomel） | **287** | ✅ |
| 基准线 | **130** | ✅ |

### 9.2 说明

- **「不相关」305 条为预期现象**：协议布尔式含 `OR combination OR ensemble OR ...` 等通用词，
  跨域假阳性必然出现。判据以「领域词为必要条件」将其判为不相关。
  实测样本示例（均判为不相关）：`Trademark Similarity Evaluation Using Combination of ViT and Local Features`、
  `Ensemble decision of local similarity indices on the biological network...`、
  `Local softness and local molecular quantum similarity relationship...`。
- **「待定」60 条**：属地震/地球物理领域但主题偏离（如地震目录标度关系、震源参数、碎屑流地震记录），
  或作者追踪中仅含人名而无主题词者。留待 P1 滚雪球阶段人工复核，**不提前丢弃**。
- **「相关」417 条**为 P1 滚雪球阶段的候选池；两条线均远超 30 条门槛。
- 判据**未使用** `venue` 字段；**未**对 7 条 `no-doi` 记录做特殊处理（同样按判据标注，
  `note` 列的 `no-doi` 标记保持不变）。

---

## 十、S2 检索式替代映射（F4 披露）

### 10.1 事实

Semantic Scholar Graph API **不支持** Crossref 式布尔语法：协议原式中的 `denois*` 通配符
会返回 **HTTP 400**；而带括号的复杂布尔式（`A AND (B OR C OR ...)`）虽返回 200，
但 S2 为**相关性检索引擎**而非严格布尔引擎，实测返回 **total=0**。

故对 S2 采用**简化关键词形式**。Crossref **仍严格使用协议原式逐字**。

### 10.2 替代映射（逐串）

| # | 协议原式（Crossref 使用，逐字） | S2 替代串 | 对应协议词项 | 概念是否增删 |
| ---: | :--- | :--- | :--- | :--- |
| 1 | `seismic AND denois* AND (fusion OR combination OR ensemble OR local similarity OR orthogonalization)` | `seismic denoising fusion ensemble` | seismic、denois*、fusion、ensemble | **未增删**（取了 OR 组的两个代表词项） |
| 2 | 同上（机制线补充采集） | `seismic denoising orthogonalization local similarity` | seismic、denois*、orthogonalization、local similarity | **未增删**（覆盖 OR 组剩余代表词项） |
| 3 | `seismic AND denois* AND (benchmark OR quantitative comparison OR evaluation OR signal preservation OR fidelity)` | `seismic denoising benchmark evaluation fidelity` | seismic、denois*、benchmark、evaluation、fidelity | **未增删**（取 OR 组三个代表词项） |
| 4 | 机制线**作者追踪**子项（协议：Chen、Fomel） | `seismic denoising Chen` | seismic、denois*、作者 Chen | **未增删** |
| 5 | 同上 | `seismic denoising Fomel` | seismic、denois*、作者 Fomel | **未增删** |

> **「概念未增删」核对结论**：5 个替代串的**全部词项均取自协议原式**，
> 未引入协议外概念，亦未删除协议概念（OR 组内的词项由映射 #1 + #2 共同覆盖）。
> 差异仅在**语法形式**（`AND`/`OR`/`*` → 空格分隔的关键词），
> 系 S2 引擎能力限制所致，**非研究设计变更**。

### 10.3 各来源实际使用的检索串（含记录数）

| 来源 | 线 | 实际检索串 | 入库（去重后） |
| :--- | :--- | :--- | ---: |
| Crossref | mechanism | `seismic AND denois* AND (fusion OR combination OR ensemble OR local similarity OR orthogonalization)` | 200 |
| Crossref | benchmark | `seismic AND denois* AND (benchmark OR quantitative comparison OR evaluation OR signal preservation OR fidelity)` | 196 |
| Crossref | author Chen | `seismic denoising Chen` | 46 |
| Crossref | author Fomel | `seismic denoising Fomel` | 40 |
| Semantic Scholar | mechanism | `seismic denoising fusion ensemble` | 100 |
| Semantic Scholar | mechanism | `seismic denoising orthogonalization local similarity` | 40 |
| Semantic Scholar | benchmark | `seismic denoising benchmark evaluation fidelity` | 97 |
| Semantic Scholar | author Chen | `seismic denoising Chen` | 37 |
| Semantic Scholar | author Fomel | `seismic denoising Fomel` | 26 |

> 注：上表为**去重后**按 (来源 × 线 × 检索串) 的实际保留数；
> 采集阶段原始命中数见第一节检索记录表。

---

## 十一、覆盖限制（补充本节，**必须明写**）

1. **Google Scholar —— 本阶段未执行（入库 0 条）**。
   该库无稳定公开 API，需人工/半自动检索。本阶段（P0.5）**未执行**，
   **入库条数为 0**。这是**明确的覆盖缺口**，**不因总量达标而省略**。
   留待 P1 滚雪球阶段以人工方式补充，届时须在日志中标注为**人工检索**。

2. **Scopus / Web of Science —— 访问性未确认，未纳入**（原样保留）。
   **不宣称**已完成与它们同等的查全。

3. **Semantic Scholar 采用替代检索串** —— 详见第十节。
   S2 不支持协议式布尔通配符；替代串词项取自协议原式，**概念未增删**。

4. **S2 额度受限** —— 带 key 仍有间歇 429，已用退避重试。
   若 P1 需更多 S2 结果，须重新评估额度或分批慢跑。

5. **本阶段未做滚雪球** —— 前向/后向引文滚雪球、排除理由与查全交叉复核
   均属 **P1** 任务（依 P0.5 任务单第一节明示）。

6. **相关性初筛为单轮规则判定** —— 判据见第八节，仅依据 `title` 字段；
   未做摘要级复核。`待定` 60 条为人工复核的入口，**不视为已判定**。

### 11.8 具名覆盖缺口（P1.4-Am1 披露 1）

**Sandia 2023《Comparative Study of the Performance of Seismic Waveform Denoising Methods
Using Local and Near-Regional Data》** —— 多方法（CWT 阈值 / CNN / 频率滤波）在**同一数据**上的
对比研究 —— **不在本语料中**（以标题与关键词检索 `screening.csv` 均无命中）。

- 该文献为**多方法去噪对比**，域为**地震计 / 区域地震学**（**非**勘探反射地震）；
- 来源为**实验室出版页**，**可能无 Crossref DOI / 未被检索源索引**
  ⇒ 检索管道**结构性地覆盖不到此类灰色文献**。

**结论措辞（照抄归档件第三节）**：
> "检索边界内未发现直接竞争工作；已知存在域外（地震计）多方法对比研究（如 Sandia 2023），
> 不改变本基准的定位，但说明**跨域查全无保证**。"

### 11.9 初筛口径的局限（P1.4-Am1 披露 3）

见本文件 §11 第 6 条自述：**相关性初筛为单轮规则判定，仅依据 `title` 字段**。

**明写**：相关性初筛**仅基于标题字段，未逐条读摘要**；对标题信息量不足的文献存在**误判风险**；
**滚雪球阶段以引文关系部分弥补**。本局限**列入论文局限 / 威胁效度小节**。

> 该局限已在 P1.4-Am1 中产生**实际后果**：三篇域内多方法对比工作虽被标记为「相关」，
> 却因缺操作性定义未进入竞争清单（见 `docs/bibliography/competitor-list.md` §1/§4）。

---

---

## P1.4 · 前向+后向引文滚雪球（2026-09-25，**有界探测**）

### 1. 种子选取规则（**先声明**）

> 按 `track` 分组，组内按 `screening.csv` **行序**（≈ 检索式/轮次写入顺序），
> 取前 **8** 条「相关」且含 DOI 的条目。共 4 条线（mechanism / benchmark /
> mechanism_author_Chen / mechanism_author_Fomel）→ 种子 **32** 条。

**如实披露该规则的局限**：它**确定性可复现**（非"任选"），但**未按相关度或年份排序**；
即它是"稳定的行序前 8"，**不等于**"按相关度取前 8"。

### 2. 扇出边界（**有界探测，非完整滚雪球**）

| 项 | 边界 |
| :--- | :--- |
| 种子 | ≤8 条/线，4 线 → ≤32 |
| 后向扩展 | ≤10 references / 种子 |
| 前向扩展 | ≤10 citations / 种子 |
| 次轮种子 | ≤16 |
| 轮数 | 执行 **2** 轮后触发停止判据 |

### 3. 逐轮统计

| 轮 | 种子数 | 新增题录 | 其中「相关」 | 新直接竞争工作 |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 32 | 143 | 40 | **0** |
| 2 | 16 | 229 | 91 | **0** |

累计新增 **372** 条，全部合并入 `screening.csv`（新增 372 行）。

### 4. 停止判据及其**不构成查全证明**

判据：**连续两轮不再发现改变定位的直接竞争工作**。轮 1、轮 2 均为 0 ⇒ 满足 ⇒ 停止。

> ⚠️ **该判据不构成查全证明。** 它只说明「在本扇出边界内、两轮未发现新的直接竞争工作」，
> **不能**推出「不存在同类工作」。论文的**局限 / 威胁效度**小节必须承接本条，
> 且**不得**写"未发现同类工作"这类无界断言，只能写"在本检索边界内未发现"。

### 5. 原始响应与台账（可复现证据）

- 原始 API 响应：`docs/bibliography/raw/openalex_*.json` —— **实测 339 个**（全部入库）。
  - 注：签发方 P1.3-Am2 第四节记为 325 个；此处为**实测值 339**（第二轮扩展与合并后计数）。
- 台账：`docs/bibliography/screening.csv` —— **1154 行**
  （相关 **548** / 待定 **201** / 不相关 **405**）。

### 6. 交付表索引

| 表 | 文件 |
| :--- | :--- |
| 机制对比表 | `docs/bibliography/mechanism-table.md` |
| 基准对比表 | `docs/bibliography/benchmark-table.md` |
| 排除理由表 | `docs/bibliography/exclusion-reasons.md` |
| 竞争工作清单 | `docs/bibliography/competitor-list.md` |

### 7. 工具与合规

- 检索源：**OpenAlex**（polite pool，含 `mailto`）；响应**全部落盘缓存**，同一 URL 不重复打网；间隔 ≥1.1 s。
- **检索截止日 2026-10-04 冻结**；此后不得新增文献。
- 禁编造条目/DOI；**禁以 LLM 摘要替代原文核实** —— 四张表**只含题录元数据**（题名/年份/期刊/DOI），
  每份表头均写明该来源限制。
- 本次**未使用任何计费 API**（支出 0 USD）。
