"""收集守卫：保证定义了测试的文件必被 pytest 收集，并防止辅助模块静默堆积。

规则（P0.4-Am1 裁定 1，替代 Am1 裁定 3 的过粗表述）
---------------------------------------------------
1. **真绿守卫（核心）**：``tests/`` 下任何**定义了顶层 ``def test_*`` 或 ``class Test*``**
   的 ``*.py``，**必须**命名为 ``test_*.py``，否则 fail。
   依据：假绿的根因是"定义了测试却不被收集"，此条直接针对该根因。
2. **清单守卫**：``tests/`` 下**不定义测试**的 ``*.py``，必须或为 ``conftest.py``，
   或登记在显式清单 ``tests/_auxiliary.tsv``（格式：`文件名<TAB>用途<TAB>被谁导入`）。
   **不使用代码内豁免名单**——豁免写在代码里会被逐步掏空；清单文件才是可审计、
   可 diff 的载体。

设立缘由（历史）
----------------
本仓库曾发生一次**假绿**：验收文件名为 ``metrics_acceptance.py``，
不匹配 pytest 默认收集模式，导致权威入口 ``run_tests.ps1`` 只跑了 ricker 的 17 项、
**整个 metrics 验收一项未跑**，却仍报"全绿"。这是**静默失效**——不是失败，而是没跑。
"""

from __future__ import annotations

import ast
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
AUXILIARY_MANIFEST = TESTS_DIR / "_auxiliary.tsv"


def _defines_tests(path: Path) -> bool:
    """判断文件是否定义了顶层 ``def test_*`` 或 ``class Test*``。

    非 ``.py`` 或不可读的文件返回 ``False``（该函数只回答"是否定义测试"）。
    """
    if path.suffix != ".py" or not path.is_file():
        return False
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return False
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_"):
                return True
        elif isinstance(node, ast.ClassDef):
            if node.name.startswith("Test"):
                return True
    return False


def _read_manifest() -> dict[str, list[str]]:
    """读取辅助模块清单；返回 {文件名: [字段...]}。忽略空行与 `#` 注释行。"""
    if not AUXILIARY_MANIFEST.exists():
        return {}
    entries: dict[str, list[str]] = {}
    for raw in AUXILIARY_MANIFEST.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        entries[fields[0].strip()] = fields
    return entries


def _test_files() -> list[Path]:
    return sorted(p for p in TESTS_DIR.glob("*.py"))


# ---------------------------------------------------------------------------
# 规则 1：真绿守卫
# ---------------------------------------------------------------------------
def test_files_defining_tests_must_be_named_test_star() -> None:
    """定义了测试的文件必须以 ``test_`` 开头，否则 fail（直击假绿根因）。"""
    offenders: list[str] = []
    for path in _test_files():
        if path.name.startswith("test_"):
            continue
        if _defines_tests(path):
            offenders.append(path.name)

    assert not offenders, (
        "以下文件定义了测试用例却不匹配 pytest 默认收集模式 "
        f"`test_*.py`，会被静默漏收（假绿）：{offenders}。请重命名。"
    )


# ---------------------------------------------------------------------------
# 规则 2：清单守卫
# ---------------------------------------------------------------------------
def test_non_test_files_are_registered_in_auxiliary_manifest() -> None:
    """不定义测试的文件必须是 ``conftest.py`` 或在 ``_auxiliary.tsv`` 中登记。"""
    registered = _read_manifest()
    offenders: list[str] = []

    for path in _test_files():
        if path.name.startswith("test_") or path.name == "conftest.py":
            continue
        if _defines_tests(path):
            # 归规则 1 管（已在上一测试中判失败），此处不重复报
            continue
        if path.name not in registered:
            offenders.append(path.name)

    assert not offenders, (
        "以下辅助模块未登记在 tests/_auxiliary.tsv 中（禁止代码内豁免名单）："
        f"{offenders}"
    )


def test_auxiliary_manifest_entries_exist_and_have_three_fields() -> None:
    """清单每行须为三字段（文件名 / 用途 / 被谁导入），且对应文件真实存在。"""
    for name, fields in _read_manifest().items():
        assert len(fields) >= 3, f"清单行 {name!r} 不足三字段（需 TAB 分隔）: {fields}"
        assert (TESTS_DIR / name).is_file(), f"清单登记了不存在的文件：{name}"


def test_auxiliary_manifest_has_no_stale_entries() -> None:
    """清单不得残留已不存在的文件记录（防静默堆积）。"""
    stale = [n for n in _read_manifest() if not (TESTS_DIR / n).is_file()]
    assert not stale, f"清单存在陈旧条目（文件已删除）：{stale}"


# ---------------------------------------------------------------------------
# 守卫自身健全性 + 配置意图固化
# ---------------------------------------------------------------------------
def test_guard_is_effective_on_synthetic_case() -> None:
    """守卫有效性自检：确认 ``_defines_tests`` 能识别测试定义。"""
    assert _defines_tests(TESTS_DIR / "test_naming_convention.py") is True
    assert _defines_tests(AUXILIARY_MANIFEST.parent / "_auxiliary.tsv") is False


def test_tests_directory_has_collectable_files() -> None:
    """守卫自身健全性：``tests/`` 至少应存在一个可收集的测试文件。"""
    collectable = [p.name for p in _test_files() if p.name.startswith("test_")]
    assert collectable, "tests/ 下不存在任何可被默认模式收集的测试文件，守卫失效"


def test_declared_python_files_matches_pytest_default() -> None:
    """``pyproject.toml`` 的 ``python_files`` 必须显式声明为默认模式（防 config 漂移）。"""
    pyproject = TESTS_DIR.parent / "pyproject.toml"
    assert pyproject.exists(), "未找到 pyproject.toml"

    text = pyproject.read_text(encoding="utf-8")
    assert "python_files" in text, (
        "pyproject.toml 未显式声明 python_files；应写明 python_files = [\"test_*.py\"] 以固化意图"
    )
    assert "test_*.py" in text, "python_files 中应包含 test_*.py"
