# Codex 备份（Win + macOS 通用）

这个方案使用同一个脚本和同一种 zip 格式，在 Windows 和 macOS 间互相导出/恢复/合并。

脚本文件：`codex_backup.py`

## 1) 导出备份 zip

Windows:

```powershell
python .\codex_backup.py export --output-dir .\codex-backup
```

macOS:

```bash
python3 ./codex_backup.py export --output-dir ./codex-backup
```

## 2) 导入并合并（恢复）

Windows:

```powershell
python .\codex_backup.py import --backup-zip .\codex-backup\codex-backup-YYYYMMDD-HHMMSS.zip
```

macOS:

```bash
python3 ./codex_backup.py import --backup-zip ./codex-backup/codex-backup-YYYYMMDD-HHMMSS.zip
```

## 3) 可选参数

- `--include-state`: 导出 `state_*.sqlite*`（更接近完整状态迁移）
- `--include-auth`: 导出 `auth.json`/`cap_sid`（敏感，不建议跨账号）
- `--replace-state`: 导入时替换本机 `state_*.sqlite*`
- `--import-auth`: 导入 `auth.json`/`cap_sid`
- `--codex-home <path>`: 指定 Codex 数据目录（默认 `~/.codex` 或 `CODEX_HOME`）

示例（导出时包含 state）：

```bash
python3 ./codex_backup.py export --output-dir ./codex-backup --include-state
```

示例（导入时替换 state）：

```bash
python3 ./codex_backup.py import --backup-zip ./codex-backup/codex-backup-YYYYMMDD-HHMMSS.zip --replace-state
```

## 4) 合并规则

- `sessions / rules / skills`: 按文件哈希去重
- 同路径不同内容：保留为 `*-imported-时间戳.*` 冲突副本
- `history.jsonl`: 逐行去重后追加
- 若文件被运行中的 Codex/VSCode 占用，会记为 `locked` 并跳过，不中断整体导入

## 5) 建议

- 导入前先关闭 Codex/VSCode，减少 `locked` 文件
- 跨账号迁移一般不要导入认证文件（`auth.json`）
