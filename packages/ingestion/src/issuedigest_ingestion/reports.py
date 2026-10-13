"""Exclusive private manifest creation, with no source-root writes."""

import json
import os
from pathlib import Path

from .audit import AuditResult
from .errors import AuditError
from .filesystem import DIRECTORY_FLAGS, open_directory


def _inside_root(parent_fd: int, root_info: os.stat_result) -> bool:
    cursor = os.dup(parent_fd)
    try:
        while True:
            info = os.fstat(cursor)
            current = (info.st_dev, info.st_ino)
            if current == (root_info.st_dev, root_info.st_ino):
                return True
            ancestor = os.open("..", DIRECTORY_FLAGS, dir_fd=cursor)
            above = os.fstat(ancestor)
            os.close(cursor)
            cursor = ancestor
            if current == (above.st_dev, above.st_ino):
                return False
    finally:
        os.close(cursor)


def save_private_manifest(
    result: AuditResult, data_root: str | Path, destination: str | Path
) -> None:
    """Save a new mode-600 file; remove our partial file if publication fails."""
    parent_fd: int | None = None
    root_fd: int | None = None
    output_fd: int | None = None
    created_info: os.stat_result | None = None
    name = ""
    try:
        root = Path(os.path.abspath(data_root))
        target = Path(os.path.abspath(destination))
        if target.is_relative_to(root):
            raise AuditError("manifest_failed")
        root_fd = open_directory(root)
        parent_fd = open_directory(target.parent)
        if _inside_root(parent_fd, os.fstat(root_fd)):
            raise AuditError("manifest_failed")
        content = (json.dumps(result.manifest, ensure_ascii=True, indent=2) + "\n").encode("utf-8")
        name = target.name
        output_fd = os.open(
            name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=parent_fd,
        )
        created_info = os.fstat(output_fd)
        os.fchmod(output_fd, 0o600)
        offset = 0
        while offset < len(content):
            written = os.write(output_fd, content[offset:])
            if written <= 0:
                raise OSError("write failed")
            offset += written
        os.fsync(output_fd)
        os.close(output_fd)
        output_fd = None
    except (OSError, ValueError, TypeError, AuditError):
        if output_fd is not None:
            os.close(output_fd)
            output_fd = None
        if created_info is not None and parent_fd is not None:
            try:
                current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
                if (current.st_dev, current.st_ino) == (created_info.st_dev, created_info.st_ino):
                    os.unlink(name, dir_fd=parent_fd)
            except OSError:
                pass
        raise AuditError("manifest_failed") from None
    finally:
        if root_fd is not None:
            os.close(root_fd)
        if parent_fd is not None:
            os.close(parent_fd)
