# seismic-denoise-bench

**基于信息互补性分析的地震数据去噪基准与轻量融合方法**


---

## 1. 项目目标与能力边界

**固定主贡献**：可复现的去噪基准、信号保真评估框架、跨方法互补性发现。

**条件性方法贡献**：无需训练、可在 CPU 运行的相干噪声感知时频融合元方法。其论文地位由预先注册的三态规则（A / B / C）决定，不由事后叙述决定。

**能力边界（明确写入的限制）**：融合主要重新组合各输入方法**已经保留**的互补信息。若某段真实信号被所有输入方法**共同删除**，融合通常不能可靠恢复该信号。本研究**不承诺**恢复所有现有方法均未保留的信息，也**不把融合描述成未经证明的信号并集**。


完整协议见 [`docs/protocol-v5.md`](docs/protocol-v5.md)（AI Council 会谈纪要 V5 快照）。

---

## 2. 仓库结构

```
seismic-denoise-bench/
├── configs/                 # 冻结的配置清单（配置/种子/指标/野外面板）
├── docs/
│   ├── protocol-v5.md        # 协议快照（外部，未改动）
│   ├── execution-log.md      # 执行日志（追加式）
│   ├── budget-ledger.md      # 预算台账
│   ├── api-ledger.csv        # 现金 API 逐笔记账（≤10 USD 硬上限）
│   ├── license-register.csv  # 第三方源码/权重/数据 许可登记表
│   └── task-sheets/          # 任务单归档
│       ├── MANIFEST.md
│       └── *.md
├── src/
│   ├── bench/
│   │   ├── data/             # 合成模型正演、加噪、真值事件窗生成
│   │   ├── methods/          # 4–6 种方法的统一输入输出接口
│   │   ├── metrics/          # ΔSNR / Lsig / CNA / 事件级与野外四项指标
│   │   ├── stats/            # 配对置换检验、 Holm 校正、分层自助置信区间
│   │   ├── fusion/           # 时频加权融合 + 相干噪声鉴别模块
│   │   └── field/            # 野外无真值评估与泄漏代理 LP
│   ├── paper/                # 论文图表与稿件来源（从落盘数组重建）
│   └── search/               # 新颖性检索日志、机制表、基准表
├── tests/                    # 单元测试与验收测试
├── runs/                     # 运行产物（不入库，仅保留目录占位）
├── data/
│   └── field/                # 野外数据（许可合格者；说明与校验值）
├── run_tests.ps1             # 测试入口（PowerShell）
├── run_tests.sh              # 测试入口（POSIX / Git Bash）
├── requirements.lock         # 环境精确版本锁定（pip freeze 输出）
├── LICENSE
├── pyproject.toml
└── .gitignore
```

---

## 3. 不可变性：Git tag 体系

| tag | 冻结对象 | 计划时点 |
| :--- | :--- | :--- |
| `protocol-frozen` | 协议冻结 |
| `config-frozen` | 数据 / 指标 / 配置 / 野外面板冻结 |
| `fusion-rules-frozen` | 融合规则冻结 |
| `tri-state-locked` | 三态判定锁定 |
| `field-locked` | 野外设置锁定 |

实际创建时点以 [`docs/execution-log.md`](docs/execution-log.md) 记录为准。

**执行规则**：
- `fusion-rules-frozen` 必须**严格早于**任何正式融合运行；
- `tri-state-locked` 一经创建，**不得通过更换指标、配置或基线改变锁定状态**；唯一允许的变更是状态 A 依协议单向降级为 B。

---

## 4. 关键预注册约定（摘要）

