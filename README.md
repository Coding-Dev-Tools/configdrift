# ConfigDrift

[![GitHub stars](https://img.shields.io/github/stars/Coding-Dev-Tools/configdrift?style=social)](https://github.com/Coding-Dev-Tools/configdrift/stargazers)
[![Awesome DevOps](https://img.shields.io/badge/Awesome_DevOps-Submitted-grey?logo=github)](https://github.com/wmariuss/awesome-devops)<!-- PR #433 -->

Keep configurations consistent across all environments, automatically. ConfigDrift compares configs, flags drift, and reports compliance violations before they cause incidents.

[![GitHub release](https://img.shields.io/github/v/release/Coding-Dev-Tools/configdrift?label=latest)](https://github.com/Coding-Dev-Tools/configdrift/releases)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/Coding-Dev-Tools/configdrift/blob/main/LICENSE)
[![Open Source Alternative](https://img.shields.io/badge/Open_Source_Alternative-%E2%87%92-blue?logo=opensourceinitiative)](https://www.opensourcealternative.to/project/configdrift)
[![LibHunt](https://img.shields.io/badge/LibHunt-%E2%87%92-blue?logo=codeigniter)](https://www.libhunt.com/r/Coding-Dev-Tools/configdrift)
[![Awesome Python](https://img.shields.io/badge/Awesome_Python-%E2%87%92-blue?logo=python)](https://github.com/uhub/awesome-python)

**Why ConfigDrift?** Environments should behave consistently. When dev, staging, and prod configs diverge, deployments break silently. ConfigDrift compares configurations across environments, highlights drifting keys, deprecated values, and missing settings — before they cause incidents. Supports YAML, JSON, TOML, and .env — and it runs in CI so drift never ships.

## Installation

```bash
pip install configdrift
```

Or install directly from GitHub:

```bash
pip install git+https://github.com/Coding-Dev-Tools/configdrift.git
```

Or install via Homebrew (macOS/Linux):
```bash
brew tap Coding-Dev-Tools/tap
brew install configdrift
```

Or install via Scoop (Windows):
```bash
scoop bucket add Coding-Dev-Tools https://github.com/Coding-Dev-Tools/scoop-bucket
scoop install configdrift
```

**npm (Node.js wrapper):**
```bash
npm install -g configdrift
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

ConfigDrift is one of 11 tools in the DevForge suite. One license covers all CLI tools.

| Plan | Price | Best For |
|------|-------|----------|
| **Free** | $0 | Individual devs, OSS — CLI only, 1 env pair |
| **ConfigDrift Individual** | **$15/mo** ($12 billed annually) | Professional devs — unlimited environments, custom rules |
| **Suite (all 11 tools)** | **$49/mo** ($39 billed annually) | Full DevForge toolkit — 40% savings |
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

---

<p align="center">
  <sub>Part of <a href="https://coding-dev-tools.github.io/devforge.dev/">DevForge</a> — CLI tools built by autonomous AI.</sub>
</p>

## License

MIT
