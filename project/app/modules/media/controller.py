from __future__ import annotations

import os
from typing import Optional

from flask import current_app
from werkzeug.datastructures import FileStorage

from app.extensions import db

from .helpers import (
    allowed_extension,
    allocate_storage_path,
    extract_geo_info_if_tiff,
    extract_image_info,
    guess_mime,
    sha256_of_file,
)
from .models import Asset, AssetType, StorageLocation


class MediaController:
    def save_local_upload(self, file: FileStorage) -> Asset:
        if not file or not getattr(file, "filename", None):
            raise ValueError("No file provided")

        filename = file.filename
        _, ext = os.path.splitext(filename)
        ext = ext.lower()
        if not allowed_extension(filename):
            raise ValueError("Unsupported file type")

        # Compute size and sha256 by reading file stream
        size_bytes = 0
        try:
            # Werkzeug FileStorage provides stream; use for size and hash
            stream = file.stream
            # We need to hash and also know size; use sha256_of_file which resets pointer
            digest = sha256_of_file(stream)
            stream.seek(0, os.SEEK_END)
            size_bytes = stream.tell()
            stream.seek(0)
        except Exception:
            # Fallback: save first then stat
            digest = sha256_of_file(file.stream)

        storage_key, abs_path = allocate_storage_path(ext)
        # Persist to disk
        file.save(abs_path)

        if not size_bytes:
            try:
                size_bytes = os.path.getsize(abs_path)
            except OSError:
                size_bytes = 0

        # Metadata
        mime = guess_mime(abs_path)
        img = extract_image_info(abs_path)
        geo = extract_geo_info_if_tiff(abs_path)

        asset_type = (
            AssetType.GEOTIFF.value if ext in {".tif", ".tiff"} else AssetType.IMAGE.value
        )

        asset = Asset(
            uuid=os.path.splitext(os.path.basename(abs_path))[0],
            original_name=filename,
            ext=ext.lstrip("."),
            mime=mime,
            asset_type=asset_type,
            storage=StorageLocation.LOCAL.value,
            storage_key=storage_key,
            sha256=digest,
            size_bytes=size_bytes,
            width=img.width,
            height=img.height,
            is_geo=geo.is_geo,
            crs=geo.crs,
            bounds=geo.bounds,
            transform=geo.transform,
            exif=img.exif,
        )

        db.session.add(asset)
        db.session.commit()
        return asset

    def delete_asset(self, asset_id: int) -> bool:
        asset = Asset.query.get(asset_id)
        if not asset:
            return False
        # Only local storage supported for now
        from .helpers import _media_root
        base = _media_root()
        abs_path = os.path.join(base, asset.storage_key)
        try:
            if os.path.isfile(abs_path):
                os.remove(abs_path)
        except Exception:
            # Continue even if file missing or cannot delete
            pass
        db.session.delete(asset)
        db.session.commit()
        return True
