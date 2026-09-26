"""P2.1 方法集（去噪方法实现）。

**本包不导入任何具体方法模块** —— 以避免方法间形成传递依赖。
加载请用 :func:`load_method`（按名动态导入），或直接经 ``importlib`` 按路径导入。

统一接口
--------
每个方法模块导出::

    run(noisy: np.ndarray, params: dict, rng: np.random.Generator) -> np.ndarray

另导出元信息：``METHOD_NAME`` / ``FAMILY`` / ``PARAMS_DEFAULT`` / ``DETERMINISTIC``。

确定性
------
**本项目方法集全部为确定性实现**：不使用 ``rng``、不建全局随机源。
``rng`` 仅为统一签名而保留（便于将来纳入随机方法）。
故「同配置同种子两次运行逐字节相同」由**构造保证**。
"""

from __future__ import annotations

import importlib
from typing import Any

__all__ = ["METHODS", "load_method"]

#: 已登记的方法名（与 configs/methods_registry.yaml 一一对应）
METHODS: tuple[str, ...] = (
    "fk_filter",
    "fx_deconv",
    "wavelet_threshold",
    "ssa_decomposition",
    "svd_lowrank",
)


def load_method(name: str) -> Any:
    """按名加载方法模块（动态导入，不在本文件产生静态导入边）。"""
    if name not in METHODS:
        raise KeyError(f"未登记的方法：{name!r}；已登记：{list(METHODS)}")
    return importlib.import_module(f"bench.methods.{name}")
