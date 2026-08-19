"""Configuration loaders for YAML, JSON, TOML, and .env formats."""

import importlib
import json
import re
from pathlib import Path
from typing import Any

_literal_dotted_cache: dict[str, dict[str, tuple[str, ...]]] = {}


def get_literal_dotted_keys(path: str) -> dict[str, tuple[str, ...]]:
    """Retrieve literal dotted keys stored by the most recent load_file(path) call.

    Returns a dict mapping each flattened key whose reconstruction path
    differs from naive dot-splitting to the tuple of original key segments.
    For example, ``{"service.config.host": ("service.config", "host")}``
    means the first segment is a literal dotted key ``service.config``
    with child ``host`` nested beneath it.
    """
    return _literal_dotted_cache.get(str(Path(path).resolve()), {})


def has_dotted_collision(flat_data: dict[str, Any]) -> list[str]:
    """Detect ambiguous collisions between literal dotted keys and nested paths.

    Returns the list of flat keys that appear both as a literal dotted key
    (a top-level key whose name already contains ``.`` in the source
    document) AND as the reconstruction of a genuinely nested path. When
    both exist, flattening collapses them to a single key — the later
    value overwrites the earlier — and reconstruction writes back only
    one of the two mappings, silently deleting the other. Callers should
    reject write-back for any target where this returns non-empty.

    Detection: a flat key is ambiguous iff it appears as a literal dotted
    key AND there also exists some other flat key that shares its prefix
    (i.e., the nested form ``k.replace('.', '/')`` would nest under the
    same path).
    """
    collisions: list[str] = []
    for k in flat_data:
        if "." not in k:
            continue
        # A key is a literal dotted key iff splitting it yields a path
        # that does NOT exist elsewhere — but we can detect collision
        # directly: the same flat key is reachable both ways iff some
        # other flat key starts with ``k + "."`` (nested children) or
        # k's prefix path exists as a separate top-level mapping.
        # Simpler: look for any other flat key that would reconstruct
        # to the same nested location. A genuine nested form of ``k``
        # is present iff there exists a flat key ``k + ".<child>"``.
        prefix = k + "."
        if any(other.startswith(prefix) for other in flat_data if other != k):
            collisions.append(k)
    return collisions


_toml = importlib.import_module("tomllib" if __import__("sys").version_info >= (3, 11) else "tomli")


def load_file(path: str) -> dict[str, Any]:
    """Load a config file based on its extension.

    Returns flat data with dot-separated keys for nested values.
    Literal dotted keys (top-level keys already containing dots in the
    source document) are stored internally and can be retrieved via
    ``get_literal_dotted_keys(path)`` — used by the ``fix`` command to
    avoid re-splitting them during reconstruction.
    """
    p = Path(path)
    ext = p.suffix.lower()
    resolved = str(p.resolve())
    if ext in (".yaml", ".yml"):
        result, literal = _load_yaml(p)
        _literal_dotted_cache[resolved] = literal
        return result
    elif ext == ".json":
        result, literal = _load_json(p)
        _literal_dotted_cache[resolved] = literal
        return result
    elif ext == ".toml":
        result, literal = _load_toml(p)
        _literal_dotted_cache[resolved] = literal
        return result
    elif ext == ".env" or p.name == ".env" or p.name.startswith(".env."):
        _literal_dotted_cache[resolved] = {}
        return _load_dotenv(p)
    else:
        for loader in [_load_yaml, _load_json, _load_toml]:
            try:
                result, literal = loader(p)
                _literal_dotted_cache[resolved] = literal
                return result
            except Exception:
                continue
        # Last resort: try dotenv
        try:
            _literal_dotted_cache[resolved] = {}
            return _load_dotenv(p)
        except Exception:
            pass
        raise ValueError(f"Unsupported file format: {ext}") from None


def _load_yaml(path: Path) -> tuple[dict[str, Any], dict[str, tuple[str, ...]]]:
    import yaml

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain a mapping at the top level, got {type(data).__name__}")
    return _flatten_nested(data)


def _load_json(path: Path) -> tuple[dict[str, Any], dict[str, tuple[str, ...]]]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain an object at the top level, got {type(data).__name__}")
    return _flatten_nested(data)


