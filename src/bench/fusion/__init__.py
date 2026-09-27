"""P3.2 融合包。

**硬约束**：本包**不得导入** ``bench.methods``（方法实现）或 ``bench.data.synthetic``（真值生成器）；
公开接口 ``fuse(y_i, y_j, params)`` **不含真值形参**。
由 ``tests/test_fusion_independence.py`` 的 AST 级守卫机械核验（含反证）。
"""

from .fusion import fuse

__all__ = ["fuse"]
