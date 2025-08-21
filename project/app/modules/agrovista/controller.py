import uuid
from pathlib import Path
from datetime import datetime

import numpy as np
from werkzeug.utils import secure_filename

from app.extensions import db
from .helpers import DATA_DIR, allowed_file, compute_ndvi, save_png
from .models import NDVIImage


def process_upload(file_storage) -> dict:
    if not file_storage or not allowed_file(file_storage.filename):
        raise ValueError("invalid file format")
    safe = secure_filename(file_storage.filename)
    tmp_path = DATA_DIR / f"raw_{uuid.uuid4().hex}_{safe}"
    file_storage.save(tmp_path)
    try:
        ndvi = compute_ndvi(tmp_path)
        img_id = uuid.uuid4().hex
        npy_path = DATA_DIR / f"{img_id}.npy"
        png_path = DATA_DIR / f"{img_id}.png"
        np.save(npy_path, ndvi)
        save_png(ndvi, png_path)
        h, w = ndvi.shape
        record = NDVIImage(
            id=img_id,
            filename=safe,
            png_path=str(png_path),
            npy_path=str(npy_path),
            width=w,
            height=h,
            upload_date=datetime.utcnow(),
        )
        db.session.add(record)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return {"id": record.id, "width": record.width, "height": record.height}
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


def load_ndvi(img_id: str) -> np.ndarray:
    record = db.session.get(NDVIImage, img_id)
    if not record:
        raise FileNotFoundError("ndvi not found")
    path = Path(record.npy_path)
    if not path.exists():
        raise FileNotFoundError("ndvi not found")
    return np.load(path)
