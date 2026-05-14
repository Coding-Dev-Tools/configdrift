# ConfigDrift

Your configs drifted again. ConfigDrift catches it before production does.

[![PyPI](https://img.shields.io/pypi/v/configdrift)](https://pypi.org/project/configdrift/)
[![Python](https://img.shields.io/pypi/pyversions/configdrift)](https://pypi.org/project/configdrift/)
[![License](https://img.shields.io/pypi/l/configdrift)](https://github.com/Coding-Dev-Tools/configdrift/blob/main/LICENSE)

**Why ConfigDrift?** Dev and prod configs always diverge — it's not if, it's when. One missing env var, one wrong endpoint, one stale secret, and your deployment breaks silently. ConfigDrift compares configurations across environments, highlights drift, deprecated keys, and missing values before they become incidents. Supports YAML, JSON, TOML, and .env — and it works in CI.

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

## Pricing

One license covers all Revenue Holdings CLI tools. Pricing is per-seat.

| Tier | Price | Best For |
|------|-------|----------|
| **Open Source** | $0 | Individual devs, OSS projects — CLI only, 1 env pair |
| **Pro** | **$29/mo** ($23 billed annually) | Professional devs — unlimited environments, custom rules |
| **Team** | **$79/mo** ($63 billed annually) | Teams up to 5 — drift history, Slack alerts, priority support |
| **Enterprise** | **$199/mo** (custom) | Organizations — compliance reports, RBAC, SSO, SLA |

🔹 **No lock-in**: CLI works fully offline on the free tier — no telemetry, no phone-home.  
🔹 **Annual billing**: Save 20%.  

### Per-Tier Features

| Feature | OSS | Pro | Team | Enterprise |
|---------|:---:|:---:|:----:|:----------:|
| CLI: check, scan | ✓ | ✓ | ✓ | ✓ |
| Unlimited environments | — | ✓ | ✓ | ✓ |
| Drift history / audit trail | — | — | ✓ | ✓ |
| Slack / webhook alerts | — | — | ✓ | ✓ |
| Compliance reports | — | — | — | ✓ |
| RBAC | — | — | — | ✓ |
| SSO / SAML / OIDC | — | — | — | ✓ |
| Priority support | Community | 24h | 8h | Dedicated |

## License

MIT
