"""P1.3 面板选定模块的机械守卫（R-N2）。

三项守卫：
  1. **import 行守卫**：``src/bench/field/panel_selection.py`` 的 **import/from 行**
     不得含 ``methods`` / ``fusion`` / ``coherence``。
     → 扫描**限定 import 行**，不得全文匹配（本项目已两次因全文匹配而误报自身注释）。
  2. **常设规则守卫**：断言扫描实现只接受 import 行（用一个含"敏感词"的样例字符串验证，
     该样例出现在**注释**中时必须**不**触发）。
  3. **重放一致性检查**：若原始 `.sgy` 数据存在，则重放选定并与冻结 top-3 比对
     （数据不入 git，缺失时 skip，但**必须**给出跳过原因）。

常设规则（由本批确立，写入 ``docs/quarantine-register.md``）
------------------------------------------------------------
* **扫描必须限定 import 行**：任何"是否导入某模块"的机械检查，一律只匹配
  ``^\\s*(import|from)\\s+`` 开头的行；**禁止**对全文做子串匹配。
* **扫描脚本必须入库**：用于核验交付物的扫描/守卫脚本本身要进仓库，
  否则核验不可独立重放。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
FIELD_PKG = REPO / "src" / "bench" / "field"
FORBIDDEN = ("methods", "fusion", "coherence")

IMPORT_LINE = re.compile(r"^\s*(import|from)\s+")


def import_lines(path: Path) -> list[str]:
    """返回文件中所有 **import / from 行**（常设规则的唯一合法扫描口径）。"""
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()
            if IMPORT_LINE.match(ln)]


# ---------------------------------------------------------------------------
# 1) import 行守卫
# ---------------------------------------------------------------------------
def test_panel_selection_imports_are_clean() -> None:
    """面板选定模块的 import 行不得含 methods / fusion / coherence。"""
    target = FIELD_PKG / "panel_selection.py"
    assert target.exists(), f"缺少 R-N2 要求的入库脚本：{target}"
    offenders = [ln for ln in import_lines(target) if any(k in ln for k in FORBIDDEN)]
    assert not offenders, f"面板选定模块导入了被评对象相关模块：{offenders}"


def test_field_package_imports_are_clean() -> None:
    """整个 ``src/bench/field/`` 包同样不得导入被评对象相关模块。"""
    offenders: list[str] = []
    for f in sorted(FIELD_PKG.glob("*.py")):
        for ln in import_lines(f):
            if any(k in ln for k in FORBIDDEN):
                offenders.append(f"{f.name}: {ln}")
    assert not offenders, f"field 包导入了被评对象相关模块：{offenders}"


# ---------------------------------------------------------------------------
# 2) 常设规则守卫（防"全文匹配"复发）
# ---------------------------------------------------------------------------
def test_scan_is_restricted_to_import_lines() -> None:
    """常设规则：扫描**只认 import 行**。

    用一个"敏感词只出现在注释中"的真实样例验证：
    本文件自身在注释/docstring 里写了 ``methods`` / ``fusion`` / ``coherence``（为说明规则），
    但按 import 行口径扫描应得到**零命中** —— 这正是全文匹配会误报的场景。
    """
    hits = [ln for ln in import_lines(Path(__file__)) if any(k in ln for k in FORBIDDEN)]
    assert hits == [], f"扫描误把非 import 行计入：{hits}"


def test_fulltext_scan_would_have_false_positived() -> None:
    """反证：对**全文**做子串匹配会误报本文件（说明为何必须限定 import 行）。"""
    text = Path(__file__).read_text(encoding="utf-8")
    assert any(k in text for k in FORBIDDEN), (
        "本文件应在注释中提到敏感词（用于说明规则）——若未提到，该反证失效"
    )


# ---------------------------------------------------------------------------
# 3) 重放一致性（数据缺失时 skip，但给出原因）
# ---------------------------------------------------------------------------
def test_replay_matches_frozen_top3() -> None:
    """重放面板选定，结果须与 ``field_panels_draft.yaml`` 冻结的 top-3 **完全一致**。

    原始 ``.sgy`` 不入 git，若缺失则 **skip 并注明原因**（不得静默通过）。
    """
    import sys

    cfg_path = REPO / "configs" / "field_panels_draft.yaml"
    data_root = REPO / "data" / "field" / "zenodo-mv"
    assert cfg_path.exists(), "缺少 configs/field_panels_draft.yaml"

    needed = ["mv1001shots_subset8000.sgy", "nan3001shots_subset8000.sgy"]
    missing = [n for n in needed if not (data_root / n).exists()]
    if missing:
        pytest.skip(
            f"原始数据不在仓库内（设计如此：data/** 被 .gitignore 忽略），"
            f"缺少 {missing}；重放需先按 docs/field-data-note.md 获取数据"
        )

    sys.path.insert(0, str(REPO / "src"))
    from bench.field.panel_selection import _to_key, load_config, run_selection

    cfg = load_config(cfg_path)
    top = run_selection(cfg, data_root)
    assert [_to_key(p) for p in top] == [_to_key(p) for p in cfg["panels"]]
