# Cross-Repository Session Sync Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Automate session context synchronization across `relational-engine` and `sap_di_etl_monorepo` using Claude Code hooks and a centralized sessions repository, so developers always have the full cross-repo feature context when starting work.

**Architecture:** The `claude-sessions-archive` repository becomes the single source of truth for all session state. Claude Code hooks (`SessionStart`/`SessionEnd`) automatically pull/push session files via a shared shell script. The session skill is reduced from 12 commands to 5, with `send`/`inbox`/`offload`/`resume`/`pause`/`status` replaced by automatic hook-based sync.

**Tech Stack:** Bash (sync script), Claude Code hooks (`hooks.json`), Claude Code skill (SKILL.md markdown specification)

**Repositories:**
- `claude-di-marketplace` (`git@gitlab.com:tchibo-com/bi/sap-di/claude-di-marketplace.git`) -- skill + hooks
- `claude-sessions-archive` (`git@gitlab.com:tchibo-com/bi/sap-di/claude-sessions-archive.git`) -- sessions repo

---

## Context for Implementors

### What This Changes

**Before:** Sessions lived inside each project repo (`.claude/sessions/{branch}/`). Cross-repo communication required manual `send`/`inbox` commands and file copying. Offloading to the archive was a separate manual step before merging.

**After:** The sessions archive repo becomes a centralized sessions hub with `ongoing/` and `archive/` folders. Hooks automatically sync on every Claude Code session start/end. Developers see the full cross-repo feature history without any manual steps. A session for ticket DI-2826 worked on in relational-engine is automatically available when someone opens the monorepo on the same branch.

### Key Design Decisions

1. **Sessions belong to tickets, not repos.** A feature branch like `feat/DI-2826_s4_iproduct_rf` has ONE session timeline regardless of which repo the work happened in. The session frontmatter records which `repo` each session was worked in.

2. **Only the latest session is pulled locally.** Each new session carries forward cumulative context from all previous ones, so pulling the full history is redundant. The sessions repo retains the full history.

3. **Hooks handle git plumbing, skill handles content.** The `SessionStart` hook pulls, the `SessionEnd` hook pushes. The `/session start|save|complete` commands manage session file content. No overlap.

4. **Fail-open on sync errors.** If the sessions repo is unreachable, the hook logs a warning and continues. Local development is never blocked by sync failures.

### File Path Convention

Session files reference code paths with the repo name as a root prefix:
- `relational-engine/tchibo_relational_engine/orm_models/deferred_reflections.py`
- `sap_di_etl_monorepo/data_intelligence/orm_models/datasphere_raw/iproduct.py`

This makes paths unambiguous when sessions span both repos.

---

## Part A: Sessions Repository Restructuring

Work in: `claude-sessions-archive` on branch `feat/cross-repo-session-sync`

### Task A1: Create the new directory structure

**Files:**
- Create: `ongoing/.gitkeep`
- Create: `archive/.gitkeep`

**Step 1: Create feature branch**
```bash
cd /Users/gabriel/Documents/code/tch/claude-sessions-archive
git checkout -b feat/cross-repo-session-sync
```

**Step 2: Create the ongoing and archive directories**
```bash
mkdir -p ongoing archive
touch ongoing/.gitkeep archive/.gitkeep
```

**Step 3: Commit**
```bash
git add ongoing/ archive/
git commit -m "chore: create ongoing/ and archive/ directory structure"
```

### Task A2: Migrate existing sessions to archive

All existing sessions in the repo are from completed/merged branches, so they all go to `archive/`. The migration merges the per-repo folders (`relational-engine/{branch}/`, `sap_di_etl_monorepo/{branch}/`) into unified `archive/{branch}/` folders.

**Step 1: Write the migration script**

Create: `_migrate.sh` (temporary, deleted after use)

