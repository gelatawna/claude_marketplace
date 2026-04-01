# Session Management

This repository uses shared session management across `relational-engine` and `sap_di_etl_monorepo`.

- On startup, check `.claude/sessions/` for session files pulled by the SessionStart hook
- If a session file exists for the current branch, read it before doing any work -- it contains cumulative context, decisions, and progress from all previous sessions (including work done in the other repo)
- Use `/session init` to formally open a session with a recap and create a new session file
- Use `/session save` to persist current context and sync to the central sessions repo
- Session files use `{repo}/relative/path` format for all file paths (e.g., `relational-engine/tchibo_relational_engine/orm_models/...`)
