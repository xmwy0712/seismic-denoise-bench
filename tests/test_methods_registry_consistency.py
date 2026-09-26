"""P2.1 方法登记表 ↔ 实现一致性守卫（**机械化自查**，非人工声明）。

设计遵循常设规则 14：
  1. 只做结构化比对（YAML 字段 vs 模块属性），**不做全文子串匹配**；
  2. 本脚本入库（可独立重放）；
  3. 自带**反证**：故意构造不一致的登记项，断言守卫能检出。

比对项（逐方法）：
  · 模块路径     registry.methods[].module  ↔ 实际可导入模块的 __file__
  · 方法名       name                        ↔ 模块 METHOD_NAME
  · 机制族       family_mechanism_table      ↔ 模块 FAMILY
  · 参数名集合   key_params 的键              ↔ 模块 PARAMS_DEFAULT 的键（**双向**）
  · 参数默认值   key_params[].value           ↔ 模块 PARAMS_DEFAULT 的值
  · 确定性标记   （本批全确定性）              ↔ 模块 DETERMINISTIC
  · 方法总数     methods_count                ↔ len(bench.methods.METHODS)
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bench.methods import METHODS, load_method

REPO = Path(__file__).resolve().parents[1]
REGISTRY = REPO / "configs" / "methods_registry.yaml"


def _registry() -> dict:
    return yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))


def _reg_params(entry: dict) -> dict:
    return {k: v["value"] for k, v in (entry.get("key_params") or {}).items()}


def _norm(v):
    """把 YAML null / 数值统一到可比较形式。"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return str(v)


def _compare(entry: dict) -> list[str]:
    """返回不一致项列表（空列表 = 一致）。"""
    name = entry["name"]
    mod = load_method(name)
    bad: list[str] = []

    if mod.METHOD_NAME != name:
        bad.append(f"METHOD_NAME={mod.METHOD_NAME!r} != registry {name!r}")
    if mod.FAMILY != entry["family_mechanism_table"]:
        bad.append(f"FAMILY={mod.FAMILY!r} != registry {entry['family_mechanism_table']!r}")

    reg = _reg_params(entry)
    impl = mod.PARAMS_DEFAULT
    if set(reg) != set(impl):
        bad.append(f"参数名不一致：registry-only={sorted(set(reg)-set(impl))} "
                   f"impl-only={sorted(set(impl)-set(reg))}")
    for k in set(reg) & set(impl):
        if _norm(reg[k]) != _norm(impl[k]):
            bad.append(f"参数 {k}: registry={reg[k]!r} != impl={impl[k]!r}")

    if not mod.DETERMINISTIC:
        bad.append("本批要求全方法确定性，但 DETERMINISTIC=False")
    return bad


# ---------------------------------------------------------------- 1 逐方法一致
@pytest.mark.parametrize("entry", _registry()["methods"], ids=lambda e: e["name"])
def test_registry_matches_implementation(entry: dict) -> None:
    bad = _compare(entry)
    assert not bad, f"{entry['name']} 登记表与实现不一致：\n  - " + "\n  - ".join(bad)


# ---------------------------------------------------------------- 2 集合与总数
def test_registry_method_set_equals_implementation_set() -> None:
    reg = {e["name"] for e in _registry()["methods"]}
    assert reg == set(METHODS), f"registry-only={reg-set(METHODS)} impl-only={set(METHODS)-reg}"


def test_methods_count_field_matches() -> None:
    r = _registry()
    assert int(r["methods_count"]) == len(METHODS)
    assert int(r["methods_count"]) == len(r["methods"])


def test_module_paths_exist_and_match() -> None:
    for entry in _registry()["methods"]:
        rel = entry["module"]
        p = REPO / rel
        assert p.exists(), f"{entry['name']} 登记的模块路径不存在：{rel}"
        mod = load_method(entry["name"])
        assert Path(mod.__file__).resolve() == p.resolve(), (
            f"{entry['name']} 实际模块路径 {mod.__file__} != 登记 {rel}")


# ---------------------------------------------------------------- 3 协议类别覆盖
def test_all_mandatory_protocol_categories_covered() -> None:
    """协议必须类别（滤波/变换阈值/分解/低秩）须各有 >=1 实现。"""
    cats = {e["protocol_category"] for e in _registry()["methods"]}
    for must in ("滤波", "变换阈值", "分解", "低秩"):
        assert must in cats, f"协议必须类别 {must} 无实现"


def test_strong_baseline_present() -> None:
    """协议第 18 行强制保留至少一种相干噪声强基线。"""
    sb = [e for e in _registry()["methods"] if e.get("is_strong_baseline")]
    assert sb, "无强基线方法"


# ---------------------------------------------------------------- 4 反证（规则 14 第 3 条）
def test_guard_detects_parameter_drift_counterproof() -> None:
    """**反证**：把登记值改坏，守卫必须检出（证明本守卫非恒真）。"""
    entry = dict(_registry()["methods"][0])
    entry["key_params"] = {k: dict(v) for k, v in entry["key_params"].items()}
    first = next(iter(entry["key_params"]))
    entry["key_params"][first]["value"] = 999999.0
    assert _compare(entry), "反证失败：改坏登记值后守卫仍未检出"

    entry2 = dict(_registry()["methods"][0])
    entry2["family_mechanism_table"] = "不存在的族"
    assert _compare(entry2), "反证失败：改坏机制族后守卫仍未检出"


def test_guard_accepts_current_registry_without_exception() -> None:
    """正向基线：当前登记表在守卫下**零不一致**。"""
    allbad = {e["name"]: _compare(e) for e in _registry()["methods"]}
    assert all(not v for v in allbad.values()), allbad
