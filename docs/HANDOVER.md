# Cross-Repo Session Sharing — Handover

End-to-end handover for the `session` plugin and the cross-repo session-sharing feature it powers.

> **Status**: feature branch — not yet merged. Live on `feat/cross-repo-session-sync` of `claude-di-marketplace` (GitLab + GitHub). User-facing workflow is documented in [docs/onboarding/session-workflow.md](onboarding/session-workflow.md).

## What this delivers

A team-wide Claude Code workflow where session context for a ticket follows the work — across `relational-engine`, `sap_di_etl_monorepo`, and across team members.

- One session file per branch/ticket, stored in a central git repo (`claude-sessions-archive`)
- `SessionStart` hook pulls the matching session for the current branch into `.claude/sessions/`
- `SessionEnd` hook pushes any local session updates back to the central repo (detached, survives Ctrl+C)
- 5 user-facing slash commands: `/session init`, `/session save`, `/session complete`, `/session status`, `/session rule`, `/session commit-msg`
- Sibling-repo awareness (read freely, modify only with same-branch + user approval)
- Files Changed grouped by repo so cross-repo scope is explicit to reviewers

## Repositories involved

| Repo | Branch | Role |
| --- | --- | --- |
| `claude-di-marketplace` | `feat/cross-repo-session-sync` | Plugin source: hooks, skill, rules template |
| `claude-sessions-archive` | `feat/cross-repo-session-sync` | Central session storage (`ongoing/` + `archive/`) |
| `relational-engine` | `feat/DI-9999_session-sync-test` | Consumer — has plugin enabled + rules file |
| `sap_di_etl_monorepo` | `feat/DI-9999_session-sync-test` | Consumer — has plugin enabled + rules file |

> **Before merging**: revert the `DEFAULT_BRANCH = "feat/cross-repo-session-sync"` constant in `sync_sessions.py` to `main` (sessions repo) and update marketplace install instructions to drop the branch pin.

## Plugin layout

```text
claude-di-marketplace/.claude-plugin/session/
├── plugin.json                        # v0.3.0
├── hooks/
│   ├── hooks.json                     # SessionStart=pull, SessionEnd=push (detached)
│   └── sync_sessions.py               # pull | push | archive | status (Python stdlib only)
├── skills/session/
│   └── SKILL.md                       # /session init|save|complete|status|rule|commit-msg
└── templates/
    └── session_management.md          # Copied into each consumer's .claude/rules/
```

Hook commands (already in place):

```json
{
  "SessionStart": [{ "matcher": "startup|resume",
    "hooks": [{ "type": "command",
      "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/sync_sessions.py pull",
      "timeout": 30 }] }],
  "SessionEnd":   [{ "matcher": "",
    "hooks": [{ "type": "command",
      "command": "nohup python3 ${CLAUDE_PLUGIN_ROOT}/hooks/sync_sessions.py push </dev/null >/dev/null 2>&1 &",
      "timeout": 30 }] }]
}
```

`nohup ... </dev/null >/dev/null 2>&1 &` detaches push so Ctrl+C doesn't kill it.

## Sessions archive layout

```text
claude-sessions-archive/
├── ongoing/    # active sessions, keyed by sanitized branch name
└── archive/    # completed sessions (moved here by /session complete)
```

Session files use the cross-repo path convention: `{repo}/relative/path` for every file reference, regardless of which repo's session opened the file.

## Setup — install from the feature branch

Because the work isn't merged yet, the plugin must be pinned to the feature branch and the sessions repo must be on the matching branch.

### 1. Clone all three repos side-by-side

```bash
mkdir -p ~/code/tch && cd ~/code/tch
git clone git@gitlab.com:tchibo-com/bi/sap-di/claude-di-marketplace.git
git clone git@gitlab.com:tchibo-com/bi/sap-di/claude-sessions-archive.git
git clone git@gitlab.com:tchibo-com/bi/sap-di/relational-engine.git
git clone git@gitlab.com:tchibo-com/bi/sap-di/sap_di_etl_monorepo.git
```

`relational-engine` and `sap_di_etl_monorepo` MUST be siblings under the same parent — sibling lookup uses `../{repo}`.

### 2. Check out the feature branch on the sessions archive

```bash
cd ~/code/tch/claude-sessions-archive
git checkout feat/cross-repo-session-sync
```

`sync_sessions.py` is hard-coded to push/pull this branch until the work is merged.

### 3. Register the marketplace and install the plugin

```bash
# From either consumer repo (relational-engine or sap_di_etl_monorepo):
cd ~/code/tch/relational-engine

# Add the marketplace from local path (so we use the feature-branch checkout)
claude plugin marketplace add ~/code/tch/claude-di-marketplace

# Install the session plugin into this project
claude plugin install session@BDAP_DI_marketplace
```

