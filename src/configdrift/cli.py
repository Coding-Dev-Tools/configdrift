"""ConfigDrift CLI entry point."""

from __future__ import annotations

import os
import typer
from enum import Enum
from pathlib import Path
from rich.console import Console
from rich.table import Table
from typing import Any

try:
    from revenueholdings_license import require_license
except ImportError:
    import warnings

    warnings.warn("revenueholdings-license not installed; license checks skipped", stacklevel=2)

    def require_license(product: str) -> None:  # type: ignore[misc]
        pass


from configdrift import __version__
from configdrift._atomic import atomic_dump_toml, atomic_dump_yaml, atomic_write_text

def _json_null_handler(obj: Any) -> Any:
    """JSON serializer for objects not serializable by default json code.

    Handles None values and date/datetime objects that were preserved through
    the flatten cycle so they serialize correctly instead of raising TypeError.
    Date/datetime objects are serialized as ISO strings so cross-format
    fixes converge (YAML date → JSON string won't keep reporting drift).
    """
    if obj is None:
        return None
    # Handle date/datetime objects from cross-format fixes (YAML/TOML → JSON)
    import datetime
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if isinstance(obj, datetime.date):
        return obj.isoformat()
    if isinstance(obj, datetime.time):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
from configdrift.diff import (
    Severity,
    diff_environments,
)
from configdrift.loader import get_literal_dotted_keys, load_file

app = typer.Typer(
    name="configdrift",
    help="Detect and fix configuration file drift across environments.",
    invoke_without_command=True,
)
console = Console()

_require_license_strict: bool = False


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"configdrift v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(  # noqa: B008
        False,
        "--version",
        "-V",
        help="Show the version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
    require_license_flag: bool = typer.Option(  # noqa: B008
        False,
        "--require-license",
        help=(
            "Exit with an error if revenueholdings-license is not installed "
            "or if the license check fails. "
            "Also enabled via REVENUEHOLDINGS_REQUIRE_LICENSE=1."
        ),
    ),
) -> None:
    """ConfigDrift CLI — detect and fix configuration drift."""
    global _require_license_strict
    _require_license_strict = require_license_flag or bool(os.environ.get("REVENUEHOLDINGS_REQUIRE_LICENSE"))
    if _require_license_strict:
        try:
            from revenueholdings_license import require_license as _rl

            _rl("configdrift")
        except ImportError:
            console.print(
                "[bold red]Error:[/bold red] revenueholdings-license is not installed. "
                "Install it with: pip install revenueholdings-license",
                err=True,
            )
            raise typer.Exit(code=1) from None
        except Exception:
            raise


class OutputFormat(str, Enum):
    TABLE = "table"
    JSON = "json"
    SILENT = "silent"


# Module-level defaults to avoid B008 (function calls in argument defaults)
_DEFAULT_BASELINE = "dev"
_DEFAULT_TARGET = "target"
_DEFAULT_OUTPUT: OutputFormat = OutputFormat.TABLE
_DEFAULT_STRICT = False
_FILES_ARG = typer.Argument(..., help="Config files to compare (2+ files; first file is baseline).")
_BASELINE_OPT = typer.Option(
    _DEFAULT_BASELINE,
    "--baseline",
    "-b",
    help="Baseline environment label (default: 'dev').",
)
_TARGET_OPT = typer.Option(
    _DEFAULT_TARGET,
    "--target",
    "-t",
    help="Target environment label (default: 'target').",
)
_OUTPUT_OPT = typer.Option(
    _DEFAULT_OUTPUT,
    "--output",
    "-o",
    help="Output format: table, json, or silent (exit code only).",
)
_STRICT_OPT = typer.Option(_DEFAULT_STRICT, "--strict", help="Exit 1 on ANY drift, not just breaking changes.")


