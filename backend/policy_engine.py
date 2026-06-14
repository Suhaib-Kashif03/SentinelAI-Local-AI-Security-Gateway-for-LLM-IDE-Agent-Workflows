from pathlib import Path
from typing import Dict, List, Optional, Set

import yaml


DECISION_RANK = {
    "ALLOW": 0,
    "WARN": 1,
    "REQUIRE_APPROVAL": 2,
    "BLOCK": 3
}


DEFAULT_POLICY = {
    "policy_name": "built_in_default_policy",
    "version": 1.0,
    "mode": "default",
    "thresholds": {
        "allow_max_score": 20,
        "warn_min_score": 21,
        "require_approval_min_score": 50,
        "block_min_score": 80
    },
    "category_actions": {
        "PROMPT_INJECTION": "BLOCK",
        "JAILBREAK": "REQUIRE_APPROVAL",
        "SECRET_LEAKAGE": "BLOCK",
        "DESTRUCTIVE_COMMAND": "BLOCK",
        "UNSAFE_NETWORK_EXECUTION": "BLOCK",
        "NETWORK_EXFILTRATION": "BLOCK",
        "SECURITY_CONTROL_DISABLE": "BLOCK",
        "PRIVILEGE_ESCALATION": "REQUIRE_APPROVAL",
        "PACKAGE_INSTALLATION": "REQUIRE_APPROVAL",
        "SYSTEM_RECONNAISSANCE": "WARN",
        "NETWORK_RECONNAISSANCE": "WARN",
        "UNSAFE_CODE": "REQUIRE_APPROVAL",
        "CONTAINER_ESCAPE_RISK": "BLOCK",
        "UNKNOWN_RISK": "WARN"
    }
}


def get_default_policy_path() -> Path:
    """
    Return the default policy path from the project root.
    """
    project_root = Path(__file__).resolve().parent.parent
    return project_root / "policies" / "default_policy.yaml"


def deep_merge(base: Dict, override: Dict) -> Dict:
    """
    Recursively merge two dictionaries.
    Values from override take priority.
    """
    result = base.copy()

    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def load_policy(policy_path: Optional[str] = None) -> Dict:
    """
    Load policy from YAML file.

    If the file is missing or invalid, fall back to the built-in default policy.
    """
    path = Path(policy_path) if policy_path else get_default_policy_path()

    if not path.exists():
        return DEFAULT_POLICY

    try:
        with open(path, "r", encoding="utf-8") as file:
            loaded_policy = yaml.safe_load(file) or {}

        return deep_merge(DEFAULT_POLICY, loaded_policy)

    except Exception:
        return DEFAULT_POLICY


def decision_from_score(risk_score: int, policy: Dict) -> str:
    """
    Convert risk score into decision using policy thresholds.
    """
    thresholds = policy.get("thresholds", {})

    allow_max = thresholds.get("allow_max_score", 20)
    warn_min = thresholds.get("warn_min_score", 21)
    approval_min = thresholds.get("require_approval_min_score", 50)
    block_min = thresholds.get("block_min_score", 80)

    if risk_score >= block_min:
        return "BLOCK"

    if risk_score >= approval_min:
        return "REQUIRE_APPROVAL"

    if risk_score >= warn_min:
        return "WARN"

    if risk_score <= allow_max:
        return "ALLOW"

    return "WARN"


def strongest_decision(decisions: List[str]) -> str:
    """
    Return the strongest decision from a list.

    BLOCK > REQUIRE_APPROVAL > WARN > ALLOW
    """
    if not decisions:
        return "ALLOW"

    return max(decisions, key=lambda decision: DECISION_RANK.get(decision, 0))


def decision_from_categories(categories: Set[str], policy: Dict) -> str:
    """
    Convert matched security categories into a policy-based decision.
    """
    category_actions = policy.get("category_actions", {})

    decisions = []

    for category in categories:
        action = category_actions.get(category)

        if action:
            decisions.append(action)

    return strongest_decision(decisions)


def decide_by_policy(
    risk_score: int,
    categories: Set[str],
    policy_path: Optional[str] = None
) -> str:
    """
    Final policy decision.

    The final decision is the strongest result from:
    1. Risk-score threshold decision
    2. Category action decision
    """
    policy = load_policy(policy_path)

    score_decision = decision_from_score(risk_score, policy)
    category_decision = decision_from_categories(categories, policy)

    return strongest_decision([score_decision, category_decision])


def get_policy_summary(policy_path: Optional[str] = None) -> Dict:
    """
    Return policy metadata for API visibility.
    """
    policy = load_policy(policy_path)

    return {
        "policy_name": policy.get("policy_name"),
        "version": policy.get("version"),
        "mode": policy.get("mode"),
        "thresholds": policy.get("thresholds"),
        "category_actions": policy.get("category_actions"),
        "audit": policy.get("audit", {}),
        "redaction": policy.get("redaction", {})
    }