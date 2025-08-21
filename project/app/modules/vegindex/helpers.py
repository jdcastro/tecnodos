from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

from .services.storage import LocalStorage, S3Storage, StorageBackend


def get_storage_and_path(source: str) -> Tuple[StorageBackend, str]:
    if source.startswith("local:"):
        base_dir = os.getenv("VEGINDEX_LOCAL_BASE")
        base = Path(base_dir).resolve() if base_dir else None
        return LocalStorage(base), source.split("local:", 1)[1]
    if source.startswith("s3://") or source.startswith("s3:"):
        bucket = os.getenv("VEGINDEX_S3_BUCKET")
        clean = source.replace("s3:", "", 1) if source.startswith("s3:") else source
        return S3Storage(bucket=bucket), clean
    raise ValueError("Unsupported source. Use local:<path> or s3://bucket/key")
