# ConfigDrift

[![GitHub stars](https://img.shields.io/github/stars/Coding-Dev-Tools/configdrift?style=social)](https://github.com/Coding-Dev-Tools/configdrift/stargazers)

Keep configurations consistent across all environments, automatically. ConfigDrift compares configs, flags drift, and reports compliance violations before they cause incidents.

> ⭐ **Star this repo** if you manage multi-environment configs — it helps other devs find ConfigDrift!

[![GitHub release](https://img.shields.io/github/v/release/Coding-Dev-Tools/configdrift?label=latest)](https://github.com/Coding-Dev-Tools/configdrift/releases)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/Coding-Dev-Tools/configdrift/blob/main/LICENSE)
[![Open Source Alternative](https://img.shields.io/badge/Open_Source_Alternative-%E2%87%92-blue?logo=opensourceinitiative)](https://www.opensourcealternative.to/project/configdrift)
[![CI](https://github.com/Coding-Dev-Tools/configdrift/actions/workflows/ci.yml/badge.svg)](https://github.com/Coding-Dev-Tools/configdrift/actions/workflows/ci.yml)
[![GitHub last commit](https://img.shields.io/github/last-commit/Coding-Dev-Tools/configdrift)](https://github.com/Coding-Dev-Tools/configdrift/commits)



Real-world scenarios:
- **Multi-environment compliance**: Ensure staging and prod configs are identical before every deploy
- **Secrets audit**: Detect env vars that exist in one environment but are missing in another
- **CI/CD gating**: Block PRs that introduce config drift across environments
- **Incident prevention**: Catch a changed database endpoint before it causes a production outage

## Installation

```bash
pip install git+https://github.com/Coding-Dev-Tools/configdrift.git
```

Editable install for development:
```bash
pip install -e ".[dev]"
```

Then run: `configdrift --help`

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

ConfigDrift is one of 11 tools in the Revenue Holdings suite. One license covers all CLI tools.

| Plan | Price | Best For |
|------|-------|----------|
| **Free** | $0 | Individual devs, OSS — CLI only, 1 env pair |
| **ConfigDrift Individual** | **$15/mo** ($12 billed annually) | Professional devs — unlimited environments, custom rules |
| **Suite (all 11 tools)** | **$49/mo** ($39 billed annually) | Full Revenue Holdings toolkit — 40% savings |
| **Team** | **$79/mo** ($63 billed annually) | Up to 5 devs — drift history, Slack alerts, priority support |
| **Enterprise** | Custom | SSO, RBAC, compliance reports, dedicated support |

🔹 **No lock-in**: CLI works fully offline on the free tier — no telemetry, no phone-home.
🔹 **Annual billing**: Save 20%.

### Per-Tier Features

| Feature | Free | ConfigDrift | Suite | Team | Enterprise |
|---------|:----:|:-----------:|:-----:|:----:|:----------:|
| CLI: check, scan | ✓ | ✓ | ✓ | ✓ | ✓ |
| Unlimited environments | — | ✓ | ✓ | ✓ | ✓ |
| Custom rules / policies | — | ✓ | ✓ | ✓ | ✓ |
| Drift history / audit trail | — | — | — | ✓ | ✓ |
| Slack / webhook alerts | — | — | — | ✓ | ✓ |
| Compliance reports | — | — | — | — | ✓ |
| RBAC | — | — | — | — | ✓ |
| SSO / SAML / OIDC | — | — | — | — | ✓ |
| Priority support | Community | 24h | 24h | 8h | Dedicated |

## License

MIT
