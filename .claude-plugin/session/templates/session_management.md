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

1. **Identify** the specific change needed
2. **Describe** it to the user: what file, what change, and why it's required
3. **Wait** for explicit approval before editing the sibling
4. Once approved, edit the sibling and record it in the session's **Files Changed** section using the sibling's `{repo}/path` prefix
