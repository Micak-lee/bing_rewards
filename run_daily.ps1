<#
    run_daily.ps1 — 每天 08:00 自动执行 Microsoft Rewards 脚本（main.py）

    作用：自动把 "30 0"（PC 搜索 30 次、移动端 0 次）喂给 main.py 的两个交互式提问，
          并把本次运行的全部输出追加写入 logs\daily_YYYY-MM-DD.log。

    手动测试：
        powershell -NoProfile -ExecutionPolicy Bypass -File D:\new_bing\run_daily.ps1 -DryRun
        powershell -NoProfile -ExecutionPolicy Bypass -File D:\new_bing\run_daily.ps1

    注册计划任务（只需一次，任务名 MicrosoftRewards Daily 0800）：
        powershell -NoProfile -ExecutionPolicy Bypass -File D:\new_bing\run_daily.ps1 -Register
    删除计划任务：
        schtasks /Delete /TN "MicrosoftRewards Daily 0800" /F
#>
[CmdletBinding()]
param(
    [int]$PcCount = 30,                              # 第一个提问：PC 搜索次数
    [int]$MobileCount = 0,                           # 第二个提问：移动端搜索次数
    [string]$Target = 'main.py',                     # 要执行的 python 脚本
    [string]$LogDir,                                 # 日志目录，默认 <脚本目录>\logs
    [switch]$DryRun,                                 # 只打印将要执行的命令，不真的运行
    [switch]$Register                                # 注册每天 08:00 的 Windows 计划任务
)

$ErrorActionPreference = 'Continue'

# ---------- 基本路径 ----------
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Root) { $Root = (Get-Location).Path }
Set-Location -LiteralPath $Root

if (-not $LogDir) { $LogDir = Join-Path $Root 'logs' }
if (-not (Test-Path -LiteralPath $LogDir)) {
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
}
$LogFile = Join-Path $LogDir ('daily_{0}.log' -f (Get-Date -Format 'yyyy-MM-dd'))
$TaskName = 'MicrosoftRewards Daily 0800'

function Write-Log {
    param([string]$Message)
    $line = '{0} {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    try { $line | Add-Content -LiteralPath $LogFile -Encoding UTF8 } catch { }
    Write-Host $line
}

# ---------- 注册计划任务 ----------
if ($Register) {
    $psExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $argLine = '-NoProfile -ExecutionPolicy Bypass -File "{0}" -PcCount {1} -MobileCount {2}' -f `
        (Join-Path $Root 'run_daily.ps1'), $PcCount, $MobileCount
    $taskCmd = '"{0}" {1}' -f $psExe, $argLine
    Write-Host "Registering task '$TaskName' -> daily 08:00"
    Write-Host "  $taskCmd"
    schtasks.exe /Create /TN $TaskName /TR $taskCmd /SC DAILY /ST 08:00 /F
    exit $LASTEXITCODE
}

# ---------- 让 Python 与控制台都用 UTF-8，避免中文日志乱码 ----------
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
# 注意：必须用「不带 BOM」的 UTF8，否则第一行 stdin 会带上 \ufeff，
# 导致 main.py 的 int() 抛 ValueError 并静默退回 config 里的默认次数。
try { $OutputEncoding = [System.Text.UTF8Encoding]::new($false) } catch { }

# ---------- 定位 python 解释器 ----------
$Python = $null
foreach ($name in @('python', 'python3', 'py')) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd) { $Python = $cmd.Source; break }
}
if (-not $Python) {
    foreach ($cand in @(
            (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'),
            'C:\Users\Musle\anaconda3\python.exe')) {
        if (Test-Path -LiteralPath $cand) { $Python = $cand; break }
    }
}

Write-Log "=== START (PC=$PcCount, Mobile=$MobileCount, target=$Target) ==="
if (-not $Python) {
    Write-Log 'ERROR: python not found (PATH / LOCALAPPDATA / anaconda)'
    exit 127
}
Write-Log "python: $Python"

# ---------- 避免与上一次尚未结束的运行重叠 ----------
$targetName = [System.IO.Path]::GetFileName($Target)
try {
    $busy = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" -ErrorAction Stop |
        Where-Object { $_.CommandLine -and $_.CommandLine -like "*$targetName*" }
    if ($busy) {
        Write-Log "SKIP: previous run still in progress (PID $($busy.ProcessId -join ','))"
        exit 0
    }
}
catch { Write-Log "WARN: overlap check skipped: $($_.Exception.Message)" }

$TargetPath = if ([System.IO.Path]::IsPathRooted($Target)) { $Target } else { Join-Path $Root $Target }
if (-not (Test-Path -LiteralPath $TargetPath)) {
    Write-Log "ERROR: target script not found: $TargetPath"
    exit 2
}

# main.py 会连续问两次（PC 次数、移动端次数）；
# 多送两个空行，用于「未登录时按回车」的那个提问，避免直接 EOF 退出。
$StdIn = @("$PcCount", "$MobileCount", '', '')

if ($DryRun) {
    Write-Log "DRY-RUN: `"$Python`" -u `"$TargetPath`"   stdin = $($StdIn -join ' | ')"
    exit 0
}

# ---------- 执行 ----------
$StdIn | & $Python -u $TargetPath 2>&1 | ForEach-Object {
    $text = [string]$_
    try { $text | Add-Content -LiteralPath $LogFile -Encoding UTF8 } catch { }
    Write-Host $text
}
$code = $LASTEXITCODE

Write-Log "=== END (exit code $code) ==="
exit $code
