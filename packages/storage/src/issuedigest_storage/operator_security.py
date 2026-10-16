"""Shared private operator files and engine-owned silent pool lifecycle handling."""

import logging
import os
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine


class PrivatePoolLogger(logging.Logger):
    """Engine-owned sink: discard private records and remember lifecycle failures."""

    def __init__(self) -> None:
        # A direct Logger instance has no global registry entry or handlers.
        super().__init__("workspace-provision-pool")
        self.failed = False

    def isEnabledFor(self, level: int) -> bool:
        # Detect failures even when a caller has disabled ordinary logging.
        return True

    def handle(self, record: logging.LogRecord) -> None:
        args = record.args if isinstance(record.args, tuple) else ()
        if (
            record.levelno >= logging.WARNING
            or record.exc_info
            or any(isinstance(arg, BaseException) for arg in args)
        ):
            self.failed = True
        # Never format, propagate or retain input-bearing record/exception details.


def read_private_file(path: str, max_bytes: int) -> bytes:
    try:
        target = Path(path)
        if not target.is_absolute() or len(target.parts) < 2:
            raise ValueError("Absolute private file required")
        # Anchor each directory descriptor so neither parent nor file symlinks are followed.
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        directory = os.open("/", directory_flags)
        try:
            for part in target.parts[1:-1]:
                child = os.open(part, directory_flags, dir_fd=directory)
                os.close(directory)
                directory = child
            # Nonblocking prevents a raced FIFO from hanging before the fstat guard.
            fd = os.open(
                target.parts[-1],
                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                dir_fd=directory,
            )
        finally:
            os.close(directory)
        with os.fdopen(fd, "rb") as file:
            info = os.fstat(file.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) not in {0o400, 0o600}
                or info.st_size > max_bytes
            ):
                raise ValueError("Private regular file required")
            raw = file.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise ValueError("Private file exceeds bounds")
        return raw
    except Exception:
        raise ValueError("Unable to read private operator file") from None


@contextmanager
def private_engine_lifecycle(engine: Engine) -> Iterator[None]:
    pool = engine.pool
    original_logger = pool.logger
    lifecycle = PrivatePoolLogger()
    pool.logger = lifecycle
    try:
        try:
            yield
        finally:
            engine.dispose()
        if lifecycle.failed:
            raise ValueError("Unable to complete database operation")
    finally:
        pool.logger = original_logger


def unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def reject_json_constant(value: str) -> object:
    raise ValueError("Invalid JSON number")
