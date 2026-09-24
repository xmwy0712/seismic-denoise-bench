# 执行日志（追加式）

> **规则**：本文件为**只追加**日志。禁止覆盖、截断或删除历史条目。
> 每条记录格式：`时间 | 阶段 | 动作 | 结果 | 证据（哈希/文件/命令）`。
> 任何"尚未实施"的事项**不得**写成"已通过"。

---

## P0 — 脚手架与协议冻结

### 2026-09-23 | P0.1 | 项目骨架初始化

**授权链**
- 用户以任务单形式下达 P0.1 指令，明确"同意"执行。
- 权限判定：**L2**（workspace 外写入 + `git init` 生成 `.git/`，取值交集）。按工作区安全宪法走 `BLOCK → CONFIRM → OTP → RECHECK → SNAPSHOT → EXECUTE → AUDIT`。
- **确认**：2026-09-23 21:50 用户回复"同意"。
- **OTP**：2026-09-23 21:50 提供 6 位动态码，经 `skills/otp-verify/verify_otp.py` 校验返回 `VALID`（退出码 0）。明文未记录。
- **RECHECK**：执行前复核 `D:\` 非重解析点（attrs=ReadOnly,Hidden,System,Directory；linktype 空）；`D:\projects` 与目标路径均不存在；无全局 GPG 签名要求。
- **SNAPSHOT**：源协议文件 SHA256 基线 = `67472625C5055CCDF610522EDBCD9A574ED27358B3256C1DCE6A6B73D5C09417`（23,738 bytes，mtime 2026-09-22T17:12:03）。本次操作**不修改**该源文件，故无需覆盖式备份。

**裁定记录（用户裁定，2026-09-23 21:50）**
1. **tag 体系来源更正**：V5 协议**未定义** tag 体系；tag 体系来自**执行层《AI-Council-V5 执行手册》V3 第六节"不可变性"**。README 中该表已标注来源为"执行手册"，**未**标注为协议内容。
2. **采用执行手册五 tag 体系**（含可选的第六个 `submission-v1`），**不采用**助理先前提出的三 tag 方案。先前方案遗漏的 `fusion-rules-frozen`（协议硬规则"融合规则冻结必须早于正式融合运行"的物理载体）与 `tri-state-locked`（"三态锁定后不可更改"的物理载体）不可省略。
3. **命名注意**：为 `config-frozen`（**单数**），非 `configs-frozen`。
4. **README 标注要求**：全量写入五 tag 表，并注明"仅 `protocol-frozen` 现已存在，其余为计划节点，实际创建时点以 execution-log 记录为准"。

**执行动作与产物**
- 创建目录骨架（12 个子目录）：`configs`、`docs`、`runs`、`tests`、`data/field`、`src/paper`、`src/search`、`src/bench/{data,methods,metrics,stats,fusion,field}`。
- 空目录放置 `.gitkeep`（12 个）。
- 复制协议快照：`docs/protocol-v5.md`（字节级复制）。
- 写入：`LICENSE`(MIT)、`README.md`、`.gitignore`、`pyproject.toml`、`docs/execution-log.md`（本文件）、`docs/budget-ledger.md`、`docs/api-ledger.csv`。
- 初始化 Git 仓库：`git init` → 首次提交 → 创建**附注** tag `protocol-frozen`。
- 追加审计记录至 `~/.openclaw/workspace/security/audit.log`。

**验收证据**
- `docs/protocol-v5.md` SHA256 = `67472625C5055CCDF610522EDBCD9A574ED27358B3256C1DCE6A6B73D5C09417`，与源文件**逐字节一致**（未改动一个字）。
- 目录清单与任务单逐项比对一致。
- 见下方"首次提交"记录。

---

<!-- 后续条目追加于此行之下；请勿修改以上历史 -->

## P0 — 拍板项记录（执行层裁定）

### 2026-09-23 | 拍板项 1 | 仓库路径与仓库名
- **决定**：项目仓库路径 = `D:\projects\seismic-denoise-bench`；仓库名（project name）= `seismic-denoise-bench`。
- 状态：**已生效**（P0.1 已按此创建）。

### 2026-09-23 | 拍板项 2 | 许可证
- **决定**：本仓库自有代码采用 **MIT License**。
- **修正**：`LICENSE` 第 3 行行文由 `Copyright (c) 2026 夕暮微雨 (ZhangTao)` 改为 `Copyright (c) 2026 Zhang Tao (张涛)`（P0.1-R 整改）。
- 边界：第三方移植代码、模型权重与数据**不**适用 MIT，其许可另行逐项登记。

### 2026-09-23 | 拍板项 3 | 膨胀（dilation）语义冻结
- **决定**：真值事件窗掩码 `M` 由干净真值按**固定阈值**生成后，**膨胀一个子波长度**（协议 V5 第四条 / 步骤3）。
- **膨胀长度定义**：`T = 1 / f_main`（子波主频对应的周期）。
- **补充注记（用户 2026-09-23 22:18 追加裁定，三条，全部采纳）**：
  1. `n_T = 1/(f_main·dt)` **通常非整数**，因此除逐配置记录 `n_T` 外，**必须同时冻结取整规则**：
     ```
     n_T = round(1 / (f_main · dt))
     ```
     （`round()` 按 Python 内置 `round` 的四舍六入五成双语义，冻结时须写明所用实现以避免歧义。）
  2. P1 冻结时，**按「原式 + 取整规则 + 取整后整数值」三元组逐配置记录**。
  3. 膨胀**仅沿时间轴（时间方向）作用，不作用于道方向**。
- **额外冻结义务（用户裁定）**：`event_mask` 的**人工阈值**同为 Lsig 可复现的必要参数，**P1 必须一并冻结**。
- **理由（不可省略的原因）**：不同配置 `f_main` 不同（示例：15 / 25 / 40 Hz），`T` 与 `n_T` 随之不同（示例：dt=2 ms 时 n_T ≈ 33 / 20 / 13 点）。若只写一个全局值，`Lsig` 不可复现。
- **落点**：以上参数在 P1 冻结于 `configs/`（tag: `config-frozen`）时逐配置登记。本条目仅记录**规则**，不代替 P1 的参数冻结。

### 2026-09-23 | 拍板项 4 | 测试入口语义（用户 2026-09-23 22:18 裁定）
- **授权成立**：本机**无 `make`、无 PATH 内 `bash`**，故交付 `run_tests.sh`（POSIX / git-bash）+ `run_tests.ps1`（Windows 原生），取代 `Makefile`。
- **硬要求**：两个入口必须是**同一语义的薄封装**——等价于在仓库根执行 `python -m pytest`；**禁止任一入口只跑子集**。
- **权威入口**：README 中指定 **`run_tests.ps1` 为本机权威入口**。
- **入口语义差异登记**：见下方 P0.2 条目。


### 2026-09-24 | P0.1-R | 整改（4 项）

**授权**：用户 2026-09-24 23:03 回复「同意」并提供 6 位动态码，经 `skills/otp-verify/verify_otp.py` 校验返回 `VALID`（明文未记录）。权限判定 **L2**（仓库内多文件改写；与 P0.2 装依赖同批）。
**RECHECK**：HEAD 仍为 `9c7dcde`，工作区干净，未配置 git remote。

| 项 | 内容 |
| :--- | :--- |
| R1 | `README.md` 第 5 节拆为双表：表 A（协议周次表，来源标注「协议原文 V5 纪要 第十节」）+ 表 B（执行日历表，来源标注「执行层《AI-Council-V5 执行手册》」，P0–P7 八行），并写入 P4 三态锁定硬死线 **2026-11-08 23:59 EOD** |
| R2 | `docs/budget-ledger.md` GCP 赠金行补记到期日 **2026-11-09**，并标注为「用户 2026-09-23 提供」；第 2 节待核验清单**原样保留**——核验义务不因口头日期免除 |
| R3 | `LICENSE` 版权行 → `Copyright (c) 2026 Zhang Tao (张涛)` |
| R4 | 见下方「R4 补充注记」 |

---

### 2026-09-24 | P0 拍板项记录（3 条）

**1. 仓库路径与文件写入方式**

项目仓库确定位于 **`D:\projects\seismic-denoise-bench`**，在 workspace 之外。
因 `tools.fs.workspaceOnly` 已开启，`write` 类文件工具**无法直写** `D:\`。
既定作业方式：先在 `~/.openclaw/workspace/.openclaw/tmp/` 暂存（该路径下 `write` 工具产出天然为 **UTF-8 无 BOM + LF**），再以 `Copy-Item` **字节级**复制到目标。
仓库内全部文本文件编码约定：**UTF-8 无 BOM、LF 换行**（每次交付后逐文件字节审计 BOM 与行尾）。

**2. 许可证**

项目自有代码采用 **MIT License**；版权持有者署名按用户 2026-09-24 裁定更正为 **Zhang Tao (张涛)**。
第三方移植代码 / 权重 / 数据**不适用** MIT，须逐项单独登记许可与再分发条件（协议第七节）。

**3. 膨胀语义**

协议第五节 Lsig 的 `M` 构造表述为「膨胀一个子波长度」。
P0 拍板明确语义：**一个子波长度 = 设定主频对应的子波周期 `T = 1 / f_main`**（而非固定采样点数或其它解释）。
该语义为 Lsig 可复现的必要前提，随下方「R4 补充注记」一并冻结。

---

### 2026-09-24 | R4 补充注记（膨胀规则与 event_mask 阈值）

> **起因**：P0.2 实现 `src/bench/data/ricker.py` 时发现，协议对「膨胀一个子波长度」只给出自然语言表述，
> 而 `n_T = 1 / (f_main · dt)` 通常**非整数**；若不规定取整规则，不同实现将得到不同的 `M`，导致 Lsig 不可复现。
> 经用户 2026-09-24 裁定采纳，补充如下。

**a) 取整规则冻结**

膨胀长度（沿时间轴的采样点数）：

```
n_T = round(1 / (f_main * dt))
```

采用 **round（四舍五入取整，Python 内建 `round` 行为）**。
禁止使用 `floor` / `ceil` / 截断取整；P1 冻结后不得更改取整方式。

**b) 三元组逐配置记录（P1 冻结时必须执行）**

在 `configs/frozen.yaml` 中，对**每一个合成配置**逐条记录下述三元组，**不得只写全局单值**：

| 字段 | 含义 |
| :--- | :--- |
| `n_T_expr` | 原式，字符串 `"1/(f_main*dt)"` |
| `n_T_rule` | 取整规则标识，固定字符串 `"round"` |
| `n_T_int` | 取整后的整数值（整数） |

并同时记录该配置的 `f_main` 与 `dt`。

**理由（重要）**：不同配置的 `f_main` 不同（如 15 / 25 / 40 Hz），在 `dt = 2 ms` 下
`n_T` 分别约为 33 / 20 / 13 点。`M` 是**逐配置生成**的，不存在全局单一 `n_T`；
只记一个全局值会使 Lsig 在跨配置比较时不可复现。

**c) 膨胀仅沿时间轴**

膨胀**只作用于时间轴**，**不作用于道方向**：`M` 在空间/道维上与真值事件窗一致，不得对道方向做任何形态学扩张。

**d) 附：event_mask 人工阈值同为必要冻结参数**

`M` 的生成链为「干净真值 → 按**固定阈值**生成事件窗 → 膨胀」。
该**人工阈值**与上述膨胀规则同为 Lsig 可复现的必要参数，**P1 必须一并冻结**并随配置记录落盘；
须在运行任何方法之前冻结，之后不得调整。

---

### 2026-09-24 | P0.2 | 环境与测试基座

**权限**：**L2**（安装依赖 + 新建 `.venv` + 仓库内多文件写入），与 P0.1-R 同批授权、同一 OTP。

**1. 解释器**

| 项 | 实测值 |
| :--- | :--- |
| 解释器路径 | `C:\Users\Lenovo\AppData\Local\Programs\Python\Python312\python.exe` |
| 版本 | `Python 3.12.10`（要求 `>=3.11` ✅） |
| venv | `D:\projects\seismic-denoise-bench\.venv`（`python -m venv`，退出码 0） |
| venv 内 pip | 升级至 `pip 26.2.1` |

**2. 依赖安装（实际执行，非纸面）**

命令：`python -m pip install numpy scipy matplotlib pyyaml pandas pyproj pywavelets segyio pytest`
结果：**Successfully installed**（退出码 0）。直接依赖实测版本：

| 包 | 版本 | 包 | 版本 |
| :--- | :--- | :--- | :--- |
| numpy | 2.5.3 | pyyaml | 6.0.3 |
| scipy | 1.18.1 | pandas | 3.0.6 |
| matplotlib | 3.11.2 | pyproj | 3.8.0 |
| PyWavelets | 1.10.0 | segyio | 1.9.14 |
| pytest | 9.1.1 | | |

**3. 环境锁定文件**

`requirements.lock` = `pip freeze` 全文（24 行 / 391 bytes），逐行精确版本。
直接依赖同时写入 `pyproject.toml` 的 `[project.dependencies]`（及 `[project.optional-dependencies].dev`）。

**4. 测试入口（同语义薄封装）**

| 入口 | 内容 | 定位 |
| :--- | :--- | :--- |
| `run_tests.ps1` | 定位解释器 → `python -m pytest` | **本机权威入口** |
| `run_tests.sh` | 定位解释器 → `exec python -m pytest` | 等价封装（POSIX / Git Bash） |

- 两入口均**不传筛选参数、不跑子集**，语义等价于在仓库根执行 `python -m pytest`。
- 本机 **无 `make`**、**PATH 内无 `bash`**（存在 Git Bash）。故**未提供** `Makefile`；按任务单「Makefile **或** 测试入口脚本」的二选一授权，交付上述两个脚本。
- **入口语义差异（按要求记录）**：二者**被调用方式**不同——`run_tests.ps1` 为 PowerShell 原生、`run_tests.sh` 需经 Git Bash 或 WSL 调用；且两者在解释器回退顺序上等价（均优先 `.venv`，缺失时回退 PATH `python`）。**测试语义完全一致**：均无参数、无子集裁剪。README 第 6 节已指定 `run_tests.ps1` 为本机权威入口。

**5. 测试执行（三入口交叉验证，全文实测）**

```
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\projects\seismic-denoise-bench
configfile: pyproject.toml
testpaths: tests
collected 13 items

