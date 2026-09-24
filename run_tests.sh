#!/usr/bin/env sh
# ============================================================
# run_tests.sh —— 测试入口（POSIX / Git Bash）
#
# 语义：等价于在仓库根目录执行
#           python -m pytest
# 不传任何筛选参数、不跑子集。run_tests.ps1 与之为同一语义的薄封装
# （后者为本机权威入口，见 README.md「测试入口」小节）。
#
# 注意：本机（Windows）PATH 中没有 bash，也没有 make；本脚本需通过
# Git Bash 或 WSL 运行。本机日常验收请使用 run_tests.ps1。
# 编码约定：UTF-8 无 BOM，LF 换行
# ============================================================
set -e

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"

if [ -x ".venv/Scripts/python.exe" ]; then
    PY=".venv/Scripts/python.exe"
elif [ -x ".venv/bin/python" ]; then
    PY=".venv/bin/python"
else
    PY="python"
fi

exec "$PY" -m pytest
