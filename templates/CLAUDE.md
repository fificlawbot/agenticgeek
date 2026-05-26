# Agent Instructions

This project uses agenticgeek — a multi-agent toolkit for Claude Code.

## Available Agents

| Agent | Role | How to invoke |
|-------|------|--------------|
| atlas-orch | Orchestrator | `/atlas <task>` (skill, runs in main context) |
| stark-dev | Developer | Spawned by atlas |
| oracle-qa | QA | Spawned by atlas |
| reed-research | Researcher | Spawned by atlas |

## How to use

For any non-trivial task:

```
/atlas <describe what you want to build>
```

Atlas handles: memory prime → context gather → research → brainstorm → plan → implement → test → commit → document.

**Do not** spawn stark, oracle, or reed directly — they are designed to receive structured inputs from atlas.

## Project Notes

[Add project-specific context here: tech stack, key files, env setup, etc.]
