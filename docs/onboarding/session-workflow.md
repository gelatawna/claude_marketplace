# Session Workflow Guide

How the DI team uses Claude Code sessions to maintain context across conversations, repositories, and team members.

## Prerequisites

1. Claude Code installed and configured
2. The `session` plugin installed from `claude-di-marketplace`
3. Git SSH access to `claude-sessions-archive` (`git@gitlab.com:tchibo-com/bi/sap-di/claude-sessions-archive.git`)
4. Session rules file added to your repository (see [Setup](#setup) below)

## Quick Start

```
1. Open Claude Code on your feature branch
   -> Hook pulls latest session context automatically

2. /session init
   -> Shows recap of previous work, creates new session

3. Do your work...

4. /session save    <-- IMPORTANT: run this before closing
   -> Claude updates the session file with current context and pushes

5. Close Claude Code
   -> Hook pushes the session file to the central repo

Done. Your colleague can now pick up where you left off.
```

> **Note:** You must run `/session save` manually before closing. Automatic
> session compaction (updating the file from the conversation on close) is
> not yet working -- the SessionEnd hook only pushes the file in whatever
> state it was last saved in. If you forget to save, the session file gets
> pushed with its state at `/session init` time, losing in-session progress.

## What Are Sessions?

A session is a markdown file that captures the context of a Claude Code conversation: what you're working on, what you've learned, what decisions were made, and what's left to do. Each new session builds on the previous one, carrying forward cumulative context.

Sessions are stored centrally in the `claude-sessions-archive` repository, organized by branch:

```
claude-sessions-archive/
  ongoing/                           <-- active feature work
    feat/DI-2826_s4_iproduct_rf/
      session-20260325-074332-k9f.md
  archive/                           <-- completed features
    feat/BIFT5-9482_cursor_timeout/
      session-20260218-121310-68b.md
```

Sessions belong to **tickets/features**, not to specific repositories. A session for `DI-2826` worked on in `relational-engine` is the same session timeline as work on `DI-2826` in `sap_di_etl_monorepo`.

## How Sync Works

Two Claude Code hooks handle synchronization automatically:

**SessionStart hook** (when you open Claude Code):
- Detects your current branch and ticket
- Pulls the latest session from `ongoing/` in the sessions repo
- Copies it to your local `.claude/sessions/{branch}/`
- Prints what it found (or "no sessions" for a fresh branch)

**SessionEnd hook** (when you close Claude Code):
- Checks if a local session file exists
- Pushes it to `ongoing/` in the sessions repo
- Runs detached (survives `Ctrl+C`), cleans up local files after successful sync
- No-op if no session was started

This means you never manually copy files between repos. The context flows automatically.

> **Limitation:** The SessionEnd hook only pushes the file as-is. It does NOT
> update the file with context from the current conversation. You must run
> `/session save` manually before closing to capture in-session progress.
> See [Future Improvements](#future-improvements) for the planned fix.

## Commands

| Command | When to use |
|---------|-------------|
| `/session init` | Beginning of every work session. Reads previous context, creates a new session file. |
| `/session save` | Mid-session checkpoint. Persists current context and syncs to the sessions repo. |
| `/session complete` | Feature is done. Marks session completed and moves to `archive/`. |
| `/session rule [topic]` | Capture a convention or decision as a persistent rule in `.claude/rules/`. |
| `/session commit-msg` | Generate a commit message from session context. |

### /session init

Always run this at the beginning of a Claude Code conversation on a feature branch. It:

1. Reads any session files pulled by the SessionStart hook
2. Presents a recap of previous work (goal, progress, decisions, open questions)
3. Creates a new session file that carries forward cumulative context
4. Asks what you want to focus on

Example output:
```
## Session Context

Last session: 20260325-074332-k9f (completed) -- worked in relational-engine

**Goal**: Fix JSON payload structure for REPLICATE replication flows
**Plan Progress**: 7/7 steps complete
**Key Progress**:
  - Added deltaLoadTrigger, globalDeltaPartitionValue, deltaCheckInterval
  - Updated unit tests (52 passing)
**Pending**: Trial-and-error deployment testing against real Datasphere
**Open Questions**: Will Datasphere accept ABAPcontentTypeDisabled: True?
```

### /session save

Run this when you want to checkpoint your progress, especially before:
- Switching to the other repository
- Taking a break
- Handing off to a colleague

It updates the session file with your current context and pushes to the sessions repo.

### /session complete

Run this when the feature branch is done (ready to merge). It:
- Saves final context
- Marks the session as `completed`
- Moves sessions from `ongoing/` to `archive/` in the sessions repo
- Cleans up local session files

## Cross-Repo Workflow

The most powerful aspect of sessions is automatic cross-repo context sharing.

### Example: DI-2826 (Datasphere Replication Flow)

This feature required changes in both `relational-engine` (framework support for REPLICATE load type) and `sap_di_etl_monorepo` (ORM model for the IPRODUCT table).

**Day 1 -- Alice in sap_di_etl_monorepo:**
```
/session init
-> "No previous sessions for this branch. Starting fresh."

Goal: Create IPRODUCT ORM model for Datasphere replication

Work: Creates iproduct.py with 156 columns, deployment script, BigQuery table.
Hits a blocker: connection ID validation failure in the framework.

/session save
-> Session synced to sessions repo
```

**Day 2 -- Alice in relational-engine:**
```
(SessionStart hook pulls the session from Day 1)

/session init
-> "Last session: worked in sap_di_etl_monorepo"
-> Shows: ORM model done, blocked on connection IDs, framework needs REPLICATE support

Goal: Fix JSON payload structure for REPLICATE flows

Work: Adds deltaLoadTrigger, deltaCheckInterval, etc. All 52 tests pass.

Close Claude Code
-> SessionEnd hook pushes session automatically
```

**Day 3 -- Bob in sap_di_etl_monorepo:**
```
(SessionStart hook pulls the session from Day 2)

/session init
-> "Last session: worked in relational-engine"
-> Shows: Framework REPLICATE support added, ready for deployment testing

Bob has full context of both the ORM model work AND the framework changes.
He can proceed with deployment testing without asking Alice.
```

## Session File Anatomy

Each session file has YAML frontmatter and markdown sections:

```yaml
---
session_id: 20260325-074332-k9f
branch: feat/DI-2826_s4_iproduct_rf
ticket: DI-2826
ticket_url: https://tchibo.atlassian.net/browse/DI-2826
repo: relational-engine
status: active
started_at: 2026-03-25T07:43:32
updated_at: 2026-03-25T08:15:00   # set on every /session save
ended_at: null                     # set only by /session complete
---

## Goal
Fix JSON payload structure for REPLICATE replication flows.

## Plan
### Approach
Divide-and-conquer: fix confident fields first, trial-and-error the rest.

### Steps
- [x] Add deltaLoadTrigger to contents for REPLICATE flows
- [x] Add globalDeltaPartitionValue to replicationTaskSetting
- [ ] Deploy and test against real Datasphere

## Context
### Current Understanding
...
### Codebase Understanding
- relational-engine/tchibo_relational_engine/orm_models/deferred_reflections.py -- main logic
- sap_di_etl_monorepo/data_intelligence/orm_models/datasphere_raw/iproduct.py -- ORM model
...

## Decisions
- Use divide-and-conquer for REPLICATE fields (human decision)
- Skip connectionMetaschema in CREATE payload (agent default)

## Progress
### Completed
- Added 4 REPLICATE-specific fields (agent default)
- Updated 2 unit tests (agent default)

### Pending
- Trial-and-error deployment testing

## Files Changed
- relational-engine/tchibo_relational_engine/orm_models/deferred_reflections.py
- relational-engine/tests/unit/orm_models/test_datasphere_raw_reflection.py
```

Key conventions:
- **File paths** use `{repo}/relative/path` format so they're unambiguous across repos
- **Decisions** are tagged `(human decision)` or `(agent default)` so future sessions know which choices are load-bearing
- **Progress** items include learnings, not just checkboxes

## Best Practices

**Always run `/session init`** at the beginning of work. Even if you think it's a quick fix. Context accumulates.

**Run `/session save` before closing or switching repos.** This is not optional right now -- the SessionEnd hook only pushes the file, it does not update it from the conversation. Without a save, you lose all in-session progress.

**Be verbose in sessions.** Write more context than you think is needed. The next person reading this session (or Claude in the next conversation) doesn't have your mental model.

**Include "why", not just "what".** "Changed X to Y" is less useful than "Changed X to Y because the API requires Z format (discovered by reading the Datasphere CLI source)."

**Use `/session complete` when merging.** This keeps `ongoing/` clean and moves context to `archive/` for reference.

## Troubleshooting

**Hook says "Could not reach sessions repo"**: Check your SSH access to GitLab. Run `git ls-remote git@gitlab.com:tchibo-com/bi/sap-di/claude-sessions-archive.git` to test connectivity. The hook fails silently, so you can still work -- your session just won't sync until connectivity is restored.

**No session pulled but one should exist**: The hook only looks in `ongoing/{branch}/`. If the branch name doesn't match exactly (e.g., different suffix), the hook won't find it. Branch names must match across repos for auto-sync to work.

**Session file seems stale / missing recent progress**: You probably closed Claude Code without running `/session save`. The SessionEnd hook pushes the file as-is, so any context Claude hadn't written to the file is lost. Always `/session save` before closing.

**Want to see the sessions repo directly**: Browse `https://gitlab.com/tchibo-com/bi/sap-di/claude-sessions-archive` or clone it locally.

## Setup

After installing the session plugin, add a rules file to each repository that uses session management. This tells Claude Code about the session workflow on every startup. See [Claude Code rules](https://code.claude.com/docs/en/memory#organize-rules-with-claude/rules/) for details.

Create `.claude/rules/session_management.md`:

```markdown
# Session Management

This repository uses shared session management across `relational-engine` and `sap_di_etl_monorepo`.

- On startup, check `.claude/sessions/` for session files pulled by the SessionStart hook
- If a session file exists for the current branch, read it before doing any work -- it contains cumulative context, decisions, and progress from all previous sessions (including work done in the other repo)
- Use `/session init` to formally open a session with a recap and create a new session file
- Use `/session save` to persist current context and sync to the central sessions repo
- Session files use `{repo}/relative/path` format for all file paths (e.g., `relational-engine/tchibo_relational_engine/orm_models/...`)
```

## Future Improvements

**Automatic session compaction on close (priority)**: The SessionEnd hook should update the session file from the conversation transcript before pushing -- removing the need for manual `/session save`. This was designed as an agent-type hook (LLM-powered) but never fired from project settings in testing. The hook code is preserved on the `feat/agent-hook-wip` branch. Once debugged, developers can close Claude Code without worrying about losing in-session progress.

**Automatic session init on startup**: Currently `/session init` must be run manually to create a new session file and recap previous context. This could be automated with an agent-type `SessionStart` hook. The trade-off is 30-60 seconds of latency on every session start (even quick questions), plus API cost. A reasonable middle ground: only auto-init if a previous session file was pulled (skip for fresh branches with no history).
