"""P2.1 方法集守卫：统一接口 + 方法间独立性 + 无隐式随机源。

守卫设计遵循**常设规则 14**：
  1. 扫描口径限定 import 行（或 AST），**禁止全文子串匹配**；
  2. 扫描脚本必须入库（本文件即入库件）；
  3. 每项守卫自带**反证**。
"""

from __future__ import annotations

import ast
import importlib
import inspect
import re
from pathlib import Path

import numpy as np
import pytest

from bench.methods import METHODS, load_method

METHODS_DIR = Path(__file__).resolve().parents[1] / "src" / "bench" / "methods"
IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+")


def _method_files() -> list[Path]:
    return [METHODS_DIR / f"{n}.py" for n in METHODS]


def _import_lines(path: Path) -> list[str]:
    """只取 import/from 行（常设规则 14 第 1 条）。"""
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()
            if IMPORT_RE.match(ln)]


# ------------------------------------------------------------------ 1 统一接口
@pytest.mark.parametrize("name", METHODS)
def test_method_exposes_uniform_interface(name: str) -> None:
    """每方法导出统一接口与元信息。"""
    m = load_method(name)
    for attr in ("run", "METHOD_NAME", "FAMILY", "PARAMS_DEFAULT", "DETERMINISTIC"):
        assert hasattr(m, attr), f"{name} 缺少 {attr}"
    assert m.METHOD_NAME == name
    sig = inspect.signature(m.run)
    assert list(sig.parameters) == ["noisy", "params", "rng"], (
        f"{name}.run 签名须为 (noisy, params, rng)，实测 {list(sig.parameters)}")
    assert isinstance(m.PARAMS_DEFAULT, dict)
    assert isinstance(m.DETERMINISTIC, bool)


# ------------------------------------------------------------------ 2 独立性（import 行）
@pytest.mark.parametrize("name", METHODS)
def test_method_does_not_import_other_methods(name: str) -> None:
    """任何方法模块不得导入其他方法模块（import 行扫描）。"""
    others = {n for n in METHODS if n != name}
    for path in [_method_files()[[x for x in METHODS].index(name)]]:
        for line in _import_lines(path):
            for other in others:
                assert other not in line, (
                    f"{path.name} 的 import 行导入了其他方法 {other!r}：{line}")
            assert "bench.methods" not in line, (
                f"{path.name} 不得导入 bench.methods 包（会形成传递依赖）：{line}")


# ------------------------------------------------------------------ 3 包级守卫
def test_methods_package_does_not_statically_import_methods() -> None:
    """``bench/methods/__init__.py`` 不得静态导入任何具体方法模块。"""
    init = METHODS_DIR / "__init__.py"
    for line in _import_lines(init):
        for name in METHODS:
            assert f"bench.methods.{name}" not in line, f"__init__ 静态导入了 {name}：{line}"


# ------------------------------------------------------------------ 4 无隐式随机源（AST）
@pytest.mark.parametrize("name", METHODS)
def test_method_has_no_implicit_random_source(name: str) -> None:
    """方法内部不得建全局随机源（AST 扫描 ``np.random.*`` 调用）。

    仅扫**调用表达式**，故签名/文档中的 ``np.random.Generator`` 注解不会误报。
    """
    path = METHOD_DIR = METHODS_DIR / f"{name}.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            parts, cur = [], node.func
            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name):
                parts.append(cur.id)
            chain = ".".join(reversed(parts))
            if chain.startswith("np.random.") or chain.startswith("numpy.random."):
                offenders.append(chain)
    assert not offenders, f"{name} 内部建了随机源：{offenders}"


# ------------------------------------------------------------------ 5 反证（规则 14 第 3 条）
def test_fulltext_scan_would_false_positive() -> None:
    """**反证**：全文子串匹配会把模块 docstring 里的说明判成违规，故必须限定 import 行/AST。

    各方法模块的文档字符串中**明确写着**「不使用 rng」等说明，
    且类型注解含 ``np.random.Generator``；全文匹配必然自证其罪。
    """
    text = (METHODS_DIR / "fk_filter.py").read_text(encoding="utf-8")
    assert "np.random.Generator" in text, "前提失效：注解已不存在，请复核本反证"
    # 全文匹配会命中注解 ⇒ 该口径不可用（这正是规则 14 第 1 条要防的）
    assert "np.random" in text
    # 而 import 行口径下**无** np.random 相关导入
    assert not any("random" in ln for ln in _import_lines(METHODS_DIR / "fk_filter.py"))


def test_scan_is_restricted_to_import_lines() -> None:
    """**常设规则**：扫描只认 import/from 行（固定该口径）。"""
    assert IMPORT_RE.match("import numpy as np")
    assert IMPORT_RE.match("  from __future__ import annotations")
    assert not IMPORT_RE.match("# import numpy")
    assert not IMPORT_RE.match("x = 'import numpy'")


# ------------------------------------------------------------------ 6 实际运行不变性
@pytest.mark.parametrize("name", METHODS)
def test_method_smoke_is_finite_and_shape_preserving(name: str) -> None:
    """冻结尺寸下的最小冒烟：形状一致、全有限、两次运行逐字节相同。"""
    m = load_method(name)
    rng_data = np.random.default_rng(20260926)
    noisy = rng_data.standard_normal((512, 64)) * 0.5
    y1 = m.run(noisy, dict(m.PARAMS_DEFAULT), np.random.default_rng(1))
    y2 = m.run(noisy, dict(m.PARAMS_DEFAULT), np.random.default_rng(1))
    assert y1.shape == noisy.shape
    assert np.all(np.isfinite(y1))
    assert y2.tobytes() == y1.tobytes(), f"{name} 非确定性"


def test_all_methods_reject_nonfinite_input() -> None:
    """每方法对含 NaN 的输入须抛 ValueError（不静默产出坏结果）。"""
    bad = np.full((64, 8), np.nan)
    for name in METHODS:
        m = load_method(name)
        with pytest.raises(ValueError):
            m.run(bad, dict(m.PARAMS_DEFAULT), np.random.default_rng(0))