@app.command()
def check(
    files: list[str] = _FILES_ARG,
    baseline: str = _BASELINE_OPT,
    target: str = _TARGET_OPT,
    output: OutputFormat = _OUTPUT_OPT,
    strict: bool = _STRICT_OPT,
):
    """Compare 2+ config files and report drift. Exits 1 if breaking drift found (useful for CI gating)."""
    if len(files) < 2:
        console.print("[red]ERROR: Provide at least 2 config files to compare.[/red]")
        raise typer.Exit(code=1)

    env_configs: dict[str, dict[str, Any]] = {}
    env_labels = [baseline, target] if len(files) == 2 else [f"file_{i + 1}" for i in range(len(files))]

    for label, filepath in zip(env_labels, files, strict=False):
        try:
            env_configs[label] = load_file(filepath)
        except Exception as e:
            console.print(f"[red]Error loading {filepath}: {e}[/red]")
            raise typer.Exit(code=1) from e

    baseline_env = env_labels[0]
    results = diff_environments(env_configs, baseline_env=baseline_env)

    if output == OutputFormat.JSON:
        _output_json(results)
    elif output == OutputFormat.SILENT:
        if strict:
            has_drift = any(r.count > 0 for r in results.values())
        else:
            has_drift = any(r.has_breaking for r in results.values())
        raise typer.Exit(code=1 if has_drift else 0)
    else:
        _output_table(results, baseline_env)

    # Exit codes for CI gating
    has_drift = any(r.count > 0 for r in results.values()) if strict else any(r.has_breaking for r in results.values())
    if has_drift:
        raise typer.Exit(code=1)


def _output_table(results: dict[str, Any], baseline_env: str) -> None:
    for env_name, diff_result in results.items():
        if not diff_result.changes:
            continue

        table = Table(title=f"Config Drift: {baseline_env} → {env_name}")
        table.add_column("Key", style="cyan")
        table.add_column("Change", style="bold")
        table.add_column("Old Value", style="yellow")
        table.add_column("New Value", style="green")
        table.add_column("Severity", style="magenta")

        for change in diff_result.changes:
            symbol = {"added": "+", "removed": "-", "changed": "~"}[change.change_type.value]
            old_str = str(change.old_value) if change.old_value is not None else ""
            new_str = str(change.new_value) if change.new_value is not None else ""
            sev_style = (
                "red"
                if change.severity == Severity.BREAKING
                else "yellow"
                if change.severity == Severity.WARNING
                else "white"
            )
            table.add_row(
                change.key,
                f"{symbol} {change.change_type.value}",
                old_str,
                new_str,
                f"[{sev_style}]{change.severity.value}[/{sev_style}]",
            )

        console.print(table)
        console.print(f"Total changes: {diff_result.count}")
        if diff_result.has_breaking:
            console.print("[red]⚠ BREAKING CHANGES DETECTED[/red]")
        console.print()


def _output_json(results: dict[str, Any]) -> None:
    import json

    output = {}
    for env_name, diff_result in results.items():
        output[env_name] = {
            "changes": [
                {
                    "key": c.key,
                    "type": c.change_type.value,
                    "old_value": c.old_value,
                    "new_value": c.new_value,
                    "severity": c.severity.value,
                }
                for c in diff_result.changes
            ],
            "has_breaking": diff_result.has_breaking,
            "count": diff_result.count,
        }
    console.print(json.dumps(output, indent=2, default=str))