def _load_toml(path: Path) -> tuple[dict[str, Any], dict[str, tuple[str, ...]]]:
    with open(path, "rb") as f:
        data = _toml.load(f)
    return _flatten_nested(data)


def _strip_inline_comment(value: str) -> str:
    """Strip unquoted inline comments from .env values.

    Handles: KEY=value # comment  →  value
    Preserves: KEY="val # ue"       →  "val # ue" (quotes stripped later)
    Handles: KEY="say \"#\" now"    →  "say \"#\" now" (escaped quotes don't toggle)
    """
    in_single = False
    in_double = False
    i = 0
    while i < len(value):
        ch = value[i]
        # Handle backslash-escaped characters inside double quotes
        if ch == "\\" and in_double and i + 1 < len(value):
            i += 2  # skip the escaped character
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "'" and not in_double:
            in_single = not in_single
        elif ch == "#" and not in_single and not in_double:
            return value[:i].rstrip()
        i += 1
    return value


def _load_dotenv(path: Path) -> dict[str, Any]:
    """Parse .env files. Returns flat key-value dict."""
    data = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Strip optional 'export ' prefix (shell-style .env files)
            line = re.sub(r"^export\s+", "", line)
            # Parse KEY=VALUE or KEY="VALUE" or KEY='VALUE'
            match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
            if match:
                key = match.group(1)
                val = match.group(2).strip()
                # Strip inline comments (only outside quotes)
                val = _strip_inline_comment(val)
                # Strip surrounding quotes
                if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
                    quote_char = val[0]
                    val = val[1:-1]
                    # Unescape backslash-escaped quotes for round-trip
                    # fidelity with the fix writer (KEY="say \"hi\"")
                    if quote_char == '"':
                        # Unescape: first \" → ", then remaining \\ → \.
                        # Order matters: reversing would turn \\" into \"
                        # instead of the correct \".
                        val = val.replace('\\"', '"').replace("\\\\", "\\")
                data[key] = val
    return data


def _flatten_nested(
    d: dict[str, Any], prefix: str = "", path_parts: tuple[str, ...] = ()
) -> tuple[dict[str, Any], dict[str, tuple[str, ...]]]:
    """Flatten nested dicts into dot-separated keys.

    Preserves non-dict collection values (lists, tuples) and scalar values
    without converting them to strings.  Keys that are already dotted in
    the source document are kept literal — they are never re-split on
    ``.`` during reconstruction.

    Returns a tuple of ``(flat_dict, literal_dotted)`` where
    ``literal_dotted`` maps each flattened key whose reconstruction path
    differs from naive dot-splitting to the tuple of original key segments.
    For example, ``{"service.config.host": ("service.config", "host")}``
    indicates the top-level key ``service.config`` (a literal dotted key)
    with ``host`` nested beneath it.  During reconstruction, the path
    tuple is used directly instead of splitting on ``.``.
    """
    result: dict[str, Any] = {}
    literal_dotted: dict[str, tuple[str, ...]] = {}
    for key, value in d.items():
        full_key = f"{prefix}.{key}" if prefix else key
        current_path = path_parts + (key,)
        if isinstance(value, dict):
            if not value:
                # Preserve empty mappings so reconstruction doesn't
                # silently drop them when other keys need fixing.
                result[full_key] = {}
            else:
                sub, sub_literal = _flatten_nested(value, full_key, current_path)
                result.update(sub)
                literal_dotted.update(sub_literal)
        elif value is None:
            # Preserve null as None so the fix cycle can distinguish
            # "baseline is null" from "baseline is empty string".
            # Writers handle None appropriately per format.
            result[full_key] = None
        else:
            # Preserve lists, tuples, ints, floats, bools, and strings as-is
            result[full_key] = value
        # Record the path whenever it differs from naive dot-splitting.
        # This covers: literal dotted leaf keys, literal dotted parent
        # keys with dict children (propagating boundary to descendants),
        # and any combination thereof.
        if "." in full_key and tuple(full_key.split(".")) != current_path:
            literal_dotted[full_key] = current_path
    return result, literal_dotted
