"""seismic-denoise-bench 基准代码包。

子包：
  * ``bench.data``    —— 合成模型正演、加噪、真值事件窗生成
  * ``bench.methods`` —— 各去噪方法的统一输入输出接口
  * ``bench.metrics`` —— ΔSNR / Lsig / CNA / 事件级与野外四项指标
  * ``bench.stats``   —— 配对置换检验、Holm 校正、分层自助置信区间
  * ``bench.fusion``  —— 时频加权融合与相干噪声鉴别模块
  * ``bench.field``   —— 野外无真值评估与泄漏代理 LP
"""

__version__ = "0.0.0"
