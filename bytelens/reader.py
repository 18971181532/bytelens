"""Safe binary file reading and path metadata."""

import os
from typing import Dict, Optional

HEAD_BYTES = 65536
DEFAULT_MAX_BYTES = 64 * 1024 * 1024  # 64 MiB fully-loaded ceiling


class BinaryFile:
    """Thin wrapper around a file path with lazy reads."""

    def __init__(self, path: str):
        self.path = os.path.abspath(path)
        if not os.path.isfile(self.path):
            raise FileNotFoundError(self.path)
        st = os.stat(self.path)
        self.size = st.st_size
        self.mtime = st.st_mtime
        self._head: Optional[bytes] = None

    @property
    def name(self) -> str:
        return os.path.basename(self.path)

    def read_head(self, length: int = HEAD_BYTES) -> bytes:
        if self._head is None or len(self._head) < length:
            with open(self.path, "rb") as fh:
                self._head = fh.read(length)
        return self._head

    def read_range(self, offset: int, length: int) -> bytes:
        with open(self.path, "rb") as fh:
            fh.seek(max(0, offset))
            return fh.read(max(0, length))

    def read_all(self, max_bytes: int = DEFAULT_MAX_BYTES) -> bytes:
        if self.size > max_bytes:
            raise ValueError(
                f"file is {self.size} bytes, exceeding the {max_bytes} "
                "fully-loaded ceiling; use streaming endpoints")
        return self.read_range(0, self.size)

    def meta(self) -> Dict[str, object]:
        root, ext = os.path.splitext(self.name)
        return {
            "path": self.path,
            "name": self.name,
            "size": self.size,
            "extension": ext.lstrip(".").lower(),
            "mtime": self.mtime,
        }
