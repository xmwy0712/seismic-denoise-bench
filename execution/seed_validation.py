"""P5.5 · 工作流 A2：种子外验证（新种子，既有代码路径与登记参数）。

**顺序纪律**：`results/validation/preregistration.md` **必须已存在**（先落盘），否则本脚本拒绝运行。

官方命令::

    python execution/seed_validation.py --out results/validation

输出：新种子的 1350 格指标（270 新观测 × 5 方法）+ 判定报告（按预注册判据）。
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml

REPO = Path(r"D:\projects\seismic-denoise-bench")
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "execution"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import full_matrix as FM                                              # noqa: E402
from bench.metrics.lsig import event_mask, lsig as lsig_value         # noqa: E402
from bench.metrics.snr import delta_snr_db                            # noqa: E402
from bench.metrics.cna import build_subspace, cna_db as cna_value     # noqa: E402
from bench.metrics.events import event_metrics                        # noqa: E402
from bench.methods import METHODS, load_method                        # noqa: E402

NEW_SEEDS = [901, 902, 903, 904, 905]
RULE = {"N1": "fx_deconv", "N2": "svd_lowrank", "N3": "fk_filter"}
FAILURE_RATE_STOP = 0.05


def run(out_dir: Path, dry_run: bool = False) -> dict:
    prereg = REPO / "results" / "validation" / "preregistration.md"
    if not prereg.exists():
        raise SystemExit("拒绝运行：预注册件不存在（先跑后补禁止）")
    print(f"[gate] 预注册件在位：{prereg.name}  mtime={time.strftime('%H:%M:%S', time.localtime(prereg.stat().st_mtime))}", flush=True)

    cfg = FM._load_frozen()
    reg = yaml.safe_load((REPO / "configs" / "methods_registry.yaml").read_text(encoding="utf-8"))
    reg_params = {m["name"]: {k: v["value"] for k, v in m["key_params"].items()} for m in reg["methods"]}
    entries = FM.build_matrix(cfg)
    methods = list(METHODS)

    # 预检
    seen = set()
    for e in entries:
        mid = e["model"]["id"]
        if mid in seen:
            continue
        FM.make_observation(e, NEW_SEEDS[0])
        seen.add(mid)
    print(f"[preflight] 模型 {sorted(seen)} 均可构造观测", flush=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    rows, failures = [], []
    total = len(entries) * len(NEW_SEEDS) * len(methods)
    done, t0 = 0, time.perf_counter()
    step = max(1, total // 10)

    for entry in entries:
        for seed in NEW_SEEDS:
            cid = FM.config_id(entry["model"]["id"], entry["noise"]["id"],
                               entry["level"]["id"], entry["f_main"])
            try:
                clean, noisy, nc = FM.make_observation(entry, seed)
                dt = float(entry["acq"]["dt_s"])
                mask = event_mask(clean, f_main=entry["f_main"], dt=dt,
                                  threshold=0.5 * float(np.max(np.abs(clean))))
                wins = FM.time_windows_from_mask(mask)
                sub = build_subspace([nc], rank_tol=1e-8) if float(np.sum(nc ** 2)) > 0 else None
            except Exception as exc:                                   # noqa: BLE001
                failures.append({"config_id": cid, "seed": seed, "method": "<data>",
                                 "error": f"{type(exc).__name__}: {exc}"})
                done += len(methods)
                continue
            for name in methods:
                try:
                    mod = load_method(name)
                    params = dict(mod.PARAMS_DEFAULT)
                    params.update(reg_params.get(name, {}))
                    y = mod.run(noisy, params, np.random.default_rng(seed))
                    if y.shape != noisy.shape:
                        raise ValueError(f"形状 {y.shape} != {noisy.shape}")
                    if not np.all(np.isfinite(y)):
                        raise ValueError("输出含非有限值")
                    ev = event_metrics(clean, y, wins, dt=dt)
                    fname = f"{cid}_{seed}_{name}.npy"
                    if not dry_run:
                        np.save(out_dir / fname, y)
                    rows.append({"config_id": cid, "seed": seed, "method": name,
                                 "y_hat_sha256": FM.sha256_of(y), "y_hat_file": fname,
                                 "delta_snr_db": delta_snr_db(clean, noisy, y),
                                 "lsig": lsig_value(clean, y, mask),
                                 "cna_db": (cna_value(nc, y - clean, sub) if sub is not None else None),
                                 "n_event_windows": len(wins),
                                 "event_timing_median_ms": getattr(ev, "timing_median_ms", None),
                                 "event_energy_median": getattr(ev, "energy_median", None)})
                except Exception as exc:                               # noqa: BLE001
                    failures.append({"config_id": cid, "seed": seed, "method": name,
                                     "error": f"{type(exc).__name__}: {exc}"})
                done += 1
                if done % step == 0:
                    print(f"[progress] {done}/{total} ({done/total:.0%}) "
                          f"elapsed={time.perf_counter()-t0:.1f}s fails={len(failures)}", flush=True)

    with (out_dir / "metrics.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader(); w.writerows(rows)

    # ── 判定（按预注册判据）
    def med(noise, method, source):
        p = REPO / ("results/metrics.csv" if source == "orig" else "results/validation/metrics.csv")
        vals = []
        with p.open(encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                if r["method"] == method and r["config_id"].split("_")[1] == noise:
                    vals.append(float(r["delta_snr_db"]))
        return float(np.median(vals)) if vals else float("nan")

    verdict = []
    for nz in ("N1", "N2", "N3"):
        o = {m: med(nz, m, "orig") for m in methods}
        n = {m: med(nz, m, "new") for m in methods}
        sel = RULE[nz]
        rank = 1 + sum(1 for m in methods if n[m] > n[sel])
        ratio = (n[sel] / o[sel]) if o[sel] else float("nan")
        hit = (n[sel] == max(n.values()))
        keep = (ratio >= 0.5)
        verdict.append({"noise": nz, "rule_method": sel,
                        "orig_median": o[sel], "new_median": n[sel],
                        "new_rank": rank, "ratio_new_over_orig": ratio,
                        "orig_all": o, "new_all": n,
                        "criterion_1_rank1": hit, "criterion_2_magnitude": keep,
                        "verdict": "PASS" if (hit and keep) else "FAIL"})
    npass = sum(1 for v in verdict if v["verdict"] == "PASS")

    summary = {
        "new_seeds": NEW_SEEDS, "cells": done, "rows": len(rows), "failures": len(failures),
        "failure_rate": round(len(failures) / max(done, 1), 6),
        "stop_threshold": FAILURE_RATE_STOP,
        "stop_flag": (len(failures) / max(done, 1)) > FAILURE_RATE_STOP,
        "elapsed_s": round(time.perf_counter() - t0, 3),
        "preregistration_mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(prereg.stat().st_mtime)),
        "rule": RULE, "per_noise": verdict, "pass_count": npass,
        "overall": ("样本外基本成立（>=2/3 PASS）" if npass >= 2 else "样本外不成立"),
        "label": "post-hoc 假设 · 探索性 · 每组 n=90 · 配对非独立",
    }
    with (out_dir / "validation_manifest.json").open("w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps({"summary": summary, "failures": failures}, ensure_ascii=False, indent=2))
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="P5.5 A2 · 种子外验证")
    ap.add_argument("--out", default="results/validation")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    print(json.dumps(run(REPO / a.out, a.dry_run), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
