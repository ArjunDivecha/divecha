---
name: divecha
description: "Create and consume portable gated implementation contracts for creator-AI-to-coding-model handoffs. Use when a user asks for Divecha, a build brief, a .spec.md implementation contract, deterministic external gates, creator AI authoring plus coding model execution, Codex/Claude Code portability, or a loop that must prove completion with shell commands instead of agent self-certification."
---

# Divecha

Divecha turns a raw build objective into a single-file implementation contract, then lets a coding model consume that same contract until external gate commands prove the task is done.

The core rule: the agent never certifies itself. A deterministic shell command with exit semantics is the primary judge; reviews and goal text are secondary.

## Mode Selection

Use **Author Mode** when operating as the creator AI, planning AI, or no-repo-access AI. Produce `<task>.spec.md`, validate it, and hand it to a coding model. Do not implement code in Author Mode.

Use **Build Mode** when operating as the coding model inside a repository. Read the `.spec.md`, inspect the real repo, resolve TODO gates into real tests/commands, implement to green, run review if configured, and append ledger state.

Use **Runner Mode** only when asked to automate the loop. The runner invokes the coding model, runs `gates[].command`, and re-invokes the coding model with failing output until the goal condition is met or the budget trips.

## Ownership Rules

- `[A]` fields belong to Author Mode: `bet`, coarse `scope`, `invariants`, gate intents, review policy, goal condition, budget, and kill/scale/graduate thresholds.
- `[B]` fields belong to Build Mode: real repo paths, test bodies, gate commands, fixture names, and permission flags that depend on actual infrastructure.
- `[L]` fields belong to the loop: ledger turns, cost, consecutive failures, blockers, and lessons.
- Do not move enforcement into a prompt, hook, or agent-internal rubric. Hooks may be convenient, but the portable contract is the external command.

## Author Mode Workflow

1. Read `references/contract_schema.md`.
2. Write `<task>.spec.md` from the user's objective.
3. Fill every `[A]` field. Leave repo-specific `[B]` fields as `TODO` or `DISCOVER_TARGETS`.
4. Keep the body to exactly these three sections: `Context`, `Build Loop vs Product Loop`, and `Verification Narrative`.
5. Separate the machine-verifiable build loop from the real-world product bet. The contract must say the coding model may not claim the product bet is satisfied merely because gates pass.
6. Run:

```bash
python3 <divecha-skill-dir>/scripts/validate_contract.py --mode author <task>.spec.md
```

7. Rewrite until validation passes. Then provide a handoff prompt:

```text
Use $divecha in Build Mode on <absolute-path-to-task.spec.md>. Resolve the TODO gates against the real repo, ask before any requires_permission gate, implement only after the test/gate plan is approved when approval is required, run all gates to exit 0, run the configured review, and append ledger state.
```

## Build Mode Workflow

1. Read the `.spec.md` and `references/contract_schema.md`.
2. Inspect the repository before planning. Replace `DISCOVER_TARGETS` with real paths.
3. Convert each gate intent into a deterministic command. Prefer repo-native tests and scripts over new harnesses.
4. Add or update test bodies before product code when the gate requires new coverage.
5. Stop for user approval before expensive external API gates, live trading/broker gates, destructive data changes, or any gate marked `requires_permission: true`.
6. Run:

```bash
python3 <divecha-skill-dir>/scripts/validate_contract.py --mode build <task>.spec.md
```

7. Implement until every `gates[].command` exits 0 from the declared repo root.
8. Run the configured review step if available. Worst verdict wins.
9. Append ledger state, including repeated mistakes that should be promoted to `AGENTS.md`.
10. Final status may say success only when the exact gate commands have passed in the current environment.

## Runner Mode

Use the shim when the user wants a headless Codex loop around an already build-ready contract:

```bash
python3 <divecha-skill-dir>/scripts/run_codex_loop.py <task>.spec.md --cwd <repo-root>
```

Useful checks:

```bash
python3 <divecha-skill-dir>/scripts/run_codex_loop.py <task>.spec.md --cwd <repo-root> --once
python3 <divecha-skill-dir>/scripts/run_codex_loop.py <task>.spec.md --cwd <repo-root> --dry-run
```

The runner is intentionally thin. It does not invent the contract, approve tests, or replace human judgment for permissioned gates.

## Resources

- `references/contract_schema.md`: the canonical `.spec.md` schema and validation rules.
- `references/agents_stanza.md`: short Codex `AGENTS.md` stanza for repos that should always know how to consume Divecha contracts.
- `scripts/validate_contract.py`: structural validator for Author Mode and Build Mode contracts.
- `scripts/run_codex_loop.py`: thin Codex loop shim that runs gate commands and re-invokes Codex on failure.
