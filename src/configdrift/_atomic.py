"""Atomic file-write helpers.

Write to a temporary file in the same directory, fsync, then os.replace()
to atomically swap.  If the process crashes mid-write the original file
is preserved intact.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Atomically write *text* to *path*.

    Creates a temporary file beside *path*, writes + fsyncs, then
    ``os.replace()`` for an atomic rename.  Preserves the original
    file's permissions when it already exists.  When *path* is a
    symlink, resolves it first so the referent is updated rather than
    the link being replaced by a regular file.
    """
    # Resolve symlinks so we update the target file, not replace the link.
    resolved = path.resolve() if path.is_symlink() else path
    parent = resolved.parent
    parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        # Preserve target permissions and ownership during atomic replacement.
        # If ownership restoration fails (e.g. unprivileged caller), abort
        # the replacement rather than installing a caller-owned file that
        # the application cannot read.
        if resolved.exists():
            st = resolved.stat()
            os.chmod(tmp, st.st_mode)
            try:
                if hasattr(os, "chown"):
                    os.chown(tmp, st.st_uid, st.st_gid)
                else:
                    # os.chown is Unix-only; on Windows ownership is managed
                    # by the filesystem ACLs and mkstemp already creates
                    # the temp file with the caller's identity.
                    pass
            except OSError as chown_err:
                with contextlib.suppress(OSError):
                    os.unlink(tmp)
                raise OSError(
                    f"Cannot preserve ownership of {resolved} "
                    f"(uid={st.st_uid}, gid={st.st_gid}): {chown_err}"
                ) from chown_err
        os.replace(tmp, resolved)
    except BaseException:
        # Clean up temp file on any failure
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Atomically write *data* to *path*.

    Preserves the original file's permissions when it already exists.
    When *path* is a symlink, resolves it first so the referent is
    updated rather than the link being replaced by a regular file.
    """
    resolved = path.resolve() if path.is_symlink() else path
    parent = resolved.parent
    parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        # Preserve target permissions and ownership during atomic replacement.
        # If ownership restoration fails, abort rather than installing a
        # caller-owned file the application cannot read.
        if resolved.exists():
            st = resolved.stat()
            os.chmod(tmp, st.st_mode)
            try:
                if hasattr(os, "chown"):
                    os.chown(tmp, st.st_uid, st.st_gid)
                else:
                    # os.chown is Unix-only; on Windows ownership is managed
                    # by the filesystem ACLs and mkstemp already creates
                    # the temp file with the caller's identity.
                    pass
            except OSError as chown_err:
                with contextlib.suppress(OSError):
                    os.unlink(tmp)
                raise OSError(
                    f"Cannot preserve ownership of {resolved} "
                    f"(uid={st.st_uid}, gid={st.st_gid}): {chown_err}"
                ) from chown_err
        os.replace(tmp, resolved)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def atomic_dump_yaml(path: Path, data: object, **dump_kwargs: object) -> None:
    """Serialize *data* via ``yaml.dump`` into a temp file, then atomically rename."""
    import io
    import yaml

    buf = io.StringIO()
    yaml.dump(data, buf, **dump_kwargs)  # type: ignore[arg-type]
    atomic_write_text(path, buf.getvalue())


def atomic_dump_toml(path: Path, data: object) -> None:
    """Serialize *data* via ``tomli_w.dump`` into a temp file, then atomically rename."""
    import io
    import tomli_w

    buf = io.BytesIO()
    tomli_w.dump(data, buf)  # type: ignore[arg-type]
    atomic_write_bytes(path, buf.getvalue())
