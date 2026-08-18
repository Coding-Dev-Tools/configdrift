"""Configuration loaders for YAML, JSON, TOML, and .env formats."""

import importlib
import json
import re
from pathlib import Path
from typing import Any

_toml = importlib.import_module("tomllib" if __import__("sys").version_info >= (3, 11) else "tomli")


def load_file(path: str) -> tuple[dict[str, Any], set[str]]:
    """Load a config file based on its extension.

    Returns a tuple of (flat_data, literal_dotted_keys) where
    literal_dotted_keys is the set of top-level keys that already
    contained dots in the original document.
    """
    p = Path(path)
    ext = p.suffix.lower()
    if ext in (".yaml", ".yml"):
        return _load_yaml(p)
    elif ext == ".json":
        return _load_json(p)
    elif ext == ".toml":
        return _load_toml(p)
    elif ext == ".env":
        return _load_dotenv(p), set()
    else:
        # Try known parsers in order
        for loader in [_load_yaml, _load_json, _load_toml]:
            try:
                return loader(p)
            except Exception:
                continue
        # Last resort: try dotenv
        try:
            return _load_dotenv(p), set()
        except Exception:
            pass
        raise ValueError(f"Unsupported file format: {ext}") from None


def _load_yaml(path: Path) -> tuple[dict[str, Any], set[str]]:
    import yaml

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain a mapping at the top level, got {type(data).__name__}")
    return _flatten_nested(data)


def _load_json(path: Path) -> tuple[dict[str, Any], set[str]]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain an object at the top level, got {type(data).__name__}")
    return _flatten_nested(data)


def _load_toml(path: Path) -> tuple[dict[str, Any], set[str]]:
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


def _flatten_nested(d: dict[str, Any], prefix: str = "") -> tuple[dict[str, Any], set[str]]:
    """Flatten nested dicts into dot-separated keys.

    Preserves non-dict collection values (lists, tuples) and scalar values
    without converting them to strings.  Keys that are already dotted in
    the source document are kept literal — they are never re-split on
    ``.`` during reconstruction.

    Returns a tuple of (flat_dict, literal_dotted_keys) where
    literal_dotted_keys is the set of top-level keys in the original
    document that already contained dots.
    """
    result: dict[str, Any] = {}
    literal_dotted: set[str] = set()
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
        # Track keys that already contained dots in the ORIGINAL document
        # (not from flattening) so reconstruction can skip splitting them.
        if not prefix and isinstance(key, str) and "." in key:
            literal_dotted.add(key)
    return result, literal_dotted
