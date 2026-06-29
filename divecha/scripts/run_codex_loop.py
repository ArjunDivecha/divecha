#!/usr/bin/env python3
"""Thin Codex loop shim for build-ready Divecha contracts."""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from validate_contract import load_contract, validate_data, write_contract  # noqa: E402


DEFAULT_AGENT_COMMAND = "codex -a never -s danger-full-access exec --skip-git-repo-check"


def choose_shell() -> str:
    candidates = [
        os.environ.get("DIVECHA_SHELL"),
        os.environ.get("SHELL"),
        "/bin/zsh",
        "/bin/bash",
        "/bin/sh",
        "zsh",
        "bash",
        "sh",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        if os.path.isabs(candidate) and os.path.exists(candidate):
            return candidate
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise RuntimeError("no usable shell found for gate command execution")


def run_shell(command: str, cwd: Path, timeout: int | None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        shell=True,
        text=True,
        capture_output=True,
        timeout=timeout,
        executable=choose_shell(),
    )


def summarize_output(result: subprocess.CompletedProcess[str], limit: int = 6000) -> str:
    combined = "\n".join(
        part for part in [result.stdout.strip(), result.stderr.strip()] if part
    ).strip()
    if len(combined) <= limit:
        return combined
    return combined[-limit:]


def run_gates(data: dict[str, Any], cwd: Path, timeout: int | None) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for gate in data.get("gates", []):
        command = gate["command"]
        result = run_shell(command, cwd, timeout)
        results.append(
            {
                "id": gate.get("id", "UNKNOWN"),
                "intent": gate.get("intent", ""),
                "command": command,
                "returncode": result.returncode,
                "output": summarize_output(result),
            }
        )
    return results


def failures(gate_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [result for result in gate_results if result["returncode"] != 0]


def permissioned_gates(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [gate for gate in data.get("gates", []) if gate.get("requires_permission") is True]


def update_ledger(
    spec_path: Path,
    data: dict[str, Any],
    body: str,
    status: str,
    failed: list[dict[str, Any]],
    increment_turn: bool,
) -> None:
    ledger = data.setdefault("ledger", {})
    if increment_turn:
        ledger["turns"] = int(ledger.get("turns", 0)) + 1
    if failed:
        ledger["consecutive_failures"] = int(ledger.get("consecutive_failures", 0)) + 1
        blockers = ledger.setdefault("blockers", [])
        stamp = datetime.now(timezone.utc).isoformat()
        blockers.append(
            {
                "at": stamp,
                "failed_gates": [item["id"] for item in failed],
                "summary": "; ".join(f"{item['id']} rc={item['returncode']}" for item in failed),
            }
        )
    else:
        ledger["consecutive_failures"] = 0
    data["status"] = status
    write_contract(spec_path, data, body)


def build_agent_prompt(spec_path: Path, cwd: Path, failed: list[dict[str, Any]]) -> str:
    lines = [
        "Use $divecha in Build Mode.",
        f"Contract: {spec_path}",
        f"Repo root: {cwd}",
        "",
        "The external gates failed. Inspect the repo and contract, fix the implementation or gate setup, update the ledger, and stop only when the gates pass.",
        "",
        "Failing gates:",
    ]
    for item in failed:
        lines.extend(
            [
                f"- {item['id']}: {item['intent']}",
                f"  command: {item['command']}",
                f"  returncode: {item['returncode']}",
                "  output:",
                item["output"] or "  <no output>",
            ]
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a thin Codex loop around a build-ready Divecha contract.")
    parser.add_argument("spec", type=Path, help="Path to <task>.spec.md")
    parser.add_argument("--cwd", type=Path, default=Path.cwd(), help="Repository root for gate commands")
    parser.add_argument("--agent-command", default=os.environ.get("DIVECHA_AGENT_COMMAND", DEFAULT_AGENT_COMMAND))
    parser.add_argument("--timeout", type=int, default=None, help="Per-gate timeout in seconds")
    parser.add_argument("--once", action="store_true", help="Run gates once without invoking Codex")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print the planned loop without running gates")
    parser.add_argument("--allow-permissioned", action="store_true", help="Allow gates marked requires_permission=true")
    parser.add_argument("--no-ledger", action="store_true", help="Do not rewrite the contract ledger/status")
    args = parser.parse_args(argv)

    spec_path = args.spec.resolve()
    cwd = args.cwd.resolve()
    data, body = load_contract(spec_path)
    errors = validate_data(data, body, "build")
    if errors:
        print("DIVECHA_LOOP_NOT_READY")
        for error in errors:
            print(f"- {error}")
        return 2

    gated = permissioned_gates(data)
    if gated and not args.allow_permissioned:
        print("DIVECHA_LOOP_NEEDS_PERMISSION")
        for gate in gated:
            print(f"- {gate.get('id')}: {gate.get('intent')}")
        return 3

    max_turns = int(data.get("budget", {}).get("max_turns", 1))
    max_failures = int(data.get("budget", {}).get("max_consecutive_failures", 1))

    if args.dry_run:
        print("DIVECHA_LOOP_DRY_RUN")
        print(f"spec={spec_path}")
        print(f"cwd={cwd}")
        print(f"agent_command={args.agent_command}")
        for gate in data.get("gates", []):
            print(f"- {gate.get('id')}: {gate.get('command')}")
        return 0

    while True:
        gate_results = run_gates(data, cwd, args.timeout)
        failed = failures(gate_results)
        for result in gate_results:
            status = "PASS" if result["returncode"] == 0 else "FAIL"
            print(f"{status} {result['id']} rc={result['returncode']} command={result['command']}")
            if result["output"]:
                print(result["output"])

        if not failed:
            if not args.no_ledger:
                update_ledger(spec_path, data, body, "done", failed, increment_turn=False)
            print("DIVECHA_LOOP_DONE")
            return 0

        if not args.no_ledger:
            update_ledger(spec_path, data, body, "in_progress", failed, increment_turn=True)
            data, body = load_contract(spec_path)

        ledger = data.get("ledger", {})
        if args.once:
            print("DIVECHA_LOOP_FAILED_ONCE")
            return 1
        if int(ledger.get("turns", 0)) >= max_turns:
            print("DIVECHA_LOOP_BUDGET_TRIPPED max_turns")
            return 4
        if int(ledger.get("consecutive_failures", 0)) >= max_failures:
            print("DIVECHA_LOOP_BUDGET_TRIPPED max_consecutive_failures")
            return 4

        prompt = build_agent_prompt(spec_path, cwd, failed)
        command = f"{args.agent_command} {shlex.quote(prompt)}"
        agent_result = run_shell(command, cwd, timeout=None)
        print(agent_result.stdout, end="")
        if agent_result.stderr:
            print(agent_result.stderr, file=sys.stderr, end="")
        if agent_result.returncode != 0:
            print(f"DIVECHA_AGENT_FAILED rc={agent_result.returncode}")
            return agent_result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
