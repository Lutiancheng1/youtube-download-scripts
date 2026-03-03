#!/usr/bin/env python3
"""Cross-platform Codex backup tool for export/import/merge.

Works on Windows and macOS (also Linux) with a single zip format.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


TEXT_FILES = ("history.jsonl", "config.toml", "version.json")
DIR_NAMES = ("sessions", "rules", "skills")
AUTH_FILES = ("auth.json", "cap_sid")


@dataclass
class MergeStats:
    copied_new: int = 0
    skipped_same: int = 0
    copied_conflict: int = 0
    skipped_locked: int = 0


@dataclass
class HistoryStats:
    appended: int = 0
    skipped_same: int = 0


def timestamp_local() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def timestamp_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def detect_codex_home(override: str | None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    env_home = os.environ.get("CODEX_HOME")
    if env_home:
        return Path(env_home).expanduser().resolve()
    return (Path.home() / ".codex").resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def copy_file_if_exists(source: Path, target: Path) -> bool:
    if not source.exists():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return True


def copy_dir_content_if_exists(source_dir: Path, target_dir: Path) -> bool:
    if not source_dir.is_dir():
        return False
    target_dir.mkdir(parents=True, exist_ok=True)
    for item in source_dir.iterdir():
        dst = target_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dst)
    return True


def zip_payload(payload_root: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(payload_root.rglob("*")):
            if path.is_file():
                arcname = path.relative_to(payload_root).as_posix()
                zf.write(path, arcname)


def export_backup(args: argparse.Namespace) -> int:
    codex_home = detect_codex_home(args.codex_home)
    if not codex_home.exists():
        raise RuntimeError(f"Cannot find Codex home: {codex_home}")

    stamp = timestamp_local()
    stage_root = Path(tempfile.mkdtemp(prefix=f"codex-export-{stamp}-"))
    payload_root = stage_root / "payload"
    payload_root.mkdir(parents=True, exist_ok=True)

    copied_items: list[str] = []
    try:
        for name in TEXT_FILES:
            if copy_file_if_exists(codex_home / name, payload_root / name):
                copied_items.append(name)

        for name in DIR_NAMES:
            if copy_dir_content_if_exists(codex_home / name, payload_root / name):
                copied_items.append(name)

        if args.include_state:
            state_files = [p for p in codex_home.glob("state_*.sqlite*") if p.is_file()]
            for path in state_files:
                shutil.copy2(path, payload_root / path.name)
            if state_files:
                copied_items.append("state_*.sqlite*")

        if args.include_auth:
            for name in AUTH_FILES:
                if copy_file_if_exists(codex_home / name, payload_root / name):
                    copied_items.append(name)

        metadata = {
            "format": "codex-backup-v2",
            "created_at_utc": timestamp_utc_iso(),
            "platform": platform.platform(),
            "python_version": sys.version.split()[0],
            "codex_home": str(codex_home),
            "include_state": bool(args.include_state),
            "include_auth": bool(args.include_auth),
            "copied_items": copied_items,
        }
        (payload_root / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        output_dir = Path(args.output_dir).expanduser().resolve()
        zip_path = output_dir / f"codex-backup-{stamp}.zip"
        zip_payload(payload_root, zip_path)

        print(f"Export completed: {zip_path}")
        print("Included: " + (", ".join(copied_items) if copied_items else "(none)"))
        print("Tip: keep auth.json private; only include it for same-account migration.")
        return 0
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)


def resolve_payload_root(extract_root: Path) -> Path:
    payload = extract_root / "payload"
    return payload if payload.is_dir() else extract_root


def resolve_compat_source_dir(payload_root: Path, name: str) -> Path:
    direct = payload_root / name
    if not direct.is_dir():
        return direct

    nested = direct / name
    if nested.is_dir():
        children = list(direct.iterdir())
        if len(children) == 1 and children[0].is_dir() and children[0].name == name:
            return nested
    return direct


def merge_directory(source_dir: Path, target_dir: Path, stamp: str) -> MergeStats:
    stats = MergeStats()
    if not source_dir.is_dir():
        return stats

    target_dir.mkdir(parents=True, exist_ok=True)
    for src in source_dir.rglob("*"):
        if not src.is_file():
            continue

        try:
            rel = src.relative_to(source_dir)
        except ValueError:
            rel = Path(src.name)

        dest = target_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)

        if not dest.exists():
            try:
                shutil.copy2(src, dest)
                stats.copied_new += 1
            except OSError:
                stats.skipped_locked += 1
            continue

        try:
            if sha256_file(src) == sha256_file(dest):
                stats.skipped_same += 1
                continue
        except OSError:
            stats.skipped_locked += 1
            continue

        conflict = dest.with_name(f"{dest.stem}-imported-{stamp}{dest.suffix}")
        idx = 1
        while conflict.exists():
            conflict = dest.with_name(f"{dest.stem}-imported-{stamp}-{idx}{dest.suffix}")
            idx += 1

        try:
            shutil.copy2(src, conflict)
            stats.copied_conflict += 1
        except OSError:
            stats.skipped_locked += 1

    return stats


def merge_history_jsonl(source_file: Path, target_file: Path) -> HistoryStats:
    stats = HistoryStats()
    if not source_file.is_file():
        return stats

    target_file.parent.mkdir(parents=True, exist_ok=True)
    if not target_file.exists():
        shutil.copy2(source_file, target_file)
        with target_file.open("r", encoding="utf-8", errors="replace") as f:
            stats.appended = sum(1 for _ in f)
        return stats

    existing: set[str] = set()
    with target_file.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            existing.add(line.rstrip("\r\n"))

    with source_file.open("r", encoding="utf-8", errors="replace") as sf, target_file.open(
        "a", encoding="utf-8"
    ) as tf:
        for line in sf:
            key = line.rstrip("\r\n")
            if key in existing:
                stats.skipped_same += 1
                continue
            existing.add(key)
            tf.write(line if line.endswith("\n") else line + "\n")
            stats.appended += 1

    return stats


def replace_state_files(payload_root: Path, codex_home: Path, stamp: str) -> str:
    state_files = [p for p in payload_root.glob("state_*.sqlite*") if p.is_file()]
    if not state_files:
        return "ReplaceState enabled, but no state_*.sqlite* files found in backup."

    backup_dir = codex_home / f"state-backup-{stamp}"
    existing_state = [p for p in codex_home.glob("state_*.sqlite*") if p.is_file()]
    if existing_state:
        backup_dir.mkdir(parents=True, exist_ok=True)
        for src in existing_state:
            shutil.move(str(src), str(backup_dir / src.name))
    for src in state_files:
        shutil.copy2(src, codex_home / src.name)

    if existing_state:
        return f"State replaced. Old state files moved to: {backup_dir}"
    return "State replaced."


def import_backup(args: argparse.Namespace) -> int:
    backup_zip = Path(args.backup_zip).expanduser().resolve()
    if not backup_zip.is_file():
        raise RuntimeError(f"Backup zip not found: {backup_zip}")

    codex_home = detect_codex_home(args.codex_home)
    codex_home.mkdir(parents=True, exist_ok=True)

    extract_root = Path(tempfile.mkdtemp(prefix="codex-import-"))
    stamp = timestamp_local()
    try:
        with zipfile.ZipFile(backup_zip, "r") as zf:
            zf.extractall(extract_root)

        payload_root = resolve_payload_root(extract_root)
        sessions_source = resolve_compat_source_dir(payload_root, "sessions")
        rules_source = resolve_compat_source_dir(payload_root, "rules")
        skills_source = resolve_compat_source_dir(payload_root, "skills")

        print(f"Import source: {backup_zip}")
        print(f"Codex home: {codex_home}")
        print("Tip: close Codex/VSCode while importing to avoid state lock issues.")

        sessions_stats = merge_directory(sessions_source, codex_home / "sessions", stamp)
        rules_stats = merge_directory(rules_source, codex_home / "rules", stamp)
        skills_stats = merge_directory(skills_source, codex_home / "skills", stamp)
        history_stats = merge_history_jsonl(payload_root / "history.jsonl", codex_home / "history.jsonl")

        src_config = payload_root / "config.toml"
        dest_config = codex_home / "config.toml"
        if src_config.is_file():
            if not dest_config.exists():
                shutil.copy2(src_config, dest_config)
                print("config.toml copied (target did not exist).")
            else:
                print("config.toml exists; skipped overwrite.")

        if args.replace_state:
            print(replace_state_files(payload_root, codex_home, stamp))
        else:
            print("State files were not replaced.")

        if args.import_auth:
            imported = 0
            for name in AUTH_FILES:
                src = payload_root / name
                if src.is_file():
                    shutil.copy2(src, codex_home / name)
                    imported += 1
                    print(f"{name} imported.")
            if imported == 0:
                print("ImportAuth enabled, but no auth files found in backup.")
        else:
            print("Auth files were not imported.")

        print(
            "Sessions: "
            f"new={sessions_stats.copied_new}, same={sessions_stats.skipped_same}, "
            f"conflict={sessions_stats.copied_conflict}, locked={sessions_stats.skipped_locked}"
        )
        print(
            "Rules:    "
            f"new={rules_stats.copied_new}, same={rules_stats.skipped_same}, "
            f"conflict={rules_stats.copied_conflict}, locked={rules_stats.skipped_locked}"
        )
        print(
            "Skills:   "
            f"new={skills_stats.copied_new}, same={skills_stats.skipped_same}, "
            f"conflict={skills_stats.copied_conflict}, locked={skills_stats.skipped_locked}"
        )
        print(f"History:  appended={history_stats.appended}, same={history_stats.skipped_same}")
        print("Import and merge completed.")
        return 0
    finally:
        shutil.rmtree(extract_root, ignore_errors=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex_backup.py",
        description="Cross-platform Codex backup tool (zip export/import/merge).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    export_p = sub.add_parser("export", help="Create a backup zip from local Codex data.")
    export_p.add_argument("--output-dir", default="./codex-backup", help="Directory for output zip.")
    export_p.add_argument("--codex-home", default=None, help="Override Codex home path.")
    export_p.add_argument("--include-state", action="store_true", help="Include state_*.sqlite* files.")
    export_p.add_argument("--include-auth", action="store_true", help="Include auth.json and cap_sid.")
    export_p.set_defaults(func=export_backup)

    import_p = sub.add_parser("import", help="Import a backup zip and merge into local Codex data.")
    import_p.add_argument("--backup-zip", required=True, help="Backup zip path.")
    import_p.add_argument("--codex-home", default=None, help="Override Codex home path.")
    import_p.add_argument("--replace-state", action="store_true", help="Replace local state_*.sqlite* files.")
    import_p.add_argument("--import-auth", action="store_true", help="Import auth.json and cap_sid from zip.")
    import_p.set_defaults(func=import_backup)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
