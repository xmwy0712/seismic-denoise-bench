# 机制对比表（P1.4）

> **字段来源声明**：本表全部字段取自 `screening.csv` 的**题录元数据**（题名/年份/期刊/DOI）。
> **未逐篇读全文**；因此只给出**可由标题判定的方法族归类**，不给未核实的定量指标。
> 协议禁止「以 LLM 摘要替代原文核实」，故本表**不含**任何未亲自读到的数值。

统计基数：相关条目 548 条（台账总 1154 条）。

## 1. 方法族分布

| 方法族 | 条目数 |
| :--- | ---: |
| 深度学习 / 神经网络 | 165 |
| 稀疏 / 低秩 / 矩阵分解 | 61 |
| 多尺度变换（小波/曲波/剪切波/contourlet） | 34 |
| 模态分解（EMD/VMD/SSA） | 15 |
| 中值/均值/预测滤波（经典） | 7 |
| 局部相似度 / 正交化 / 结构约束 | 41 |
| 物理/偏微分方程约束（扩散/反应扩散） | 15 |
| 其他 / 未归类 | 210 |

## 2. 各方法族代表条目（按被引/年份）

### 深度学习 / 神经网络（165 条）

| 年份 | DOI | 题名 |
| :--- | :--- | :--- |
| 2026 | `10.1190/tle-2025-1046` | Automated CO2 plume detection from time-lapse seismic  using local orthogonalization and deep learning |
| 2026 | `10.21203/rs.3.rs-8012706/v1` | SET-CNN: Stacked Ensemble of CNNs for Robust Image Embedding and Similarity Retrieval |
| 2026 | `10.1109/LGRS.2026.3676613` | Robust Seismic Denoising Framework: A GAN-Based Approach With Multiscale Feature Fusion and Signal Preservatio |
| 2026 | `10.1007/s11600-026-01799-3` | MSBE-UNet: A deep learning denoising method for effective seismic noise suppression |
| 2026 | `10.1007/s11600-026-01813-8` | SFA-PromptIR: a step-by-step feature fusion attentional network for DAS VSP background noise suppression |
| 2026 | `10.1111/1365-2478.70147` | Seismic Random Noise Attenuation via Channel Attention‐Weighted Unsupervised Deep Learning |
| 2026 | `10.2118/233244-ms` | Assessing Geological Fidelity of GAN-Generated Seismic Images for CO2 Monitoring at Sleipner |
| 2026 | `10.1016/j.aiig.2026.100219` | An open benchmark dataset of synthetic seismic data and real swell noise for evaluating deep learning denoisin |
| … | … | 其余 157 条见 `screening.csv`（track=`mechanism`） |

### 稀疏 / 低秩 / 矩阵分解（61 条）

| 年份 | DOI | 题名 |
| :--- | :--- | :--- |
| 2026 | `10.36922/jse025440098` | Random noise suppression in node seismometer signals using improved complete ensemble empirical mode decomposi |
| 2026 | `10.1088/2631-8695/ae470e` | A matching pursuit variational mode decomposition method for microseismic signal denoising |
| 2026 | `10.36922/jse026230102` | Non-local weighted structure tensor total variation model for seismic data denoising |
| 2026 | `10.1109/TGRS.2025.3646696` | Seismic Denoising Based on Convolutional Dictionary Learning With ADMM |
| 2026 | `10.1109/ACCESS.2026.3672906` | Quantum-Accelerated Dictionary Learning Based on HHL and QSVT for Seismic Data Denoising |
| 2026 | `10.1109/EICCT69950.2026.11564570` | Seismic Random Noise Suppression using Variational Mode Decomposition and Quantum Chaotic Fruit Fly Optimizati |
| 2025 | `10.1109/TGRS.2025.3540208` | Seismic Denoising Based on Dictionary Learning With Double Regularization for Random and Erratic Noise Attenua |
| 2025 | `10.1109/LGRS.2025.3529463` | Tensor Decomposition Dictionary Learning With Low-Rank Regularization for Seismic Data Denoising |
| … | … | 其余 53 条见 `screening.csv`（track=`mechanism`） |

### 多尺度变换（小波/曲波/剪切波/contourlet）（34 条）

