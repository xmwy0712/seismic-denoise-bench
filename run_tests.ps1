# ============================================================
# run_tests.ps1 —— 本机权威测试入口（Windows / PowerShell）
#
# 语义：等价于在仓库根目录执行
#           python -m pytest
# 不传任何筛选参数、不跑子集。run_tests.sh 与之为同一语义的薄封装。
# 详细约定见 README.md「测试入口」小节与 docs/execution-log.md。
# 编码约定：UTF-8 无 BOM，LF 换行
# ============================================================

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$venvPy = Join-Path $root '.venv\Scripts\python.exe'
$py = if (Test-Path $venvPy) { $venvPy } else { 'python' }

& $py -m pytest
exit $LASTEXITCODE
