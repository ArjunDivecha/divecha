---
spec_id: SAMPLE-002
status: approved
target_agent: codex
scope:
  in:
    - /tmp/**
  out: []
  forbid:
    - /tmp/forbidden/**
    - "**/secrets*"
bet:
  if: "a build-ready sample contract runs its gate"
  then: "the gate command exits 0"
  observable: "the runner reports DIVECHA_LOOP_DONE"
invariants:
  - id: INV1
    holds: "the sample gate exits 0"
    check_intent: "run the sample Python command and require exit code 0"
gates:
  - id: G1
    intent: "INV1 holds for the sample gate"
    must_assert: "INV1 holds; exit nonzero if the sample command fails"
    command: "python3 -c 'import sys; sys.exit(0)'"
    requires_permission: false
review:
  models:
    - council
  aggregation: worst_verdict_wins
  sees:
    - diff
    - invariants
    - scope
goal_condition: "all gates exit 0 AND git diff --name-only is a subset of scope.in AND no scope.forbid path is modified"
budget:
  max_turns: 3
  max_consecutive_failures: 2
  token_cap: 10000
  preflight_estimate: complete
kill_scale_graduate:
  kill: "INV1 still fails after 3 turns"
  graduate: "gates green AND review verdict=pass AND no forbidden-scope touch"
  scale: "graduated AND gates rerun clean on a second fixture"
ledger:
  turns: 0
  cost_to_date: 0
  consecutive_failures: 0
  blockers: []
  lessons: []
---

## Context

This sample contract validates the Divecha runner with a harmless Python command. It is not a real implementation request and should not be copied into a repository.

## Build Loop vs Product Loop

The build loop can prove that the external gate command executes and returns exit code 0. The product loop would be whether a real implementation solves the user's shipped workflow. The coding model may not claim the product bet is satisfied solely because gates pass.

## Verification Narrative

Run the sample command through the Divecha runner with `--once --no-ledger` from any local directory. A valid pass reports the sample gate as PASS and prints `DIVECHA_LOOP_DONE`.
