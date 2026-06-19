---
name: feedback-no-approvals
description: Minimize approval requests everywhere — execute continuously; only stop for security issues or destructive actions
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 339c2d5b-5aa3-44a7-9125-b672bcf0a3b5
---

Don't seek approvals on project work. Execute continuously. Broadened 2026-06-10: applies to all work, not just plan execution — "ensure you don't need to seek too many approvals unless we are in a security breach issue."

**Why:** User runs parallel async sessions; approval checkpoints block progress.

**How to apply:** Proceed through design → implement → test → commit without approval gates, including superpowers skill gates (user instruction overrides skill checklists). Make reasonable decisions, state them, keep moving. Only stop for: security issues, irreversible/destructive operations (data deletion, force-push, external publishing), or genuinely missing inputs only user can supply.
