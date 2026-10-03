"""P5.9 · 数字门：表 13 命中率复算值与论文表格的**机器一致性**核验。

判据
----
逐噪声类型命中率（规则所选方法 == 逐观测最优单法的观测占比）由 **既有产物** 独立复算：
`results/validation/replication_diagnostics.json`（原种子）与同源分析（新种子）。
论文 `docs/paper/draft-vXX.md` 表 13 中每一格的 (原, 新) 百分比必须与之一致（±0.05pp）。

自带反证
--------
`--self-test` 故意篡改一个期望值，核验器**必须报 FAIL**；若不报，说明核验器失效。

退出码：全部一致 0；任一不一致非 0。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOL = 0.05  # 百分点
RULE = {"N1": "fx_deconv", "N2": "svd_lowrank", "N3": "fk_filter"}


def expected() -> dict:
    d = json.loads((REPO / "results/validation/replication_diagnostics.json")
                   .read_text(encoding="utf-8"))
    out = {}
    for nt in ("N1", "N2", "N3"):
        out[nt] = (d["original_seeds"]["per_noise"][nt]["hit_rate"] * 100.0,
                   d["new_seeds"]["per_noise"][nt]["hit_rate"] * 100.0)
    out["global"] = (d["original_seeds"]["hit_rate_global"] * 100.0,
                     d["new_seeds"]["hit_rate_global"] * 100.0)
    return out


def parse_table(doc: Path) -> dict:
    t = doc.read_text(encoding="utf-8")
    got = {}
    for nt, label in (("N1", "N1 带限随机"), ("N2", "N2 线性相干"), ("N3", "N3 频散面波")):
        m = re.search(rf"^\| {label} \|[^|]*\|[^|]*\|[^|]*\|\s*\*{{0,2}}([\d.]+)%\s*→\s*([\d.]+)%",
                      t, re.M)
        got[nt] = (float(m.group(1)), float(m.group(2))) if m else None
    m = re.search(r"全库命中率由\s*([\d.]+)%\s*降至\s*([\d.]+)%", t)
    got["global"] = (float(m.group(1)), float(m.group(2))) if m else None
    return got


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="P5.9 数字门 · 表 13 命中率一致性")
    ap.add_argument("--doc", default="docs/paper/draft-v10.md")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    exp, got = expected(), parse_table(REPO / a.doc)
    if a.self_test:
        exp["N1"] = (exp["N1"][0] + 1.0, exp["N1"][1])
    bad = []
    for k in ("N1", "N2", "N3", "global"):
        e, g = exp[k], got.get(k)
        if g is None:
            bad.append((k, "论文缺该格", e))
        elif abs(e[0] - g[0]) > TOL or abs(e[1] - g[1]) > TOL:
            bad.append((k, f"论文 {g} != 复算 {e}", e))
    for k in ("N1", "N2", "N3", "global"):
        print(f"  {k:6} 复算 {exp[k][0]:.2f}/{exp[k][1]:.2f}  论文 {got.get(k)}")
    print(f"  总判定 = {'PASS' if not bad else 'FAIL'}")
    for b in bad:
        print(f"    {b}")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