| 年份 | DOI | 题名 |
| :--- | :--- | :--- |
| 2026 | `10.36922/jse026270125` | Pre-stack seismic lithology prediction constrained by multi-scale structural similarity and logarithmic opinio |
| 2026 | `10.1109/GAIIS69281.2026.11519217` | Robust Image Denoising: A Method Based on Multi-Scale Local Adaptive Hybrid Iterative Bilateral Filtering |
| 2025 | `10.1109/CEI66465.2025.11398537` | Research on Frequency-Division Denoising Method for Seismic Data Based on Intelligent Adaptive Wavelet Transfo |
| 2025 | `10.22564/brjg.v43i1.2336` | Improving Seismic First Arrival Picking in Noisy Data: A Wavelet-Based Denoising Technique |
| 2025 | `10.1007/s11770-025-1289-6` | Improved PSO-VMD seismic signal denoising method combined with modified wavelet transform |
| 2024 | `10.1145/3711129.3711377` | Rolling Bearing Fault Diagnosis Based on CEEMDAN-IWT Denoising and Multiscale Feature Fusion |
| 2024 | `10.1111/1365-2478.13574` | Simultaneous seismic data de‐aliasing and denoising with a fast adaptive method based on hybrid wavelet transf |
| 2024 | `10.1080/10916466.2024.2380731` | Seismic data denoising using the 3D curvelet transform method |
| … | … | 其余 26 条见 `screening.csv`（track=`mechanism`） |

### 模态分解（EMD/VMD/SSA）（15 条）

| 年份 | DOI | 题名 |
| :--- | :--- | :--- |
| 2026 | `10.1108/ijsi-12-2025-0315` | An optimised method for denoising wheel flat dynamic stress signals based on multi-sensor fusion and ICEEMDAN |
| 2026 | `10.1109/ICCCS69761.2026.11613386` | Hierarchical Spatiotemporal Feature Fusion for Robust Anomaly Detection in Distributed Acoustic Sensing with a |
| 2026 | `10.5194/isprs-archives-xlix-b1-2026-217-2026` | Denoising microwave interferometry data for high-Rise buildings with CEEMDAN energy-Correlation dual Criteria |
| 2026 | `10.1109/TIM.2026.3654724` | IBKA-CEEMDAN-SPMF Algorithm for Denoising Electromagnetic Radiation in Loaded Coal–Rock |
| 2026 | `10.1109/AEEES69423.2026.11556665` | Precise Identification and Localization of Cable Fault Traveling Wave Heads Based on the Fusion of EEMD and TE |
| 2026 | `10.12677/csa.2026.168277` | Joint Entropy-Driven Improved Sparrow Search Optimized VMD for DAS Signal Denoising |
| 2025 | `10.3390/geosciences15110409` | Research on High-Density Discrete Seismic Signal Denoising Processing Method Based on the SFOA-VMD Algorithm |
| 2024 | `10.1109/ICICSP62589.2024.10809097` | An Improved EMD Denoising Framework for Underwater Distributed Acoustic Sensing Signals by Exploring Permutati |
| … | … | 其余 7 条见 `screening.csv`（track=`mechanism`） |

### 中值/均值/预测滤波（经典）（7 条）

| 年份 | DOI | 题名 |
| :--- | :--- | :--- |
| 2024 | `10.3997/2214-4609.2024101661` | Ensemble Model Predictive Seismic Streamer Steering |
| 2021 | `10.3997/2214-4609.202011763` | Elastic Seismic Inversion Using an Iterative Ensemble Kalman Filter |
| 2017 | `10.1109/LGRS.2017.2697942` | Simultaneous Denoising and Interpolation of 3-D Seismic Data via Damped Data-Driven Optimal Singular Value Shr |
| 2012 | `10.1190/geo2011-0117.1` | Random noise attenuation using f-x regularized nonstationary autoregression |
| 2011 | `10.1007/s11770-010-0244-2` | Seismic noise attenuation using nonstationary polynomial fitting |
| 2007 | `10.3997/2214-4609.201403077` | Ensemble Kalman Filter Adjusted to Time-Lapse Seismic Data |
| 1995 | `10.1190/1.1443920` | Lateral prediction for noise attenuation by t-x and f-x techniques |

### 局部相似度 / 正交化 / 结构约束（41 条）

