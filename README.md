# ConfigDrift

Detect and fix configuration file drift across environments (dev/staging/prod).

[![PyPI](https://img.shields.io/pypi/v/configdrift)](https://pypi.org/project/configdrift/)
[![Python](https://img.shields.io/pypi/pyversions/configdrift)](https://pypi.org/project/configdrift/)
[![License](https://img.shields.io/pypi/l/configdrift)](https://github.com/Coding-Dev-Tools/configdrift/blob/main/LICENSE)

ConfigDrift compares configuration files across environments and highlights drift, deprecated keys, and missing values. It supports YAML, JSON, TOML, and .env formats.

## Installation

```bash
pip install configdrift
```

## Quick Start

Compare two config files:

```bash
configdrift check dev.yaml prod.yaml
```

Scan entire directories as environments:

```bash
configdrift scan ./config/dev ./config/staging ./config/prod
```

Use a config file to define environments:

```bash
configdrift init
configdrift scan --config .configdrift.yaml
```

## Usage

### `check` — Compare config files

```bash
configdrift check <file1> <file2> [--output table|json|silent] [--baseline dev] [--target prod]
```

Output formats:
- `table` (default): Rich colored table output
- `json`: Machine-readable JSON for CI integration
- `silent`: Exit code only (0 = no breaking drift, 1 = breaking drift found)

### `scan` — Compare environment directories

```bash
configdrift scan ./dev ./staging ./prod --baseline dev
```

Scans all config files in each directory, merges them, and compares against a baseline environment.

### `init` — Generate a config file

```bash
configdrift init .
```

Creates `.configdrift.yaml` in the specified directory.

### CI/CD Integration

Use `--output silent` for CI gating:

```bash
configdrift check dev.yaml prod.yaml --output silent || echo "Drift detected!"
```

## Supported Formats

| Format  | Extension      | Notes                         |
|---------|---------------|-------------------------------|
| YAML    | `.yaml`, `.yml` | Full nested structure support |
| JSON    | `.json`        | Nested flattening             |
| TOML    | `.toml`        | Python 3.11+ native           |
| .env    | `.env`         | `KEY=VALUE` format            |

## Severity Levels

- **Info**: Non-critical value changes
- **Warning**: Added or removed optional keys
- **Breaking**: Changes to critical keys (`database*`, `auth*`, `api_key*`, `secret*`, `password*`, `token*`, `endpoint*`)

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=configdrift
```

## License

MIT
