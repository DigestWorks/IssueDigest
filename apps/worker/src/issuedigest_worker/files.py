"""Descriptor-anchored bounded private files and exclusive atomic artifact publication."""

import os
import secrets
import stat
from pathlib import Path

from .models import PreparationError

_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def _parent(path: str) -> tuple[int, str]:
    target = Path(path)
    if (
        not target.is_absolute()
        or len(target.parts) < 2
        or any(part in {".", ".."} for part in path.split("/"))
    ):
        raise ValueError("Absolute path required")
    directory = os.open("/", _DIR_FLAGS)
    try:
        for part in target.parts[1:-1]:
            child = os.open(part, _DIR_FLAGS, dir_fd=directory)
            os.close(directory)
            directory = child
        return directory, target.parts[-1]
    except BaseException:
        os.close(directory)
        raise


def _fingerprint(info: os.stat_result) -> tuple[int, ...]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_uid,
        info.st_mode,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
        info.st_nlink,
    )


def read_private(path: str, maximum: int) -> bytes:
    """Never follow symlinks or block on FIFOs; reject replacement and in-place mutation."""
    try:
        directory, name = _parent(path)
        try:
            fd = os.open(
                name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=directory
            )
            try:
                before = os.fstat(fd)
                if (
                    not stat.S_ISREG(before.st_mode)
                    or before.st_uid != os.geteuid()
                    or stat.S_IMODE(before.st_mode) not in {0o400, 0o600}
                    or before.st_size > maximum
                    or before.st_size <= 0
                ):
                    raise ValueError("Private bounded regular file required")
                chunks: list[bytes] = []
                count = 0
                while True:
                    chunk = os.read(fd, min(65536, maximum + 1 - count))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    count += len(chunk)
                    if count > maximum:
                        raise ValueError("File size exceeded")
                after = os.fstat(fd)
                current = os.stat(name, dir_fd=directory, follow_symlinks=False)
                if (
                    _fingerprint(before) != _fingerprint(after)
                    or _fingerprint(before) != _fingerprint(current)
                    or count != before.st_size
                ):
                    raise ValueError("File changed")
                return b"".join(chunks)
            finally:
                os.close(fd)
        finally:
            os.close(directory)
    except Exception:
        raise PreparationError("Unable to read private preparation input") from None


def write_private(path: str, raw: bytes) -> None:
    """Publish a complete 600 artifact by exclusive link in an owned 700 parent."""
    directory = -1
    temporary: str | None = None
    published = False
    name = ""
    try:
        directory, name = _parent(path)
        before = os.fstat(directory)
        if before.st_uid != os.geteuid() or stat.S_IMODE(before.st_mode) != 0o700:
            raise ValueError("Private parent required")
        candidate = ".hwpx-" + secrets.token_hex(16)
        fd = os.open(
            candidate,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=directory,
        )
        temporary = candidate
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb", closefd=False) as output:
                output.write(raw)
                output.flush()
                os.fsync(fd)
        finally:
            os.close(fd)
        after = os.fstat(directory)
        if (after.st_uid, after.st_mode) != (before.st_uid, before.st_mode):
            raise ValueError("Parent changed")
        os.link(temporary, name, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
        published = True
        os.unlink(temporary, dir_fd=directory)
        temporary = None
        os.fsync(directory)
        published = False
    except Exception:
        raise PreparationError("Unable to write private preparation output") from None
    finally:
        if directory != -1:
            try:
                if published:
                    os.unlink(name, dir_fd=directory)
                if temporary is not None:
                    os.unlink(temporary, dir_fd=directory)
            finally:
                os.close(directory)