```bash
#!/bin/bash
set -euo pipefail

# Migrate from {repo}/{branch}/ to archive/{branch}/
# Sessions from both repos for the same branch merge into one folder

for repo_dir in relational-engine sap_di_etl_monorepo; do
    if [ ! -d "$repo_dir" ]; then
        echo "Skipping $repo_dir (not found)"
        continue
    fi

    # Find all branch directories (skip _index.md, _legacy)
    find "$repo_dir" -mindepth 2 -maxdepth 2 -type d | while read branch_dir; do
        branch_name=$(echo "$branch_dir" | cut -d'/' -f2-)
        target="archive/$branch_name"

        echo "Migrating: $repo_dir/$branch_name -> $target"
        mkdir -p "$target"

        # Copy all files (session-*.md and any other artifacts)
        cp -n "$branch_dir"/* "$target/" 2>/dev/null || true
    done
done

echo ""
echo "Migration complete. Verify, then remove old directories:"
echo "  rm -rf relational-engine/ sap_di_etl_monorepo/"
```

**Step 2: Run the migration and verify**
```bash
chmod +x _migrate.sh
./_migrate.sh
```

Expected: Each branch folder from both repo directories is now in `archive/`. Cross-repo branches (like `feat/DI-2826_s4_iproduct_rf`) have sessions from both repos merged into one folder.

**Step 3: Verify cross-repo merges**

Check that tickets with sessions in both repos were merged correctly:
```bash
# These should show sessions from BOTH repos:
ls archive/feat/DI-2826_s4_iproduct_rf/
# Expected: session-20260313-170751-a1x.md (was in monorepo)
#           session-20260320-123814-j7w.md (was in monorepo)
#           session-20260320-143204-ad0.md (was in RE)
#           session-20260325-074332-k9f.md (was in RE)

ls archive/feat/DI-1141-claude-sessionize-skill/
# Expected: sessions from both repos merged

ls archive/feat/DI-1214-interval-load-strategy/
# Expected: sessions from both repos merged

ls archive/feat/DI-2730-view-management/
# Expected: sessions from both repos merged
```

**Step 4: Handle edge cases**

Some branches exist only in one repo -- these are straightforward moves. Some tickets have different branch names across repos (e.g., `bugfix/DI-2812_interval_numeric_columns` in RE vs `bugfix/DI-2812_crm_loyd_interval_loading_config` in monorepo). These are separate branches doing separate work, so they stay as separate folders in `archive/`.

Non-session files (`ticket-DI-1141.md`, `story-session-offloading.md`, `mock_pk_existence_log.sql`, `DI-2740-ticket.md`) are carried along into the archive branch folder as-is.

Legacy files (`sap_di_etl_monorepo/_legacy/DI-2725_session.md`) go to `archive/_legacy/`.

**Step 5: Remove old structure and clean up**
```bash
rm -rf relational-engine/ sap_di_etl_monorepo/
rm _migrate.sh
```

**Step 6: Commit**
```bash
git add .
git commit -m "refactor: migrate to ongoing/archive structure

Merged per-repo session folders into unified branch folders.
Cross-repo sessions (same ticket) now share one directory.
All existing sessions moved to archive/ (completed branches)."
```

### Task A3: Update the index file

**Files:**
- Modify: `_index.md`

**Step 1: Rewrite _index.md to document the new structure**

```markdown
# Claude Sessions

Central repository for Claude Code session state across the BDAP DI ecosystem.

## Structure

- **`ongoing/`** -- Active feature branch sessions. Synced automatically by Claude Code hooks.
- **`archive/`** -- Completed feature branch sessions. Moved here by `/session complete`.

Each branch folder contains session files sorted chronologically:

    ongoing/feat/DI-XXXX_feature_name/
        session-20260325-074332-k9f.md  (latest -- carries cumulative context)
        session-20260320-143204-ad0.md  (earlier session)

Session files record which repository the work happened in via the `repo` frontmatter field.
```

**Step 2: Commit**
```bash
git add _index.md
git commit -m "docs: update index for new ongoing/archive structure"
```

**Step 3: Push feature branch**
```bash
git push -u origin feat/cross-repo-session-sync
```

---

## Part B: Sync Script

