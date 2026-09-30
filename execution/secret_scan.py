"""P5.4 · WS3 前置门：**发布前凭据扫描（只读）**。

规则（P5.4 硬门）
----------------
* 发布前必须对**全仓库**做凭据模式正则扫描 + `.gitignore` 覆盖人工复核；
* **任何疑似凭据 ⇒ 停机，不得 push**；
* **零回显**：本脚本**绝不输出**匹配到的任何字符（连前后缀都不给），只报
  「模式 / 文件 / 行号 / 归类」。

扫描范围：`git ls-files`（**即将被推送的受管文件**），并按既定规则排除
`.venv/`、`.git/`、`data/`、`docs/bibliography/raw/`。
"""

from __future__ import annotations

import io
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(r"D:\projects\seismic-denoise-bench")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

EXCLUDE = re.compile(r"(^|/)(\.venv|\.git)(/|$)")   # 覆盖缺口修正：raw 亦为受管文件，必须扫

PATTERNS = [
    ("github_token", r"\b(gho|ghp|ghs|ghr)_[A-Za-z0-9]{20,}"),
    ("github_pat", r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    ("aws_akid", r"\bAKIA[0-9A-Z]{16}\b"),
    ("openai_key", r"\bsk-[A-Za-z0-9]{20,}\b"),
    ("google_api_key", r"\bAIza[0-9A-Za-z_\-]{30,}\b"),
    ("slack_token", r"\bxox[baprs]-[A-Za-z0-9\-]{10,}"),
    ("telegram_bot_token", r"\b[0-9]{8,10}:[A-Za-z0-9_\-]{30,}\b"),
    ("private_key_block", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ("url_with_credentials", r"https?://[^\s/:@]+:[^\s/:@]+@"),
    ("bearer_literal", r"(?i)\bbearer\s+[A-Za-z0-9._\-]{20,}"),
    ("assignment_secret",
     r"(?i)\b(api[_\-]?key|apikey|secret|token|password|passwd|pwd|credential)\b"
     r"\s*[:=]\s*[\"'][^\"'\s]{8,}[\"']"),
    ("env_secret_line",
     r"(?i)^\s*(set|export|\$env:)\s+[A-Z0-9_]*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)"
     r"[A-Z0-9_]*\s*[:=]\s*\S+"),
    ("known_secret_names",
     r"(?i)\b(COMMANDCODE_API_KEY|TAVILY_API_KEY|TELEGRAM_BOT_TOKEN|VOYAGE_API_KEY|"
     r"OPENAI_API_KEY|DEEPSEEK_API_KEY|NOTION_TOKEN|GITHUB_PERSONAL_ACCESS_TOKEN|"
     r"OPENALEX_API_KEY|S2_API_KEY)\b\s*[:=]\s*[^\s\"'\[]+"),
]

COMPILED = [(n, re.compile(p)) for n, p in PATTERNS]


def tracked() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True,
                         text=True, encoding="utf-8").stdout
    return [f for f in out.splitlines() if f.strip() and not EXCLUDE.search(f.replace("\\", "/"))]


def scan() -> dict:
    files = tracked()
    hits: list[dict] = []
    scanned = 0
    for rel in files:
        p = REPO / rel
        if not p.exists():
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        scanned += 1
        for i, line in enumerate(txt.splitlines(), 1):
            for name, rx in COMPILED:
                if rx.search(line):
                    # 零回显：只记位置与模式名
                    hits.append({"pattern": name, "file": rel, "line": i})
    return {"tracked_files": len(files), "scanned": scanned, "hits": hits,
            "hit_count": len(hits),
            "verdict": "CLEAN" if not hits else "STOP_SUSPECTED_CREDENTIAL"}


def gitignore_review() -> dict:
    gi = (REPO / ".gitignore")
    txt = gi.read_text(encoding="utf-8") if gi.exists() else ""
    need = {
        "results/*.npy": "结果数组（y_hat）",
        "results/fusion/*.npy": "融合输出数组",
        "results/fusion10/*.npy": "10 配对输出数组",
        "results/fusion_ablation/*.npy": "消融输出数组",
        "results/field/*.npy": "野外面板数据块",
        "data/**": "野外原始数据",
        "docs/bibliography/raw": "检索原始响应",
        ".venv": "虚拟环境",
    }
    covered = {k: (k in txt) for k in need}
    return {"covered": covered, "all_covered": all(covered.values()),
            "uncovered": [k for k, v in covered.items() if not v]}


if __name__ == "__main__":
    res = scan()
    gi = gitignore_review()
    print("=== 凭据模式扫描（git ls-files，已排除 .venv/.git/data/raw）===")
    print(f"  受管文件 {res['tracked_files']} 个，实际读取 {res['scanned']} 个")
    print(f"  命中 = {res['hit_count']}")
    for h in res["hits"][:40]:
        print(f"    [{h['pattern']}] {h['file']} : L{h['line']}")
    print(f"  判定 = {res['verdict']}")
    print()
    print("=== .gitignore 覆盖复核 ===")
    for k, v in gi["covered"].items():
        print(f"  {'OK  ' if v else 'MISS'} {k}")
    print(f"  全覆盖 = {gi['all_covered']}   未覆盖 = {gi['uncovered']}")
