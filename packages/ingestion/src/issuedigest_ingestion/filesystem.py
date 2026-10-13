"""Descriptor-based access prevents following input symbolic links."""

import errno
import hashlib
import os
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from .errors import AuditError

DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def open_directory(path: Path) -> int:
    """Open every absolute path component without following links."""
    absolute = Path(os.path.abspath(path))
    fd = os.open("/", DIRECTORY_FLAGS)
    try:
        for part in absolute.parts[1:]:
            child = os.open(part, DIRECTORY_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


@contextmanager
def input_directories(root: Path) -> Iterator[dict[str, int]]:
    descriptors: dict[str, int] = {}
    try:
        try:
            root_fd = open_directory(root)
            descriptors["root"] = root_fd
            for tree in ("parsed", "pdfs"):
                descriptors[tree] = os.open(tree, DIRECTORY_FLAGS, dir_fd=root_fd)
        except (OSError, ValueError):
            raise AuditError("invalid_data_root") from None
        yield descriptors
    finally:
        for fd in descriptors.values():
            os.close(fd)


def identity(info: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


@dataclass(frozen=True)
class FileRef:
    parts: tuple[str, ...]
    info: os.stat_result
    ancestors: tuple[tuple[int, int], ...]

    @property
    def path(self) -> str:
        return "/".join(self.parts)


@dataclass
class Budget:
    maximum: int
    used: int = 0

    def consume(self, count: int) -> None:
        self.used += count
        if self.used > self.maximum:
            raise AuditError("total_bytes_exceeded")


def scan(
    trees: dict[str, int], maximum: int
) -> tuple[dict[str, list[FileRef]], list[dict[str, str]]]:
    found: dict[str, list[FileRef]] = {"parsed": [], "pdfs": []}
    skipped: list[dict[str, str]] = []
    count = 0

    def walk(fd: int, parts: tuple[str, ...], ancestors: tuple[tuple[int, int], ...]) -> None:
        nonlocal count
        with os.scandir(fd) as entries:
            for entry in entries:
                info = entry.stat(follow_symlinks=False)
                child_parts = (*parts, entry.name)
                if stat.S_ISDIR(info.st_mode):
                    child = os.open(entry.name, DIRECTORY_FLAGS, dir_fd=fd)
                    try:
                        opened = os.fstat(child)
                        if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                            raise AuditError("read_failed")
                        walk(child, child_parts, (*ancestors, (info.st_dev, info.st_ino)))
                    finally:
                        os.close(child)
                    continue
                count += 1
                if count > maximum:
                    raise AuditError("file_limit_exceeded")
                if stat.S_ISLNK(info.st_mode):
                    reason = "symlink"
                elif not stat.S_ISREG(info.st_mode):
                    reason = "special_file"
                elif Path(entry.name).suffix.lower() != (
                    ".json" if parts[0] == "parsed" else ".pdf"
                ):
                    reason = "unsupported_extension"
                else:
                    found[parts[0]].append(FileRef(child_parts, info, ancestors))
                    continue
                skipped.append({"path": "/".join(child_parts), "reason": reason})

    try:
        for tree in ("parsed", "pdfs"):
            walk(trees[tree], (tree,), ())
    except (OSError, RecursionError):
        raise AuditError("read_failed") from None
    for refs in found.values():
        refs.sort(key=lambda ref: ref.path)
    return found, sorted(skipped, key=lambda item: item["path"])


def read_file(
    tree_fd: int, ref: FileRef, maximum: int, budget: Budget, *, json_content: bool
) -> tuple[bytes, str, int, str | None]:
    """Stream a regular file, rechecking identity and changes before returning."""
    parent = os.dup(tree_fd)
    file_fd: int | None = None
    try:
        try:
            for part, expected in zip(ref.parts[1:-1], ref.ancestors, strict=True):
                child = os.open(part, DIRECTORY_FLAGS, dir_fd=parent)
                os.close(parent)
                parent = child
                info = os.fstat(parent)
                if (info.st_dev, info.st_ino) != expected:
                    return b"", "", 0, "changed"
            file_fd = os.open(
                ref.parts[-1],
                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                dir_fd=parent,
            )
            before = os.fstat(file_fd)
            if not stat.S_ISREG(before.st_mode) or identity(before) != identity(ref.info):
                return b"", "", 0, "changed"
            if before.st_size > maximum:
                return b"", "", before.st_size, "too_large"
            digest = hashlib.sha256()
            content = bytearray()
            size = 0
            while chunk := os.read(
                file_fd, min(64 * 1024, maximum - size + 1, budget.maximum - budget.used + 1)
            ):
                budget.consume(len(chunk))
                size += len(chunk)
                if size > maximum:
                    return b"", "", size, "too_large"
                digest.update(chunk)
                if json_content:
                    content.extend(chunk)
                elif len(content) < 1024:
                    content.extend(chunk[: 1024 - len(content)])
            after = os.fstat(file_fd)
            current = os.stat(ref.parts[-1], dir_fd=parent, follow_symlinks=False)
            if (
                identity(before) != identity(after)
                or identity(before) != identity(current)
                or size != before.st_size
            ):
                return b"", "", size, "changed"
            return bytes(content), digest.hexdigest(), size, None
        except OSError as error:
            if error.errno in {errno.ELOOP, errno.ENOENT, errno.ENOTDIR}:
                return b"", "", 0, "changed"
            raise AuditError("read_failed") from None
    finally:
        if file_fd is not None:
            os.close(file_fd)
        os.close(parent)
