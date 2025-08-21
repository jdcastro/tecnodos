import uuid
from pathlib import Path
import numpy as np
from werkzeug.utils import secure_filename
from .helpers import DATA_DIR, allowed_file, compute_ndvi, save_png

def process_upload(file_storage) -> dict:
    if not file_storage or not allowed_file(file_storage.filename):
        raise ValueError("invalid file format")
    safe = secure_filename(file_storage.filename)
    tmp_path = DATA_DIR / f"raw_{uuid.uuid4().hex}_{safe}"
    file_storage.save(tmp_path)
    try:
        ndvi = compute_ndvi(tmp_path)
        img_id = uuid.uuid4().hex
        np.save(DATA_DIR / f"{img_id}.npy", ndvi)
        save_png(ndvi, DATA_DIR / f"{img_id}.png")
        h, w = ndvi.shape
        return {"id": img_id, "width": w, "height": h}
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

def load_ndvi(img_id: str) -> np.ndarray:
    path = DATA_DIR / f"{img_id}.npy"
    if not path.exists():
        raise FileNotFoundError("ndvi not found")
    return np.load(path)