tests\test_ricker.py .............                                       [100%]

============================= 13 passed in 0.16s ==============================
```

| 入口 | 结果 | 退出码 |
| :--- | :--- | ---: |
| `python -m pytest`（直接） | 13 passed | 0 |
| `run_tests.ps1`（本机权威入口） | 13 passed | 0 |
| `run_tests.sh`（Git Bash） | 13 passed | 0 |

**6. 协议第七条验收实测值（逐主频记录）**

测量参数：`dt = 2 ms`、`n_samples = 512`、FFT 零填充 `n_fft = 65536`、峰值邻域三点抛物线插值。
判定阈值：协议预注册值 **5%**（`TOL_REL = 0.05`，**未放大、未收紧**）。

| 设定主频 `f_main` (Hz) | 回算主频 `f_est` (Hz) | 相对误差 | 阈值 | 判定 |
| ---: | ---: | ---: | ---: | :--- |
| 15.0 | 15.000001 | 0.000004 % | 5 % | 通过 |
| 25.0 | 25.000000 | 0.000001 % | 5 % | 通过 |
| 40.0 | 40.000000 | 0.000001 % | 5 % | 通过 |

> 说明：误差处于 1e-6 % 量级。原因是本测量采用 65536 点零填充 + 抛物线插值，
> **测量精度**远高于判定阈值。该富余量**不构成**对阈值的收紧或放宽，判定阈值恒为协议值 5%。

**7. 实现过程中发现并修正的问题（如实记录）**

初次运行 13 项测试中有 **2 项失败**；定位后确认为**测试代码自身的假设错误**，而非实现缺陷：

- `test_ricker_symmetry_and_peak`：断言 `argmax(w) == n//2`。但 `n = 512` 为偶数时，`t0 = (n-1)·dt/2` 落在第 255 与第 256 个样点**之间**，`argmax` 返回 255。
- `test_ricker_amplitude_normalization`：断言 `max(w) == 1`。同理**没有样点落在 tau = 0**，离散峰值为 0.98159 < 1。

修正方式：**仅修改测试断言**（改为「中心两样点并列取极大」；并新增 `t0 = k·dt` 对齐时峰值精确为 1 的用例），
`src/bench/data/ricker.py` **实现未改动**。修正后 13 项全绿。

**8. 本次交付文件**

新增：`src/bench/__init__.py`、`src/bench/data/__init__.py`、`src/bench/data/ricker.py`、`tests/test_ricker.py`、`run_tests.ps1`、`run_tests.sh`、`requirements.lock`。
修改：`pyproject.toml`、`README.md`、`LICENSE`、`docs/budget-ledger.md`。
目录 `src/bench/data` 与 `tests` 已含实际文件，其占位 `.gitkeep` **已删除**。

**9. 未做（红线保持）**

未配置 git remote；未 push；未联网上传；未改用户级/系统级环境变量；未改 `openclaw.json` / `gateway.cmd`；未重启 gateway；未建定时任务；未创建 `config-frozen` 及后续任何 tag；未修改 `docs/protocol-v5.md`。

**10. 提交**

采用**新 commit**（**未使用 `--amend`**）；本阶段提交哈希以 `git log --oneline` 为准。
