# youtube-download-scripts

一个用于 **YouTube 下载** 的小工具仓库，核心流程是：

1. 浏览器插件导出 `cookies.txt`
2. 用脚本调用 `yt-dlp` 下载
3. 可选用 `ffmpeg` 做无损修复（重封装，不重编码）

支持平台：
- Windows（PowerShell 脚本）
- macOS（Bash 脚本）

## 文件说明

- `download_youtube_win.ps1`：Windows 下载脚本
- `download_youtube_mac.sh`：macOS 下载脚本
- `youtube-download-mac-guide.md`：中文详细指南（已包含 Win + Mac）
- `.gitignore`：已忽略视频/音频/图片/压缩包/cookies 等素材文件

## 依赖

必需：
- `yt-dlp`

建议：
- `deno`（用于 YouTube JS challenge）
- `ffmpeg`（用于 `-Fix/--fix` 无损修复）

## 先做这一步：导出 cookies.txt

当遇到 `Sign in to confirm you're not a bot` 时：

1. 登录 YouTube
2. 打开目标视频页面
3. 用插件 `Get cookies.txt LOCALLY` 导出 `cookies.txt`

建议把 `cookies.txt` 放到脚本同目录，下载完成后删除。

## Windows 快速开始

安装依赖（可选）：

```powershell
winget install --id yt-dlp.yt-dlp -e
winget install --id DenoLand.Deno -e
winget install --id Gyan.FFmpeg -e
```

下载：

```powershell
powershell -ExecutionPolicy Bypass -File .\download_youtube_win.ps1 `
  -Url "https://www.youtube.com/watch?v=WvhQLqtVRLY" `
  -Cookies ".\cookies.txt" `
  -Output "."
```

下载并自动无损修复：

```powershell
powershell -ExecutionPolicy Bypass -File .\download_youtube_win.ps1 `
  -Url "https://www.youtube.com/watch?v=WvhQLqtVRLY" `
  -Cookies ".\cookies.txt" `
  -Output "." `
  -Fix
```

## macOS 快速开始

安装依赖：

```bash
brew install yt-dlp ffmpeg deno
```

给脚本执行权限：

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

下载并自动无损修复：

```bash
./download_youtube_mac.sh \
  -u "https://www.youtube.com/watch?v=WvhQLqtVRLY" \
  -c "~/Downloads/cookies.txt" \
  -o "~/Downloads" \
  --fix
```

## 说明

- 请遵守目标平台服务条款和版权要求，仅用于你有权下载的内容。
- `cookies.txt` 属于敏感登录信息，不要上传到代码仓库（本仓库已默认忽略）。