Work in: `claude-di-marketplace` on branch `feat/cross-repo-session-sync`

### Task B1: Create the sync script

**Files:**
- Create: `.claude-plugin/session/hooks/sync-sessions.sh`

**Step 1: Create the hooks directory**
```bash
mkdir -p .claude-plugin/session/hooks
```

**Step 2: Write the sync script**

```bash
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
```

**Step 3: Make executable**
```bash
chmod +x .claude-plugin/session/hooks/sync-sessions.sh
```

**Step 4: Commit**
```bash
git add .claude-plugin/session/hooks/
git commit -m "feat: add session sync script for hook-based cross-repo sync"
```

### Task B2: Test the sync script locally

**Step 1: Test pull with no sessions (new branch)**
```bash
cd /Users/gabriel/Documents/code/tch/relational-engine
git checkout -b feat/TEST-0000_sync-test
./../claude-di-marketplace/.claude-plugin/session/hooks/sync-sessions.sh pull
```
Expected output: `No existing sessions for this branch. Use /session start to create one.`

**Step 2: Test push with a mock session**
```bash
mkdir -p .claude/sessions/feat/TEST-0000_sync-test
cat > .claude/sessions/feat/TEST-0000_sync-test/session-20260331-120000-tst.md << 'EOF'
---
session_id: 20260331-120000-tst
branch: feat/TEST-0000_sync-test
ticket: TEST-0000
repo: relational-engine
status: active
started_at: 2026-03-31T12:00:00
ended_at: null
---

## Goal

Test session for sync verification.
EOF

./../claude-di-marketplace/.claude-plugin/session/hooks/sync-sessions.sh push
```
Expected output: `Session synced to sessions repo.`

**Step 3: Verify in sessions repo**
```bash
cd /Users/gabriel/Documents/code/tch/claude-sessions-archive
git pull
ls ongoing/feat/TEST-0000_sync-test/
```
Expected: `session-20260331-120000-tst.md`

**Step 4: Test pull from the other repo**
```bash
cd /Users/gabriel/Documents/code/tch/sap_di_etl_monorepo
git checkout -b feat/TEST-0000_sync-test
./../claude-di-marketplace/.claude-plugin/session/hooks/sync-sessions.sh pull
```
Expected output: `Found 1 session(s) for feat/TEST-0000_sync-test in sessions repo.`

Verify the file was pulled:
```bash
cat .claude/sessions/feat/TEST-0000_sync-test/session-20260331-120000-tst.md
```
Expected: The test session file with `repo: relational-engine`.

**Step 5: Test archive**
```bash
cd /Users/gabriel/Documents/code/tch/relational-engine
./../claude-di-marketplace/.claude-plugin/session/hooks/sync-sessions.sh archive
```
Expected output: `Sessions archived for feat/TEST-0000_sync-test.`

Verify:
```bash
cd /Users/gabriel/Documents/code/tch/claude-sessions-archive
git pull
ls archive/feat/TEST-0000_sync-test/
# Expected: session-20260331-120000-tst.md
ls ongoing/feat/TEST-0000_sync-test/ 2>/dev/null
# Expected: directory does not exist
```

**Step 6: Clean up test branches and data**
```bash
# Clean up test branches
cd /Users/gabriel/Documents/code/tch/relational-engine
rm -rf .claude/sessions/feat/TEST-0000_sync-test
git checkout -

cd /Users/gabriel/Documents/code/tch/sap_di_etl_monorepo
rm -rf .claude/sessions/feat/TEST-0000_sync-test
git checkout -

# Clean up test data in sessions repo
cd /Users/gabriel/Documents/code/tch/claude-sessions-archive
rm -rf archive/feat/TEST-0000_sync-test
git add -A && git commit -m "chore: clean up sync test data" && git push
```

---

## Part C: Hook Configuration

Work in: `claude-di-marketplace` on branch `feat/cross-repo-session-sync`

### Task C1: Create hooks.json

**Files:**
- Create: `.claude-plugin/session/hooks/hooks.json`

