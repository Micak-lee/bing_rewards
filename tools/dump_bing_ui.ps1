<#
    抓取必应 App 当前界面的节点树，保存到 android\uidump\ 下，供调整自动化规则用。

    用法：
        powershell -NoProfile -ExecutionPolicy Bypass -File D:\new_bing\tools\dump_bing_ui.ps1 -Tag home
        powershell -NoProfile -ExecutionPolicy Bypass -File D:\new_bing\tools\dump_bing_ui.ps1 -Tag article -NoLaunch
#>
param(
    [string]$Tag = 'ui',
    [string]$Device = '',
    [switch]$NoLaunch,
    [int]$WaitSeconds = 8
)

$ErrorActionPreference = 'Continue'
$Root = 'D:\new_bing'
$OutDir = Join-Path $Root 'android\uidump'
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function Invoke-Adb {
    param([string[]]$AdbArgs)
    $full = @()
    if ($Device) { $full += @('-s', $Device) }
    $full += $AdbArgs
    return (& adb @full 2>&1 | Out-String)
}

$devices = (Invoke-Adb @('devices')) -split "`n" |
    ForEach-Object { $_.Trim() } |
    Where-Object { $_ -match '\tdevice$' -or $_ -match '\sdevice$' }
if (-not $devices) {
    Write-Host "没有检测到已授权的设备。请插上手机并在手机上点「允许 USB 调试」。" -ForegroundColor Red
    exit 1
}
Write-Host ("设备: " + ($devices -join ', ').Trim())

if (-not $NoLaunch) {
    Write-Host "拉起必应 App…"
    Invoke-Adb @('shell', 'monkey', '-p', 'com.microsoft.bing', '-c', 'android.intent.category.LAUNCHER', '1') | Out-Null
    Start-Sleep -Seconds $WaitSeconds
}

$focus = (Invoke-Adb @('shell', 'dumpsys', 'window')) -split "`n" | Where-Object { $_ -match 'mCurrentFocus' } | Select-Object -First 1
Write-Host ("当前前台: " + ($focus -as [string]).Trim())

$remote = "/sdcard/ui_$Tag.xml"
$ok = $false
for ($i = 1; $i -le 4; $i++) {
    $res = Invoke-Adb @('shell', 'uiautomator', 'dump', $remote)
    if ($res -match 'dumped to') { $ok = $true; break }
    Write-Host "第 $i 次 dump 失败: $($res.Trim())" -ForegroundColor Yellow
    Start-Sleep -Seconds 2
}
if (-not $ok) {
    Write-Host "uiautomator dump 一直失败，改用截图。" -ForegroundColor Yellow
    $png = Join-Path $OutDir ("screen_$Tag.png")
    & adb $(if ($Device) { @('-s', $Device) } else { @() }) exec-out screencap -p > $png
    Write-Host "截图: $png"
    exit 2
}

$local = Join-Path $OutDir ("ui_$Tag.xml")
Invoke-Adb @('pull', $remote, $local) | Out-Null
$item = Get-Item $local -ErrorAction SilentlyContinue
if ($item) {
    Write-Host ("已保存: {0} ({1:N0} 字节)" -f $item.FullName, $item.Length) -ForegroundColor Green
    Write-Host "--- 界面上的文本节点（前 60 条）---"
    [xml]$xml = Get-Content -LiteralPath $local -Encoding UTF8
    $nodes = $xml.SelectNodes('//node') | Where-Object {
        ($_.text -and $_.text.Trim().Length -gt 0) -or ($_.'content-desc' -and $_.'content-desc'.Trim().Length -gt 0)
    }
    $nodes | Select-Object -First 60 | ForEach-Object {
        $t = if ($_.text) { $_.text.Trim() } else { '' }
        $d = if ($_.'content-desc') { $_.'content-desc'.Trim() } else { '' }
        $b = $_.bounds
        "{0,-46} | desc={1,-30} | {2} | cls={3}" -f $t.Substring(0, [Math]::Min(46, $t.Length)), $d.Substring(0, [Math]::Min(30, $d.Length)), $b, ($_.'class' -replace '.*\.', '')
    }
} else {
    Write-Host "拉取失败" -ForegroundColor Red
    exit 3
}