@app.command()
def scan(
    dirs: list[str] | None = typer.Argument(  # noqa: B008
        None,
        help="Directories containing config files. Each dir is treated as an environment.",
    ),
    baseline: str = typer.Option(  # noqa: B008
        "dev", "--baseline", "-b", help="Baseline directory name for comparison."
    ),
    config: str | None = typer.Option(  # noqa: B008
        None, "--config", "-c", help="Path to .configdrift.yaml config file."
    ),
    output: OutputFormat = typer.Option(  # noqa: B008
        OutputFormat.TABLE, "--output", "-o", help="Output format."
    ),
    strict: bool = typer.Option(  # noqa: B008
        False, "--strict", help="Exit 1 on ANY drift, not just breaking changes."
    ),
):
    """Scan directories of config files and compare environments."""
    if config:
        # Load config file for directory -> env mapping (raw, not flattened)
        import yaml as _yaml

        with open(config, encoding="utf-8") as _f:
            cfg_data = _yaml.safe_load(_f) or {}
        dir_mapping = cfg_data.get("environments", {})
    elif dirs:
        # Use directory basenames as env names
        dir_mapping = {}
        for d in dirs:
            env_name = Path(d).name
            dir_mapping[env_name] = d
    else:
        console.print("[red]ERROR: Provide either --config or directories as arguments.[/red]")
        raise typer.Exit(code=1)

    if baseline not in dir_mapping:
        console.print(f"[red]Baseline environment '{baseline}' not found.[/red]")
        raise typer.Exit(code=1)

    env_configs: dict[str, dict[str, Any]] = {}
    for env_name, dir_path in dir_mapping.items():
        env_configs[env_name] = {}
        p = Path(dir_path)
        if not p.is_dir():
            console.print(f"[yellow]Warning: '{dir_path}' is not a directory, skipping.[/yellow]")
            continue
        # Load all supported config files in the directory and merge
        for ext in ("*.yaml", "*.yml", "*.json", "*.toml", "*.env"):
            for f in p.glob(ext):
                try:
                    data = load_file(str(f))
                    env_configs[env_name].update(data)
                except Exception as e:
                    console.print(f"[yellow]Warning: could not load {f}: {e}[/yellow]")

    results = diff_environments(env_configs, baseline_env=baseline)

    if output == OutputFormat.JSON:
        _output_json(results)
    elif output == OutputFormat.SILENT:
        if strict:
            has_drift = any(r.count > 0 for r in results.values())
        else:
            has_drift = any(r.has_breaking for r in results.values())
        raise typer.Exit(code=1 if has_drift else 0)
    else:
        _output_table(results, baseline)

    has_drift = any(r.count > 0 for r in results.values()) if strict else any(r.has_breaking for r in results.values())
    if has_drift:
        raise typer.Exit(code=1)


