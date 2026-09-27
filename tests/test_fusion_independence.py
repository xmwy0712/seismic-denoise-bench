"""P3.2 阶段 2 守卫：融合模块的 **AST 级独立性 + 禁真值**。

守卫对象：``src/bench/fusion/``（全部 ``*.py``）

**硬约束**（`configs/fusion-rules.yaml` / `preregistration.md` §0.1）
  1. 公开接口签名 ``fuse(y_i, y_j, params)`` —— **禁** ``clean`` / ``s`` / ``mask`` / ``truth`` 形参；
  2. 模块**不得导入** ``bench.methods``（方法实现）或 ``bench.data.synthetic``（**真值生成器**）。

守卫设计遵循**常设规则 14**：AST 级扫描（比行扫描更严）· 脚本入库 · **每项自带反证**。
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "src" / "bench" / "fusion"
IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+")

FORBIDDEN_MODULES = ("bench.methods", "bench.data.synthetic")
FORBIDDEN_PARAMS = ("clean", "s", "mask", "truth")


def _py_files() -> list[Path]:
    return sorted(p for p in PKG.glob("*.py"))


def _imported_modules(p: Path) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            out.update(al.name for al in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
    return out


def _func_params(p: Path, fname: str) -> list[str]:
    for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
        if isinstance(node, ast.FunctionDef) and node.name == fname:
            a = node.args
            return [x.arg for x in (*a.posonlyargs, *a.args, *a.kwonlyargs)]
    raise AssertionError(f"{p.name} 未找到函数 {fname}")


def _check_imports(p: Path) -> list[str]:
    return [m for m in _imported_modules(p)
            if any(m == f or m.startswith(f + ".") for f in FORBIDDEN_MODULES)]


# ────────────────────────────────────────── 1 禁导入
@pytest.mark.parametrize("path", _py_files(), ids=lambda p: p.name)
def test_fusion_package_does_not_import_methods_or_truth_generator(path: Path) -> None:
    """**核心守卫**：不得导入 `bench.methods` 或 `bench.data.synthetic`（AST 级）。"""
    bad = _check_imports(path)
    assert not bad, f"{path.name} 导入了禁止模块：{bad}"


# ────────────────────────────────────────── 2 禁真值形参
def test_fuse_signature_has_no_ground_truth_params() -> None:
    """**核心守卫**：`fuse` 签名不得出现 clean / s / mask / truth。"""
    names = _func_params(PKG / "fusion.py", "fuse")
    bad = [n for n in names if n in FORBIDDEN_PARAMS]
    assert not bad, f"fuse 含真值形参：{bad}"
    assert names[:3] == ["y_i", "y_j", "params"], f"fuse 签名须为 (y_i, y_j, params)，实测 {names}"


def test_no_ground_truth_params_anywhere_in_package() -> None:
    """更严：包内**任何**函数的形参都不得直接为真值名。"""
    offenders: list[str] = []
    for p in _py_files():
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(node, ast.FunctionDef):
                a = node.args
                for x in (*a.posonlyargs, *a.args, *a.kwonlyargs):
                    if x.arg in FORBIDDEN_PARAMS:
                        offenders.append(f"{p.name}:{node.name}({x.arg})")
    assert not offenders, f"包内出现真值形参：{offenders}"


def test_params_whitelist_allows_x_and_forbids_truth() -> None:
    """`params` 白名单：允许 `x`（共享含噪输入、非真值）；禁止真值键。"""
    import yaml
    d = yaml.safe_load((REPO / "configs" / "fusion-rules.yaml").read_text(encoding="utf-8"))
    allowed = " ".join(d["hard_constraint_no_ground_truth"]["allowed_in_params"])
    assert "x" in allowed, "白名单须显式允许 x"
    assert "非真值" in allowed, "白名单须声明 x 非真值"
    forb = d["hard_constraint_no_ground_truth"]["forbidden_params"]
    for f in FORBIDDEN_PARAMS:
        assert f in forb, f"冻结件应禁止 {f}"


# ────────────────────────────────────────── 3 反证（规则 14 第 3 条）
def test_guard_detects_injected_forbidden_import_counterproof() -> None:
    """**反证**：构造含禁止导入的源码，AST 守卫必须检出。"""
    src = "from bench.methods import METHODS\nimport bench.data.synthetic as S\n"
    found: set[str] = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            found.update(al.name for al in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    bad = [m for m in found if any(m.startswith(f) for f in FORBIDDEN_MODULES)]
    assert set(bad) == set(FORBIDDEN_MODULES), f"反证失败：{bad}"


def test_guard_detects_injected_ground_truth_param_counterproof() -> None:
    """**反证**：构造含真值形参的签名，守卫必须检出。"""
    src = "def fuse(y_i, y_j, params, clean=None):\n    return y_i\n"
    names: list[str] = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.FunctionDef) and node.name == "fuse":
            a = node.args
            names = [x.arg for x in (*a.posonlyargs, *a.args, *a.kwonlyargs)]
    assert [n for n in names if n in FORBIDDEN_PARAMS] == ["clean"], "反证失败"


def test_fulltext_scan_would_false_positive_counterproof() -> None:
    """**反证**：全文子串匹配必误报 —— 包文档字符串里**明确写着**禁止模块名。"""
    text = (PKG / "fusion.py").read_text(encoding="utf-8")
    assert "bench.methods" in text or "bench.data.synthetic" in text, (
        "前提失效：docstring 已不含禁止模块名，请复核本反证")
    assert not any("bench.methods" in ln or "bench.data.synthetic" in ln
                   for p in _py_files() for ln in p.read_text(encoding="utf-8").splitlines()
                   if IMPORT_RE.match(ln)), "import 行口径下不应命中"


def test_scan_is_restricted_to_import_lines() -> None:
    """**常设规则**：import 行扫描口径（固定）。"""
    assert IMPORT_RE.match("import numpy as np")
    assert not IMPORT_RE.match("# import bench.methods")
    assert not IMPORT_RE.match("x = 'bench.data.synthetic'")


# ────────────────────────────────────────── 4 行为冒烟
def test_fuse_runs_and_is_finite_and_deterministic() -> None:
    """最小冒烟：形状保持、全有限、两次逐字节相同、含退化规则。"""
    import hashlib
    import numpy as np
    sys.path.insert(0, str(REPO / "src"))
    from bench.fusion import fuse
    rng = np.random.default_rng(7)
    yi = rng.standard_normal((128, 16))
    yj = yi * 0.9 + rng.standard_normal((128, 16)) * 0.2
    x = (yi + yj) / 2.0
    o1 = fuse(yi, yj, {"n_t": 13, "gamma": 0.5, "x": x})
    o2 = fuse(yi, yj, {"n_t": 13, "gamma": 0.5, "x": x})
    assert o1.shape == yi.shape
    assert np.all(np.isfinite(o1))
    assert hashlib.sha256(o1.tobytes()).digest() == hashlib.sha256(o2.tobytes()).digest()
    z = np.zeros((128, 16))
    assert np.allclose(fuse(z, z, {"n_t": 13, "gamma": 0.5, "x": z}), 0.0)


def test_fuse_records_b_degradation_when_x_missing() -> None:
    """条件 2：`x` 缺失 ⇒ `b` 未启用（供 metrics.csv 标注）。"""
    import numpy as np
    sys.path.insert(0, str(REPO / "src"))
    from bench.fusion import fuse
    rng = np.random.default_rng(3)
    yi = rng.standard_normal((128, 16))
    yj = rng.standard_normal((128, 16))
    fuse(yi, yj, {"n_t": 13, "gamma": 0.5, "x": yi})
    assert fuse.last_b_enabled is True
    fuse(yi, yj, {"n_t": 13, "gamma": 0.5})
    assert fuse.last_b_enabled is False
