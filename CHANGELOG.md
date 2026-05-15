# Changelog

All notable changes to ConfigDrift CLI will be documented in this file.

## [0.1.0] — 2026-05-14

### Added

- Initial release
- Configuration file comparison across formats (YAML, JSON, TOML, .env)
- `configdrift check` — compare two config files with auto-flattening and diff output
- `configdrift scan` — compare environment directories against a baseline
- `configdrift init` — generate `.configdrift.yaml` scaffolding
- Three output formats: rich `table`, machine-readable `json`, `silent` (exit code only)
- Severity-level drift classification: Info, Warning, Breaking
- Breaking-change heuristics for critical keys (`database*`, `auth*`, `api_key*`, `secret*`, `password*`, `token*`, `endpoint*`)
- CI/CD integration with non-zero exit on breaking drift
- Python 3.10+ support