**Step 1: Write the hook configuration**

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/sync-sessions.sh pull",
            "timeout": 30
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/sync-sessions.sh push",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

Note: `SessionStart` matcher is `startup` so it only fires on fresh session start, not on `resume`/`clear`/`compact`. The `SessionEnd` matcher is empty (fires on all session ends).

Timeout is 30 seconds to allow for the git clone + push without blocking too long.

**Step 2: Commit**
```bash
git add .claude-plugin/session/hooks/hooks.json
git commit -m "feat: add SessionStart/SessionEnd hooks for automatic session sync"
```

### Task C2: Update plugin.json to declare hooks

**Files:**
- Modify: `.claude-plugin/session/plugin.json`

**Step 1: Add hooks path to plugin config**

Check the current plugin.json format to determine if hooks are declared there or auto-discovered from the `hooks/` directory. If declaration is needed:

```json
{
  "name": "session",
  "description": "Session management with automatic cross-repo sync via hooks.",
  "version": "0.3.0"
}
```

**Step 2: Commit**
```bash
git add .claude-plugin/session/plugin.json
git commit -m "chore: bump session plugin to v0.3.0"
```

---

## Part D: Update the Session Skill

Work in: `claude-di-marketplace` on branch `feat/cross-repo-session-sync`

### Task D1: Rewrite SKILL.md

**Files:**
- Modify: `.claude-plugin/session/skills/session/SKILL.md`

**Step 1: Write the new skill specification**

The full new SKILL.md follows. Key changes from the previous version:
- **Removed commands**: `send`, `inbox`, `offload`, `resume`, `pause`, `status` (replaced by hooks)
- **Updated commands**: `save` now calls sync script, `complete` now archives
- **New frontmatter field**: `repo` in session files
- **New file path convention**: `{repo}/relative/path`
- **Updated allowed-tools**: added sync script execution

```yaml
---
name: session
description: Manage conversation sessions with automatic cross-repo sync
argument-hint: start|save|complete|rule|commit-msg [args]
disable-model-invocation: true
allowed-tools:
  - Read(.claude/sessions/**)
  - Read(.claude/rules/**)
  - Write(.claude/sessions/**)
  - Write(.claude/rules/**)
  - Edit(.claude/sessions/**)
  - Edit(.claude/rules/**)
  - Glob(.claude/sessions/**)
  - Bash(git branch --show-current)
  - Bash(git diff --name-only:*)
  - Bash(ls -la .claude/sessions/**)
  - Bash(stat -f %m .claude/sessions/**)
  - Bash(rm .claude/sessions/**)
  - Bash(mkdir -p .claude/sessions/**)
  - Bash(git remote get-url origin)
  - Bash(git add .claude/sessions/**)
  - Bash(git commit:*)
  - Bash(date:*)
  - Bash(mv .claude/sessions/**)
  - Bash(${CLAUDE_PLUGIN_ROOT}/hooks/sync-sessions.sh:*)
---
```

The full SKILL.md content is specified in Task D2.

**Step 2: Verify allowed-tools includes the sync script call**

The key addition is:
```
- Bash(${CLAUDE_PLUGIN_ROOT}/hooks/sync-sessions.sh:*)
```
This allows the `save` and `complete` commands to call the sync script from within the skill.

### Task D2: Write the full SKILL.md content

Replace the entire SKILL.md with the following specification:

````markdown
# Session Management

Execute the session command: **$ARGUMENTS**

## How It Works

Sessions are stored centrally in the **sessions repository** (`claude-sessions-archive`). Claude Code hooks automatically sync session context:

- **On session start**: The `SessionStart` hook pulls the latest session for the current branch from the sessions repo into `.claude/sessions/{branch}/`.
- **On session end**: The `SessionEnd` hook pushes local session files back to the sessions repo.

This means that when you start working on `feat/DI-2826` in `sap_di_etl_monorepo`, you automatically get the latest session context -- even if the last session was worked in `relational-engine`.

## Commands Reference

