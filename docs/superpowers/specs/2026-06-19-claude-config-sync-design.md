# Claude Config Sync — Design Spec

**Date:** 2026-06-19
**Home:** `agenticgeek` repo (`github.com/fificlawbot/agenticgeek`)
**Goal:** Back up and restore the full personal Claude Code config (skills, agents, hooks, settings, memory, MCP, plugins) to any machine — portable across usernames, kept in sync via git.

## Problem

All Claude Code config lives in `~/.claude/`, but it is **not git-backed, not synced**, and riddled with hardcoded `/Users/trp` paths plus stale `astha.tarun@gmail.com` Google Drive paths (dead account). Moving to a new machine today = manual copy + broken hooks. Some config (`~/tradingview-mcp/`) lives outside `~/.claude` entirely.

## Decisions (locked)

| Question | Decision |
|----------|----------|
| New-machine username | Unknown → design for portability (token paths, auto-detect `$HOME`) |
| Sync model | Ongoing sync — git-backed, both machines push/pull |
| Memory | Auto-memory only (14 files); skip 1.2 GB claude-mem observation DB |
| Stale astha.tarun paths | Purge during capture |
| Home repo | Reuse existing `agenticgeek` (already on GitHub, already a config toolkit) |

## Architecture

Existing `agenticgeek/install.sh` is **repo → machine deploy** (pushes agenticgeek's own atlas/stark/oracle/reed toolkit). It stays **unchanged**. A new `config-sync/` subdir adds the **reverse + restore** for the user's full personal config.

```
agenticgeek/
  install.sh              # UNCHANGED — agenticgeek toolkit deploy
  config-sync/            # NEW
    sync.sh               # push = machine→repo, pull = repo→machine
    RESTORE.md            # new-machine steps, top to bottom
    plugins.txt           # marketplaces + plugins, machine-readable
    claude/               # captured bespoke config, paths tokenized to __HOME__
      settings.json
      .mcp.json
      skills/             # all 18
      agents/             # all 35
      hooks/              # custom .sh / .mjs
      memory/             # 14 auto-memory files
    .gitignore            # blocks secrets / caches / sessions
```

### Two units, one clear purpose each

- **`install.sh`** (existing): deploy agenticgeek's curated agent toolkit. Untouched.
- **`config-sync/sync.sh`** (new): capture/restore the entire personal `~/.claude` bespoke state. Two subcommands, no shared mutable state with `install.sh`.

## `sync.sh push` (machine → repo)

Captures live `~/.claude` into `config-sync/claude/`.

1. `rsync` these into `config-sync/claude/`:
   - `skills/` (all 18)
   - `agents/` (all 35)
   - `hooks/` (custom `.sh` + `context-mode-cache-heal.mjs`)
   - `settings.json`
   - `.mcp.json`
   - `projects/-Users-trp-projects/memory/` → `config-sync/claude/memory/`
2. **Tokenize paths:** `sed 's#/Users/trp#__HOME__#g'` on `settings.json`, `.mcp.json`, `hooks/*.sh`.
3. **Purge stale:** strip permission/path lines containing `astha.tarun@gmail.com` from `settings.json` (JSON-aware via node, not blind sed).
4. **Secret guard:** grep staged files for `sk-`, `api[_-]?key`, `AIza`, `ghp_`, `xoxb-`, `secret=…`. If any hit → **abort, print offending file/line, change nothing committed**.
5. Print summary of what changed. User commits + pushes manually.

## `sync.sh pull` (repo → machine)

Restores `config-sync/claude/` into `~/.claude`.

1. **Render paths:** `sed 's#__HOME__#'"$HOME"'#g'` on `settings.json`, `.mcp.json`, `hooks/*.sh`.
2. `rsync` `skills/`, `agents/`, `hooks/` into `~/.claude/`.
3. Write `settings.json`, `.mcp.json` to `~/.claude/`.
4. **Memory placement:** target dir name derives from the project path under the new `$HOME` — compute `~/.claude/projects/-Users-<user>-projects/memory/` from `$HOME`, not the literal old name. `chmod +x` restored hook scripts.
5. Print next steps (plugin reinstall, install.sh, tradingview-mcp).

## New-machine restore order (RESTORE.md)

1. `git clone github.com/fificlawbot/agenticgeek && cd agenticgeek`
2. `config-sync/sync.sh pull` — lays down settings/skills/agents/hooks/memory/mcp
3. Reinstall plugins from `plugins.txt` (4 `marketplace add` + 9 `plugin install`)
4. `./install.sh --global` — re-merges agenticgeek's own hooks/agents (idempotent)
5. `git clone github.com/tradesdontlie/tradingview-mcp ~/tradingview-mcp` (referenced by `.mcp.json`)
6. Restart Claude Code

## What is NOT in the repo (gitignored / regenerable)

- Secrets: `.env`, `token.json`, OAuth JSON in `~/Downloads`
- Regenerable: `plugins/` cache (902 MB), `context-mode/` data (155 MB), claude-mem DB (1.2 GB), `session-env/`, `shell-snapshots/`, `sessions/`, `history.jsonl`, `file-history/`
- Plugins themselves — reinstalled fresh from `plugins.txt` (latest versions, not pinned)

## Resolved unknowns

- **tradingview-mcp**: own git repo (`github.com/tradesdontlie/tradingview-mcp`, branch main). RESTORE clones it — not bundled.
- **settings.json secrets**: env block = `MAX_THINKING_TOKENS`, `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` only. No secrets. Safe to commit.

## Plugins to reinstall (plugins.txt source)

Marketplaces: `caveman` (JuliusBrussee/caveman), `claude-plugins-official` (anthropics/claude-plugins-official), `thedotmack` (thedotmack/claude-mem), `context-mode` (mksglu/context-mode).
Plugins: caveman, skill-creator, claude-md-management, claude-mem, frontend-design, superpowers, playwright, context-mode, discord.

## Out of scope

- Pinning plugin versions (reinstall pulls latest by design).
- Syncing claude-mem observation DB (explicitly excluded — auto-memory only).
- Symlink-based dotfiles (rejected: breaks on app-mutated settings.json + unknown username).
- Migrating the dirty working trees of other projects (separate task).

## Success criteria

1. `config-sync/sync.sh push` captures all 6 bespoke targets, tokenizes paths, strips astha.tarun, aborts on secrets.
2. Files committed to agenticgeek contain zero `/Users/trp` literals and zero secrets.
3. On a clean machine (any username), following RESTORE.md yields a working Claude Code with all skills, agents, hooks, memory, and MCP intact.
4. `sync.sh push` / `pull` round-trips idempotently.
