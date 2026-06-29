# AGENTS.md Stanza For Divecha

Paste this into a repo-level `AGENTS.md` when the repo should always know how to consume Divecha contracts:

```markdown
## Divecha Implementation Contracts

Use the shared Divecha skill at `<divecha-skill-dir>` whenever the task references `Divecha`, `.spec.md`, deterministic gates, creator-AI handoff, or coding-model build mode.

When consuming a Divecha `.spec.md`:

1. Read the contract and `<divecha-skill-dir>/references/contract_schema.md`.
2. Treat the contract as a two-party artifact: Author Mode owns the falsifiable bet, scope, invariants, gate intents, review policy, goal condition, budget, and thresholds; Build Mode owns repo-path resolution, test bodies, gate commands, and implementation.
3. Resolve every `TODO` gate command into a deterministic shell command before claiming build readiness.
4. Stop for approval before any gate marked `requires_permission: true`, any expensive external API gate, or any destructive/live-system gate.
5. Implement only until every `gates[].command` exits 0 and scope checks pass. Do not use model confidence as proof.
6. Keep build-loop proof separate from product-loop outcomes. Passing gates proves the implementation contract, not the real-world product bet.
7. Append ledger state for turns, failures, blockers, and lessons; promote repeated lessons to `AGENTS.md`.

Useful commands:

```bash
python3 <divecha-skill-dir>/scripts/validate_contract.py --mode build <task>.spec.md
python3 <divecha-skill-dir>/scripts/run_codex_loop.py <task>.spec.md --cwd <repo-root> --once
```
```
