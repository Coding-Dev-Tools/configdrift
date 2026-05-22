"""Configuration loaders for YAML, JSON, TOML, and .env formats."""

import json
import re
from pathlib import Path
from typing import Any


def load_file(path: str) -> dict[str, Any]:
    """Load a config file based on its extension."""
    p = Path(path)
    ext = p.suffix.lower()
    if ext in (".yaml", ".yml"):
        return _load_yaml(p)
    elif ext == ".json":
        return _load_json(p)
    elif ext == ".toml":
        return _load_toml(p)
    elif ext == ".env":
        return _load_dotenv(p)
    else:
        # Try known parsers in order
        for loader in [_load_yaml, _load_json, _load_toml]:
            try:
                return loader(p)
            except Exception:
                continue
        # Fallback: try as .env-like key-value
        try:
            return _load_dotenv(p)
        except Exception:
            raise ValueError(f"Unsupported file format: {ext}") from None


def _load_yaml(path: Path) -> dict[str, Any]:
    import yaml
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain a mapping (dict), got {type(data).__name__}")
    return _flatten_nested(data)


def _load_json(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain a mapping (dict), got {type(data).__name__}")
    return _flatten_nested(data)


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        import tomli as tomllib  # Python 3.10
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return _flatten_nested(data)


def _strip_inline_comment(value: str) -> str:
    """Strip unquoted inline comments from .env values.

    Handles: KEY=value # comment  →  value
    Preserves: KEY="val # ue"       →  "val # ue" (quotes stripped later)
    """
    in_single = False
    in_double = False
    for i, ch in enumerate(value):
        if ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "'" and not in_double:
            in_single = not in_single
        elif ch == "#" and not in_single and not in_double:
            return value[:i].rstrip()
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
            line = re.sub(r'^export\s+', '', line)
            # Parse KEY=VALUE or KEY="VALUE" or KEY='VALUE'
            match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$', line)
            if match:
                key = match.group(1)
                val = match.group(2).strip()
                # Strip inline comments (only outside quotes)
                val = _strip_inline_comment(val)
                # Strip surrounding quotes
                if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
                    val = val[1:-1]
                data[key] = val
    return data


def _flatten_nested(d: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Flatten nested dicts into dot-separated keys."""
    result = {}
    for key, value in d.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(_flatten_nested(value, full_key))
        else:
            if value is None:
                result[full_key] = ""
            else:
                result[full_key] = str(value) if not isinstance(value, (str, int, float, bool)) else value
    return result
