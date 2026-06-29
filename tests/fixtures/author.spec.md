---
spec_id: SAMPLE-001
status: draft
target_agent: either
scope:
  in:
    - DISCOVER_TARGETS
  out: []
  forbid:
    - data/raw/**
    - "**/secrets*"
bet:
  if: "a calculator division helper receives a zero denominator"
  then: "it raises the documented error instead of returning an invalid value"
  observable: "the division-zero fixture exits nonzero before the fix and exits 0 after the fix"
invariants:
  - id: INV1
    holds: "division by zero never returns a numeric value"
    check_intent: "exercise the zero-denominator fixture and require the documented exception"
gates:
  - id: G1
    intent: "INV1 holds on the division-zero fixture"
    must_assert: "INV1 holds; exit nonzero if division by zero returns any numeric value"
    command: TODO
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
  preflight_estimate: required
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

This sample contract is only for validating the Divecha validator. A coding model would discover the real calculator package, test file, and command paths before implementation.

## Build Loop vs Product Loop

The build loop can prove that the deterministic gate catches division-by-zero behavior and exits 0 after the implementation is correct. The product loop is whether downstream users experience fewer calculator failures after release. The coding model may not claim the product bet is satisfied solely because gates pass.

## Verification Narrative

Run the resolved fixture command from the repository root and confirm it exits 0. Then run the existing calculator regression suite to confirm no surrounding arithmetic behavior regressed.
