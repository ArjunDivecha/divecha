#!/usr/bin/env python3
"""Validate Divecha .spec.md implementation contracts."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - environment guard
    yaml = None


ALLOWED_STATUSES = {"draft", "approved", "in_progress", "under_review", "done", "killed"}
ALLOWED_AGENTS = {"claude_code", "codex", "either"}
REQUIRED_TOP_LEVEL = [
    "spec_id",
    "status",
    "target_agent",
    "scope",
    "bet",
    "invariants",
    "gates",
    "review",
    "goal_condition",
    "budget",
    "kill_scale_graduate",
    "ledger",
]
REQUIRED_BODY_H2 = ["Context", "Build Loop vs Product Loop", "Verification Narrative"]
VAGUE_GOAL_WORDS = {"confidence", "vibe", "seems", "likely", "probably", "agent says"}
PLACEHOLDER_VALUES = {"TODO", "TBD", "<N>", "<n>", "DISCOVER_TARGETS"}


def split_frontmatter(text: str) -> tuple[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("contract must start with YAML frontmatter delimited by ---")
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            frontmatter = "\n".join(lines[1:index])
            body = "\n".join(lines[index + 1 :]).strip() + "\n"
            return frontmatter, body
    raise ValueError("frontmatter closing --- not found")


def load_contract(path: Path) -> tuple[dict[str, Any], str]:
    if yaml is None:
        raise RuntimeError("PyYAML is required. Install pyyaml or run with a Python environment that includes yaml.")
    frontmatter, body = split_frontmatter(path.read_text(encoding="utf-8"))
    data = yaml.safe_load(frontmatter) or {}
    if not isinstance(data, dict):
        raise ValueError("frontmatter must parse to a YAML mapping")
    return data, body


def write_contract(path: Path, data: dict[str, Any], body: str) -> None:
    if yaml is None:
        raise RuntimeError("PyYAML is required. Install pyyaml or run with a Python environment that includes yaml.")
    rendered = yaml.safe_dump(data, sort_keys=False, allow_unicode=False).strip()
    path.write_text(f"---\n{rendered}\n---\n\n{body.strip()}\n", encoding="utf-8")


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_placeholder(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        stripped = value.strip()
        upper = stripped.upper()
        return upper in PLACEHOLDER_VALUES or "TODO" in upper or stripped in {"<n>", "<N>"}
    return False


def walk_placeholders(value: Any, path: str = "") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            errors.extend(walk_placeholders(child, f"{path}.{key}" if path else str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(walk_placeholders(child, f"{path}[{index}]"))
    elif is_placeholder(value):
        errors.append(f"{path} still contains placeholder value {value!r}")
    return errors


def validate_scope(data: dict[str, Any], mode: str, errors: list[str]) -> None:
    scope = data.get("scope")
    if not isinstance(scope, dict):
        errors.append("scope must be a mapping with in/out/forbid lists")
        return
    for key in ("in", "out", "forbid"):
        if key not in scope:
            errors.append(f"scope.{key} is required")
        elif not isinstance(scope[key], list):
            errors.append(f"scope.{key} must be a list")
    if not as_list(scope.get("forbid")):
        errors.append("scope.forbid must be non-empty")
    if not as_list(scope.get("in")):
        errors.append("scope.in must be non-empty; use DISCOVER_TARGETS in Author Mode if needed")
    if mode == "build":
        for key in ("in", "out"):
            if any(item == "DISCOVER_TARGETS" for item in as_list(scope.get(key))):
                errors.append(f"scope.{key} still contains DISCOVER_TARGETS in Build Mode")


def validate_bet(data: dict[str, Any], errors: list[str]) -> None:
    bet = data.get("bet")
    if not isinstance(bet, dict):
        errors.append("bet must be a mapping")
        return
    for key in ("if", "then", "observable"):
        if not nonempty_text(bet.get(key)):
            errors.append(f"bet.{key} must be non-empty text")


def validate_invariants_and_gates(data: dict[str, Any], mode: str, errors: list[str]) -> None:
    invariants = data.get("invariants")
    gates = data.get("gates")
    if not isinstance(invariants, list) or not invariants:
        errors.append("invariants must be a non-empty list")
        return
    if not isinstance(gates, list) or not gates:
        errors.append("gates must be a non-empty list")
        return

    invariant_ids: list[str] = []
    for index, invariant in enumerate(invariants):
        if not isinstance(invariant, dict):
            errors.append(f"invariants[{index}] must be a mapping")
            continue
        inv_id = invariant.get("id")
        if not nonempty_text(inv_id):
            errors.append(f"invariants[{index}].id must be non-empty text")
        else:
            invariant_ids.append(inv_id)
        for key in ("holds", "check_intent"):
            if not nonempty_text(invariant.get(key)):
                errors.append(f"invariants[{index}].{key} must be non-empty text")

    gate_text = []
    for index, gate in enumerate(gates):
        if not isinstance(gate, dict):
            errors.append(f"gates[{index}] must be a mapping")
            continue
        for key in ("id", "intent", "must_assert", "command"):
            if key not in gate:
                errors.append(f"gates[{index}].{key} is required")
        if not nonempty_text(gate.get("id")):
            errors.append(f"gates[{index}].id must be non-empty text")
        if not nonempty_text(gate.get("intent")):
            errors.append(f"gates[{index}].intent must be non-empty text")
        if not nonempty_text(gate.get("must_assert")):
            errors.append(f"gates[{index}].must_assert must be non-empty text")
        if "requires_permission" not in gate:
            errors.append(f"gates[{index}].requires_permission must be explicit")
        elif not isinstance(gate.get("requires_permission"), bool):
            errors.append(f"gates[{index}].requires_permission must be true or false")
        command = gate.get("command")
        if mode == "build" and is_placeholder(command):
            errors.append(f"gates[{index}].command must be resolved in Build Mode")
        elif mode == "author" and command is None:
            errors.append(f"gates[{index}].command must exist; use TODO in Author Mode")
        gate_text.append(f"{gate.get('intent', '')} {gate.get('must_assert', '')}")

    all_gate_text = " ".join(gate_text)
    for inv_id in invariant_ids:
        if inv_id not in all_gate_text:
            errors.append(f"invariant {inv_id} is not referenced by any gate intent or must_assert")


def validate_review_budget_thresholds(data: dict[str, Any], errors: list[str]) -> None:
    review = data.get("review")
    if not isinstance(review, dict):
        errors.append("review must be a mapping")
    else:
        if not as_list(review.get("models")):
            errors.append("review.models must be a non-empty list")
        if review.get("aggregation") != "worst_verdict_wins":
            errors.append("review.aggregation must be worst_verdict_wins")
        if not as_list(review.get("sees")):
            errors.append("review.sees must be a non-empty list")

    budget = data.get("budget")
    if not isinstance(budget, dict):
        errors.append("budget must be a mapping")
    else:
        for key in ("max_turns", "max_consecutive_failures", "token_cap"):
            value = budget.get(key)
            if not isinstance(value, int) or value <= 0:
                errors.append(f"budget.{key} must be a positive integer")
        if budget.get("preflight_estimate") not in {"required", "complete"}:
            errors.append("budget.preflight_estimate must be required or complete")

    thresholds = data.get("kill_scale_graduate")
    if not isinstance(thresholds, dict):
        errors.append("kill_scale_graduate must be a mapping")
    else:
        for key in ("kill", "graduate", "scale"):
            if not nonempty_text(thresholds.get(key)):
                errors.append(f"kill_scale_graduate.{key} must be non-empty text")


def validate_goal(data: dict[str, Any], errors: list[str]) -> None:
    goal = data.get("goal_condition")
    if not nonempty_text(goal):
        errors.append("goal_condition must be non-empty text")
        return
    goal_lower = goal.lower()
    if "gate" not in goal_lower or "exit 0" not in goal_lower:
        errors.append("goal_condition must reference gate exit 0 status")
    if "scope" not in goal_lower and "git diff" not in goal_lower:
        errors.append("goal_condition must reference scope or git diff checks")
    for word in VAGUE_GOAL_WORDS:
        if word in goal_lower:
            errors.append(f"goal_condition contains vague/non-deterministic term: {word}")


def validate_ledger(data: dict[str, Any], errors: list[str]) -> None:
    ledger = data.get("ledger")
    if not isinstance(ledger, dict):
        errors.append("ledger must be a mapping")
        return
    for key in ("turns", "consecutive_failures"):
        if not isinstance(ledger.get(key), int) or ledger[key] < 0:
            errors.append(f"ledger.{key} must be a non-negative integer")
    if not isinstance(ledger.get("cost_to_date"), (int, float)) or ledger["cost_to_date"] < 0:
        errors.append("ledger.cost_to_date must be a non-negative number")
    for key in ("blockers", "lessons"):
        if not isinstance(ledger.get(key), list):
            errors.append(f"ledger.{key} must be a list")


def section_map(body: str) -> dict[str, str]:
    matches = list(re.finditer(r"^## ([^\n]+)\s*$", body, flags=re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        name = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections[name] = body[start:end].strip()
    return sections


def validate_body(body: str, errors: list[str]) -> None:
    headings = re.findall(r"^## ([^\n]+)\s*$", body, flags=re.MULTILINE)
    if headings != REQUIRED_BODY_H2:
        errors.append(f"body must contain exactly these H2 sections in order: {', '.join(REQUIRED_BODY_H2)}")
        return
    sections = section_map(body)
    for name in REQUIRED_BODY_H2:
        if len(sections.get(name, "")) < 40:
            errors.append(f"body section {name!r} is too thin")
    split = sections.get("Build Loop vs Product Loop", "").lower()
    if "product" not in split or "build" not in split or "gate" not in split:
        errors.append("Build Loop vs Product Loop must mention product loop, build loop, and gates")
    if "may not claim" not in split and "must not claim" not in split:
        errors.append("Build Loop vs Product Loop must say the coding model may/must not claim the product bet from gate success")


def validate_data(data: dict[str, Any], body: str, mode: str) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED_TOP_LEVEL:
        if key not in data:
            errors.append(f"{key} is required")
    if errors:
        return errors

    if data.get("status") not in ALLOWED_STATUSES:
        errors.append(f"status must be one of {sorted(ALLOWED_STATUSES)}")
    if data.get("target_agent") not in ALLOWED_AGENTS:
        errors.append(f"target_agent must be one of {sorted(ALLOWED_AGENTS)}")
    if not nonempty_text(data.get("spec_id")):
        errors.append("spec_id must be non-empty text")

    validate_scope(data, mode, errors)
    validate_bet(data, errors)
    validate_invariants_and_gates(data, mode, errors)
    validate_review_budget_thresholds(data, errors)
    validate_goal(data, errors)
    validate_ledger(data, errors)
    validate_body(body, errors)

    if mode == "build":
        for placeholder_error in walk_placeholders(data):
            if "command" in placeholder_error or "DISCOVER_TARGETS" in placeholder_error:
                errors.append(placeholder_error)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a Divecha .spec.md implementation contract.")
    parser.add_argument("spec", type=Path, help="Path to <task>.spec.md")
    parser.add_argument("--mode", choices=["author", "build"], default="author")
    args = parser.parse_args(argv)

    try:
        data, body = load_contract(args.spec)
    except Exception as exc:  # noqa: BLE001 - CLI should report all parse failures
        print("DIVECHA_CONTRACT_INVALID")
        print(f"- {exc}")
        return 1

    errors = validate_data(data, body, args.mode)
    if errors:
        print("DIVECHA_CONTRACT_INVALID")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"DIVECHA_CONTRACT_VALID mode={args.mode} path={args.spec}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
