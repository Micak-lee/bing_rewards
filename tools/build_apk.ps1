<#
    编译「必应阅读助手」APK。

    用法：
        # 只编译（产物：android\app\build\outputs\apk\debug\app-debug.apk）
        powershell -NoProfile -ExecutionPolicy Bypass -File D:\new_bing\tools\build_apk.ps1

        # 编译并直接安装到已连接的手机
        powershell -NoProfile -ExecutionPolicy Bypass -File D:\new_bing\tools\build_apk.ps1 -Install

        # 指定设备序列号
        powershell -NoProfile -ExecutionPolicy Bypass -File D:\new_bing\tools\build_apk.ps1 -Install -Device AVXB6R6123003468
#>
param(
    [switch]$Install,
    [string]$Device = '',
    [ValidateSet('debug', 'release')][string]$Variant = 'debug',
    [switch]$Clean,
    [switch]$Recompile,
    [switch]$Incremental
)

$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Root    = 'D:\new_bing'
$Project = Join-Path $Root 'android'
$Gradle  = Join-Path $Root '.toolchain\gradle-8.11.1\bin\gradle.bat'
$JavaHome = 'C:\Program Files\Android\Android Studio\jbr'
$Sdk     = Join-Path $Root '.android-sdk'

if (-not (Test-Path $Gradle)) { Write-Host "找不到 Gradle: $Gradle" -ForegroundColor Red; exit 2 }
if (-not (Test-Path (Join-Path $Sdk 'platforms'))) { Write-Host "Android SDK 尚未就绪: $Sdk" -ForegroundColor Red; exit 3 }

$env:JAVA_HOME = $JavaHome
$env:ANDROID_HOME = $Sdk
$env:ANDROID_SDK_ROOT = $Sdk
$env:GRADLE_USER_HOME = Join-Path $Root '.gradle-home'
$env:PATH = (Join-Path $JavaHome 'bin') + ';' + $env:PATH

$task = if ($Variant -eq 'release') { 'assembleRelease' } else { 'assembleDebug' }
$gradleArgs = @('-p', $Project, $task, '--console=plain', '--stacktrace')
if ($Clean) { $gradleArgs += 'clean' }
if ($Recompile) { $gradleArgs += '--rerun-tasks' }

# 工作区里的文件带“低完整性”标签，禁止被同沙箱进程覆盖：
# 每次构建前清掉旧产物，否则打包时会报 "app-debug.apk is not writeable"。
if (-not $Incremental) {
    $buildDir = Join-Path $Project 'app\build'
    if (Test-Path $buildDir) {
        Write-Host "清理旧产物: $buildDir" -ForegroundColor DarkGray
        Remove-Item -LiteralPath $buildDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "===== gradle $task =====" -ForegroundColor Cyan
& $Gradle @gradleArgs 2>&1 | ForEach-Object { $_ }
$code = $LASTEXITCODE
Write-Host "===== gradle 退出码 $code =====" -ForegroundColor $(if ($code -eq 0) { 'Green' } else { 'Red' })

$apk = Join-Path $Project ("app\build\outputs\apk\{0}\app-{0}.apk" -f $Variant)
if (Test-Path $apk) {
    $item = Get-Item $apk
    Write-Host ("APK: {0}  ({1:N1} MB)" -f $item.FullName, ($item.Length / 1MB)) -ForegroundColor Green
} else {
    Write-Host "没有生成 APK" -ForegroundColor Red
    exit 1
}

if ($Install) {
    $adbArgs = @()
    if ($Device) { $adbArgs += @('-s', $Device) }
    $adbArgs += @('install', '-r', '-d', $apk)
    Write-Host "===== adb install =====" -ForegroundColor Cyan
    & adb @adbArgs 2>&1 | ForEach-Object { $_ }
    Write-Host "===== adb 退出码 $LASTEXITCODE =====" -ForegroundColor $(if ($LASTEXITCODE -eq 0) { 'Green' } else { 'Red' })
}

exit $code
