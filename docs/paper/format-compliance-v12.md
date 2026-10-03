# 格式合规自检报告（P5.11-Am · draft-v12）

> **对象**：`docs/paper/draft-v12.md`（65694 B，`B5EAFDD3DCB90AE98A883ECBFC3AFA02FD1D6B28B0BD1A8DDF0C5F9BF286D70D`）
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

## 本批四处微瑕与排版硬伤

| # | 项 | 处置 |
| :--- | :--- | :--- |
| 1 | 摘要排版笔误与括号漏闭 | 核验：`。；` 与漏右括号**在 v11 已消除**（P5.10 摘要重写时一并修掉，实测 0 次） |
| 2 | §3.2 提前剧透实验数值 | 「0.0588 dB 对 0.0422 dB」「0.020640 对 0.015129」等读数**全部移出方法节**，改为概念化表述；具体数值仅留第 4.3 节 |
| 3 | §6「度量学」未降级 | 收尾段改为「**无偏基准协议与候选度量的病理诊断构成核心方法学贡献**」；§4.2 的「度量学发现」一并降为「**度量框架层面的发现**」，全文「度量学」清零 |
| 4 | FP3「零检出」→ 严谨性 | §2.2 / §4.4 / 摘要三处改述为「**坚持预注册冻结门槛、拒绝事后主观放宽阈值回填**的真实边界记录」 |

另：摘要补回 v11 重写时遗失的判据结论「**仅部分通过样本外验证**」。

**本报告由脚本生成，可机械复算。**
