# Changelog

All notable changes to ConfigDrift will be documented in this file.

## [0.1.0] — 2026-05-14

### Added

- Initial release
- Config file comparison (YAML, JSON, TOML, .env)
- Environment directory scanning
- Severity levels: info, warning, breaking
- Breaking drift detection on critical keys (database*, auth*, api_key*, secret*, password*, token*, endpoint*)
- CI gating with silent output mode
- Human-readable table output
- Machine-readable JSON output
- `.configdrift.yaml` init command
- Python 3.10+ support
