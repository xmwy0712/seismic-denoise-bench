"""P3.1 独立性守卫：互补性模块不得导入融合或方法实现（规则 14 三条全用）。

守卫对象：``src/bench/analysis/complementarity.py``
**硬约束**（P3.1 第三节第 1 条）：**不得导入** ``bench.fusion`` / ``bench.methods`` ——
互补性度量只依赖**误差与真值**，不依赖任何方法实现或融合实现。

守卫设计遵循**常设规则 14**：
  1. 扫描口径限定 **import 行**（AST 级更严：只认 Import / ImportFrom 节点）；
  2. 扫描脚本**入库**（本文件即入库件）；
  3. 每项守卫**自带反证**。
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MOD = REPO / "src" / "bench" / "analysis" / "complementarity.py"
IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+")

FORBIDDEN = ("bench.fusion", "bench.methods", "bench.analysis")   # 自身亦不得自导入


def _import_lines(p: Path) -> list[str]:
    return [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines()
            if IMPORT_RE.match(ln)]


def _imported_modules(p: Path) -> set[str]:
    """AST 级：取全部 import / from-import 的模块名（比行扫描更严，防换行续写规避）。"""
    out: set[str] = set()
    tree = ast.parse(p.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for al in node.names:
                out.add(al.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                out.add(node.module)
    return out


# ────────────────────────────────────────────── 1 主体守卫
def test_complementarity_does_not_import_fusion_or_methods() -> None:
    """**核心守卫**：不得导入 `bench.fusion` / `bench.methods`（AST 级，模块名精确比对）。"""
    mods = _imported_modules(MOD)
    bad = [m for m in mods
           if m == "bench.fusion" or m.startswith("bench.fusion.")
           or m == "bench.methods" or m.startswith("bench.methods.")]
    assert not bad, f"互补性模块导入了禁止项：{bad}"


def test_complementarity_does_not_import_itself() -> None:
    """不得自导入 `bench.analysis`（防经包 `__init__` 形成回路）。"""
    mods = _imported_modules(MOD)
    bad = [m for m in mods if m == "bench.analysis" or m.startswith("bench.analysis.")]
    assert not bad, f"互补性模块自导入了：{bad}"


def test_analysis_package_init_does_not_import_methods_or_fusion() -> None:
    """包 `__init__.py` 同样不得静态导入方法与融合（防传递依赖）。"""
    init = MOD.parent / "__init__.py"
    if not init.exists():
        pytest.skip("analysis/__init__.py 不存在")
    mods = _imported_modules(init)
    bad = [m for m in mods
           if m.startswith(("bench.fusion", "bench.methods"))]
    assert not bad, f"analysis/__init__.py 导入了禁止项：{bad}"


def test_complementarity_imports_are_only_allowed_roots() -> None:
    """白名单守卫：允许的 bench.* 根只有 `bench.data` / `bench.metrics`。"""
    mods = _imported_modules(MOD)
    bench = [m for m in mods if m.startswith("bench.")]
    allowed = ("bench.data", "bench.metrics")
    bad = [m for m in bench if not m.startswith(allowed)]
    assert not bad, f"出现白名单外的 bench 导入：{bad}"


# ────────────────────────────────────────────── 2 反证（规则 14 第 3 条）
def test_fulltext_scan_would_false_positive_counterproof() -> None:
    """**反证**：全文子串匹配必然误报 —— 本模块文档字符串里**明确写着**禁止项的名称。

    这正是规则 14 第 1 条要防的：交付物常在注释/文档中说明「不得导入 X」。
    """
    text = MOD.read_text(encoding="utf-8")
    assert "bench.fusion" in text and "bench.methods" in text, (
        "前提失效：文档字符串里已不再出现禁止项名称，请复核本反证")
    # 而 import 行口径下**无**禁止项
    assert not any("bench.fusion" in ln or "bench.methods" in ln for ln in _import_lines(MOD))


def test_guard_detects_injected_forbidden_import_counterproof() -> None:
    """**反证**：构造一段含禁止导入的源码，AST 守卫必须能检出（证明守卫非恒真）。"""
    src = "from bench.methods import METHODS\nimport bench.fusion\n"
    tree = ast.parse(src)
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(al.name for al in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    bad = [m for m in found if m.startswith(("bench.methods", "bench.fusion"))]
    assert bad == ["bench.methods", "bench.fusion"] or set(bad) == {"bench.methods", "bench.fusion"}


def test_scan_is_restricted_to_import_lines() -> None:
    """**常设规则**：import 行扫描口径（固定）。"""
    assert IMPORT_RE.match("import numpy as np")
    assert IMPORT_RE.match("from __future__ import annotations")
    assert not IMPORT_RE.match("# from bench.methods import METHODS")
    assert not IMPORT_RE.match("x = 'bench.fusion'")