- **主合成模型**：Ricker 子波 × 水平层状速度模型反射系数序列 → 褶积正演；噪声含带限高斯随机噪声、指定视速度线性相干干扰、具速度—频率关系的频散面波；每配置 **≥5 个独立随机种子**。
- **第二合成模型**：非纯水平层状，至少含倾斜同相轴、弯曲同相轴与一处简单断层或横向速度变化。
- **首要质量指标**：ΔSNR（输出 SNR 提升，越高越好）。
- **唯一首要信号泄漏指标**：Lsig（真值事件窗归一化重建误差，越低越好）；事件窗由干净真值按固定阈值生成后膨胀一个子波长度，规则**在运行方法前冻结**。
- **相干噪声指标**：CNA（越高越好），投影实现须先用纯相干噪声数据验证回收误差 ≤5%。
- **统计**：配置内对种子求均值 → 全配置等权宏平均；同配置同种子配对差值；双侧配对置换检验 α=0.05；同一首要指标下对全部单法比较使用 Holm 校正；报告配置分层自助 95% 置信区间。
- **三态锁定**：按唯一规则锁定 A / B / C；锁定后不得升级（但A 可单向降级为 B）。
- **野外评估**：在查看方法标签结果**前**冻结 3 个代表性面板/时窗 × 3 档融合保守度参数 = **9 个预注册设置**；四项固定权重综合分 U（振幅保持 30% / 频谱残差 25% / 同相轴连续性 25% / 盲评 20%）与独立泄漏代理 LP 裁决。

---

## 5. 测试入口

两个入口是**同一语义的薄封装**，均等价于在仓库根目录执行：

```
python -m pytest
```

二者**不传任何筛选参数、不跑子集**。

| 入口 | 运行环境 | 说明 |
| :--- | :--- | :--- |
| `run_tests.ps1` | Windows / PowerShell |
| `run_tests.sh` | POSIX / Git Bash |

两个入口会自动优先使用仓库内 `.venv` 解释器，缺失时回退到 PATH 上的 `python`。

**环境**：Python 3.12.10；精确依赖版本见 [`requirements.lock`](requirements.lock)。安装与验收记录见 [`docs/execution-log.md`](docs/execution-log.md)。


---

## 6. 开放与合规

- 全部源码在采用前核验**许可证、版权声明、修改标注义务、专利条款、模型权重条款与再分发兼容性**；登记于 [`docs/license-register.csv`](docs/license-register.csv)。
- 只有允许拟定 GitHub 与 Zenodo 发布方式的代码 / 权重 / 数据才能进入开放仓库；不能再分发的材料只发布**下载脚本、校验值和用户自行获取说明**，不虚假承诺公开原文件。
- 逐数据集核验来源、学术使用权、衍生结果发表权、引用义务与再分发限制。

---

## 7. 许可

本仓库自有代码采用 [MIT License](LICENSE)。第三方移植代码、模型权重与数据的许可另行逐项登记，以 [`docs/license-register.csv`](docs/license-register.csv) 为准。

### 7.1 SEG-Y 读取库（`segyio`，LGPL-3.0-or-later）—— 四条硬约束

本项目采用 **`segyio`** 作为 SEG-Y 读取依赖。其许可为
**LGPL-3.0-or-later**。因本项目仅以 **pip 依赖方式调用**（不复制源码、不静态链接、
不随仓分发其源码或二进制），**不触发对本仓库 MIT 代码的传染**。为维持该状态，以下四条为**硬约束**：

1. **禁止**把 `segyio` / `obspy` 的源码复制进本仓库任何位置；
2. **禁止** vendor / 打包其源码或二进制随 GitHub / Zenodo 发布；
3. 依赖通过 `pyproject.toml` / `requirements.lock` 声明，由使用者自行从 PyPI 安装；
4. 若**将来**需要分发其源码或修改版，必须**重新核验**并满足 LGPL-3.0 的
   §2 修改标注、§3 / §4 通告与随附 GPL + LGPL 全文义务（届时另行裁定）。

`obspy` 的许可**已核验**（同为 LGPL-3.0），但**本次不纳入**（体量与依赖面更大，非许可原因），
保留为备选记录。详见 [`docs/license-register.csv`](docs/license-register.csv) 第一节。

### 7.2 野外数据致谢义务

若使用 Stratton 3D 数据集，须**致谢 Bureau of Economic Geology, The University of Texas at Austin**
（原文摘录见 [`docs/license-register.csv`](docs/license-register.csv) 第三节）。
