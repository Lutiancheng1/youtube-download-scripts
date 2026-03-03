# YouTube 下载指南（Windows + Mac）

这份文档包含你现在这套可用方案：`插件导出 cookies.txt + 脚本下载`，支持 Windows 和 macOS。

## 1. 核心思路

1. 用 `yt-dlp` 下载 YouTube。
2. 被风控（`Sign in to confirm you're not a bot`）时，导出浏览器 `cookies.txt`。
3. 下载命令或脚本里加 `--cookies`。
4. 如需修复拖动/时间戳问题，用 `ffmpeg` 做无损重封装（不重编码）。

## 2. 先导出 cookies.txt（通用）

1. 打开 Chrome 并登录你的 YouTube 账号。
2. 打开要下载的视频页面。
3. 使用扩展 `Get cookies.txt LOCALLY` 导出。
4. 保存为本地文件，比如：
   - Windows: `C:\Users\你的用户名\Downloads\cookies.txt`
   - Mac: `~/Downloads/cookies.txt`

注意：`cookies.txt` 是登录态敏感文件，下载结束建议删除。

## 3. Windows 教程

### 3.1 安装依赖（推荐用 winget）

```powershell
winget install --id yt-dlp.yt-dlp -e
winget install --id DenoLand.Deno -e
winget install --id Gyan.FFmpeg -e
```

检查：

```powershell
yt-dlp --version
deno --version
ffmpeg -version
```

### 3.2 使用 Windows 脚本

脚本文件：`download_youtube_win.ps1`

在脚本目录执行（可临时绕过执行策略）：

```powershell
powershell -ExecutionPolicy Bypass -File .\download_youtube_win.ps1 `
  -Url "https://www.youtube.com/watch?v=WvhQLqtVRLY" `
  -Cookies ".\cookies.txt" `
  -Output "."
```

下载后顺便做无损修复：

```powershell
powershell -ExecutionPolicy Bypass -File .\download_youtube_win.ps1 `
  -Url "https://www.youtube.com/watch?v=WvhQLqtVRLY" `
  -Cookies ".\cookies.txt" `
  -Output "." `
  -Fix
```

## 4. macOS 教程

### 4.1 安装依赖

```bash
brew install yt-dlp ffmpeg deno
```

检查：

```bash
yt-dlp --version
ffmpeg -version
deno --version
```

### 4.2 使用 Mac 脚本

脚本文件：`download_youtube_mac.sh`

先给执行权限：

```bash
chmod +x download_youtube_mac.sh
```

下载：

```bash
./download_youtube_mac.sh \
  -u "https://www.youtube.com/watch?v=WvhQLqtVRLY" \
  -c "~/Downloads/cookies.txt" \
  -o "~/Downloads"
```

下载后顺便做无损修复：

```bash
./download_youtube_mac.sh \
  -u "https://www.youtube.com/watch?v=WvhQLqtVRLY" \
  -c "~/Downloads/cookies.txt" \
  -o "~/Downloads" \
  --fix
```

## 5. 常见问题

### 5.1 报 `Sign in to confirm you're not a bot`

- 重新导出最新 `cookies.txt` 并重试。

### 5.2 报 `No supported JavaScript runtime`

- 安装 `deno`，并确认 `deno --version` 正常。
- 下载时加 `--js-runtimes deno`（脚本会自动尝试）。

### 5.3 视频能播放但拖动不顺

- 用 `ffmpeg` 无损重封装（脚本的 `-Fix/--fix` 已内置）：

```bash
ffmpeg -y -fflags +genpts -i "video.mp4" -map 0 -c copy -movflags +faststart "video_fixed.mp4"
```

## 6. 清理建议

- 删除 `cookies.txt`：
  - Windows: `del cookies.txt`
  - Mac: `rm -f ~/Downloads/cookies.txt`
