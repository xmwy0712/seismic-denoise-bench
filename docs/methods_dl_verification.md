# DL 核验轮（P2.2 前置门）· 逐候选四项核验

> **依据**：`P2.1-Am1-机制表出入裁定与DL核验轮-2026-10-03.md` 第三节（裁定 I）
> + `P2.2-DL核验与云上全矩阵-2026-10-08.md` 第一节。
> **核验四项**：① 许可（权重与代码**分别**核）② 权重来源与哈希（渠道+版本+SHA256）
> ③ 域适配声明（训练域 vs 勘探反射域）④ 推理确定性（同权重同输入两次推理是否逐字节相同）。

**取证纪律**：全部字段来自**官方 API 实测**（`gh api`），不凭印象填写；
网页搜索摘要不作为许可结论依据。

---

## 候选 1 · DeepDenoiser（AI4EPS）

| 项 | 实测值 |
| :--- | :--- |
| 仓库 | `https://github.com/AI4EPS/DeepDenoiser` |
| 论文 | Zhu, W., Mousavi, S. M., & Beroza, G. C. (2019). *Seismic Signal Denoising and Decomposition Using Deep Neural Networks*. **arXiv:1811.02695**（语料内 `10.48550/arXiv.1811.02695` 若无则记 arXiv ID） |
| 1 许可（**代码**） | **MIT** ✅ —— `gh api repos/AI4EPS/DeepDenoiser/license` → `spdx_id = MIT`，path `LICENSE`(1069 B)；正文首行 `MIT License`，`Copyright (c) 2021 Weiqiang Zhu` |
| 1 许可（**权重**） | **MIT（同仓随代码）** ✅ —— 权重位于**同一仓库内**（`model/190614-104802/`），无独立权重许可条款；MIT 覆盖仓库内软件与其副本 |
| 2 权重来源与哈希 | **渠道**：GitHub 官方仓库（无第三方镜像）；**版本锁定**：目录名 `190614-104802`（= 建立日期 2019-06-14 10:48:02） |
| 3 训练域 | **地震计 / 事件地震学**（地震台阵信号去噪，Zhu/Mousavi/Beroza） |
| 3 域适配 | ⚠️ **跨域**：训练域 = 地震计事件信号；本项目数据域 = **勘探反射**（可控源、道集、反射同相轴）。**须作为局限如实声明**，不得默许读者当作同域 |
| 4 推理确定性 | **未能实测** —— 依赖 **TensorFlow**（`requirements.txt` = tensorflow/matplotlib/scipy/pandas/tqdm；`env.yml` 要求 python=3.7），**本机未安装**，且 **TensorFlow 不在 `requirements.lock` 中** |

**权重目录实测清单**（`gh api repos/AI4EPS/DeepDenoiser/contents/model/190614-104802`）

| 类型 | 字节 | 文件 | git blob SHA（前 12） |
| :--- | ---: | :--- | :--- |
| file | 259 | `checkpoint` | `45b9e7c916ec` |
| file | 16548004 | `model_95.ckpt.data-00000-of-00001` | `c94e8bcce49b` |
| file | 8873 | `model_95.ckpt.index` | `910c38254904` |
| file | 2911765 | `model_95.ckpt.meta` | `ce60a0cdaf4a` |

> **SHA256 状态**：未计算（需下载权重文件后计算；**未下载**，理由见下）。
> GitHub API 提供的是 **git blob SHA-1**，**不是 SHA256**，两者不可混用。

### 候选 1 结论：**建议不纳入**（交签发方确认）

| 项 | 判定 |
| :--- | :--- |
| ① 许可 | **通过**（代码与权重均 MIT，官方 API 实证） |
| ② 权重来源与哈希 | **部分通过**（渠道与版本已锁定；**SHA256 未计算**） |
| ③ 域适配 | **通过但带显著局限**（跨域，须如实声明） |
| ④ 推理确定性 | **未测**（受阻于新增依赖） |

**阻断原因（如实）**：项 ④ 需安装 **TensorFlow**，而该包 **不在冻结的 `requirements.lock` 中**。
按红线「**不装未列出的包**」与四级权限模型，安装依赖属 **L2**，须**用户确认 + OTP**，
且新增依赖会**改变冻结环境**（`requirements.lock` 为冻结件之一）。
**本执行方未擅自安装，也未下载权重。**

**另需注意的连带影响**：若纳入 DL 成第 6 方法，则（a）矩阵由 270×5 变 **270×6**；
（b）单观测成本需加 DL 推理时间；（c）环境须新增 TensorFlow 并**更新 `requirements.lock`**（属冻结件变更 →
须**新版本 + 新 tag + 书面说明**）。

**建议**：**DL 槽位不纳入**，按裁定 I 的允许结果记录
「**经核验无许可合格且域合适的预训练模型**」——更准确地说：
**许可合格的候选存在（DeepDenoiser, MIT），但域为地震计域（跨域），且其推理确定性核验受阻于新增依赖**；
在**不新增依赖、不改冻结环境**的前提下，无**域合适**的预训练模型可纳入。
⇒ **DL 槽位留空，方法数 = 5**。**结论交签发方确认后**方可启动全矩阵。

> 若签发方希望纳入 DL：需（1）授权安装 TensorFlow（L2 + OTP）；
> （2）同意更新 `requirements.lock`（**新版本 + 新 tag + 书面说明**）；
> （3）在论文局限小节承担**跨域**声明。三项缺一不可。

---

## 语料内勘探域 DL 候选扫描（补充核验）

语料内「相关」且题名含 DL 信号者 **150** 条；其中题名同时含勘探/反射域词者 **8** 条。

| 年份 | DOI | 题名 |
| :--- | :--- | :--- |
| 2025 | `10.1093/jge/gxaf142` | Deep Learning for Efficient Prestack Seismic Internal Multiples Suppression with Global-Local Feature Fus |
| 2025 | `10.1038/s41598-025-87481-y` | MFIEN: multi-scale feature interactive enhancement network for seismic data denoising in desert areas |
| 2025 | `10.1190/geo2024-0472.1` | Deep learning-based denoising of pre-stack seismic angle gathers with application to time-lapse data |
| 2023 | `10.1007/s11200-022-0535-0` | Self-similarity convolution neural network for seismic noise suppression in desert environment |
| 2026 | `10.36922/jse026130057` | Self-supervised denoising of seismic common reflection point gathers with a learnable activation network |
| 2020 | `10.1109/TGRS.2019.2947149` | Poststack Seismic Data Denoising Based on 3-D Convolutional Neural Network |
| 2019 | `10.1109/tgrs.2019.2938836` | Low-Frequency Desert Noise Intelligent Suppression in Seismic Data Based on Multiscale Geometric Analysis |
| 2023 | `10.1111/1365-2478.13443` | Attenuating free‐surface multiples and ghost reflection from seismic data using a trace‐by‐trace convolut |

**判定**：上表为**论文**，未检出**随论文发布的、许可合格的预训练权重**
（权重可得性需逐个仓库核验；在**不新增依赖**的前提下**无从运行**，故本批不做进一步下载）。
`docs/license-register.csv` 中另有一条**拖缆近偏移距恢复（含预训练模型）**候选
（`10.5281/zenodo.21325738`，CC BY 4.0，状态「未核验」），
其**权重许可须单独登记**；本批**未采用**。

**扫描边界（如实声明）**：本扫描限于**本仓语料**（`screening.csv`）与 DeepDenoiser 一类具名代表，
**不是**对外部预训练模型的穷尽调查；且**受「不新增依赖」约束**，
凡需新框架的候选**均无法在本环境实测推理确定性**。
