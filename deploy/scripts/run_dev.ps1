# Windows 本地开发：装依赖 + 注入 GITHUB_TOKEN + 启动 server
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSCommandPath))
$serverDir = Join-Path $root "server\python"

Write-Host "=== 安装依赖 ==="
& python -m pip install -q -r (Join-Path $serverDir "requirements.txt")

if (-not (Test-Path (Join-Path $serverDir "config.yaml"))) {
    Copy-Item (Join-Path $serverDir "config.example.yaml") (Join-Path $serverDir "config.yaml")
    Write-Host "已复制 config.example.yaml -> config.yaml；请编辑后再启动" -ForegroundColor Yellow
    return
}

if (-not $env:GITHUB_TOKEN) {
    try {
        $tok = (gh auth token).Trim()
        if ($tok) {
            $env:GITHUB_TOKEN = $tok
            Write-Host "已从 gh CLI 注入 GITHUB_TOKEN（仅当前进程）"
        }
    } catch {
        Write-Host "未检测到 GITHUB_TOKEN；如需远端 push/pull，请先 gh auth login 或手动 set" -ForegroundColor Yellow
    }
}

Write-Host "=== 启动 ling-server ==="
Set-Location $serverDir
python -m ling_server.cli -c config.yaml --verbose serve
