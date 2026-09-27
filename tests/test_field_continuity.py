"""P4 守卫：野外连续性模块的独立性（`frozen-v2.item_11` 与 `item_20` 义务）。

**硬约束**（协议第 44 行 + frozen item_11）：
「LP 与连续性采用**独立结构张量实现**，禁止与融合局部相干度**共享代码和参数**」
⇒ `src/bench/field/continuity.py` **不得导入** `bench.fusion`（也不得导入 `bench.methods`）。

守卫遵循**常设规则 14**：AST 级扫描 · 脚本入库 · **自带反证**。
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MOD = REPO / "src" / "bench" / "field" / "continuity.py"
IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+")
FORBIDDEN = ("bench.fusion", "bench.methods")


def _mods(p: Path) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
    return out


def test_continuity_does_not_share_code_with_fusion() -> None:
    """**核心守卫**：连续性模块不得导入 `bench.fusion`（不得与融合共享代码/参数）。"""
    bad = [m for m in _mods(MOD) if m.startswith(FORBIDDEN)]
    assert not bad, f"continuity.py 导入了禁止项：{bad}"


def test_continuity_uses_dip_guided_not_zero_lag() -> None:
    """**口径守卫**：实现须含局部倾角（`local_dip`），且**不**只用零延迟相关。

    item_20 的教训是「沿道轴零延迟相关」不表达几何质量；
    本模块须为**倾角对齐**口径。
    """
    src = MOD.read_text(encoding="utf-8")
    assert "def local_dip" in src, "须提供 local_dip（结构张量倾角）"
    assert "shift_trace" in src or "_shift_trace" in src, "须含倾角对齐重采样"
    # 反证：确保不是"零延迟"实现（若只有 np.dot 原始道、无对齐，则口径错误）
    assert "np.roll" not in src, "不得用 np.roll 冒充倾角对齐（那是零延迟的变体）"


def test_guard_detects_injected_import_counterproof() -> None:
    """**反证**：构造含禁止导入的源码，AST 守卫必须检出。"""
    src = "from bench.fusion import fuse\nimport bench.methods\n"
    found: set[str] = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    bad = [m for m in found if m.startswith(FORBIDDEN)]
    assert set(bad) == set(FORBIDDEN), f"反证失败：{bad}"


def test_fulltext_scan_would_false_positive_counterproof() -> None:
    """**反证**：全文匹配必误报（文档里写着禁止项名称）。"""
    text = MOD.read_text(encoding="utf-8")
    assert "bench.fusion" in text, "前提失效：docstring 已不含禁止模块名"
    assert not any(IMPORT_RE.match(ln) and "bench.fusion" in ln
                   for ln in text.splitlines())


def test_scan_is_restricted_to_import_lines() -> None:
    """**常设规则**：import 行扫描口径（固定）。"""
    assert IMPORT_RE.match("import numpy as np")
    assert not IMPORT_RE.match("# import bench.fusion")