| Command | Action |
|---------|--------|
| `start` | Create new session on current branch, recap previous context |
| `save` | Persist context snapshot and sync to sessions repo |
| `complete` | Mark session completed, move to archive |
| `rule [topic]` | Interactive rule creation for CLAUDE.md |
| `commit-msg` | Generate a suggested commit message from session context |

## Execution Steps

### 1. Get Current Branch
```bash
git branch --show-current
```

### 2. Parse Ticket (if present)
Extract ticket from branch using pattern: `(DI-\d+|BIFT5-\d+)`
- If found: Jira URL = `https://tchibo.atlassian.net/browse/{TICKET}`
- If not found: omit ticket metadata

### 3. Determine Repository Name
```bash
basename $(git remote get-url origin) .git
```

### 4. Session Path
Sessions are stored locally at: `.claude/sessions/{branch}/session-{TIMESTAMP}-{RAND}.md`

**Naming format**: `session-{YYYYMMDD}-{HHMMSS}-{rand3}.md`
- Example: `session-20260128-143022-x7k.md`
- Timestamp from session start time
- 3-character random suffix for collision resistance

## Command Behaviors

### start
1. Check for existing session files in `.claude/sessions/{branch}/`
   - These may have been pulled by the `SessionStart` hook from the sessions repo
   - Or may be left over from a previous local session
2. If sessions found, **Session Context Recap**:
   - Read the latest session file completely (it carries cumulative context from all prior sessions)
   - Extract and present:
     - **Goal**: What the feature/ticket aims to accomplish
     - **Repo**: Which repository the last session was worked in
     - **Context sections**: Current Understanding, Codebase Understanding, Working Memory
     - **Plan**: Approach, steps, constraints (if present)
     - **Decisions**: Key decisions with alternatives and rationale
     - **Progress**: Completed items with learnings, pending items
     - **Open Questions**: Unresolved questions
   - Present recap to user:
     ```
     ## Session Context

     Last session: {session-id} ({status}) -- worked in {repo}

     **Goal**: {goal summary}
     **Plan Progress**: {checked/total steps, or "no plan"}
     **Key Progress**: {bullet list of key accomplishments}
     **Key Decisions**: {decisions with (human decision)/(agent default) tags}
     **Pending**: {items that remain unfinished}
     **Open Questions**: {unresolved questions}
     ```
3. If no sessions found, report: "No previous sessions for this branch. Starting fresh."
4. Generate new session filename: `session-{YYYYMMDD}-{HHMMSS}-{rand3}.md`
5. Create session file with YAML frontmatter and all required sections:
   - **repo**: Set to current repository name
   - **Plan**: Carry forward from previous session or create placeholder
   - **Context**: Pre-populate with knowledge from previous session
   - **Decisions**: Carry forward unresolved decisions
   - **Progress**: Carry forward pending items
   - Open Questions: Carry forward unresolved questions
6. Ask: "What would you like to focus on?"

### save
1. Update Plan section (check off completed steps, add new steps if needed)
2. Update Context section with current knowledge
   - File paths use `{repo}/relative/path` format (e.g., `relational-engine/tchibo_relational_engine/orm_models/deferred_reflections.py`)
3. Update Decisions section with any new decisions made
4. Update Progress items (with `(human decision)`/`(agent default)` annotations)
5. Update Files Changed from git: `git diff --name-only`
6. Keep status unchanged
7. Sync to sessions repo:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/hooks/sync-sessions.sh push
   ```
8. Report: "Session saved and synced to sessions repo."

### complete
1. Persist final context snapshot (same as save steps 1-5)
2. Set `status: completed`
3. Set `ended_at` timestamp
4. If Plan has unchecked steps: mark them as abandoned with a note, or check them if completed
5. Prompt for final summary
6. Archive in sessions repo (moves from `ongoing/` to `archive/`):
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/hooks/sync-sessions.sh push
   ${CLAUDE_PLUGIN_ROOT}/hooks/sync-sessions.sh archive
   ```
