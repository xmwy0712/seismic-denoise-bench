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