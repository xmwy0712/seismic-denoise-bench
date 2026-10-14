# 格式合规自检报告（v19）

> **对象**：`docs/paper/draft-v19.md`（80081 B，`8A0DA78EB80EF9CE5FB6081D95BFA88A2ED2423230AFC4D16EF0F0D1B8B0C0C6`）
> **门禁**：`execution/format_compliance.py`（**19 项**；图/表标签覆盖中英；引用支持多位数）

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
| `G-cite-ref` | 正文 [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31] / 文献表 [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31] | PASS |
| `G-reader-terms` | 命中 = 无（词表 26 项；附录 B 登记表已排除） | PASS |
| `G-reader-structure` | 标题行=True 首个二级标题=摘要:True 无##0.:True 标题块无引注:True | PASS |
| `G-table-continuity` | 表格块 = 15；疑似断裂 = 无；分隔行异常 = 无 | PASS |
| `G-math-balance` | $ 不成对的行 = 无 | PASS |
| `G-key-symbols` | 缺失 = 无（共 3 项） | PASS |
| `G-encoding` | BOM=False CR=0 | PASS |

**总判定 = PASS（exit 0）**

## 说明

v18 → v19：参考文献由 10 条扩充至 **31 条**（全部取自仓库文献语料 `docs/bibliography/screening.csv`，
元数据按 Crossref 题录记录登记），并补入正文引用句；更正参考文献表说明中的条目计数。**数值与结论零变化。**

同批门禁加强：`G-cite-ref` 原正则 `\[(\d)\]` **只能匹配单位数**，对 `[10]` 及以后**长期失明**，
已修为 `\[(\d+)\]`；新增 `G-math-balance`（行内 `$` 成对）与 `G-key-symbols`（§3.2/§3.4 关键符号在场）。
门数 **17 → 19**。

**本报告由脚本生成，可机械复算。**
