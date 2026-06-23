# configdrift

## Purpose
CLI tool that detects and fixes configuration file drift across environments (dev/staging/prod). Supports YAML, JSON, TOML, and .env formats.

## Build & Test Commands
- Install: `pip install -e .` or `pip install git+https://github.com/Coding-Dev-Tools/configdrift.git`
- Test: `pytest tests/` (or `python -m pytest tests/ -v --tb=short`)
- Lint: `ruff check src/ tests/`
- Build: `pip install build twine && python -m build && twine check dist/*`
- CLI check: `configdrift --help`

## Architecture
Key directories:
- `src/configdrift/` — Main package (CLI, config parsers, drift detection, compliance)
- `tests/` — Test suite
- `.github/workflows/` — CI/CD (auto-code-review.yml, ci.yml, pages.yml, publish.yml)
- `dist/` — Built distributions

## Conventions
- Language: Python 3.10+
- Test framework: pytest (with coverage)
- CI: GitHub Actions (matrix: Python 3.10, 3.11, 3.12, 3.13)
- Linting: ruff (line-length 120, target py310)
- Formatting: ruff
- Package layout: src/ layout with setuptools
- Type checking: py.typed included
- Dependencies: typer, rich, pyyaml, tomli, tomli-w
- CLI entry point: configdrift.cli:app
- Default branch: main