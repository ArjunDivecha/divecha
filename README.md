# Divecha

Divecha is a portable Codex/Claude Code skill for turning build objectives into gated implementation contracts.

The central idea is simple: the agent does not certify itself. A creator AI writes a `.spec.md` contract with falsifiable invariants and gate intents; a coding model resolves those intents into deterministic commands and implements until those commands exit 0.

## What It Contains

- `divecha/SKILL.md`: the two-mode skill entrypoint.
- `divecha/references/contract_schema.md`: the `.spec.md` schema.
- `divecha/references/agents_stanza.md`: optional repo-level `AGENTS.md` instructions.
- `divecha/scripts/validate_contract.py`: contract validator.
- `divecha/scripts/run_codex_loop.py`: thin Codex loop runner.

## Install

Copy the `divecha/` folder into your shared skills directory:

```bash
cp -R divecha ~/.claude/skills/divecha
```

If Codex uses `~/.codex/skills`, either copy it there too or symlink your skill directories to one shared source.

Install the Python dependency used by the validator:

```bash
python3 -m pip install -r requirements.txt
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

Run a build-ready contract once:

```bash
python3 divecha/scripts/run_codex_loop.py <task>.spec.md --cwd <repo-root> --once
```

## License

MIT License. See `LICENSE`.
