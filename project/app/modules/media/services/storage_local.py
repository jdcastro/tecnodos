# media/services/storage_local.py
import os
from typing import BinaryIO
from werkzeug.utils import secure_filename
from .storage_base import Storage

class LocalStorage(Storage):
    def __init__(self, base_dir: str, public_base_url: str):
        self.base_dir = base_dir
        self.public_base_url = public_base_url.rstrip("/")

    def _path(self, key: str) -> str:
        safe = secure_filename(key)
        return os.path.join(self.base_dir, safe)

    def save(self, key: str, stream: BinaryIO, size: int, content_type: str) -> None:
        path = self._path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                f.write(chunk)

    def open(self, key: str) -> BinaryIO:
        return open(self._path(key), "rb")

    def exists(self, key: str) -> bool:
        return os.path.exists(self._path(key))

    def url(self, key: str, expires: int = 3600) -> str:
        return f"{self.public_base_url}/{key}"
