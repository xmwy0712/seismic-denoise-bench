# Zenodo 归档包（P5.4 · WS3）

> **状态：待上传。** 本包已备好；本机**未配置 Zenodo 凭据**，故**未生成 DOI**（不伪造）。

## 1. 内容

- `payload/configs/` —— 冻结配置四件（frozen.yaml / frozen-v2.yaml / fusion-rules.yaml / methods_registry.yaml）
- `payload/preregistration/` —— 预注册件（互补性、融合、统计、补充比较）
- `payload/results/` —— 全部指标与统计产物（CSV）
- `payload/paper/` —— 论文初稿 `draft-v5.md`、数字溯源对照、参考文献、格式合规报告、5 张图
- `payload/docs/` —— 野外数据署名与许可登记、判定输入汇编
- `MANIFEST.sha256` —— 包内每个文件的 SHA256 与字节数
- `ARRAYS.sha256` —— **未随包上传**的输出数组清单（逐文件 SHA256）

## 2. 关于输出数组（**记为本地件并披露**）

方法输出与融合输出数组共 **16473 个文件、4.37 GB**，**不随本包上传**。理由：

1. 它们可由冻结配置 + 随机种子 + 本仓库代码**确定性重放**（无随机成分的方法实现；融合亦为确定性构造）；
2. 体积远大于其余全部材料之和；
3. 其**逐文件 SHA256 已记入 `ARRAYS.sha256`**，因此即使不传输也可核验重放结果是否逐字节一致。

若审阅需要具体数组，可按 `ARRAYS.sha256` 逐项重放比对。

## 3. 复现入口

- 测试：`run_tests.ps1`（本机权威）/ `run_tests.sh`
- 各执行脚本头部 docstring 给出官方运行命令

## 4. 许可与署名

- 本研究自有代码：**MIT**
- 野外数据：**CC BY 4.0**（上游署名见 `payload/docs/field-data-note.md`，再分发须保留）

## 5. 上传后须回填

- 本包上传至 Zenodo 后，把 DOI 回填至论文 `draft-v5.md` 第「数据与代码可用性」节与附录 A。
