---
name: claude-config-sync
description: How the full Claude Code config is backed up / restored across machines
metadata: 
  node_type: memory
  type: project
  originSessionId: 68c4882c-de1e-4177-bcb4-416dc986d00e
---

Personal `~/.claude` config (skills, agents, hooks, settings.json, .mcp.json, auto-memory, plugin list) is backed up in the `agenticgeek` repo under `config-sync/`. Branch `feat/config-sync` pushed to `github.com/fificlawbot/agenticgeek` (PR not yet merged as of 2026-06-19).

- `config-sync/sync.sh push` — capture live `~/.claude` → repo. Tokenizes `$HOME`→`__HOME__`, strips dead `astha.tarun` account (both `astha.tarun@gmail.com` and path-encoded `astha-tarun-gmail-com` forms), secret-scan aborts before any write, regens `plugins.txt`. Existence-guards missing sources.
- `config-sync/sync.sh pull` — restore repo → `~/.claude`. Renders `__HOME__`→live `$HOME`, merges settings/mcp by entry identity (never clobbers local keys), places memory under username-derived path (`-Users-<user>-projects`). Test via `SYNC_HOME=<sandbox>` so real config untouched.
- Idempotent both ways (`rsync -rcti` no `--delete`; second run = `added=0 updated=0 dir-changes=0`). Never prunes local-only files.
- New-machine steps in `config-sync/RESTORE.md`: clone → pull → reinstall plugins from `plugins.txt` → `./install.sh --global` → clone `~/tradingview-mcp` (its own repo `tradesdontlie/tradingview-mcp`) → restart.
- NOT included: secrets (gitignored), claude-mem observation DB (auto-memory files only), plugin caches (reinstalled latest).
- `install.sh` (agenticgeek's own toolkit deploy) left untouched — `config-sync/` is a separate concern.

Spec + plan: `agenticgeek/docs/superpowers/specs/2026-06-19-claude-config-sync-design.md`, `.../plans/2026-06-19-claude-config-sync.md`.

Related: [[hyperframes-setup]]