@app.command()
def fix(
    files: list[str] = _FILES_ARG,
    baseline: str = _BASELINE_OPT,
    target: str = _TARGET_OPT,
    dry_run: bool = typer.Option(  # noqa: B008
        False, "--dry-run", "-n", help="Show what would change without modifying files."
    ),
) -> None:
    baseline_path = Path(files[0])
    if not baseline_path.exists():
        console.print(f"[red]ERROR: Baseline file not found: {baseline_path}[/red]")
        raise typer.Exit(code=1)
    try:
        baseline_data = load_file(str(baseline_path))
    except Exception as e:
        console.print(f"[red]Error loading baseline config: {e}[/red]")
        raise typer.Exit(code=1) from e
    if len(files) < 2:
        console.print("[red]ERROR: fix requires at least one baseline and one target file.[/red]")
        raise typer.Exit(code=1)


    # Track targets that could not be fixed so the command returns a
    # non-zero exit code when any target is missing, fails to load, or
    # uses an unsupported format.
    failed_targets: list[str] = []

    # Process every supplied target file (not just files[1])
    for target_file in files[1:]:
        target_path = Path(target_file)
        if not target_path.exists():
            console.print(f"[red]ERROR: Target file not found: {target_path}[/red]")
            failed_targets.append(str(target_path))
            continue

        try:
            target_data = load_file(str(target_path))
        except Exception as e:
            console.print(f"[red]Error loading target config {target_path}: {e}[/red]")
            failed_targets.append(str(target_path))
            continue

        changes = 0
        # Detect dotenv target early so we can normalize boolean comparisons.
        _target_ext = target_path.suffix.lower()
        _target_is_dotenv = (
            _target_ext == ".env"
            or target_path.name == ".env"
            or target_path.name.startswith(".env.")
        )
        for key, value in baseline_data.items():
            # Distinguish missing keys from null values: a baseline null
            # must restore a missing target key, not be silently skipped.
            if key not in target_data:
                changes += 1
                if not dry_run:
                    target_data[key] = value
            else:
                # When fixing a dotenv target, normalize all scalar baseline
                # values to their string form so the comparison converges
                # (8080 vs "8080" and True vs "true" would otherwise keep drifting).
                cmp_value = value
                if _target_is_dotenv:
                    if isinstance(value, (dict, list, tuple)):
                        # Collections cannot be represented in dotenv.
                        # Count as drift so we don't silently report
                        # "no drift" when the baseline has a collection
                        # that the target cannot hold.
                        changes += 1
                        continue
                    if value is None:
                        cmp_value = ""
                    elif isinstance(value, bool):
                        cmp_value = "true" if value else "false"
                    elif not isinstance(value, str):
                        cmp_value = str(value)
                if target_data[key] != cmp_value:
                    changes += 1
                    if not dry_run:
                        target_data[key] = cmp_value

        # Skip write-back when no changes detected
        if changes == 0:
            if dry_run:
                console.print(f"[yellow]Dry run: no changes needed in {target_path}[/yellow]")
            else:
                console.print(f"[green]No drift detected in {target_path}[/green]")
            continue

        if dry_run:
            # Validate that the target format supports write-back even in
            # dry-run mode so --dry-run accurately predicts whether the
            # real run would succeed.
            ext = target_path.suffix.lower()
            # .env files need name-based detection: literal .env, or
            # environment-suffixed variants like .env.prod, .env.dev
            is_dotenv = (
                ext == ".env"
                or target_path.name == ".env"
                or target_path.name.startswith(".env.")
            )
            supported_exts = {".json", ".yaml", ".yml", ".toml"}
            if ext == ".toml":
                try:
                    import tomli_w  # noqa: F401
                except ImportError:
                    console.print("[red]Error: tomli-w is required to write TOML files. Install with: pip install tomli-w[/red]")
                    failed_targets.append(str(target_path))
                    continue
                # Validate null compatibility during dry run so --dry-run
                # accurately predicts the real-run rejection.
                has_null = any(v is None for v in target_data.values())
                if has_null:
                    null_keys = [k for k, v in target_data.items() if v is None]
                    console.print(
                        f"[red]Error: TOML does not support null values. "
                        f"Keys with null: {', '.join(null_keys[:5])}[/red]"
                    )
                    failed_targets.append(str(target_path))
                    continue
            # Validate dotenv keys and multiline values during dry run so
            # --dry-run accurately predicts real-run rejections.
            if is_dotenv:
                import re as _dr_re
                _DR_KEY = _dr_re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
                prospective_keys = set(baseline_data.keys()) | set(target_data.keys())
                bad_keys = [k for k in prospective_keys if not isinstance(k, str) or not _DR_KEY.match(k)]
                if bad_keys:
                    console.print(
                        f"[red]Error: dotenv keys must match [A-Za-z_][A-Za-z0-9_]*. "
                        f"Invalid keys: {', '.join(str(k) for k in bad_keys[:5])}[/red]"
                    )
                    failed_targets.append(str(target_path))
                    continue
                # Check for multiline values that would corrupt the dotenv file
                bad_multiline = [
                    k for k, v in baseline_data.items()
                    if isinstance(v, str) and '\n' in v
                ]
                if bad_multiline:
                    console.print(
                        f"[red]Error: dotenv values must not contain newlines. "
                        f"Keys with newlines: {', '.join(bad_multiline[:5])}[/red]"
                    )
                    failed_targets.append(str(target_path))
                    continue
            elif not is_dotenv and ext not in supported_exts:
                console.print(f"[red]Error: unsupported format '{ext}' for write-back of {target_path}.[/red]")
                failed_targets.append(str(target_path))
                continue
            console.print(f"[yellow]Dry run: {changes} key(s) would be updated in {target_path}[/yellow]")
        else:
            ext = target_path.suffix.lower()
            is_dotenv = (
                target_path.name == ".env"
                or target_path.name.startswith(".env.")
            )
            if ext == ".json":
                import json as _json

                # Reject non-string keys before JSON write-back.
                # json.dumps coerces int keys to strings (1 → "1"), so
                # reloading the JSON produces a string key that no longer
                # matches the baseline's integer key, causing perpetual
                # drift. It can also create duplicate names when the
                # target already contains the string form.
                non_str_keys = [k for k in target_data if not isinstance(k, str)]
                if non_str_keys:
                    console.print(
                        f"[red]Error: JSON keys must be strings. "
                        f"Non-string keys from baseline: {', '.join(repr(k) for k in non_str_keys[:5])}[/red]"
                    )
                    failed_targets.append(str(target_path))
                    continue

                # Preserve nested JSON structure: rebuild from flat keys.
                # Literal dotted keys (keys that already contain '.') in the
                # source document are kept as single mapping keys rather
                # than being re-split into nested levels.
                # Merge literal dotted keys from both baseline and target
                all_literal_dotted = get_literal_dotted_keys(str(baseline_path)) | get_literal_dotted_keys(str(target_path))
                nested: dict[str, Any] = {}
                for k, v in target_data.items():
                    if "." not in k or k in all_literal_dotted:
                        nested[k] = v
                    else:
                        parts = k.split(".")
                        d = nested
                        for part in parts[:-1]:
                            if not isinstance(d.get(part), dict):
                                d[part] = {}
                            d = d[part]
                        d[parts[-1]] = v
                atomic_write_text(target_path, _json.dumps(nested, indent=2, default=_json_null_handler) + "\n")
            elif ext in (".yaml", ".yml"):
                # Reconstruct nested structure from flat keys for YAML output
                all_literal_dotted = get_literal_dotted_keys(str(baseline_path)) | get_literal_dotted_keys(str(target_path))
                nested: dict[str, Any] = {}
                for k, v in target_data.items():
                    if "." not in k or k in all_literal_dotted:
                        nested[k] = v
                    else:
                        parts = k.split(".")
                        d = nested
                        for part in parts[:-1]:
                            if not isinstance(d.get(part), dict):
                                d[part] = {}
                            d = d[part]
                        d[parts[-1]] = v
                atomic_dump_yaml(target_path, nested, default_flow_style=False, sort_keys=False)
            elif ext == ".toml":
                try:
                    import tomli_w  # noqa: F401

                    # Reject None values before building the TOML dict —
                    # TOML has no null representation, so tomli_w would
                    # raise TypeError on serialization. Check recursively
                    # through lists and nested dicts for embedded nulls.
                    def _has_null(val: Any) -> bool:
                        if val is None:
                            return True
                        if isinstance(val, dict):
                            return any(_has_null(v) for v in val.values())
                        if isinstance(val, (list, tuple)):
                            return any(_has_null(v) for v in val)
                        return False
                    null_keys = [k for k, v in target_data.items() if _has_null(v)]
                    if null_keys:
                        console.print(
                            f"[red]Error: TOML does not support null values. "
                            f"Keys with null: {', '.join(null_keys[:5])}[/red]"
                        )
                        failed_targets.append(str(target_path))
                        continue
                    all_literal_dotted = get_literal_dotted_keys(str(baseline_path)) | get_literal_dotted_keys(str(target_path))
                    nested_toml: dict[str, Any] = {}
                    for k, v in target_data.items():
                        if "." not in k or k in all_literal_dotted:
                            nested_toml[k] = v
                        else:
                            parts = k.split(".")
                            d = nested_toml
                            for part in parts[:-1]:
                                if not isinstance(d.get(part), dict):
                                    d[part] = {}
                                d = d[part]
                            d[parts[-1]] = v
                    atomic_dump_toml(target_path, nested_toml)
                except ImportError:
                    console.print("[red]Error: tomli-w is required to write TOML files. Install with: pip install tomli-w[/red]")
                    failed_targets.append(str(target_path))
                    continue
            elif is_dotenv:
                # Handle .env targets: write flat KEY=VALUE format.
                # Reject keys containing dots — _load_dotenv only accepts
                # [A-Za-z_][A-Za-z0-9_]* identifiers, so dotted keys from
                # flattened JSON/YAML baselines would be silently dropped
                # on reload, causing perpetual drift.
                import re as _dotenv_re
                _DOTENV_KEY_RE = _dotenv_re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
                bad_keys = [k for k in target_data if not isinstance(k, str) or not _DOTENV_KEY_RE.match(k)]
                if bad_keys:
                    console.print(
                        f"[red]Error: dotenv keys must match [A-Za-z_][A-Za-z0-9_]*. "
                        f"Invalid keys: {', '.join(str(k) for k in bad_keys[:5])}[/red]"
                    )
                    failed_targets.append(str(target_path))
                    continue
                # Reject multiline values — newlines (\n) and carriage
                # returns (\r) would corrupt the dotenv file by splitting
                # a single KEY=VALUE across multiple physical lines.
                # Readers using universal-newline handling treat \r as a
                # line boundary, truncating the setting.
                multiline_keys = [
                    k for k, v in target_data.items()
                    if isinstance(v, str) and ('\n' in v or '\r' in v)
                ]
                if multiline_keys:
                    console.print(
                        f"[red]Error: dotenv values must not contain newlines or "
                        f"carriage returns. Keys affected: {', '.join(multiline_keys[:5])}[/red]"
                    )
                    failed_targets.append(str(target_path))
                    continue
                lines = []
                for k, v in target_data.items():
                    # Reject non-scalar values that dotenv cannot represent
                    if isinstance(v, (dict, list, tuple)):
                        console.print(
                            f"[red]Error: dotenv cannot represent collection values. "
                            f"Key '{k}' has type {type(v).__name__}[/red]"
                        )
                        failed_targets.append(str(target_path))
                        break
                    # Convert Python booleans to lowercase for dotenv compatibility
                    if isinstance(v, bool):
                        str_v = "true" if v else "false"
                    else:
                        str_v = str(v) if v is not None else ""
                    # Quote values containing whitespace (space, tab),
                    # comments (#), or double quotes. Tabs at the start
                    # or end are stripped by _load_dotenv's .strip(),
                    # so quoting preserves them through round-trip.
                    if " " in str_v or "\t" in str_v or "#" in str_v or '"' in str_v:
                        escaped = str_v.replace('"', '\\"')
                        lines.append(f'{k}="{escaped}"')
                    else:
                        lines.append(f"{k}={str_v}")
                else:
                    atomic_write_text(target_path, "\n".join(lines) + "\n")
                    continue
            else:
                console.print(f"[red]Error: unsupported format '{ext}' for write-back of {target_path}.[/red]")
                failed_targets.append(str(target_path))
                continue
            console.print(f"[green]Fixed {changes} key(s) in {target_path}[/green]")

    if failed_targets:
        console.print(
            f"[red]ERROR: {len(failed_targets)} target(s) could not be fixed: "
            f"{', '.join(failed_targets)}[/red]"
        )
        raise typer.Exit(code=1)


@app.command()
def init(
    path: str = typer.Argument(".", help="Directory to create .configdrift.yaml in."),  # noqa: B008
):
    """Generate a .configdrift.yaml configuration file."""
    template = """# ConfigDrift configuration
# Define your environments and the config files to compare.

environments:
  dev: ./config/dev
  staging: ./config/staging
  prod: ./config/prod
"""
    target = Path(path) / ".configdrift.yaml"
    if target.exists():
        console.print(f"[yellow]File already exists: {target}[/yellow]")
        raise typer.Exit(code=1)
    target.write_text(template)
    console.print(f"[green]Created {target}[/green]")
