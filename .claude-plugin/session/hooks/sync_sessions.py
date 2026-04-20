#!/usr/bin/env python3
"""Sync session files between a local repo and the central sessions repo.

Usage:
    sync_sessions.py pull     Pull latest session for current branch from sessions repo
    sync_sessions.py push     Push local session files to sessions repo (ongoing/)
    sync_sessions.py archive  Move sessions from ongoing/ to archive/ in sessions repo
    sync_sessions.py status   Print summary of remote and local session state (read-only)

Environment:
    SESSIONS_REPO_URL  Override the sessions repo URL (for testing)
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# TODO: revert "feat/cross-repo-session-sync" to "main" after sessions-archive branch is merged
DEFAULT_REPO_URL = "git@gitlab.com:tchibo-com/bi/sap-di/claude-sessions-archive.git"
DEFAULT_REPO_BRANCH = "feat/cross-repo-session-sync"

LOG_FILE = Path.home() / ".claude" / "session-sync.log"


def log(msg: str) -> None:
    from datetime import datetime
    with LOG_FILE.open("a") as f:
        f.write(f"[{datetime.now().astimezone().isoformat()}] {msg}\n")


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


def clone_sessions_repo(repo_url: str, tmp_dir: Path, branch: str = DEFAULT_REPO_BRANCH) -> bool:
    result = git("clone", "--depth", "1", "--single-branch", "--branch", branch, repo_url, str(tmp_dir), check=False)
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


def read_frontmatter_field(md_file: Path, field: str) -> str | None:
    """Parse a single frontmatter field from a markdown file."""
    try:
        content = md_file.read_text()
    except (FileNotFoundError, UnicodeDecodeError):
        return None
    match = re.search(rf"^{re.escape(field)}:\s*(.+?)\s*$", content, re.MULTILINE)
    if not match:
        return None
    value = match.group(1).strip()
    if value.lower() in ("null", "none", ""):
        return None
    return value


def cmd_pull(branch: str, local_sessions: Path, tmp_dir: Path) -> None:
    """Pull the latest session for the branch. Falls back to archive/ if ongoing/ is empty."""
    ongoing_dir = tmp_dir / "ongoing" / branch
    archive_dir = tmp_dir / "archive" / branch

    source_dir: Path | None = None
    source_label = ""
    if ongoing_dir.is_dir():
        session_files = sorted(ongoing_dir.glob("session-*.md"))
        if session_files:
            source_dir = ongoing_dir
            source_label = "ongoing"

    if source_dir is None and archive_dir.is_dir():
        session_files = sorted(archive_dir.glob("session-*.md"))
        if session_files:
            source_dir = archive_dir
            source_label = "archive"

    if source_dir is None:
        print("No existing sessions for this branch. Use /session init to create one.")
        return

    session_files = sorted(source_dir.glob("session-*.md"))
    latest = session_files[-1]
    local_sessions.mkdir(parents=True, exist_ok=True)
    shutil.copy2(latest, local_sessions / latest.name)

    print(f"Found {len(session_files)} session(s) for {branch} in {source_label}/.")
    print(f"Pulled latest ({latest.name}) into .claude/sessions/.")
    if source_label == "archive":
        print("Note: this branch was previously archived (completed). Reopening resumes its history.")
    print("Use /session init to open a new session.")


def cmd_push(branch: str, repo_name: str, local_sessions: Path, tmp_dir: Path) -> None:
    if not local_sessions.is_dir():
        return

    session_files = list(local_sessions.glob("session-*.md"))
    if not session_files:
        return

    ongoing_dir = tmp_dir / "ongoing" / branch

    # Concurrent-session guard: detect remote sessions we don't have locally.
    # These indicate someone else pushed to this branch while we were working.
    if ongoing_dir.is_dir():
        local_names = {f.name for f in session_files}
        remote_only = [f for f in ongoing_dir.glob("session-*.md") if f.name not in local_names]
        if remote_only:
            remote_latest = sorted(remote_only)[-1]
            remote_updated = read_frontmatter_field(remote_latest, "updated_at") or "unknown"
            remote_repo = read_frontmatter_field(remote_latest, "repo") or "unknown"
            print(f"Warning: another session was pushed to {branch} while you were working.", file=sys.stderr)
            print(f"  Remote session: {remote_latest.name} (repo: {remote_repo}, updated_at: {remote_updated})", file=sys.stderr)
            print(f"  Your session will be added alongside it -- no data lost, but review their changes before continuing.", file=sys.stderr)
            log(f"PUSH concurrent session detected: {remote_latest.name}")

    ongoing_dir.mkdir(parents=True, exist_ok=True)

    for f in session_files:
        shutil.copy2(f, ongoing_dir / f.name)

    git("add", "-A", cwd=str(tmp_dir))

    diff = git("diff", "--cached", "--quiet", cwd=str(tmp_dir), check=False)
    if diff.returncode == 0:
        log("PUSH no diff, cleaning up local sessions")
        shutil.rmtree(local_sessions)
        return

    git("commit", "-m", f"Sync session from {repo_name}/{branch}", cwd=str(tmp_dir))

    if git_push_with_retry(str(tmp_dir)):
        log("PUSH success, cleaning up local sessions")
        shutil.rmtree(local_sessions)
    else:
        log("PUSH failed, preserving local sessions")
        print("Warning: Could not push to sessions repo. Local sessions preserved.", file=sys.stderr)


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


def cmd_status(branch: str, local_sessions: Path, tmp_dir: Path) -> None:
    """Read-only report of local and remote session state for the current branch."""
    print(f"Branch: {branch}")
    print()

    # Local state
    print("Local:")
    if local_sessions.is_dir():
        local_files = sorted(local_sessions.glob("session-*.md"))
        if local_files:
            for f in local_files:
                updated = read_frontmatter_field(f, "updated_at") or "never"
                status = read_frontmatter_field(f, "status") or "unknown"
                print(f"  {f.name}  (status: {status}, updated_at: {updated})")
        else:
            print("  (no session files)")
    else:
        print("  (no session directory)")
    print()

    # Remote state
    ongoing_dir = tmp_dir / "ongoing" / branch
    archive_dir = tmp_dir / "archive" / branch

    ongoing_count = len(list(ongoing_dir.glob("session-*.md"))) if ongoing_dir.is_dir() else 0
    archive_count = len(list(archive_dir.glob("session-*.md"))) if archive_dir.is_dir() else 0

    print(f"Remote (sessions repo):")
    print(f"  ongoing/{branch}/: {ongoing_count} session(s)")
    print(f"  archive/{branch}/: {archive_count} session(s)")

    if ongoing_count > 0:
        latest = sorted(ongoing_dir.glob("session-*.md"))[-1]
        updated = read_frontmatter_field(latest, "updated_at") or "never"
        repo = read_frontmatter_field(latest, "repo") or "unknown"
        print(f"  Latest ongoing: {latest.name} (repo: {repo}, updated_at: {updated})")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("pull", "push", "archive", "status"):
        print("Usage: sync_sessions.py <pull|push|archive|status>", file=sys.stderr)
        sys.exit(1)

    mode = sys.argv[1]
    log(f"START mode={mode} cwd={Path.cwd()}")

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
        elif mode == "status":
            cmd_status(branch, local_sessions, tmp_dir)
    except Exception as e:
        log(f"ERROR {e}")
        raise
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        log(f"END mode={mode}")


if __name__ == "__main__":
    main()
