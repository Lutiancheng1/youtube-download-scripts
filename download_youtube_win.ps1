[CmdletBinding()]
param(
    [string]$Url,
    [string]$Cookies,
    [string]$Output = ".",
    [switch]$Fix,
    [switch]$Help
)

function Show-Usage {
    @"
用法:
  powershell -ExecutionPolicy Bypass -File .\download_youtube_win.ps1 -Url "<YouTube_URL>" [-Cookies cookies.txt] [-Output out_dir] [-Fix]

参数:
  -Url       必填，YouTube 视频链接
  -Cookies   可选，cookies.txt 路径（遇到 bot 校验时建议提供）
  -Output    可选，输出目录，默认当前目录
  -Fix       可选，下载后执行 ffmpeg 无损重封装并替换原文件
  -Help      显示帮助

示例:
  powershell -ExecutionPolicy Bypass -File .\download_youtube_win.ps1 -Url "https://www.youtube.com/watch?v=WvhQLqtVRLY" -Cookies ".\cookies.txt" -Output "." -Fix
"@
}

function Expand-PathLite {
    param([string]$PathValue)
    if ([string]::IsNullOrWhiteSpace($PathValue)) { return $PathValue }
    if ($PathValue.StartsWith("~")) {
        $suffix = $PathValue.Substring(1).TrimStart("\", "/")
        return Join-Path $HOME $suffix
    }
    return $PathValue
}

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "缺少命令: $Name。请先安装。可用: winget install --id yt-dlp.yt-dlp -e"
    }
}

try {
    if ($Help) {
        Show-Usage
        exit 0
    }

    if ([string]::IsNullOrWhiteSpace($Url)) {
        Show-Usage
        throw "错误: 缺少 -Url 参数"
    }

    Require-Command "yt-dlp"

    $outputDir = Expand-PathLite $Output
    if (-not (Test-Path -LiteralPath $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    }
    $outputDir = (Resolve-Path -LiteralPath $outputDir).Path

    $cookieArgs = @()
    if (-not [string]::IsNullOrWhiteSpace($Cookies)) {
        $cookiePath = Expand-PathLite $Cookies
        if (-not (Test-Path -LiteralPath $cookiePath)) {
            throw "错误: cookies 文件不存在: $cookiePath"
        }
        $cookiePath = (Resolve-Path -LiteralPath $cookiePath).Path
        $cookieArgs = @("--cookies", $cookiePath)
    }

    $jsArgs = @()
    if (Get-Command deno -ErrorAction SilentlyContinue) {
        $jsArgs = @("--js-runtimes", "deno")
    }

    $marker = "__FILE__"
    $ytArgs = @()
    $ytArgs += $jsArgs
    $ytArgs += $cookieArgs
    $ytArgs += @(
        "-f", "b[ext=mp4]/b",
        "--no-playlist",
        "-o", (Join-Path $outputDir "%(title)s.%(ext)s"),
        "--print", "after_move:${marker}%(filepath)s",
        $Url
    )

    Write-Host "开始下载..."
    $ytLines = @()
    & yt-dlp @ytArgs 2>&1 | Tee-Object -Variable ytLines
    $ytExit = $LASTEXITCODE
    if ($ytExit -ne 0) {
        throw "yt-dlp 下载失败（exit code: $ytExit）"
    }

    $downloadedPath = $ytLines |
        ForEach-Object { "$_" } |
        Where-Object { $_.StartsWith($marker) } |
        Select-Object -Last 1

    if ($downloadedPath) {
        $downloadedPath = $downloadedPath.Substring($marker.Length).Trim('"')
    }

    if ([string]::IsNullOrWhiteSpace($downloadedPath) -or -not (Test-Path -LiteralPath $downloadedPath)) {
        $latest = Get-ChildItem -LiteralPath $outputDir -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($latest) {
            $downloadedPath = $latest.FullName
        }
    }

    if ([string]::IsNullOrWhiteSpace($downloadedPath) -or -not (Test-Path -LiteralPath $downloadedPath)) {
        throw "下载完成，但未定位到输出文件。请检查 yt-dlp 输出。"
    }

    Write-Host "下载完成: $downloadedPath"

    if ($Fix) {
        Require-Command "ffmpeg"

        $ext = [System.IO.Path]::GetExtension($downloadedPath)
        if ($ext.ToLowerInvariant() -ne ".mp4") {
            Write-Host "检测到扩展名不是 mp4（$ext），已跳过无损修复。"
            exit 0
        }

        $dir = [System.IO.Path]::GetDirectoryName($downloadedPath)
        $name = [System.IO.Path]::GetFileNameWithoutExtension($downloadedPath)
        $fixedPath = Join-Path $dir ($name + "_fixed.mp4")
        $backupPath = Join-Path $dir ($name + ".bak.mp4")

        Write-Host "开始无损重封装..."
        & ffmpeg -y -fflags +genpts -i $downloadedPath -map 0 -c copy -movflags +faststart $fixedPath
        if ($LASTEXITCODE -ne 0) {
            throw "ffmpeg 修复失败（exit code: $LASTEXITCODE）"
        }

        Move-Item -LiteralPath $downloadedPath -Destination $backupPath -Force
        Move-Item -LiteralPath $fixedPath -Destination $downloadedPath -Force

        Write-Host "修复完成: $downloadedPath"
        Write-Host "备份文件: $backupPath"
    }
}
catch {
    Write-Error $_
    exit 1
}


