"""Configuration loaders for YAML, JSON, TOML, and .env formats."""

import importlib
import json
import re
from pathlib import Path
from typing import Any

_literal_dotted_cache: dict[str, dict[str, int]] = {}


def get_literal_dotted_keys(path: str) -> dict[str, int]:
    """Retrieve literal dotted keys stored by the most recent load_file(path) call.

    Returns a dict mapping each flattened key that contained a literal dot
    in the source document to its parent nesting depth (number of real
    nesting levels above the literal-dotted leaf).  For example,
    ``{"outer.log.level": 1}`` means split on the first dot to get the
    parent ``outer``, then keep ``log.level`` as the leaf key.
    """
    return _literal_dotted_cache.get(str(Path(path).resolve()), {})


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
    elif ext == ".env":
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


def _load_yaml(path: Path) -> tuple[dict[str, Any], dict[str, int]]:
    import yaml

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain a mapping at the top level, got {type(data).__name__}")
    return _flatten_nested(data)


def _load_json(path: Path) -> tuple[dict[str, Any], dict[str, int]]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain an object at the top level, got {type(data).__name__}")
    return _flatten_nested(data)


def _load_toml(path: Path) -> tuple[dict[str, Any], dict[str, int]]:
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
        if ch == '\\' and in_double and i + 1 < len(value):
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
                        val = val.replace('\\"', '"')
                data[key] = val
    return data


def _flatten_nested(d: dict[str, Any], prefix: str = "") -> tuple[dict[str, Any], dict[str, int]]:
    """Flatten nested dicts into dot-separated keys.

    Preserves non-dict collection values (lists, tuples) and scalar values
    without converting them to strings.  Keys that are already dotted in
    the source document are kept literal — they are never re-split on
    ``.`` during reconstruction.

    Returns a tuple of ``(flat_dict, literal_dotted)`` where
    ``literal_dotted`` is a dict mapping each flattened key whose *leaf*
    already contained a dot in the source document to its parent nesting
    depth (the number of real dict levels above the literal-dotted leaf).
    A top-level literal dotted key has depth ``0``; a literal dotted key
    under ``{"outer": {"log.level": "x"}}`` flattens to ``"outer.log.level"``
    with depth ``1`` so reconstruction can rebuild the ``outer`` parent
    while keeping ``log.level`` as a single leaf key.
    """
    result: dict[str, Any] = {}
    literal_dotted: dict[str, int] = {}
    # Parent depth for keys beneath this prefix: number of dict levels
    # already traversed. Empty prefix = top level (0); each dot in a
    # non-empty prefix represents one level.
    parent_depth = 0 if not prefix else prefix.count(".") + 1
    for key, value in d.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            if not value:
                # Preserve empty mappings so reconstruction doesn't
                # silently drop them when other keys need fixing.
                result[full_key] = {}
            else:
                sub, sub_literal = _flatten_nested(value, full_key)
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
        # Track keys whose LEAF already contained a dot in the ORIGINAL
        # document (not from flattening) so reconstruction can keep the
        # leaf as a single mapping key. Record at every nesting level
        # because nested mappings can also carry literal dotted keys.
        if isinstance(key, str) and "." in key:
            literal_dotted[full_key] = parent_depth
    return result, literal_dotted
