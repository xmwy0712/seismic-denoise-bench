"""收集守卫：保证 ``tests/`` 下每个 Python 文件都能被 pytest 默认模式收集。

设立理由（P0.3-Am1 裁定 3）
---------------------------
本仓库曾出现一次**假绿**：验收文件名为 ``metrics_acceptance.py``，
不匹配 pytest 默认收集模式 ``test_*.py``，导致权威入口 ``run_tests.ps1``
只跑了 ricker 的 17 项、**整个 metrics 验收一项未跑**，却仍报"全绿"。
这是一个**静默失效**——不是失败，而是没跑。本守卫即为封堵该缺陷类型。

规则
----
``tests/`` 目录下除 ``__init__.py`` 与 ``conftest.py`` 外，每个 ``*.py``
必须满足 pytest 默认模式（``test_*.py`` 或 ``*_test.py``），否则本测试失败。
"""

from __future__ import annotations

from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent

# pytest 默认 python_files = ["test_*.py", "*_test.py"]；此处显式复现该模式。
ALLOWED_EXCEPTIONS = {"__init__.py", "conftest.py"}


def _collectable_by_default(name: str) -> bool:
    return name.startswith("test_") and name.endswith(".py") or name.endswith("_test.py")


def test_every_test_file_matches_pytest_default_pattern() -> None:
    """``tests/`` 下每个 ``*.py`` 都必须能被默认模式收集，否则 fail。"""
    offenders = []
    for path in sorted(TESTS_DIR.glob("*.py")):
        if path.name in ALLOWED_EXCEPTIONS:
            continue
        if not _collectable_by_default(path.name):
            offenders.append(path.name)

    assert not offenders, (
        "以下文件不会被 pytest 默认模式收集（会造成静默漏测，即'假绿'）："
        f"{offenders}。请重命名为 test_<name>.py。"
    )


def test_tests_directory_is_non_empty_and_has_collectable_files() -> None:
    """守卫自身健全性：``tests/`` 至少应存在一个可收集的测试文件。"""
    collectable = [
        p.name
        for p in TESTS_DIR.glob("*.py")
        if p.name not in ALLOWED_EXCEPTIONS and _collectable_by_default(p.name)
    ]
    assert collectable, "tests/ 下不存在任何可被默认模式收集的测试文件，守卫失效"


def test_declared_python_files_matches_pytest_default() -> None:
    """``pyproject.toml`` 的 ``python_files`` 必须显式声明为默认模式。

    声明意图，防止将来 config 漂移（Am1 裁定 3 要求）。
    """
    pyproject = TESTS_DIR.parent / "pyproject.toml"
    assert pyproject.exists(), "未找到 pyproject.toml"

    text = pyproject.read_text(encoding="utf-8")
    assert "python_files" in text, (
        "pyproject.toml 未显式声明 python_files；应写明 python_files = [\"test_*.py\"] 以固化意图"
    )
    assert 'test_*.py' in text, "python_files 中应包含 test_*.py"
