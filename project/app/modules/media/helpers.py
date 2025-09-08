from __future__ import annotations

import hashlib
import mimetypes
import os
import uuid
from dataclasses import dataclass
from typing import Optional, Tuple

from flask import current_app


def _media_root() -> str:
    """Return absolute path for local media storage root.

    Defaults to `<project-root>/storage/media` if MEDIA_STORAGE_DIR is not set.
    """
    base = current_app.config.get("MEDIA_STORAGE_DIR")
    if not base:
        # Project root is two levels above app/__init__.py
        project_root = os.path.abspath(os.path.join(current_app.root_path, os.pardir))
        base = os.path.join(project_root, "storage", "media")
    os.makedirs(base, exist_ok=True)
    return base


def allowed_extension(filename: str) -> bool:
    allowed = {".tif", ".tiff", ".png", ".jpg", ".jpeg"}
    _, ext = os.path.splitext(filename.lower())
    return ext in allowed


def guess_mime(filepath: str) -> str:
    return mimetypes.guess_type(filepath)[0] or "application/octet-stream"


def sha256_of_file(fileobj) -> str:
    fileobj.seek(0)
    h = hashlib.sha256()
    for chunk in iter(lambda: fileobj.read(8192), b""):
        h.update(chunk)
    fileobj.seek(0)
    return h.hexdigest()


@dataclass
class ImageInfo:
    width: Optional[int] = None
    height: Optional[int] = None
    exif: Optional[dict] = None


def extract_image_info(filepath: str) -> ImageInfo:
    info = ImageInfo()
    # Try Pillow first
    try:
        from PIL import Image, ExifTags  # type: ignore

        with Image.open(filepath) as im:
            info.width, info.height = im.size
            try:
                raw_exif = im._getexif() or {}
                exif = {}
                for tag_id, value in raw_exif.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    exif[str(tag)] = value
                info.exif = exif
            except Exception:
                info.exif = None
        return info
    except Exception:
        pass

    # Fallback: attempt rasterio for tiffs (gives width/height too)
    try:
        import rasterio  # type: ignore

        with rasterio.open(filepath) as src:
            info.width = int(src.width)
            info.height = int(src.height)
        return info
    except Exception:
        return info


@dataclass
class GeoInfo:
    is_geo: bool = False
    crs: Optional[str] = None
    bounds: Optional[dict] = None
    transform: Optional[dict] = None


def extract_geo_info_if_tiff(filepath: str) -> GeoInfo:
    geo = GeoInfo()
    ext = os.path.splitext(filepath.lower())[1]
    if ext not in {".tif", ".tiff"}:
        return geo
    try:
        import rasterio  # type: ignore

        with rasterio.open(filepath) as src:
            geo.is_geo = True
            try:
                geo.crs = src.crs.to_string() if src.crs else None
            except Exception:
                geo.crs = None
            try:
                b = src.bounds
                geo.bounds = {"left": b.left, "bottom": b.bottom, "right": b.right, "top": b.top}
            except Exception:
                geo.bounds = None
            try:
                t = src.transform
                geo.transform = {
                    "a": t.a,
                    "b": t.b,
                    "c": t.c,
                    "d": t.d,
                    "e": t.e,
                    "f": t.f,
                }
            except Exception:
                geo.transform = None
    except Exception:
        # Not a fatal error; treat as non-geo
        pass
    return geo


def allocate_storage_path(ext: str) -> Tuple[str, str]:
    """Create a unique storage path and return (storage_key, abs_path).

    Path schema: local/<first2>/<next2>/<uuid>.<ext>
    """
    uid = str(uuid.uuid4())
    shard1, shard2 = uid[:2], uid[2:4]
    rel_dir = os.path.join("local", shard1, shard2)
    abs_dir = os.path.join(_media_root(), rel_dir)
    os.makedirs(abs_dir, exist_ok=True)
    filename = f"{uid}{ext}"
    storage_key = os.path.join(rel_dir, filename)
    abs_path = os.path.join(abs_dir, filename)
    return storage_key, abs_path