| 年份 | DOI | 题名 |
| :--- | :--- | :--- |
| 2026 | `10.1111/1365-2478.70164` | Unsupervised Local Primary‐and‐Multiple Orthogonalization Learning for Seismic Multiple Leakage Estimation |
| 2026 | `10.1190/geo2024-0365.1` | Local similarity-integrated self-learning model and its application to suppress seismic migration artifacts |
| 2025 | `10.1190/geo2024-0055.1` | Improving fluid-induced time-lapse seismic monitoring using local orthogonalization |
| 2025 | `10.21203/rs.3.rs-7468614/v1` | Seismic energy dissipation finite element analysis and damage quantitative evaluation of reinforced concrete f |
| 2025 | `10.1109/TGRS.2025.3527998` | Robust Bidirectional Q-Compensated Denoising for Seismic Data With Adaptive Structural Regularization |
| 2024 | `10.1115/pvp2024-123075` | Benchmark Analysis on Pipe Support Structures for Establishing Inelastic Seismic Design |
| 2024 | `10.48550/arXiv.2407.04461` | VCD-Texture: Variance Alignment based 3D-2D Co-Denoising for Text-Guided Texturing |
| 2024 | `` | Adaptive Graded Denoising of Seismic Data Based on Noise Estimation and Local Similarity |
| … | … | 其余 33 条见 `screening.csv`（track=`mechanism`） |

### 物理/偏微分方程约束（扩散/反应扩散）（15 条）

| 年份 | DOI | 题名 |
| :--- | :--- | :--- |
| 2026 | `10.48550/arXiv.2607.03349` | PedestrianDiffusion: Multimodal Generative Denoising and Dense State Estimation for Inertial Navigation |
| 2026 | `10.1109/TASE.2026.3730792` | Multi-Source Data State Estimation of Power System Based on Denoising Diffusion Implicit Model With Data Augme |
| 2026 | `10.1109/JOE.2025.3635984` | UIE-DDPM: Underwater Image Enhancement Based on the Integration of Physical Model and Conditional Denoising Di |
| 2026 | `10.5194/egusphere-egu26-10528` | Discriminator-Augmented Denoising Diffusion Probabilistic Models for Seismic Data |
| 2025 | `10.1109/JBHI.2026.3732677` | TFCDiff: Robust ECG Denoising via Time-Frequency Complementary Diffusion. |
| 2025 | `10.1109/SmartGridComm65349.2025.11204605` | Synthetic Power Flow Data Generation Using Physics-Informed Denoising Diffusion Probabilistic Models |
| 2025 | `10.1109/BigData66926.2025.11402216` | DPT-DDPM: A Denoising Diffusion Probabilistic Model for Tabular Data With Differential Privacy Enhancement |
| 2025 | `10.1109/ICCV51701.2025.01307` | Generic Event Boundary Detection via Denoising Diffusion |
| … | … | 其余 7 条见 `screening.csv`（track=`benchmark`） |

### 其他 / 未归类（210 条）

| 年份 | DOI | 题名 |
| :--- | :--- | :--- |
| 2026 | `10.2139/ssrn.6203338` | Ensemble Learning-Based Seismic Hazard Forecasting for Safety Enhancement in Underground Coal Mine |
| 2026 | `10.3997/2214-4609.202638052` | Bayesian Elastic Seismic Inversion Using Ensemble with Multiple Data Assimilation Applied to the Santos Basin  |
| 2026 | `10.1016/j.dsp.2026.105936` | Blind seismic denoising via ensemble iterative data refinement with adaptive spectral-spatial feature fusion |
| 2026 | `10.1088/2631-8695/ae7bbf` | An SNR-stacking ensemble method for multi-model fusion noise reduction in GAFDEM signals |
| 2026 | `10.1109/ACCESS.2026.3721347` | A Partially Validated Probabilistic Framework for Urban Seismic Damage Prediction With Scenario Ensembles and  |
| 2026 | `10.1016/j.petsci.2026.06.021` | A fluidic hammer as a high-fidelity seismic-while-drilling source: A direct, quantitative comparison with conv |
| 2026 | `10.1109/iclo69056.2026.11625057` | The Impact of Helically-Wound Cable on Signal Fidelity using DAS for Seismic Exploration |
| 2026 | `10.5194/egusphere-gc14-fibreoptic-110` | Quantitative comparison of DAS and point seismic sensors at Svelvik CO2 Field Lab |
| … | … | 其余 202 条见 `screening.csv`（track=`mechanism`） |

