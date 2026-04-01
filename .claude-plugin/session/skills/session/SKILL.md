---
name: session
description: Manage conversation sessions with automatic cross-repo sync
argument-hint: init|save|complete|rule|commit-msg [args]
disable-model-invocation: true
allowed-tools:
  - Read(.claude/sessions/**)
  - Read(.claude/rules/**)
  - Write(.claude/sessions/**)
  - Write(.claude/rules/**)
  - Edit(.claude/sessions/**)
  - Edit(.claude/rules/**)
  - Glob(.claude/sessions/**)
  - Glob(.claude/rules/**)
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
  - Bash(python3 ${CLAUDE_PLUGIN_ROOT}/hooks/sync_sessions.py:*)
---

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
| `init` | Initialize or resume a session on current branch, recap previous context |
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

### 4. Get Current Timestamp
Always run this to get the real current time for session filenames and frontmatter:
```bash
date +%Y%m%d-%H%M%S
```
Use the output for the session filename and `started_at` field. Never guess or hardcode timestamps.

### 5. Session Path
Sessions are stored locally at: `.claude/sessions/{branch}/session-{TIMESTAMP}-{RAND}.md`

**Naming format**: `session-{YYYYMMDD}-{HHMMSS}-{rand3}.md`
- Example: `session-20260128-143022-x7k.md`
- Timestamp from step 4
- 3-character random suffix for collision resistance

## Command Behaviors

### init
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
3. **Delete the old session file(s)** after reading. Only one session file should exist at a time:
   ```bash
   rm .claude/sessions/{branch}/session-*.md
   ```
4. If no sessions found, report: "No previous sessions for this branch. Starting fresh."
5. Generate new session filename: `session-{YYYYMMDD}-{HHMMSS}-{rand3}.md`
6. Create session file with YAML frontmatter and all required sections:
   - **repo**: Set to current repository name
   - **Plan**: Carry forward from previous session or create placeholder
   - **Context**: Pre-populate with knowledge from previous session
   - **Decisions**: Carry forward unresolved decisions
   - **Progress**: Carry forward pending items
   - Open Questions: Carry forward unresolved questions
7. Ask: "What would you like to focus on?"

### save
1. Get current timestamp: `date +%Y-%m-%dT%H:%M:%S`
2. Set `updated_at` in frontmatter to current timestamp
3. Update Plan section (check off completed steps, add new steps if needed)
4. Update Context section with current knowledge
   - File paths use `{repo}/relative/path` format (e.g., `relational-engine/tchibo_relational_engine/orm_models/deferred_reflections.py`)
5. Update Decisions section with any new decisions made
6. Update Progress items (with `(human decision)`/`(agent default)` annotations)
7. Update Files Changed from git: `git diff --name-only`
8. Keep status unchanged
7. Sync to sessions repo:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/hooks/sync_sessions.py push
   ```
8. Report: "Session saved and synced to sessions repo."

### complete
1. Persist final context snapshot (same as save steps 1-8)
2. Set `status: completed`
3. Set `ended_at` to current timestamp
4. Set `updated_at` to current timestamp
4. If Plan has unchecked steps: mark them as abandoned with a note, or check them if completed
5. Prompt for final summary
6. Archive in sessions repo (moves from `ongoing/` to `archive/`, cleans up local files on success):
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/hooks/sync_sessions.py push
   python3 ${CLAUDE_PLUGIN_ROOT}/hooks/sync_sessions.py archive
   ```
7. Report: "Session completed and archived."

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
updated_at: {ISO-8601|null}   # Set on every save (manual or automatic)
ended_at: {ISO-8601|null}     # Set only by /session complete
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

The hooks call `sync_sessions.py` with `pull` or `push`. If the sessions repo is unreachable, the hooks fail silently and log a warning.

**What this means for you:**
- When you open Claude Code on a feature branch, the latest session context is already available locally
- When you close Claude Code, your session state is automatically pushed to the central repo
- When your colleague opens the same feature branch (even in a different repo), they see your latest context
- You never need to manually copy session files between repos
