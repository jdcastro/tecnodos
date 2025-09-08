# media/services/processor.py
import io, hashlib
from typing import Tuple, Dict, Any
from PIL import Image
import rasterio
from rasterio.transform import Affine

def sha256_stream(stream) -> str:
    h = hashlib.sha256()
    pos = stream.tell()
    stream.seek(0)
    for chunk in iter(lambda: stream.read(1024*1024), b""):
        h.update(chunk)
    stream.seek(pos)
    return h.hexdigest()

def image_meta(stream):
    pos = stream.tell()
    stream.seek(0)
    with Image.open(stream) as im:
        width, height = im.size
        exif = getattr(im, "info", {})
    stream.seek(pos)
    return width, height, exif

def geotiff_meta(stream):
    pos = stream.tell()
    stream.seek(0)
    with rasterio.MemoryFile(stream.read()) as mem:
        with mem.open() as ds:
            width, height = ds.width, ds.height
            crs = ds.crs.to_string() if ds.crs else None
            bounds = {"west": ds.bounds.left, "south": ds.bounds.bottom, "east": ds.bounds.right, "north": ds.bounds.top}
            transform: Affine = ds.transform
            mpp = (abs(transform.a) + abs(transform.e)) / 2.0
            transform_gdal = transform.to_gdal()
    stream.seek(pos)
    return width, height, crs, bounds, transform_gdal, mpp

def make_thumbnail(stream, max_px=512) -> bytes:
    pos = stream.tell()
    stream.seek(0)
    with Image.open(stream) as im:
        im.thumbnail((max_px, max_px))
        out = io.BytesIO()
        im.save(out, format="PNG", optimize=True)
        out.seek(0)
        data = out.read()
    stream.seek(pos)
    return data
