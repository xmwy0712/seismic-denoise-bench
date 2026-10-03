# 格式合规自检报告（en-v7）

> **对象**：`docs/paper/draft-en-v7.md`（88473 B，`D47AB1CE67B5ED6D203814ECA4939E176339A13064B1C27D2448FDE14B9CFCD7`）
> **门禁**：`execution/format_compliance.py`（**17 项**；图/表标签识别已覆盖中英）

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
| `G-cite-ref` | 正文 [1, 2, 3, 4, 5, 6, 7, 8, 9] / 文献表 [1, 2, 3, 4, 5, 6, 7, 8, 9] | PASS |
| `G-reader-terms` | 命中 = 无（词表 26 项；附录 B 登记表已排除） | PASS |
| `G-reader-structure` | 标题行=True 首个二级标题=摘要:True 无##0.:True 标题块无引注:True | PASS |
| `G-table-continuity` | 表格块 = 15；疑似断裂 = 无；分隔行异常 = 无 | PASS |
| `G-encoding` | BOM=False CR=0 | PASS |

**总判定 = PASS（exit 0）**

## 说明

英文稿重定位（四批）：标题/摘要/关键词/Highlights；替换表逐条；相关工作段与 3 篇已核验文献；§3.3 恒等式；§3.5 野外口径；§4.3–§4.5；新增 §5.4/§5.5；§6；附录 B 两条登记。并在交付门禁中删去 §1.3 早于表 1 的 `(Table 9)`（同中文处理）。**数值与结论零变化。**

**本报告由脚本生成，可机械复算。**