This writes `session@BDAP_DI_marketplace: true` to `.claude/settings.local.json` in the project. Repeat for `sap_di_etl_monorepo`.

> **Why local-path marketplace?** It points at your working tree, so the feature branch's hooks and skill are picked up directly. After merge, switch to the remote marketplace URL.

### 4. Drop the rules template into each consumer

Copy the template once per consumer repo:

```bash
mkdir -p ~/code/tch/relational-engine/.claude/rules
cp ~/code/tch/claude-di-marketplace/.claude-plugin/session/templates/session_management.md \
   ~/code/tch/relational-engine/.claude/rules/session_management.md

# same for sap_di_etl_monorepo
```

The rule is read by Claude on every conversation — it's how the agent knows to read the pulled session file before doing work.

### 5. Verify

Open Claude Code in `relational-engine` on a feature branch. You should see:

- `~/.claude/session-sync.log` lines for `START pull`, `END pull`
- A session file in `.claude/sessions/` if the branch has one in `ongoing/`
- `/session init|save|complete|status|rule|commit-msg` available as slash commands

Run `/session status` to see central-repo state for the current branch.

## Branch-name → ticket extraction

Sessions are keyed by sanitized branch name. The script supports any of these prefixes and always extracts what comes after the first `/`:

```text
feat/DI-2826_iproduct-rawvault     → DI-2826_iproduct-rawvault
fix/DI-1141_pit-watermark          → DI-1141_pit-watermark
bugfix/...  hotfix/...  chore/...  → same rule
```

So both repos working on `feat/DI-2826_…` see the same session file — the cross-repo sharing is automatic as long as branch names match.

## Sibling-repo modification rules

The skill and rules template enforce:

1. **Read-only access**: free, no approval needed (sibling is at `../{repo}`)
2. **Writes**: require (a) sibling on same branch, (b) explicit user approval, (c) entry in `Files Changed` under the right repo subsection

Same-branch check (run before proposing a sibling edit):

```bash
git -C ../sap_di_etl_monorepo branch --show-current
```

If it diverges, stop and tell the user — coordinated changes must land on one feature branch in both repos.

## Known limitations

- **Agent-type SessionEnd hook does not fire from `settings.local.json`.** The detached `command` push is the production path. Agent-driven LLM compaction is preserved on `feat/agent-hook-wip` for later investigation. Do not delete that branch.
- **Markdown lint warnings** in `SKILL.md` are pre-existing and not in scope for this feature.
- **Detached push is fire-and-forget.** Failures only show in `~/.claude/session-sync.log`. Run `/session status` if you want to confirm a session reached the remote.

## Files changed during this work

### claude-di-marketplace (`feat/cross-repo-session-sync`)

- `.claude-plugin/session/plugin.json` (bumped to 0.3.0)
- `.claude-plugin/session/hooks/hooks.json` (new)
- `.claude-plugin/session/hooks/sync_sessions.py` (new — Python stdlib only)
- `.claude-plugin/session/skills/session/SKILL.md` (5-command skill, sibling awareness, status command)
- `.claude-plugin/session/templates/session_management.md` (rules template — same-branch + grouped Files Changed)
- `docs/onboarding/session-workflow.md` (team onboarding guide)
- `docs/HANDOVER.md` (this doc)

### claude-sessions-archive (`feat/cross-repo-session-sync`)

- Restructured per-repo folders into `ongoing/` + `archive/`
- Cross-repo sessions merged for shared tickets (DI-2826, DI-1141, DI-1214, DI-2730)

### relational-engine + sap_di_etl_monorepo (`feat/DI-9999_session-sync-test`)

- `.claude/settings.local.json` (enables `session@BDAP_DI_marketplace`)
- `.claude/rules/session_management.md` (copy of marketplace template — keep in sync)

## Path to merge

1. Field-test the workflow with one or two team members on real tickets
2. If agent-hook compaction is wanted, debug `feat/agent-hook-wip` and merge first
3. Revert the `DEFAULT_BRANCH` constant in `sync_sessions.py` from `feat/cross-repo-session-sync` → `main`
4. Move sessions repo branch contents to `main` and switch the script's pin
5. Merge `feat/cross-repo-session-sync` on the marketplace, bump plugin version
6. Update onboarding doc to drop the branch pin from install steps
7. Notify team; have everyone run `claude plugin update session@BDAP_DI_marketplace`

## References

- User-facing workflow: [docs/onboarding/session-workflow.md](onboarding/session-workflow.md)
- Sync log: `~/.claude/session-sync.log`
- Marketplace remotes:
  - GitLab: `git@gitlab.com:tchibo-com/bi/sap-di/claude-di-marketplace.git`
  - GitHub mirror: `git@github.com:gelatawna/claude_marketplace.git`
- Sessions repo: `git@gitlab.com:tchibo-com/bi/sap-di/claude-sessions-archive.git`
