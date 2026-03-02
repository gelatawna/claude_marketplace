---
name: session
description: Manage conversation sessions for context persistence and cross-session communication
argument-hint: start|resume|status|pause|complete|erase|rule|save|commit-msg|send|inbox|offload [args]
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
  - Bash(git clone:*)
  - Bash(git -C:*)
  - Bash(cp -r .claude/sessions/**)
  - Bash(rm -rf .claude/sessions/**)
  - Bash(git add .claude/sessions/**)
  - Bash(git commit:*)
  - Bash(date:*)
  - Bash(mv .claude/sessions/**)
---

# Session Management

Execute the session command: **$ARGUMENTS**

## Commands Reference

| Command | Action |
|---------|--------|
| `start` | Start new session on current branch |
| `resume [id]` | Resume session (latest if no id) |
| `status` | Show current session status |
| `pause` | Pause and persist context |
| `complete` | Mark session completed |
| `erase [id]` | Delete a dead-end session |
| `rule [topic]` | Interactive rule creation for CLAUDE.md |
| `save` | Persist context snapshot |
| `commit-msg` | Generate a suggested commit message from session context |
| `send <repo> [msg]` | Send message to Claude session in another repo |
| `inbox` | Check and read messages from other Claude sessions |
| `offload` | Move branch sessions to archive repo before merge |

## Execution Steps

### 1. Get Current Branch
```bash
git branch --show-current
```

### 2. Parse Ticket (if present)
Extract ticket from branch using pattern: `(DI-\d+|BIFT5-\d+)`
- If found: Jira URL = `https://tchibo.atlassian.net/browse/{TICKET}`
- If not found: omit ticket metadata

### 3. Session Path
Sessions are stored at: `.claude/sessions/{branch}/session-{TIMESTAMP}-{RAND}.md`

**Naming format**: `session-{YYYYMMDD}-{HHMMSS}-{rand3}.md`
- Example: `session-20260128-143022-x7k.md`
- Timestamp from session start time
- 3-character random suffix for collision resistance

### 4. Backwards Compatibility Check
**IMPORTANT**: Before executing any command, check for old structure and migrate if needed.

See [Migration from Old Structure](#migration-from-old-structure) section.

## Command Behaviors

### start
1. Run migration check (see Migration section)
2. **Check inbox for pending messages** from other Claude sessions
   - If messages exist, notify: "You have X message(s) from other sessions. Use `/session inbox` to read."
3. Check for existing `active` session → offer resume or mark abandoned
4. Run abandon detection (active + untouched 24h+)
5. **Full Session History Recap** (IMPORTANT - do not skip):
   - List all session files in `.claude/sessions/{branch}/` sorted by filename (chronological)
   - Read EACH session file completely
   - For each session, extract and internalize:
     - **Goal**: What the session aimed to accomplish
     - **Plan**: Approach, steps, constraints (if present)
     - **Context sections**: Current Understanding, Codebase Understanding, Working Memory
     - **Decisions**: Key decisions with alternatives and rationale
     - **Progress.Completed**: All completed items with their learnings
     - **Progress.Pending**: Items that were never finished
     - **Open Questions**: Unresolved questions from previous sessions
     - **Files Changed**: What was modified
   - Build a cumulative understanding of:
     - What has been accomplished on this branch across all sessions
     - What codebase knowledge has been gathered
     - What decisions were made and why (and by whom: human vs agent)
     - What the plan is and which steps are done
     - What remains to be done
   - Present a **Branch History Recap** to the user:
     ```
     ## Branch Session History

     Found {N} previous session(s) on this branch.

     ### Session 1: {session-id} ({status})
     **Goal**: {goal summary}
     **Plan Progress**: {checked/total steps, or "no plan" if absent}
     **Completed**: {bullet list of key accomplishments}
     **Key Decisions**: {decisions with (human decision)/(agent default) tags}
     **Learnings**: {key insights discovered}

     ### Session 2: {session-id} ({status})
     ...

     ### Cumulative State
     **Total Progress**: {summary of what's been done across all sessions}
     **Plan Status**: {overall plan step completion across sessions, if any}
     **Pending Items**: {items from any session that remain unfinished}
     **Key Decisions**: {all decisions carried forward, with human/agent tags}
     **Open Questions**: {unresolved questions carried forward}
     **Key Codebase Knowledge**: {important file/architecture discoveries}
     ```
6. Generate new session filename: `session-{YYYYMMDD}-{HHMMSS}-{rand3}.md`
7. Create session file with YAML frontmatter and all required sections:
   - **Plan**: Create with placeholder text (optional -- user fills in when ready)
   - **Context**: Pre-populate with cumulative knowledge from previous sessions
   - **Decisions**: Create empty section; carry forward any unresolved decisions from prior sessions
   - **Progress**: Create with Completed/In Progress/Pending subsections
   - Carry forward unresolved Open Questions
   - Carry forward Pending items from previous sessions

### resume [id]
1. Run migration check (see Migration section)
2. **Check inbox for pending messages** from other Claude sessions
   - If messages exist, notify: "You have X message(s) from other sessions. Use `/session inbox` to read."
3. **Full Session History Recap** (IMPORTANT - do not skip):
   - Read ALL session files on the branch (not just the one being resumed)
   - Build cumulative understanding of branch progress, decisions, and codebase knowledge
   - This ensures context from other sessions informs the resumed session
4. Find target session file:
   - If id provided: match by partial filename (e.g., `resume 20260128` matches `session-20260128-143022-x7k.md`)
   - If no id: find latest by `started_at` frontmatter or filename sort
5. **Deep Context Loading** for target session:
   - Read entire session file
   - Internalize Plan section (Approach, Steps checklist, Constraints) if present
   - Internalize Context section (Current Understanding, Codebase, Working Memory, Open Questions, Next Steps)
   - Internalize Decisions (what was decided, alternatives, rationale, human vs agent)
   - Check Progress (Completed/In Progress/Pending) - includes learnings, context, and `(human decision)`/`(agent default)` annotations
6. Present **Branch History Recap** (same format as `start` command) followed by target session details
7. Update status to `active`, clear `ended_at`
8. Ask: "Ready to continue. What would you like to focus on?"

### status
1. Run migration check (see Migration section)
2. Scan all session files in `.claude/sessions/{branch}/`
3. Read frontmatter from each file to build status view
4. Display: session id (from filename), status, started_at, ended_at, goal summary

### pause
1. Persist current context to session file (including Plan progress, Decisions, and annotations)
2. Update status to `paused`
3. Set `ended_at` timestamp
4. Prompt for optional pause reason

### complete
1. Persist final context snapshot (including Plan, Decisions, and annotations)
2. Update status to `completed`
3. Set `ended_at` timestamp
4. Auto-populate files changed: `git diff --name-only`
5. If Plan has unchecked steps: mark them as abandoned with a note, or check them if completed
6. Prompt for final summary

### send <repo> [message]
Send a message to a Claude session running in another git repository.

1. Get current repo context:
   ```bash
   git remote get-url origin
   git branch --show-current
   ```
2. **Full Session History Recap** (if not already loaded this conversation):
   - Read ALL session files on the branch to understand full context
   - This context informs what information to include in the message
3. Create outbox directory if needed: `.claude/sessions/_outbox/`
3. Generate message filename: `msg-{YYYYMMDD}-{HHMMSS}-{rand3}.md`
4. Write message file with structured format:
   ```yaml
   ---
   from_repo: {current-repo-name}
   from_branch: {current-branch}
   from_session: {current-session-id}  # if active session
   to_repo: {target-repo}
   created_at: {ISO-8601}
   status: pending
   ---

   ## Context
   {Current session context: what you're working on, relevant state}

   ## Message
   {The message content - what you need from the other session}

   ## Relevant Files
   {List of files/paths that are relevant, with brief descriptions}

   ## Expected Action
   {What the receiving session should do}
   ```
5. If no message argument provided, prompt for message details
6. Report: "Message written to `.claude/sessions/_outbox/msg-{id}.md`"
7. Instruct user: "Copy this file to the target repo's `.claude/sessions/_inbox/` folder"

### inbox
Check for and process messages from other Claude sessions.

1. **Full Session History Recap** (if not already loaded this conversation):
   - Read ALL session files on the branch to understand full context
   - This context helps interpret and respond to incoming messages
2. Check if inbox exists: `.claude/sessions/_inbox/`
3. If no inbox or empty: Report "No messages in inbox"
4. List all message files: `msg-*.md`
5. For each unread message (status: pending):
   - Read and display the message
   - Show: from_repo, from_branch, created_at
   - Show: Context, Message, Relevant Files, Expected Action
6. Ask: "How would you like to respond to this message?"
7. After processing, update message status to `read`
8. Optionally: Use `send` to reply to the source repo

**Manual Transfer Step** (user action):
```bash
# Copy outbox messages to target repo's inbox
cp .claude/sessions/_outbox/msg-*.md /path/to/other-repo/.claude/sessions/_inbox/

# After processing, clean up
rm .claude/sessions/_outbox/msg-*.md  # source repo
rm .claude/sessions/_inbox/msg-*.md   # target repo after reading
```

### erase [id]
1. If no id: show list of sessions with status
2. Match by partial filename
3. Confirm deletion
4. Remove session file

### save
1. Update Plan section (check off completed steps, add new steps if needed)
2. Update Context section with current knowledge
3. Update Decisions section with any new decisions made
4. Update Progress items (with `(human decision)`/`(agent default)` annotations)
5. Update Files Changed from git
6. Keep status unchanged

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

**Example Interaction**:
```
> /session rule

Claude: What topic should this rule cover?

User: SQL security

Claude: I'll create a rule file for SQL security. Let me clarify:
- Should this apply to all SQL in the codebase?
- Are there specific file patterns where SQL is used?

User: Yes all SQL. Mostly in src/repositories/

Claude: Draft rule file `.claude/rules/sql-security.md`:

  ---
  paths:
    - "src/repositories/**/*.py"
  ---

  # SQL Security Rules

  - Always use parameterized queries for SQL
  - For raw SQL strings, use SQLAlchemy's text() with bound parameters
  - Never use f-strings or .format() to build SQL queries
  - Log query patterns but never log parameter values

Does this capture your intent?

User: Yes, perfect.

Claude: Created .claude/rules/sql-security.md
        This rule will be automatically loaded by Claude Code.
```

**Best Practices**:
- Keep each rule file focused on one topic
- Use descriptive filenames: `testing.md`, `api-design.md`, `security.md`
- Use path-scoped rules only when rules truly apply to specific file types
- Organize with subdirectories for larger projects: `rules/frontend/`, `rules/backend/`

### offload

Moves all sessions for the current branch to an external archive repository before merging. This keeps trunk branches (master/develop) clean of branch-specific session data.

**Prerequisites:**
- Archive repository must exist: `claude-sessions-archive` (in same GitLab group)
- Git credentials must allow push to archive repo
- All sessions on current branch must be `completed` or `paused` (not `active`)

**Execution Steps:**

1. **Check for active sessions**
   - If any session has `status: active`, prompt user to complete/pause first
   - Abort if active sessions exist

2. **Get repository context**
   ```bash
   git branch --show-current
   git remote get-url origin
   ```
   - Extract repo name from origin URL (e.g., `relational-engine`)
   - Extract GitLab group from origin URL

3. **Check if sessions exist for this branch**
   - If `.claude/sessions/{branch}/` is empty or doesn't exist, report "No sessions to offload" and exit

4. **Clone archive repository**
   ```bash
   # Archive repo: https://gitlab.com/tchibo-com/bi/sap-di/claude-sessions-archive
   git clone --depth 1 https://gitlab.com/tchibo-com/bi/sap-di/claude-sessions-archive.git /tmp/claude-sessions-archive
   ```
   - If clone fails, report error and abort
   - For CI, use: `https://gitlab-ci-token:${DI_GITLAB_TOKEN}@gitlab.com/tchibo-com/bi/sap-di/claude-sessions-archive.git`

5. **Copy sessions to archive**
   ```bash
   mkdir -p /tmp/claude-sessions-archive/{repo-name}/{branch}/
   cp -r .claude/sessions/{branch}/* /tmp/claude-sessions-archive/{repo-name}/{branch}/
   ```

6. **Commit and push to archive**
   ```bash
   cd /tmp/claude-sessions-archive
   git add .
   git commit -m "Archive sessions from {repo-name}/{branch}"
   git push
   ```
   - If push fails, report error and abort (do not remove from source)

7. **Remove sessions from source repo**
   ```bash
   rm -rf .claude/sessions/{branch}/
   ```

8. **Report success and prompt for manual commit**
   - "Offloaded {count} sessions to archive repository"
   - "Sessions archived to: https://gitlab.com/tchibo-com/bi/sap-di/claude-sessions-archive/-/tree/main/{repo}/{branch}"
   - "Please commit and push the changes manually:"
   ```bash
   git add .claude/sessions/
   git commit -m "chore: offload sessions to archive repo

   Co-Authored-By: Claude <noreply@anthropic.com>"
   git push
   ```

**Error Handling:**
- If archive repo unreachable: fail with clear error
- If push to archive fails: do not remove from source, report error
- If no sessions exist: report "No sessions to offload" and exit cleanly

**Idempotency:**
- Re-running on already-offloaded branch is a no-op
- Check if branch folder exists before attempting offload

## Migration from Old Structure

**IMPORTANT**: Run this check before executing ANY command.

### Detection
Check if old structure exists:
1. `_index.md` file present in `.claude/sessions/{branch}/`
2. Session files matching pattern `session-\d{3}\.md` (e.g., `session-001.md`)

### Migration Steps
If old structure detected:

1. **Report detection**:
   ```
   Detected old session structure. Migrating to new format...
   ```

2. **Rename old session files**:
   For each `session-NNN.md` file:
   - Read `started_at` from frontmatter
   - Parse timestamp to generate new filename
   - If `started_at` missing, use file modification time
   - Generate 3-char random suffix
   - Rename: `session-001.md` → `session-20260115-093000-x7k.md`

3. **Remove `_index.md`**:
   - Delete `.claude/sessions/{branch}/_index.md`
   - All data already exists in session frontmatter

4. **Report completion**:
   ```
   Migrated X session(s) to new format:
   - session-001.md → session-20260115-093000-x7k.md
   - session-002.md → session-20260116-140000-m3p.md
   Removed _index.md (no longer needed)
   ```

5. **Continue with original command**

### Migration Safety
- Never lose data: rename, don't delete session content
- Handle missing `started_at`: fall back to file mtime
- Handle edge cases: empty files, malformed frontmatter

## Abandon Detection

**Heuristic**: Session is abandoned if:
- `status: active` AND
- `ended_at: null` AND
- File last modified > 24 hours ago

**On detection**: Offer Resume, Mark abandoned, or Erase

## Session File Format

```yaml
---
session_id: {YYYYMMDD-HHMMSS-rand}
branch: {branch-name}
ticket: {TICKET-ID}           # Optional
ticket_url: {JIRA-URL}        # Optional
status: active|paused|completed|abandoned
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
- **Decisions**: Key decisions made during the session. Each entry records:
  - What was decided
  - Alternatives considered (briefly)
  - Rationale for the choice
  - Who decided: `(human decision)` or `(agent default)`
- **Progress**: Completed, In Progress, Pending (be verbose - capture learnings along the way). Annotate each item with `(human decision)` if the user explicitly directed the approach, or `(agent default)` if Claude chose autonomously. This helps future sessions understand which choices are load-bearing constraints vs. paths of least resistance that can be revisited.
- **Files Changed**: List from git diff

## Reading Sessions (on resume)

Read in order:
1. Frontmatter → status, branch, ticket
2. Goal → objective
3. Plan → approach, step checklist, constraints (if present)
4. Context.Current Understanding → mental model
5. Context.Codebase Understanding → explored files
6. Context.Working Memory → key facts
7. Context.Open Questions → unresolved items
8. Context.Next Steps → where to pick up
9. Decisions → what was decided, alternatives, rationale, human vs agent
10. Progress → completed vs pending (includes learnings, context, and human/agent annotations)

Only after loading all context, summarize to user and ask how to proceed.

## File Discovery

Since there is no central index, use file-based discovery:

```bash
# List all sessions for current branch
ls .claude/sessions/{branch}/session-*.md

# Find active sessions
grep -l "status: active" .claude/sessions/{branch}/session-*.md

# Find latest session (by filename, which is timestamp-based)
ls .claude/sessions/{branch}/session-*.md | sort | tail -1
```

## Cross-Session Communication

This feature enables communication between Claude Code sessions running in different git repositories. This is useful when work in one repo requires coordination with or triggers work in another repo.

### Concept
- **Outbox**: `.claude/sessions/_outbox/` - messages you send to other sessions
- **Inbox**: `.claude/sessions/_inbox/` - messages received from other sessions
- **Manual transfer**: User copies files between repos (2-step process)

### Directory Structure
```
.claude/sessions/
├── _inbox/                          # Messages from other repos
│   └── msg-20260128-143500-abc.md
├── _outbox/                         # Messages to other repos
│   └── msg-20260128-144000-xyz.md
└── feat/DI-1234/                    # Branch sessions
    └── session-20260128-143022-x7k.md
```

### Message File Format
```yaml
---
from_repo: relational-engine
from_branch: feat/DI-1234-api-changes
from_session: 20260128-143022-x7k    # Optional
to_repo: sap_di_etl_monorepo
created_at: 2026-01-28T14:35:00Z
status: pending|read
---

## Context
Brief description of what the sending session is working on.

## Message
The actual request or information being communicated.

## Relevant Files
- `path/to/file.py` - Description of relevance
- `another/file.py:50-60` - Specific lines if applicable

## Expected Action
What the receiving Claude session should do with this information.
```

### Workflow Example

**Scenario**: Session A (relational-engine) changes an API. Session B (etl-monorepo) needs to update its client.

```
┌─────────────────────────────────────────────────────────────────────┐
│ Session A: relational-engine                                        │
├─────────────────────────────────────────────────────────────────────┤
│ > /session send etl-monorepo                                        │
│                                                                     │
│ Claude: What message should I send?                                 │
│                                                                     │
│ User: I changed the get_records API to return a dict instead of    │
│       a list. The client in etl-monorepo needs to be updated.      │
│                                                                     │
│ Claude: Message written to .claude/sessions/_outbox/msg-...-x7k.md │
│         Copy to: /path/to/etl-monorepo/.claude/sessions/_inbox/    │
└─────────────────────────────────────────────────────────────────────┘

    │
    │  User copies file: cp .claude/sessions/_outbox/msg-*.md \
    │                       ../etl-monorepo/.claude/sessions/_inbox/
    ▼

┌─────────────────────────────────────────────────────────────────────┐
│ Session B: etl-monorepo                                             │
├─────────────────────────────────────────────────────────────────────┤
│ > /session inbox                                                    │
│                                                                     │
│ Claude: You have 1 message from relational-engine:                  │
│                                                                     │
│   From: relational-engine (feat/DI-1234-api-changes)                │
│   Date: 2026-01-28T14:35:00Z                                        │
│                                                                     │
│   Context: Working on API modernization...                          │
│   Message: Changed get_records API to return dict instead of list  │
│   Expected: Update the client code to handle new return type       │
│                                                                     │
│ Claude: How would you like to respond?                              │
│                                                                     │
│ User: Find and update the client code.                              │
│                                                                     │
│ [Claude makes the updates]                                          │
│                                                                     │
│ > /session send relational-engine "Done. Updated client in         │
│   src/clients/relational.py to handle dict response."              │
└─────────────────────────────────────────────────────────────────────┘
```

### Best Practices

1. **Be specific**: Include file paths and line numbers when relevant
2. **Include context**: The receiving session doesn't have your conversation history
3. **State expected action clearly**: What should the other session do?
4. **Clean up after processing**: Delete messages from inbox/outbox after handling
5. **Reference ticket IDs**: Helps track related cross-repo work