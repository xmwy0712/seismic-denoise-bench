"""P5.5 · 工作流 A1：野外重跑（两配对 × 3 面板 × 3 γ），**增量登记、不覆盖既有产物**。

配对：
* 对照配对（预注册稳健性对照）：`fx_deconv × svd_lowrank`
* 事后最优配对（来自 10 对全跑）：`fk_filter × fx_deconv`
* 预注册主配对：`fx_deconv × wavelet_threshold`（**同批重算，供同口径并列**）

输出：`results/field2/field_pair_metrics.csv`（**新目录**，既有 `results/field/` 不动）。
四项指标口径与 `execution/field_eval.py` **完全相同**（直接复用其函数）。
"""

from __future__ import annotations

import csv
import io
import json
import sys
import time
from pathlib import Path

import numpy as np
import yaml

R = Path(r"D:\projects\seismic-denoise-bench")
sys.path.insert(0, str(R / "src"))
sys.path.insert(0, str(R / "execution"))

import field_eval as FE                                                # noqa: E402  复用指标函数（其导入亦会包装 stdout）
from bench.field import panel_selection as PS                          # noqa: E402
from bench.field.continuity import local_dip                           # noqa: E402
from bench.fusion import fuse                                          # noqa: E402
from bench.methods import METHODS, load_method                         # noqa: E402

# **不自行包装 stdout**：`field_eval` 导入时已包装（UTF-8）。
# 若再包一层，前者被 GC 时会关闭**同一个底层 buffer**，导致后续 print 报
# "I/O operation on closed file"（本轮已实测两次）。

PAIRS = {
    "primary_preregistered": ("fx_deconv", "wavelet_threshold"),
    "control_preregistered": ("fx_deconv", "svd_lowrank"),
    "posthoc_best": ("fk_filter", "fx_deconv"),
}
GAMMAS = (0.4, 0.5, 0.6)


def _flush_now(rows, out=None):
    """逐面板即时落盘：即使后续面板崩溃，已算出的结果也不丢。"""
    if not rows:
        return
    import csv as _csv
    out = out or (R / "results" / "field2")
    out.mkdir(parents=True, exist_ok=True)
    with (out / "field_pair_metrics.csv").open("w", encoding="utf-8", newline="") as fh:
        w = _csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    t0 = time.perf_counter()
    fp = yaml.safe_load((R / "configs" / "field_panels_draft.yaml").read_text(encoding="utf-8"))
    panels = {p["panel_id"]: p for p in fp["panels"]}
    reg = yaml.safe_load((R / "configs" / "methods_registry.yaml").read_text(encoding="utf-8"))
    reg_params = {m["name"]: {k: v["value"] for k, v in m["key_params"].items()} for m in reg["methods"]}
    DATA = R / "data" / "field" / "zenodo-mv"

    rows: list[dict] = []
    for pid in ("FP1", "FP2", "FP3"):
        p = panels[pid]
        blk = PS.read_trace_block(DATA / PS.REGION_FILES[p["region"]],
                                  p["trace_range"][0], p["trace_range"][1])
        orig = blk[p["sample_range"][0]:p["sample_range"][1], :]
        wins = [tuple(w) for w in p["event_windows_samples"]]
        n_t = int(p["n_T_samples"])
        dip_o = local_dip(orig)
        e_orig = FE.band_energy(orig, FE.SIGNAL_BAND, FE.DT)

        def metrics(y: np.ndarray) -> dict:
            rem = orig - y
            return {
                "amp_dev_db": 20.0 * np.log10(max(FE.envelope_rms(y), 1e-300) /
                                              max(FE.envelope_rms(orig), 1e-300)),
                "spectral_residual": (FE.band_energy(rem, FE.SIGNAL_BAND, FE.DT) / e_orig
                                      if e_orig > 0 else float("nan")),
                "continuity_gain": FE.continuity_gain(y, orig, dip_o, wins),
                "lp": FE.continuity_gain(rem, orig, dip_o, wins),
            }

        store = {}
        for m in METHODS:
            mod = load_method(m)
            prm = dict(mod.PARAMS_DEFAULT)
            prm.update({k: v for k, v in reg_params.get(m, {}).items() if v is not None})
            store[m] = mod.run(orig, prm, np.random.default_rng(0))
        for name, (mi, mj) in PAIRS.items():
            for g in GAMMAS:
                yf = fuse(store[mi], store[mj], {"n_t": n_t, "gamma": g, "x": orig, "dt": FE.DT,
                                                 "v_lo_m_s": 100.0, "band_hz": FE.SIGNAL_BAND})
                m = metrics(yf)
                rows.append({"panel": pid, "pair": name, "pair_i": mi, "pair_j": mj,
                             "gamma": g, **m, "n_event_windows": len(wins)})
        # 成员单法一并登记（同批同口径）
        for mname in {x for pr in PAIRS.values() for x in pr}:
            m = metrics(store[mname])
            rows.append({"panel": pid, "pair": "member_single", "pair_i": mname, "pair_j": "",
                         "gamma": "", **m, "n_event_windows": len(wins)})
        print(f"  {pid} 完成（累计 {len(rows)} 行）", flush=True)
        _flush_now(rows)

    out = R / "results" / "field2"
    out.mkdir(parents=True, exist_ok=True)
    with (out / "field_pair_metrics.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader(); w.writerows(rows)

    summary = {
        "pairs": {k: list(v) for k, v in PAIRS.items()},
        "gammas": list(GAMMAS), "panels": ["FP1", "FP2", "FP3"], "rows": len(rows),
        "incremental": "写入 results/field2/，既有 results/field/ 未改动",
        "metrics": ["amp_dev_db", "spectral_residual", "continuity_gain", "lp"],
        "note": ("无真值、四项无参考指标；延续既有不可区分判定（连续性不参与综合）；"
                 "本表只列原始指标，不计算综合分（既有 u_scores_partial 的归一化口径未见文档，故不外推）"),
        "elapsed_s": round(time.perf_counter() - t0, 2),
    }
    (out / "manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    import traceback
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        raise SystemExit(3)
