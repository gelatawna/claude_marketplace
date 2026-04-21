# Session Management

This repository uses shared session management across `relational-engine` and `sap_di_etl_monorepo`.

- On startup, check `.claude/sessions/` for session files pulled by the SessionStart hook
- If a session file exists for the current branch, read it before doing any work -- it contains cumulative context, decisions, and progress from all previous sessions (including work done in the other repo)
- Use `/session init` to formally open a session with a recap and create a new session file
- Use `/session save` to persist current context and sync to the central sessions repo
- Session files use `{repo}/relative/path` format for all file paths (e.g., `relational-engine/tchibo_relational_engine/orm_models/...`)

## Sibling Repository

This ticket may span both `relational-engine` and `sap_di_etl_monorepo`. Both repositories are conventionally checked out side-by-side in the same parent directory.

- **In `relational-engine`**: the sibling is at `../sap_di_etl_monorepo`
- **In `sap_di_etl_monorepo`**: the sibling is at `../relational-engine`

### When to read from the sibling

Read-only access is cheap. Always read from the sibling without asking when:

- Session context references files prefixed with the sibling repo name (e.g., `sap_di_etl_monorepo/data_intelligence/...`)
- You need to verify an assumption about code in the other repo
- Understanding the caller/callee relationship of the current work

### When the sibling needs changes

If work in the current repo requires a coordinated change in the sibling (e.g., an API signature change in `relational-engine` breaks a consumer in `sap_di_etl_monorepo`):

1. **Verify the sibling is on the same branch.** Run `git -C ../{sibling-repo} branch --show-current`. If the sibling is on a different branch, stop and tell the user: coordinated changes must land on the same feature branch in both repos so the work is reviewable as a unit and the session history stays aligned.
2. **Identify** the specific change needed
3. **Describe** it to the user: what file, what change, and why it's required
4. **Wait** for explicit approval before editing the sibling
5. Once approved, edit the sibling and record it in the session's **Files Changed** section using the sibling's `{repo}/path` prefix

### Files Changed must cover both repos

When a session touches both repos, the session's **Files Changed** section must list files from both, each with its `{repo}/relative/path` prefix. Group them explicitly:

```
## Files Changed

### relational-engine
- relational-engine/tchibo_relational_engine/orm_models/deferred_reflections.py

### sap_di_etl_monorepo
- sap_di_etl_monorepo/data_intelligence/orm_models/datasphere_raw/iproduct.py
```

This makes the cross-repo scope explicit to reviewers and to the next session that picks up this context.
