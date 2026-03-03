#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
用法:
  ./download_youtube_mac.sh -u "<YouTube_URL>" [-c cookies.txt] [-o output_dir] [--fix]

参数:
  -u, --url       必填，YouTube 视频链接
  -c, --cookies   可选，cookies.txt 路径（遇到 bot 校验时建议提供）
  -o, --output    可选，输出目录，默认当前目录
  --fix           可选，下载后执行 ffmpeg 无损重封装并替换原文件
  -h, --help      显示帮助

示例:
  ./download_youtube_mac.sh -u "https://www.youtube.com/watch?v=WvhQLqtVRLY" -c "~/Downloads/cookies.txt" -o "~/Downloads" --fix
EOF
}

expand_path() {
  local p="$1"
  if [[ "$p" == "~"* ]]; then
    p="${HOME}${p:1}"
  fi
  printf '%s' "$p"
}

need_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "缺少命令: $cmd"
    echo "请先安装后重试。macOS 可用: brew install yt-dlp ffmpeg deno"
    exit 1
  fi
}

URL=""
COOKIES=""
OUTPUT_DIR="."
DO_FIX=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -u|--url)
      URL="${2:-}"
      shift 2
      ;;
    -c|--cookies)
      COOKIES="${2:-}"
      shift 2
      ;;
    -o|--output)
      OUTPUT_DIR="${2:-}"
      shift 2
      ;;
    --fix)
      DO_FIX=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "未知参数: $1"
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$URL" ]]; then
  echo "错误: 缺少 --url"
  usage
  exit 1
fi

need_cmd yt-dlp

OUTPUT_DIR="$(expand_path "$OUTPUT_DIR")"
mkdir -p "$OUTPUT_DIR"

JS_ARGS=()
if command -v deno >/dev/null 2>&1; then
  JS_ARGS+=(--js-runtimes deno)
fi

COOKIE_ARGS=()
if [[ -n "$COOKIES" ]]; then
  COOKIES="$(expand_path "$COOKIES")"
  if [[ ! -f "$COOKIES" ]]; then
    echo "错误: cookies 文件不存在: $COOKIES"
    exit 1
  fi
  COOKIE_ARGS+=(--cookies "$COOKIES")
fi

echo "开始下载..."
downloaded_path="$(
  yt-dlp \
    "${JS_ARGS[@]}" \
    "${COOKIE_ARGS[@]}" \
    -f "b[ext=mp4]/b" \
    --no-playlist \
    -o "${OUTPUT_DIR}/%(title)s.%(ext)s" \
    --print "after_move:filepath" \
    "$URL"
)"

downloaded_path="$(printf '%s\n' "$downloaded_path" | tail -n 1)"

if [[ -z "$downloaded_path" || ! -f "$downloaded_path" ]]; then
  echo "下载完成，但未找到输出文件，请检查 yt-dlp 日志。"
  exit 1
fi

echo "下载完成: $downloaded_path"

if [[ "$DO_FIX" -eq 1 ]]; then
  need_cmd ffmpeg

  ext="${downloaded_path##*.}"
  ext_lc="$(printf '%s' "$ext" | tr '[:upper:]' '[:lower:]')"
  if [[ "$ext_lc" != "mp4" ]]; then
    echo "检测到扩展名不是 mp4（.$ext），已跳过无损修复。"
    exit 0
  fi

  base="${downloaded_path%.*}"
  fixed_path="${base}_fixed.mp4"
  backup_path="${base}.bak.mp4"

  echo "开始无损重封装..."
  ffmpeg -y -fflags +genpts -i "$downloaded_path" -map 0 -c copy -movflags +faststart "$fixed_path"

  mv -f "$downloaded_path" "$backup_path"
  mv -f "$fixed_path" "$downloaded_path"

  echo "修复完成: $downloaded_path"
  echo "备份文件: $backup_path"
fi
