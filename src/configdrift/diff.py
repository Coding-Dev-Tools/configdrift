"""Diff engine for comparing configuration dictionaries."""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ChangeType(Enum):
    ADDED = "added"
    REMOVED = "removed"
    CHANGED = "changed"


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    BREAKING = "breaking"


# Pre-compiled regex for camelCase splitting
_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def _split_key_into_words(key: str) -> list[str]:
    """
    Split a flattened config key into its component words.

    Handles:
    - dot notation: services.database.password -> [services, database, password]
    - snake_case: api_key -> [api, key]
    - kebab-case: api-key -> [api, key]
    - camelCase: apiKey -> [api, key]
    - concatenated: apikey -> [api, key] (via critical prefix matching below)

    Returns list of lowercase words.
    """
    # First split on common delimiters
    parts = re.split(r"[._-]+", key)

    words = []
    for part in parts:
        # Split camelCase
        camel_parts = _CAMEL_RE.split(part)
        words.extend([p.lower() for p in camel_parts if p])

    return words


def _key_contains_critical_term(key: str, critical_terms: tuple[str, ...]) -> bool:
    """
    Check if a flattened key contains any critical term as a word-boundary match.

    A match occurs when the critical term's word sequence appears as a contiguous
    subsequence in the key's word sequence. Also handles concatenated forms
    for MULTI-WORD terms (e.g., 'apikey' matches 'api_key' -> ['api', 'key']).
    Single-word terms like 'auth', 'secret', 'token' do NOT get concatenated
    matching to avoid false positives (e.g., 'author' should not match 'auth').

    Examples:
    - 'services.database.password' with 'database' -> True (word boundary)
    - 'services.database.password' with 'api_key' -> False
    - 'author' with 'auth' -> False (author != auth, word boundary prevents false positive)
    - 'secretary' with 'secret' -> False (secretary != secret)
    - 'tokenizer' with 'token' -> False (tokenizer != token)
    - 'apikey' with 'api_key' -> True (concatenated form handled for multi-word terms)
    """
    key_words = _split_key_into_words(key)

    for term in critical_terms:
        term_words = _split_key_into_words(term)
        term_len = len(term_words)

        if term_len == 0:
            continue

        # Check for contiguous subsequence match (word boundary)
        for i in range(len(key_words) - term_len + 1):
            if key_words[i:i + term_len] == term_words:
                return True

        # Also check concatenated form for MULTI-WORD terms only.
        # Single-word terms (auth, secret, token, database, password, endpoint)
        # would cause false positives like 'author' -> 'auth'.
        if term_len > 1:
            concatenated = "".join(term_words)
            key_normalized = key.lower().replace(".", "").replace("_", "").replace("-", "")
            if concatenated in key_normalized:
                return True

    return False


@dataclass
class Change:
    key: str
    change_type: ChangeType
    old_value: Any | None = None
    new_value: Any | None = None
    severity: Severity = Severity.INFO
    env: str | None = None

    def __str__(self) -> str:
        if self.change_type == ChangeType.ADDED:
            return f"[+] {self.key} = {self.new_value!r}  (env: {self.env})"
        elif self.change_type == ChangeType.REMOVED:
            return f"[-] {self.key} (was {self.old_value!r})  (env: {self.env})"
        else:
            return f"[~] {self.key}: {self.old_value!r} → {self.new_value!r}  (env: {self.env})"


@dataclass
class DiffResult:
    changes: list[Change] = field(default_factory=list)

    @property
    def has_breaking(self) -> bool:
        return any(c.severity == Severity.BREAKING for c in self.changes)

    @property
    def count(self) -> int:
        return len(self.changes)

    def by_type(self, change_type: ChangeType) -> list[Change]:
        return [c for c in self.changes if c.change_type == change_type]

    def by_severity(self, severity: Severity) -> list[Change]:
        return [c for c in self.changes if c.severity == severity]


def _values_differ(old: Any, new: Any) -> bool:
    """Type-sensitive value comparison.

    Python's ``==`` treats ``True == 1`` and ``False == 0``, so a config change
    like ``debug: true -> debug: 1`` would silently compare equal. A drift
    detector must flag cross-type changes (bool vs number) even when values
    compare equal.
    """
    if isinstance(old, bool) != isinstance(new, bool):
        return True
    return old != new


def diff_configs(
    base: dict[str, Any],
    target: dict[str, Any],
    base_env: str = "base",
    target_env: str = "target",
) -> DiffResult:
    """Compare two flat config dictionaries and return the diff."""
    result = DiffResult()
    all_keys = set(base.keys()) | set(target.keys())

    for key in sorted(all_keys):
        old_val = base.get(key)
        new_val = target.get(key)

        if key not in base:
            result.changes.append(
                Change(
                    key=key,
                    change_type=ChangeType.ADDED,
                    new_value=new_val,
                    severity=_infer_severity_added(key, new_val),
                    env=target_env,
                )
            )
        elif key not in target:
            result.changes.append(
                Change(
                    key=key,
                    change_type=ChangeType.REMOVED,
                    old_value=old_val,
                    severity=_infer_severity_removed(key, old_val),
                    env=base_env,
                )
            )
        elif _values_differ(old_val, new_val):
            result.changes.append(
                Change(
                    key=key,
                    change_type=ChangeType.CHANGED,
                    old_value=old_val,
                    new_value=new_val,
                    severity=_infer_severity_changed(key, old_val, new_val),
                    env=target_env,
                )
            )

    return result


def diff_environments(
    env_configs: dict[str, dict[str, Any]], baseline_env: str = "dev"
) -> dict[str, DiffResult]:
    """Compare multiple environments against a baseline."""
    if baseline_env not in env_configs:
        raise ValueError(f"Baseline environment '{baseline_env}' not found in configs")

    baseline = env_configs[baseline_env]
    results = {}
    for env_name, config in env_configs.items():
        if env_name == baseline_env:
            continue
        results[env_name] = diff_configs(baseline, config, baseline_env, env_name)
    return results


_CRITICAL_PREFIXES = (
    "database",
    "auth",
    "api_key",
    "secret",
    "password",
    "token",
    "endpoint",
    "auth_token",
    "secret_key",
    "password_hash",
    "database_url",
)


def _infer_severity_added(key: str, value: Any) -> Severity:
    """Heuristic: classify severity as BREAKING if the key contains a critical term at a word boundary."""
    if _key_contains_critical_term(key, _CRITICAL_PREFIXES):
        return Severity.BREAKING
    return Severity.WARNING


def _infer_severity_removed(key: str, value: Any) -> Severity:
    if _key_contains_critical_term(key, _CRITICAL_PREFIXES):
        return Severity.BREAKING
    return Severity.WARNING


def _infer_severity_changed(key: str, old: Any, new: Any) -> Severity:
    if _key_contains_critical_term(key, _CRITICAL_PREFIXES):
        return Severity.BREAKING
    return Severity.INFO