7. Clean up local session files:
   ```bash
   rm -rf .claude/sessions/{branch}/
   ```
8. Report: "Session completed and archived."

### commit-msg
Generate a suggested commit message based on the current session context.

1. Verify an active session exists on the current branch; if not, report error
2. Read the current session file
3. Get the ticket ID from session frontmatter (`ticket` field)
4. Run `git diff --name-only` to see staged and unstaged changes
5. Compose a commit message:
   - Format: `[{TICKET}] {concise summary}` (e.g., `[DI-1214] add interval-based extraction strategy`)
   - If no ticket in frontmatter: omit the bracket prefix
   - Summary derived from: Goal, Plan steps (if present), and Progress.Completed items
   - Imperative mood, max ~72 characters
   - Focus on the *what* and *why*, not the *how*
6. Output the suggestion to the user (do **not** stage or commit):
   ```
   Suggested commit message:

   [{TICKET}] {summary}

   Copy and use with: git commit -m "[{TICKET}] {summary}"
   ```
7. If the diff shows multiple logical changes, suggest multiple commit messages (one per logical group)

### rule [topic]
Interactive rule creation/refinement for `.claude/rules/` directory.

**Purpose**: Capture learnings, conventions, and decisions as persistent rules that Claude will follow in future sessions. Rules are automatically loaded by Claude Code.

**Rule Storage**:
- Project rules: `.claude/rules/{topic}.md` - shared via source control

**Interactive Loop**:
1. If topic provided, use as filename base. Otherwise ask: "What topic should this rule cover?"

2. **Clarification questions** (ask as needed):
   - "What specific behavior should this rule enforce?"
   - "Can you give an example of correct vs incorrect behavior?"
   - "Should this apply to all files or specific paths?" (for path-scoped rules)
   - "Are there exceptions to this rule?"
   - "What's the rationale? (helps Claude understand intent)"

3. **Draft the rule file**: Create a focused markdown file
   - Show the draft to user
   - Ask: "Does this capture your intent? Any refinements?"

4. **Iterate**: Refine based on feedback until user approves

5. **Write rule file**: Create/update the rule file at `.claude/rules/{topic}.md`

**Rule File Format**:
```markdown
# {Topic} Rules

- Rule 1: Be specific and actionable
- Rule 2: Include rationale when helpful
- Rule 3: Group related rules together
```

**Path-Scoped Rules** (optional frontmatter):
```markdown
---
paths:
  - "src/api/**/*.py"
  - "src/services/**/*.py"
---

# API Development Rules

- All API endpoints must include input validation
- Use the standard error response format
- Include OpenAPI documentation comments
```

## Session File Format

```yaml
---
session_id: {YYYYMMDD-HHMMSS-rand}
branch: {branch-name}
ticket: {TICKET-ID}           # Optional
ticket_url: {JIRA-URL}        # Optional
repo: {repository-name}       # e.g., relational-engine or sap_di_etl_monorepo
status: active|completed|abandoned
started_at: {ISO-8601}
ended_at: {ISO-8601|null}
---
```

### Required Sections
- **Goal**: What the session aims to accomplish
- **Plan** *(optional)*: Structured plan for the session. Contains subsections:
  - **Approach**: High-level approach description
  - **Steps**: Checklist (`- [ ]` / `- [x]`) of concrete steps to execute
  - **Constraints / Non-Goals**: What is explicitly out of scope
- **Context**: Current Understanding, Codebase Understanding, Working Memory, Open Questions, Next Steps
  - **File paths**: Always use `{repo}/relative/path` format
- **Decisions**: Key decisions made during the session. Each entry records:
  - What was decided
  - Alternatives considered (briefly)
  - Rationale for the choice
  - Who decided: `(human decision)` or `(agent default)`
- **Progress**: Completed, In Progress, Pending (be verbose - capture learnings along the way). Annotate each item with `(human decision)` if the user explicitly directed the approach, or `(agent default)` if Claude chose autonomously.
- **Files Changed**: List from git diff, using `{repo}/relative/path` format

