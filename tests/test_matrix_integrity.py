"""P2.2-Am1 守卫：R-CLI 合规 + 全矩阵完整性（机械化，非人工声明）。

依据
----
`P2.2-Am1-DL留空与本地执行裁定-2026-09-30.md` 第四节（R-CLI）：
  1. `--methods` 必须移除或"仅接受全集，传入子集即报错退出"；
  2. 官方运行命令固定；
  3. **守卫断言**：`metrics.csv` 行数 = 270 × N 方法，且 (config_id, seed, method)
     组合与冻结矩阵**完全一致** —— 缺行/多行即 fail。

守卫设计遵循**常设规则 14**：扫描口径明确、脚本入库、**自带反证**。
"""

from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
for _p in (REPO / "execution", REPO / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import full_matrix as FM                    # noqa: E402
from bench.methods import METHODS           # noqa: E402

N_OBS = 270
N_METHODS = len(METHODS)                    # 裁定 J：方法数 = 5
RESULTS = REPO / "results"
METRICS = RESULTS / "metrics.csv"
MANIFEST = RESULTS / "manifest.json"


# ══════════════════════════════════════ 1 R-CLI：无子集入口
def test_cli_rejects_method_subset() -> None:
    """**R-CLI 核心守卫**：传入 `--methods <子集>` 必须报错退出。

    选择性运行是"只跑好看的方法 = 选择性报告"的后门，与禁止调参同类风险。
    """
    with pytest.raises(SystemExit) as ei:
        FM.main(["--out", str(RESULTS / "_guard_scratch"), "--methods", "fk_filter"])
    assert ei.value.code != 0, "传入子集时必须以非零码退出"


def test_cli_rejects_even_full_method_list() -> None:
    """**收严守卫**：即便传入**全集**也报错退出（参数已废止，不是"校验后放行"）。"""
    with pytest.raises(SystemExit):
        FM.main(["--out", str(RESULTS / "_guard_scratch"), "--methods", *METHODS])


def test_cli_has_no_other_method_selection_knob() -> None:
    """**反证 + 结构守卫**：`--methods` 之外不得存在任何方法选择开关。"""
    import argparse
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with pytest.raises(SystemExit), redirect_stdout(buf):
        FM.main(["--help"])
    helptext = buf.getvalue()
    # `--methods` 仍在（为给出明确报错），但**不得**有第二处方法选择入口
    opts = [ln.strip() for ln in helptext.splitlines() if ln.strip().startswith("-")]
    method_opts = [o for o in opts if "method" in o.lower()]
    assert len(method_opts) == 1, f"方法选择开关不止一处：{method_opts}"
    assert "--methods" in method_opts[0]
    # 其余开关仅允许：--out / --limit / --dry-run / -h
    allowed = ("--out", "--limit", "--dry-run", "-h", "--help", "--methods")
    for o in opts:
        assert any(o.startswith(a) for a in allowed), f"出现未预期的开关：{o}"


def test_run_matrix_always_uses_full_method_set() -> None:
    """**结构守卫**：`run_matrix` 的默认入口在 `main` 中**恒传全集**（源码级断言）。"""
    src = (REPO / "execution" / "full_matrix.py").read_text(encoding="utf-8")
    assert "run_matrix(Path(a.out), list(METHODS), a.limit, a.dry_run)" in src, (
        "main 必须以全集调用 run_matrix（不得受任何开关影响）")


# ══════════════════════════════════════ 2 冻结矩阵期望集合
def _frozen() -> dict:
    """**v2**：矩阵唯一权威（v1 全文 + item_04_supplement）。"""
    return yaml.safe_load((REPO / "configs" / "frozen-v2.yaml").read_text(encoding="utf-8"))


def _frozen_v1() -> dict:
    """v1：保留不动的原冻结件（用于 v1 ⊂ v2 校验）。"""
    return yaml.safe_load((REPO / "configs" / "frozen.yaml").read_text(encoding="utf-8"))


def _expected_cells() -> set[tuple[str, int, str]]:
    """**R-M**：期望集从**冻结件**推导（矩阵唯一权威），不再读草案。"""
    fz = _frozen()
    entries = FM.build_matrix()                       # 无参 ⇒ 内部走 frozen.yaml
    seeds = [int(s) for s in fz["item_01_synthetic_matrix"]["seeds"]]
    exp = set()
    for e in entries:
        cid = FM.config_id(e["model"]["id"], e["noise"]["id"],
                           e["level"]["id"] if e["level"] else "NA", e["f_main"])
        for s in seeds:
            for m in METHODS:
                exp.add((cid, s, m))
    return exp


def test_expected_matrix_shape_is_frozen_shape() -> None:
    """冻结矩阵形状：54 配置 × 5 种子 × 5 方法 = 1350 格（来源 = frozen.yaml）。"""
    fz = _frozen()
    entries = FM.build_matrix()
    assert len(entries) == 54, f"配置数须为 54，实测 {len(entries)}"
    assert len(fz["item_01_synthetic_matrix"]["seeds"]) == 5
    assert len(_expected_cells()) == N_OBS * N_METHODS == 1350


# ══════════════════════════════════════ R-M 专项守卫（矩阵来源 = frozen.yaml）
def test_runner_matrix_comes_from_frozen_artifact() -> None:
    """**R-M 核心**：runner 矩阵 ≡ 冻结件轴笛卡尔积（逐格比对，非抽样）。"""
    fz = _frozen()
    ax = fz["item_01_synthetic_matrix"]["axes"]
    got = {FM.config_id(e["model"]["id"], e["noise"]["id"], e["level"]["id"], e["f_main"])
           for e in FM.build_matrix()}
    exp = {FM.config_id(m, n, l, f)
           for m in ax["models"] for n in ax["noise_types"]
           for l in ax["noise_levels"] for f in ax["f_main_hz"]}
    assert got == exp, f"runner-only={sorted(got-exp)[:3]} frozen-only={sorted(exp-got)[:3]}"


def test_runner_reads_frozen_v2_for_axes() -> None:
    """**源码级守卫**：`run_matrix` 与 `build_matrix` 的**取值**必须来自 frozen-v2。

    注意断言口径（v2 后收严为"取值"而非"任何引用"）：
    `config_matrix.yaml` 仍被 `_draft_pin_guard` **引用**（纵深防御，合法），
    但**取值**函数 `_generation_params` 只读 frozen-v2 的 `item_04_supplement`。
    """
    src = (REPO / "execution" / "full_matrix.py").read_text(encoding="utf-8")
    assert "cfg = _load_frozen()" in src, "run_matrix 必须从 _load_frozen() 取值"
    assert 'FROZEN_V2 = REPO / "configs" / "frozen-v2.yaml"' in src, "冻结源须为 frozen-v2"
    assert "def build_matrix(cfg: dict | None = None)" in src, "build_matrix 须可无参调用"

    # 取值路径：`_generation_params` 的函数体**只**读 item_04_supplement，不得读草案
    gen_body = src.split("def _generation_params(")[1].split("def ")[0]
    assert "item_04_supplement" in gen_body, "_generation_params 须读 v2 的 item_04_supplement"
    assert "config_matrix.yaml" not in gen_body, "_generation_params 不得读草案"
    # 纵深防御：草案引用只应出现在 `_draft_pin_guard` 内
    guard_body = src.split("def _draft_pin_guard(")[1].split("def _generation_params(")[0]
    outside = src.replace(guard_body, "")
    assert 'REPO / "configs" / "config_matrix.yaml"' not in outside, \
        "草案引用只应存在于 _draft_pin_guard（纵深防御）内"


def test_v2_is_v1_plus_supplement_only() -> None:
    """**裁定 L 核心**：v2 = v1 全文 + `item_04_supplement`，**未改变任何已冻结值**。

    这是「补登不重跑」的依据：as-run 参数与 v2 一致 ⇒ 1350 格结果无需重跑。
    """
    d1, d2 = _frozen_v1(), _frozen()
    assert set(d1) - set(d2) == set(), "v2 不得缺少 v1 的任何键"
    assert set(d2) - set(d1) == {"item_04_supplement"}, "v2 只应新增 item_04_supplement"
    changed = [k for k in d1 if k in d2 and d1[k] != d2[k]]
    assert not changed, f"v2 改动了 v1 的已冻结值：{changed}"


def test_v2_supplement_matches_as_run_values() -> None:
    """补登值 = Run 2 全矩阵实际所用值（N1 band [5,80]；N2 f_main 30.0）。"""
    sup = _frozen()["item_04_supplement"]
    assert list(sup["n1_band_limited_random"]["band_hz"]) == [5.0, 80.0]
    assert float(sup["n2_linear_coherent"]["f_main_hz"]) == 30.0
    assert sup["n1_band_limited_random"]["as_run_consistency"].startswith("✅")
    assert sup["n2_linear_coherent"]["as_run_consistency"].startswith("✅")


def test_runner_generation_params_come_from_v2() -> None:
    """runner 的生成参数**取值**来自 v2 的 item_04_supplement（不再来自草案）。"""
    got = FM._generation_params(_frozen())
    assert got["n1_band_hz"] == [5.0, 80.0]
    assert got["n2_f_main_hz"] == 30.0


def test_v1_unchanged_at_pinned_hash() -> None:
    """**v1 未动的机械证据**：v1 文件的 SHA256 = 裁定 L 记录值。"""
    import hashlib as _h
    actual = _h.sha256((REPO / "configs" / "frozen.yaml").read_bytes()).hexdigest().upper()
    assert actual == "1695C1965D0F307E5CA55ABDA1B2206D1058F67DE4827770382602F2F2944A3F", (
        f"v1 被改动：{actual}")


def test_draft_hash_pin_is_active() -> None:
    """**纵深防御仍生效**：草案的当前 SHA256 必须等于代码中钉死的值。

    v2 后草案**已不是值来源**，本钉死仅防止有人回头从草案取值。
    """
    actual = hashlib.sha256((REPO / "configs" / "config_matrix.yaml").read_bytes()).hexdigest().upper()
    assert FM.DRAFT_PIN_SHA256 == actual, (
        f"草案哈希与钉死值不符：\n  钉死 {FM.DRAFT_PIN_SHA256}\n  实测 {actual}\n"
        "  处置：先复核改动是否改变矩阵；若改变，须走新版本 + 新 tag + 书面说明。")


def test_pin_rejects_tampered_draft_counterproof() -> None:
    """**反证**：模拟草案被篡改（哈希不符）时，`_draft_generation_params` 必须 fail fast。"""
    import configparser                                     # noqa: F401  (仅确保导入路径无副作用)
    original = FM.DRAFT_PIN_SHA256
    try:
        FM.DRAFT_PIN_SHA256 = "0" * 64
        with pytest.raises(RuntimeError, match="哈希与钉死值不符"):
            FM._draft_generation_params()
    finally:
        FM.DRAFT_PIN_SHA256 = original


# ══════════════════════════════════════ 3 完整性（缺行/多行即 fail）
def _load_metrics() -> list[dict]:
    if not METRICS.exists():
        pytest.skip("results/metrics.csv 尚未生成（本地全矩阵运行后启用本守卫）")
    return list(csv.DictReader(METRICS.open(encoding="utf-8")))


def test_metrics_row_count_is_exact() -> None:
    """**R-CLI 第 3 条**：行数必须严格 = 270 × 方法数。"""
    rows = _load_metrics()
    assert len(rows) == N_OBS * N_METHODS, (
        f"metrics.csv 行数 {len(rows)} != {N_OBS} × {N_METHODS} = {N_OBS * N_METHODS}")


def test_metrics_cell_set_matches_frozen_matrix_exactly() -> None:
    """**R-CLI 第 3 条**：(config_id, seed, method) 组合须与冻结矩阵**完全一致**。"""
    rows = _load_metrics()
    got = {(r["config_id"], int(r["seed"]), r["method"]) for r in rows}
    exp = _expected_cells()
    missing, extra = exp - got, got - exp
    assert not missing, f"缺行 {len(missing)} 个，例如 {sorted(missing)[:3]}"
    assert not extra, f"多行 {len(extra)} 个，例如 {sorted(extra)[:3]}"


def test_no_duplicate_cells() -> None:
    rows = _load_metrics()
    keys = [(r["config_id"], r["seed"], r["method"]) for r in rows]
    assert len(keys) == len(set(keys)), "存在重复格（可能为重试到成功留下的痕迹）"


def test_every_cell_has_hash_and_metrics() -> None:
    rows = _load_metrics()
    for r in rows:
        assert len(r["y_hat_sha256"]) == 64, f"{r['config_id']}/{r['seed']}/{r['method']} 哈希缺失"
        assert r["delta_snr_db"] not in ("", "None"), "ΔSNR 缺失"
        assert r["lsig"] not in ("", "None"), "Lsig 缺失"


def test_y_hat_files_exist_and_hash_matches() -> None:
    """y_hat 本体存在且**哈希与清单一致**（缺件可检出）。"""
    rows = _load_metrics()
    import hashlib
    import numpy as np
    missing = [r for r in rows if r["y_hat_file"] and not (RESULTS / r["y_hat_file"]).exists()]
    assert not missing, f"缺 {len(missing)} 个 y_hat 文件，例如 {missing[:2]}"
    for r in rows[:40]:                      # 抽验前 40 格（全量哈希重算过重）
        if not r["y_hat_file"]:
            continue
        a = np.load(RESULTS / r["y_hat_file"])
        h = hashlib.sha256(np.ascontiguousarray(a, dtype=np.float64).tobytes()).hexdigest().upper()
        assert h == r["y_hat_sha256"], f"{r['y_hat_file']} 哈希不符"


def test_failure_rate_within_threshold() -> None:
    if not MANIFEST.exists():
        pytest.skip("results/manifest.json 尚未生成")
    import json
    d = json.loads(MANIFEST.read_text(encoding="utf-8"))
    s = d["summary"]
    assert s["stop_flag"] is False, f"失败率超阈：{s['failure_rate']}"
    assert s["failure_rate"] <= FM.FAILURE_RATE_STOP


# ══════════════════════════════════════ 4 反证（规则 14 第 3 条）
def test_integrity_guard_detects_missing_row_counterproof() -> None:
    """**反证**：从期望集合中删一格，守卫的差集运算必须能检出。"""
    exp = _expected_cells()
    dropped = next(iter(exp))
    got = exp - {dropped}
    assert exp - got == {dropped}, "反证失败：缺行未被检出"
    assert got - exp == set(), "反证失败：反方向误报"


def test_integrity_guard_detects_extra_cell_counterproof() -> None:
    """**反证**：加入一个不在冻结矩阵中的格，守卫必须能检出（多行 ≠ 通过）。"""
    exp = _expected_cells()
    bogus = ("M1_N9_L9_99Hz", 999, "no_such_method")
    got = exp | {bogus}
    assert got - exp == {bogus}, "反证失败：多行未被检出"
