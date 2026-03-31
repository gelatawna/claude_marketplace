#!/usr/bin/env python3
"""Sync session files between a local repo and the central sessions repo.

Usage:
    sync_sessions.py pull     Pull latest session for current branch from sessions repo
    sync_sessions.py push     Push local session files to sessions repo (ongoing/)
    sync_sessions.py archive  Move sessions from ongoing/ to archive/ in sessions repo

Environment:
    SESSIONS_REPO_URL  Override the sessions repo URL (for testing)
"""

import glob
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_REPO_URL = "git@gitlab.com:tchibo-com/bi/sap-di/claude-sessions-archive.git"


def git(*args: str, cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


def get_branch() -> str | None:
    result = git("branch", "--show-current", check=False)
    return result.stdout.strip() or None


def get_repo_name() -> str:
    result = git("remote", "get-url", "origin", check=False)
    url = result.stdout.strip()
    if not url:
        return "unknown"
    return Path(url).stem.removesuffix(".git") if "/" not in Path(url).stem else Path(url).name.removesuffix(".git")


def clone_sessions_repo(repo_url: str, tmp_dir: Path) -> bool:
    result = git("clone", "--depth", "1", "--single-branch", "--branch", "main", repo_url, str(tmp_dir), check=False)
    if result.returncode != 0:
        print("Warning: Could not reach sessions repo. Session sync skipped.", file=sys.stderr)
        return False
    return True


def git_push_with_retry(cwd: str) -> bool:
    result = git("push", cwd=cwd, check=False)
    if result.returncode == 0:
        return True
    # Retry once with pull-rebase in case of concurrent push
    rebase = git("pull", "--rebase", cwd=cwd, check=False)
    if rebase.returncode == 0:
        retry = git("push", cwd=cwd, check=False)
        if retry.returncode == 0:
            return True
    return False


def cmd_pull(branch: str, local_sessions: Path, tmp_dir: Path) -> None:
    ongoing_dir = tmp_dir / "ongoing" / branch

    if not ongoing_dir.is_dir():
        print("No existing sessions for this branch. Use /session start to create one.")
        return

    session_files = sorted(ongoing_dir.glob("session-*.md"))
    if not session_files:
        print("No existing sessions for this branch. Use /session start to create one.")
        return

    latest = session_files[-1]
    local_sessions.mkdir(parents=True, exist_ok=True)
    shutil.copy2(latest, local_sessions / latest.name)

    print(f"Found {len(session_files)} session(s) for {branch} in sessions repo.")
    print(f"Pulled latest ({latest.name}) into .claude/sessions/.")
    print("Use /session start to open a new session.")


def cmd_push(branch: str, repo_name: str, local_sessions: Path, tmp_dir: Path) -> None:
    if not local_sessions.is_dir():
        return

    session_files = list(local_sessions.glob("session-*.md"))
    if not session_files:
        return

    ongoing_dir = tmp_dir / "ongoing" / branch
    ongoing_dir.mkdir(parents=True, exist_ok=True)

    for f in session_files:
        shutil.copy2(f, ongoing_dir / f.name)

    git("add", "-A", cwd=str(tmp_dir))

    diff = git("diff", "--cached", "--quiet", cwd=str(tmp_dir), check=False)
    if diff.returncode == 0:
        print("Sessions already in sync.")
        return

    git("commit", "-m", f"Sync session from {repo_name}/{branch}", cwd=str(tmp_dir))

    if git_push_with_retry(str(tmp_dir)):
        print("Session synced to sessions repo.")
    else:
        print("Warning: Could not push to sessions repo. Will retry next sync.", file=sys.stderr)


def cmd_archive(branch: str, local_sessions: Path, tmp_dir: Path) -> None:
    ongoing_dir = tmp_dir / "ongoing" / branch
    archive_dir = tmp_dir / "archive" / branch

    if not ongoing_dir.is_dir():
        print(f"No ongoing sessions to archive for {branch}.")
        return

    archive_dir.mkdir(parents=True, exist_ok=True)
    for item in ongoing_dir.iterdir():
        dest = archive_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)
    shutil.rmtree(ongoing_dir)

    git("add", "-A", cwd=str(tmp_dir))

    diff = git("diff", "--cached", "--quiet", cwd=str(tmp_dir), check=False)
    if diff.returncode == 0:
        print("Nothing to archive.")
        return

    git("commit", "-m", f"Archive sessions for {branch}", cwd=str(tmp_dir))

    if git_push_with_retry(str(tmp_dir)):
        print(f"Sessions archived for {branch}.")
        if local_sessions.is_dir():
            shutil.rmtree(local_sessions)
            print("Local sessions cleaned up.")
    else:
        print("Warning: Could not push archive to sessions repo. Local sessions preserved.", file=sys.stderr)


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("pull", "push", "archive"):
        print("Usage: sync_sessions.py <pull|push|archive>", file=sys.stderr)
        sys.exit(1)

    mode = sys.argv[1]

    branch = get_branch()
    if not branch:
        print("Not on a git branch. Skipping session sync.", file=sys.stderr)
        sys.exit(0)

    repo_url = os.environ.get("SESSIONS_REPO_URL", DEFAULT_REPO_URL)
    repo_name = get_repo_name()
    orig_dir = Path.cwd()
    local_sessions = orig_dir / ".claude" / "sessions" / branch

    tmp_dir = Path(tempfile.mkdtemp(prefix="claude-sessions-sync-"))
    try:
        if not clone_sessions_repo(repo_url, tmp_dir):
            sys.exit(0)

        if mode == "pull":
            cmd_pull(branch, local_sessions, tmp_dir)
        elif mode == "push":
            cmd_push(branch, repo_name, local_sessions, tmp_dir)
        elif mode == "archive":
            cmd_archive(branch, local_sessions, tmp_dir)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
