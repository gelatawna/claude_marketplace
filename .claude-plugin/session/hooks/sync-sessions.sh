#!/bin/bash
# sync-sessions.sh -- Syncs session files between local repo and the central sessions repo.
#
# Usage:
#   sync-sessions.sh pull    Pull latest session for current branch from sessions repo
#   sync-sessions.sh push    Push local session files to sessions repo (ongoing/)
#   sync-sessions.sh archive Move sessions from ongoing/ to archive/ in sessions repo
#
# Environment:
#   SESSIONS_REPO_URL  Override the sessions repo URL (for testing)
#   SESSIONS_TMP_DIR   Override the temp clone location (for testing)

set -euo pipefail

MODE="${1:-}"
if [[ -z "$MODE" || ! "$MODE" =~ ^(pull|push|archive)$ ]]; then
    echo "Usage: sync-sessions.sh <pull|push|archive>" >&2
    exit 1
fi

SESSIONS_REPO_URL="${SESSIONS_REPO_URL:-git@gitlab.com:tchibo-com/bi/sap-di/claude-sessions-archive.git}"
TMP_DIR="${SESSIONS_TMP_DIR:-/tmp/claude-sessions-sync-$$}"
BRANCH=$(git branch --show-current 2>/dev/null || echo "")
REPO_NAME=$(basename "$(git remote get-url origin 2>/dev/null)" .git 2>/dev/null || echo "unknown")

if [[ -z "$BRANCH" ]]; then
    echo "Not on a git branch. Skipping session sync." >&2
    exit 0
fi

LOCAL_SESSIONS=".claude/sessions/$BRANCH"

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

clone_sessions_repo() {
    if ! git clone --depth 1 --single-branch --branch main "$SESSIONS_REPO_URL" "$TMP_DIR" 2>/dev/null; then
        echo "Warning: Could not reach sessions repo. Session sync skipped." >&2
        exit 0
    fi
}

# --- PULL ---
if [[ "$MODE" == "pull" ]]; then
    clone_sessions_repo

    ONGOING_DIR="$TMP_DIR/ongoing/$BRANCH"
    if [[ -d "$ONGOING_DIR" ]]; then
        SESSION_FILES=( "$ONGOING_DIR"/session-*.md )
        if [[ -e "${SESSION_FILES[0]}" ]]; then
            COUNT=${#SESSION_FILES[@]}
            LATEST=$(printf '%s\n' "${SESSION_FILES[@]}" | sort | tail -1)

            mkdir -p "$LOCAL_SESSIONS"
            cp "$LATEST" "$LOCAL_SESSIONS/"

            echo "Found $COUNT session(s) for $BRANCH in sessions repo."
            echo "Pulled latest ($(basename "$LATEST")) into .claude/sessions/."
            echo "Use /session start to open a new session."
        else
            echo "No existing sessions for this branch. Use /session start to create one."
        fi
    else
        echo "No existing sessions for this branch. Use /session start to create one."
    fi

# --- PUSH ---
elif [[ "$MODE" == "push" ]]; then
    if [[ ! -d "$LOCAL_SESSIONS" ]]; then
        exit 0
    fi

    SESSION_FILES=( "$LOCAL_SESSIONS"/session-*.md )
    if [[ ! -e "${SESSION_FILES[0]}" ]]; then
        exit 0
    fi

    clone_sessions_repo

    ONGOING_DIR="$TMP_DIR/ongoing/$BRANCH"
    mkdir -p "$ONGOING_DIR"
    cp "$LOCAL_SESSIONS"/session-*.md "$ONGOING_DIR/"

    cd "$TMP_DIR"
    git add -A
    if git diff --cached --quiet; then
        echo "Sessions already in sync."
    else
        git commit -m "Sync session from $REPO_NAME/$BRANCH"
        if git push 2>/dev/null; then
            echo "Session synced to sessions repo."
        else
            # Retry once with pull-rebase in case of concurrent push
            git pull --rebase 2>/dev/null && git push 2>/dev/null || {
                echo "Warning: Could not push to sessions repo. Will retry next sync." >&2
            }
        fi
    fi

# --- ARCHIVE ---
elif [[ "$MODE" == "archive" ]]; then
    clone_sessions_repo

    ONGOING_DIR="$TMP_DIR/ongoing/$BRANCH"
    ARCHIVE_DIR="$TMP_DIR/archive/$BRANCH"

    if [[ ! -d "$ONGOING_DIR" ]]; then
        echo "No ongoing sessions to archive for $BRANCH."
        exit 0
    fi

    mkdir -p "$ARCHIVE_DIR"
    cp -r "$ONGOING_DIR"/* "$ARCHIVE_DIR/" 2>/dev/null || true
    rm -rf "$ONGOING_DIR"

    cd "$TMP_DIR"
    git add -A
    if git diff --cached --quiet; then
        echo "Nothing to archive."
    else
        git commit -m "Archive sessions for $BRANCH"
        if git push 2>/dev/null; then
            echo "Sessions archived for $BRANCH."
        else
            git pull --rebase 2>/dev/null && git push 2>/dev/null || {
                echo "Warning: Could not push archive to sessions repo." >&2
            }
        fi
    fi

    # Clean up local sessions
    rm -rf "$LOCAL_SESSIONS"
    echo "Local sessions cleaned up."
fi
