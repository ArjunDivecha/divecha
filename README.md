# Divecha

Divecha is a portable Codex/Claude Code skill for turning build objectives into gated implementation contracts.

The goal is to replace model self-certification with deterministic external gates. A creator AI writes a `.spec.md` contract with falsifiable invariants and gate intents; a coding model resolves those intents into real commands and implements until those commands exit 0.

Divecha prevents final success from depending only on model confidence. It does not guarantee that a resolved gate is semantically sufficient. For important work, review the resolved gate commands or run an independent verifier before trusting the implementation.

## Lifecycle

1. **Author Mode**: the creator AI writes `<task>.spec.md` with a falsifiable bet, scope, invariants, and unresolved gate intents.
2. **Build Mode**: the coding model inspects the real repo, resolves TODO gates into deterministic commands, writes tests, and implements.
3. **Runner Mode**: an optional loop runner executes gate commands and re-invokes Codex until gates pass or the budget trips.

## What It Contains

- `divecha/SKILL.md`: the Author/Build skill entrypoint with optional Runner Mode.
- `divecha/references/contract_schema.md`: the `.spec.md` schema.
- `divecha/references/agents_stanza.md`: optional repo-level `AGENTS.md` instructions.
- `divecha/scripts/validate_contract.py`: structural contract validator.
- `divecha/scripts/run_codex_loop.py`: thin Codex loop runner.
- `divecha/requirements.txt`: Python dependency list for copied skill installs.

## Install

Clone the repo and install the Python dependency:

```bash
git clone https://github.com/ArjunDivecha/divecha.git
cd divecha
python3 -m pip install -r requirements.txt
```

Install or update the skill with `rsync` so stale files are removed:

```bash
rsync -a --delete divecha/ "$HOME/.claude/skills/divecha/"
```

If Codex uses `~/.codex/skills`, either copy the skill there too or symlink your skill directories to one shared source. If you only have the copied skill folder, install dependencies from the in-skill requirements file:

```bash
python3 -m pip install -r "$HOME/.claude/skills/divecha/requirements.txt"
```

## Use

Ask the creator AI:

```text
Use $divecha in Author Mode to turn this objective into a gated implementation contract.
```

Then hand the generated `<task>.spec.md` to the coding model:

```text
Use $divecha in Build Mode on <absolute-path-to-task.spec.md>.
```

Validate a contract:

```bash
python3 divecha/scripts/validate_contract.py --mode author <task>.spec.md
python3 divecha/scripts/validate_contract.py --mode build <task>.spec.md
```

## Smoke Test

Run the included fixtures without rewriting the contract:

```bash
python3 -m py_compile divecha/scripts/validate_contract.py divecha/scripts/run_codex_loop.py
python3 divecha/scripts/validate_contract.py --mode author tests/fixtures/author.spec.md
python3 divecha/scripts/validate_contract.py --mode build tests/fixtures/build.spec.md
python3 divecha/scripts/run_codex_loop.py tests/fixtures/build.spec.md --cwd "$PWD" --once --no-ledger
```

## Runner Behavior

Use `--no-ledger` for smoke tests and dry checks. Without `--no-ledger`, the runner updates `status` and `ledger`, then rewrites the YAML frontmatter with `yaml.safe_dump`. That produces valid YAML but can create noisy diffs by changing indentation, quoting, and line wrapping.

A real run:

```bash
python3 divecha/scripts/run_codex_loop.py <task>.spec.md --cwd <repo-root>
```

The default agent command is:

```bash
codex -a never -s danger-full-access exec --skip-git-repo-check
```

Override it with an environment variable:

```bash
DIVECHA_AGENT_COMMAND="codex -a never -s danger-full-access exec --skip-git-repo-check" \
python3 divecha/scripts/run_codex_loop.py <task>.spec.md --cwd <repo-root>
```

Or with a flag:

```bash
python3 divecha/scripts/run_codex_loop.py <task>.spec.md \
  --cwd <repo-root> \
  --agent-command "codex -a never -s danger-full-access exec --skip-git-repo-check"
```

## Safety Model

Divecha gates are shell commands. Treat untrusted `.spec.md` files as untrusted code. Inspect commands before running them. Do not run destructive, live-system, broker/trading, expensive API, credential-touching, or `requires_permission: true` gates without explicit approval.

The validator checks contract structure and build-readiness. It does not prove that a gate really tests the invariant, covers the user-visible behavior, prevents overfitting, or enforces every forbidden-scope rule unless those checks are represented as actual gates.

## Limitations

- The validator is structural, not semantic.
- The runner enforces gate commands only. `review:` policy is part of the contract consumed by the coding model unless you separately wire review execution into your workflow.
- A single `.spec.md` currently mixes immutable contract fields with mutable `status` and `ledger` state.
- Build Mode still needs a competent gate-resolution step. Weak gate commands can make weak implementations look green.

## License

MIT License. See `LICENSE`.
