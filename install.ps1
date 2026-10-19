# Tide Windows 一键安装脚本 (PowerShell)
# 用法: irm https://raw.githubusercontent.com/coustea/AI-Agent/my-agent/install.ps1 | iex

$ErrorActionPreference = "Stop"

$Repo = "coustea/AI-Agent"
$DefaultVersion = "v1.0.1"
$Version = if ($env:TIDE_VERSION) { $env:TIDE_VERSION } else { $DefaultVersion }

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "   🌊 正在安装 Tide (本地终端通用 AI 个人助手)      " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# 1. 检查架构
if (-not [Environment]::Is64BitOperatingSystem) {
    Write-Host "错误: Tide 仅支持 64 位 Windows 系统 (amd64)。" -ForegroundColor Red
    exit 1
}

Write-Host "=> 系统平台: Windows x64 (amd64)" -ForegroundColor Green
Write-Host "=> 目标版本: $Version" -ForegroundColor Green

# 2. 下载发布包
$ZipName = "tide-windows-amd64.zip"
$DownloadUrl = "https://github.com/$Repo/releases/download/$Version/$ZipName"
$TempDir = Join-Path $env:TEMP "tide-install-$(Get-Random)"
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

$ZipPath = Join-Path $TempDir $ZipName

Write-Host "=> 正在从 GitHub 下载发布包..."
Write-Host "   URL: $DownloadUrl" -ForegroundColor Gray

try {
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $ZipPath -UseBasicParsing
    Expand-Archive -Path $ZipPath -DestinationPath $TempDir -Force
} catch {
    Write-Host "直接下载发布包失败 ($DownloadUrl)。" -ForegroundColor Yellow
    if (Get-Command go -ErrorAction SilentlyContinue) {
        Write-Host "=> 检测到 Go 环境，正在通过 Go 工具链编译安装..." -ForegroundColor Green
        go install "github.com/$Repo/cmd/tide@latest"
        Write-Host "`n✔ Tide 安装成功！" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "错误: 无法下载发布包，请访问 https://github.com/$Repo/releases 手动下载。" -ForegroundColor Red
        exit 1
    }
}

# 3. 安装到用户目录
$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\tide"
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

$ExePath = Join-Path $InstallDir "tide.exe"
Copy-Item -Path (Join-Path $TempDir "tide.exe") -Destination $ExePath -Force

# 清理临时文件
Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "`n✔ Tide 安装成功！" -ForegroundColor Green
Write-Host "=> 安装位置: $ExePath" -ForegroundColor Green

# 4. 检查与添加 PATH
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$InstallDir*") {
    Write-Host "=> 正在将 $InstallDir 添加到用户 PATH 环境变量..." -ForegroundColor Yellow
    [Environment]::SetEnvironmentVariable("Path", "$UserPath;$InstallDir", "User")
    $env:Path = "$env:Path;$InstallDir"
    Write-Host "✔ 已成功将 Tide 添加至 PATH。" -ForegroundColor Green
}

Write-Host "`n=> 版本验证:" -ForegroundColor Cyan
& $ExePath --version

Write-Host "`n快速开始:" -ForegroundColor Cyan
Write-Host "  1. 打开新的终端窗口，输入 tide 即可启动"
Write-Host "  2. 首次启动输入 /model 配置 API Key 或切换模型平台"
Write-Host "  3. 输入 /think 或按 Ctrl+T 打开深度思考看板`n"
