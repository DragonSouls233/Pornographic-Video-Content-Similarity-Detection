# 打包脚本 - 将GUI程序打包成EXE文件

Write-Host "=========================================" -ForegroundColor Green
Write-Host "模特查重管理系统 - 打包脚本" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""

# 检查是否存在测试目录，如果不存在则创建
if (-not (Test-Path "F:\测试")) {
    Write-Host "创建测试目录..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path "F:\测试" -Force | Out-Null
}

# 复制核心文件到测试目录
Write-Host "复制核心文件到测试目录..." -ForegroundColor Yellow

# 复制core目录
if (Test-Path "core") {
    Copy-Item -Path "core" -Destination "F:\测试\core" -Recurse -Force
}

# 复制gui目录
if (Test-Path "gui") {