## Reading Sessions (on start)

Read the latest session file in order:
1. Frontmatter -> status, branch, ticket, repo
2. Goal -> objective
3. Plan -> approach, step checklist, constraints (if present)
4. Context.Current Understanding -> mental model
5. Context.Codebase Understanding -> explored files
6. Context.Working Memory -> key facts
7. Context.Open Questions -> unresolved items
8. Context.Next Steps -> where to pick up
9. Decisions -> what was decided, alternatives, rationale, human vs agent
10. Progress -> completed vs pending (includes learnings, context, and human/agent annotations)

Only after loading all context, summarize to user and ask how to proceed.

## Automatic Sync (Hooks)

The session plugin registers two hooks that run automatically:

| Hook | Trigger | Action |
|------|---------|--------|
| `SessionStart` | Claude Code session begins | Pull latest session from sessions repo |
| `SessionEnd` | Claude Code session terminates | Push local session files to sessions repo |

The hooks call `sync-sessions.sh` with `pull` or `push`. If the sessions repo is unreachable, the hooks fail silently and log a warning.

**What this means for you:**
- When you open Claude Code on a feature branch, the latest session context is already available locally
- When you close Claude Code, your session state is automatically pushed to the central repo
- When your colleague opens the same feature branch (even in a different repo), they see your latest context
- You never need to manually copy session files between repos
````

**Step 3: Commit**
```bash
git add .claude-plugin/session/skills/session/SKILL.md
git commit -m "feat: rewrite session skill for hook-based cross-repo sync

Removed: send, inbox, offload, resume, pause, status commands
Updated: save (now syncs to sessions repo), complete (now archives)
Added: repo frontmatter field, {repo}/path file path convention
Added: automatic sync documentation section"
```

---

## Part E: Team Onboarding Documentation

Work in: `claude-sessions-archive` on branch `feat/cross-repo-session-sync`

### Task E1: Write the onboarding guide

**Files:**
- Create: `docs/onboarding/session-workflow.md` (in the `claude-di-marketplace` repo)

Write the team onboarding guide as a standalone document. See `docs/onboarding/session-workflow.md` for the full content (created alongside this plan).

---

## Execution Order Summary

| Order | Task | Repository | Depends on |
|-------|------|------------|------------|
| 1 | A1: Create directory structure | sessions-archive | -- |
| 2 | A2: Migrate existing sessions | sessions-archive | A1 |
| 3 | A3: Update index | sessions-archive | A2 |
| 4 | B1: Create sync script | marketplace | -- |
| 5 | B2: Test sync script | marketplace + both repos | A2, B1 |
| 6 | C1: Create hooks.json | marketplace | B1 |
| 7 | C2: Update plugin.json | marketplace | C1 |
| 8 | D1-D2: Rewrite SKILL.md | marketplace | C1 |
| 9 | E1: Write onboarding guide | marketplace | all above |

Tasks A1-A3 and B1 can be done in parallel (different repos). B2 requires both A2 and B1.

## Testing Checklist

After all tasks are complete, verify end-to-end:

- [ ] Fresh `SessionStart` hook in relational-engine on a branch with no sessions -> prints "No existing sessions"
- [ ] `/session start` in relational-engine creates a session file with `repo: relational-engine`
- [ ] `/session save` pushes the session to `ongoing/` in sessions repo
- [ ] `SessionEnd` (close Claude Code) pushes session automatically
- [ ] `SessionStart` hook in sap_di_etl_monorepo on same branch -> pulls the session from relational-engine
- [ ] `/session start` in sap_di_etl_monorepo shows recap with "Last session worked in relational-engine"
- [ ] New session file has `repo: sap_di_etl_monorepo`
- [ ] `/session complete` moves sessions from `ongoing/` to `archive/`
- [ ] Archived branch folder no longer appears in `ongoing/`
- [ ] Sync script handles unreachable sessions repo gracefully (warning, no crash)
- [ ] Sync script handles concurrent pushes (pull-rebase retry)
