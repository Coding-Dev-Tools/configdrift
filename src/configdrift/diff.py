"""Diff engine for comparing configuration dictionaries."""

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


def diff_configs(base: dict[str, Any], target: dict[str, Any],
                 base_env: str = "base", target_env: str = "target") -> DiffResult:
    """Compare two flat config dictionaries and return the diff."""
    result = DiffResult()
    all_keys = set(base.keys()) | set(target.keys())

    for key in sorted(all_keys):
        old_val = base.get(key)
        new_val = target.get(key)

        if key not in base:
            result.changes.append(Change(
                key=key,
                change_type=ChangeType.ADDED,
                new_value=new_val,
                severity=_infer_severity_added(key, new_val),
                env=target_env,
            ))
        elif key not in target:
            result.changes.append(Change(
                key=key,
                change_type=ChangeType.REMOVED,
                old_value=old_val,
                severity=_infer_severity_removed(key, old_val),
                env=base_env,
            ))
        elif old_val != new_val:
            result.changes.append(Change(
                key=key,
                change_type=ChangeType.CHANGED,
                old_value=old_val,
                new_value=new_val,
                severity=_infer_severity_changed(key, old_val, new_val),
                env=target_env,
            ))

    return result


def diff_environments(env_configs: dict[str, dict[str, Any]],
                      baseline_env: str = "dev") -> dict[str, DiffResult]:
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
    "database", "auth", "api_key", "secret", "password", "token", "endpoint",
)


def _infer_severity_added(key: str, value: Any) -> Severity:
    """Heuristic: critical keys missing from base indicate drift."""
    if any(key.lower().startswith(p) for p in _CRITICAL_PREFIXES):
        return Severity.BREAKING
    return Severity.WARNING


def _infer_severity_removed(key: str, value: Any) -> Severity:
    if any(key.lower().startswith(p) for p in _CRITICAL_PREFIXES):
        return Severity.BREAKING
    return Severity.WARNING


def _infer_severity_changed(key: str, old: Any, new: Any) -> Severity:
    if any(key.lower().startswith(p) for p in _CRITICAL_PREFIXES):
        return Severity.BREAKING
    return Severity.INFO
