# 格式合规自检报告（P5.12 · draft-v13）

> **对象**：`docs/paper/draft-v13.md`（66417 B，`997AB3E053B634E8CC935A4BEC2E621B72AA71C9038FE523F2EFCBE8A2EDA5AF`）
> **门禁**：`execution/format_compliance.py`（**17 项**）+ `execution/number_gate.py`

| 门 | 实测 | 判定 |
| :--- | :--- | :--- |
| `G-fig-order` | 首提顺序 = [1, 2, 3, 4, 5, 6, 7, 8]；应 = 1..8 | PASS |
| `G-tab-order` | 首提顺序 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]；应 = 1..12 | PASS |
| `G-embed-order` | 嵌入顺序 = [1, 2, 3, 4, 5, 6, 7, 8] | PASS |
| `G-caption-order` | 题注顺序 = [1, 2, 3, 4, 5, 6, 7, 8] | PASS |
| `G-embed-caption-pair` | 不配对行 = 无 | PASS |
| `G-embed-exists` | 缺失 = 无（共 8 条） | PASS |
| `G-appendix-figmap` | 编号/文件名不符 = 无（共 8 行） | PASS |
| `G-tag` | \tag{ 出现 = 0 | PASS |
| `G-eq-number` | 编号 = 1..10，唯一 = True | PASS |
| `G-block-count` | $$ 块 = 10；编号数 = 10 | PASS |
| `G-no-path` | 正文命中 = 0 | PASS |
| `G-no-meta` | 命中 = 0 | PASS |
| `G-cite-ref` | 正文 [1, 2, 3, 4, 5, 6, 7] / 文献表 [1, 2, 3, 4, 5, 6, 7] | PASS |
| `G-reader-terms` | 命中 = 无（词表 26 项；附录 B 登记表已排除） | PASS |
| `G-reader-structure` | 标题行=True 首个二级标题=摘要:True 无##0.:True 标题块无引注:True | PASS |
| `G-table-continuity` | 表格块 = 15；疑似断裂 = 无；分隔行异常 = 无 | PASS |
| `G-encoding` | BOM=False CR=0 | PASS |

**格式门总判定 = PASS（exit 0）** · **数字门 = PASS（exit 0）**

## 本批：按投稿形式补齐章节

| 投稿表字段 | 处置 |
| :--- | :--- |
| 标题 / 英文标题 | 已在 v12 就位，未动 |
| 作者 / 作者单位 | 抬头补 **School of Earth Sciences and Engineering, Nanjing University, Nanjing, China** |
| 通讯作者 / 通讯邮箱 | 抬头补 **Corresponding author: Zhang Tao (251830064@smail.nju.edu.cn)** |
| Data Availability | 由原「数据与代码可用性」**拆出独立节**（英文节名），内容为合成数据冻结说明、野外数据许可与引文、校验清单指向附录 A |
| Code Availability | **独立节**（英文节名）：MIT 许可 + 公开代码仓库地址 |
| Funding | **新增**（无资助声明，按投稿模板原文） |
| Declaration of Competing Interest | **新增**（无利益冲突声明） |
| CRediT authorship contribution statement | **新增**（Zhang Tao 的 11 项贡献） |
| Acknowledgements | 「致谢」改为 **Acknowledgements**，内容不变 |
| References | 已有，格式留英文稿阶段统一 |
| Appendix A / B | 已有，未动 |
| **Code DOI / Data DOI / DOI 回填** | **不写入正文**（待生成项，按指示留空） |

## 数字

**v12 → v13 数字差集 = 无**（本批只增章节与声明，未改动任何数字）。
