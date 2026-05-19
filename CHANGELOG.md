# Changelog

All notable changes to ConfigDrift CLI will be documented in this file.

## [Unreleased]

### Added

- CLI test suite with comprehensive coverage for Change.\_\_str\_\_() and loader fallback paths
- npm wrapper (`package.json` + `cli.js`) for npm publishing
- GitHub Actions: npm publish workflow (release or manual dispatch)
- GitHub Actions: GitHub Pages deployment workflow
- `CONTRIBUTING.md` with development setup and PR guidelines
- `SECURITY.md` with security policy
- Homebrew and Scoop install methods
- Directory listing badges: Open Source Alternative, LibHunt, Awesome Python
- npm keywords optimized for discoverability (15 terms)
- `revenueholdings-license` gating on all CLI commands
- Beta badge and star CTA in README header

### Changed

- CI test matrix expanded to include Python 3.13
- CI security hardened: `persist-credentials: false`, restricted permissions
- Documentation branding updated from DevForge to Revenue Holdings
- README expanded with CI/CD examples and alternatives comparison
- README tool count updated (8 → 11)
- npm install placement and formatting fixed in README
- `project.urls` metadata added to `pyproject.toml`

### Fixed

- CI lint workflow: removed redundant ruff install and deprecated `--target-version` flag
- GitHub Actions version mismatches in CI and publish workflows
- UTF-8 encoding (mojibake) in file output
- Ruff lint issues: `datetime.UTC`, `X | None` syntax, `E501`, `B904`, `F821`
- Missing `ruff` dev dependency in `pyproject.toml`
- Broken PyPI badges replaced with GitHub release badge (not yet on PyPI)
- `revenueholdings-license` import made optional (fixes CI failures on open-source PRs)
- Dependencies bumped via Dependabot (checkout@v6, setup-node@v6, setup-python@v6)
- README install section formatting (broken Homebrew/Scoop code blocks)

## [0.1.0] — 2026-05-14

### Added

- Initial release
- Configuration file comparison across formats (YAML, JSON, TOML, .env)
- `configdrift check` — compare two config files with auto-flattening and diff output
- `configdrift scan` — compare environment directories against a baseline
- `configdrift init` — generate `.configdrift.yaml` scaffolding
- Three output formats: rich `table`, machine-readable `json`, `silent` (exit code only)
- Severity-level drift classification: Info, Warning, Breaking
- Breaking-change heuristics for critical keys
- CI/CD integration with non-zero exit on breaking drift
- Python 3.10+ support
