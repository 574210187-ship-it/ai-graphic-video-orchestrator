[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$PythonCommand = Get-Command py -ErrorAction SilentlyContinue
if ($PythonCommand) {
    & py -3 -m venv .venv
} else {
    $PythonCommand = Get-Command python -ErrorAction Stop
    & python -m venv .venv
}
if ($LASTEXITCODE -ne 0) {
    throw "PYTHON_VENV_CREATE_FAILED：无法创建.venv。"
}

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "PIP_UPGRADE_FAILED：无法升级pip。"
}
& $VenvPython -m pip install -e ".[test,media]"
if ($LASTEXITCODE -ne 0) {
    throw "PACKAGE_INSTALL_FAILED：无法安装项目依赖。"
}

Write-Host "安装完成：$RepoRoot\.venv"
Write-Host "下一步：运行 .\scripts\setup_windows_feishu.ps1"
