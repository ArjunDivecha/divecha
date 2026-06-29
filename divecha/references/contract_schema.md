# Divecha Contract Schema

A Divecha contract is a single Markdown file named `<task>.spec.md`. It starts with YAML frontmatter, followed by exactly three lean body sections:

1. `## Context`
2. `## Build Loop vs Product Loop`
3. `## Verification Narrative`

Do not include an implementation plan. The coding model plans against the real repo after reading the contract.

## Frontmatter

```yaml
---
spec_id: PIT-LEAK-GUARD-001
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
  if: "signal builder is given as_of date D"
  then: "no feature column sourced after D appears in the output frame"
  observable: "leakage-scan over output columns returns empty"

invariants:
  - id: INV1
    holds: "no forward-return column survives the as_of cut"
    check_intent: "scan output frame columns against the forward-return regex; must be empty"
  - id: INV2
    holds: "no file under scope.forbid is modified in the final diff"
    check_intent: "git diff --name-only is a subset of scope.in and excludes scope.forbid"

gates:
  - id: G1
    intent: "as_of cut produces a leakage-free frame on the standard fixture"
    must_assert: "INV1 holds for the fixture; exit nonzero with offending columns on failure"
    command: TODO
    requires_permission: false
  - id: G2
    intent: "existing signal tests still pass"
    must_assert: "current repo regression suite remains green"
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
  max_turns: 25
  max_consecutive_failures: 3
  token_cap: 200000
  preflight_estimate: required

kill_scale_graduate:
  kill: "INV1 still fails after 10 turns"
  graduate: "gates green AND review verdict=pass AND no forbidden-scope touch"
  scale: "graduated AND gates rerun clean on a second fixture"

ledger:
  turns: 0
  cost_to_date: 0
  consecutive_failures: 0
  blockers: []
  lessons: []
---
```

## Field Ownership

- `[A] Author Mode`: writes `spec_id`, initial `status`, `target_agent`, coarse `scope`, `bet`, `invariants`, gate `intent` and `must_assert`, `review`, `goal_condition`, `budget`, and `kill_scale_graduate`.
- `[B] Build Mode`: replaces `DISCOVER_TARGETS`, resolves `gates[].command`, writes test bodies, and marks `requires_permission` for expensive or risky gates.
- `[L] Loop`: updates `status` and `ledger`.

## Required Semantics

- `scope.forbid` must be non-empty. Name the catastrophic surface up front.
- Each invariant must have a stable `id`, a falsifiable `holds` assertion, and a `check_intent`.
- Every invariant must be covered by at least one gate via the invariant id in `intent` or `must_assert`.
- Each gate must be a deterministic command by Build Mode. Author Mode may leave `command: TODO`.
- Permissioned gates must say `requires_permission: true`.
- `goal_condition` must reference gate exit status and repo scope; it may not depend on model confidence.
- `budget.preflight_estimate` must be `required` before a run starts and should become `complete` once the estimate has been shown.
- The body must separate build-loop proof from product-loop outcomes. Passing gates proves the implementation contract, not the real-world product bet.

## Body Sections

### Context

Provide stateless orientation for an agent with no prior memory. Use full repo paths when known. Define terms. Avoid hidden assumptions.

### Build Loop vs Product Loop

State what the coding model can prove now with machine gates. Separately state the product bet or real-world metric that can only be evaluated after shipping or live measurement. Include a sentence that the coding model may not claim the product bet is satisfied solely because gates pass.

### Verification Narrative

Describe how a user would exercise the finished work. Use CLI commands, fixture names, or browser checks. Keep it concrete enough for a fresh agent to test.

## Validation Levels

Run author validation before handoff:

```bash
python3 <divecha-skill-dir>/scripts/validate_contract.py --mode author <task>.spec.md
```

Run build validation after resolving paths and commands:

```bash
python3 <divecha-skill-dir>/scripts/validate_contract.py --mode build <task>.spec.md
```

Author validation allows TODO commands. Build validation rejects TODO commands and `DISCOVER_TARGETS`.
