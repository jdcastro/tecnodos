# media/api_routes.py
import os, io, uuid, tempfile
from flask import request, jsonify, Response
from werkzeug.utils import secure_filename
from app.extensions import db
from . import media_api
from .models import Asset, AssetType, StorageLocation, AssetVariant
from .services.storage_local import LocalStorage
from .services.storage_s3 import S3Storage
from .services import processor, tiler

MAX_BYTES = 1024 * 1024 * 1024  # 1GB for local uploads

def get_storage():
    backend = os.environ.get("MEDIA_BACKEND", "local").lower()
    if backend == "s3":
        bucket = os.environ["MEDIA_S3_BUCKET"]
        region = os.environ.get("AWS_REGION","us-east-1")
        prefix = os.environ.get("MEDIA_S3_PREFIX","media/")
        return S3Storage(bucket=bucket, region=region, prefix=prefix), StorageLocation.S3
    base_dir = os.environ.get("LOCAL_MEDIA_DIR","/data/media")
    public_base = os.environ.get("PUBLIC_MEDIA_BASE","/media")
    return LocalStorage(base_dir=base_dir, public_base_url=public_base), StorageLocation.LOCAL

def detect_mime_and_type(filename: str, hinted: str = ""):
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext in ("tif", "tiff"):
        return "image/tiff", AssetType.GEOTIFF
    if ext in ("jpg", "jpeg"):
        return "image/jpeg", AssetType.IMAGE
    if ext == "png":
        return "image/png", AssetType.IMAGE
    raise ValueError("Unsupported file type")

@media_api.get("")
def list_assets():
    q = request.args.get("q", "").strip()
    at = request.args.get("type")
    query = Asset.query
    if q:
        like = f"%{q}%"
        query = query.filter(Asset.original_name.ilike(like))
    if at in ("image","geotiff"):
        query = query.filter(Asset.asset_type == at)
    items = query.order_by(Asset.created_at.desc()).limit(100).all()
    return jsonify([{
        "id": a.id, "uuid": a.uuid, "name": a.original_name, "type": a.asset_type,
        "mime": a.mime, "w": a.width, "h": a.height, "is_geo": a.is_geo
    } for a in items])

@media_api.post("/upload")
def upload_local():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "No file"}), 400
    if request.content_length and request.content_length > MAX_BYTES:
        return jsonify({"error": "File too large"}), 413
    mime, asset_type = detect_mime_and_type(f.filename, f.mimetype or "")

    with tempfile.NamedTemporaryFile("w+b", delete=True) as tmp:
        size = 0
        for chunk in iter(lambda: f.stream.read(1024*1024), b""):
            size += len(chunk)
            if size > MAX_BYTES:
                return jsonify({"error": "File too large"}), 413
            tmp.write(chunk)
        tmp.flush(); tmp.seek(0)

        sha = processor.sha256_stream(tmp)
        tmp.seek(0)
        width = height = None
        is_geo = False
        crs = bounds = transform = None
        mpp = None
        exif = {}

        if asset_type == AssetType.GEOTIFF:
            width, height, crs, bounds, transform, mpp = processor.geotiff_meta(tmp)
            is_geo = True
        else:
            width, height, exif = processor.image_meta(tmp)
        tmp.seek(0)

        storage, storage_loc = get_storage()
        asset_uuid = str(uuid.uuid4())
        ext = f.filename.rsplit(".",1)[-1].lower()
        key = f"{asset_uuid}/original.{ext}"
        storage.save(key, tmp, size=size, content_type=mime)

    a = Asset(
        uuid=asset_uuid,
        original_name=secure_filename(f.filename),
        ext=ext, mime=mime,
        asset_type=asset_type, storage=storage_loc,
        storage_key=key, sha256=sha, size_bytes=size,
        width=width, height=height, is_geo=is_geo,
        crs=crs, bounds=bounds, transform=transform, mpp=mpp, exif=exif
    )
    db.session.add(a); db.session.commit()
    return jsonify({"id": a.id, "uuid": a.uuid})

@media_api.post("/presign")
def presign():
    bucket = os.environ["MEDIA_S3_BUCKET"]
    region = os.environ.get("AWS_REGION","us-east-1")
    prefix = os.environ.get("MEDIA_S3_PREFIX","media/")
    asset_uuid = str(uuid.uuid4())
    key = f"{prefix.rstrip('/')}/{asset_uuid}/original"
    url = S3Storage.presign_post(bucket=bucket, key=key)
    return jsonify({"uuid": asset_uuid, "bucket": bucket, "key": key, "presigned": url})

@media_api.post("/ingest")
def ingest():
    data = request.get_json(force=True)
    uuid_str = data["uuid"]
    key = data["key"]
    original_name = data.get("original_name", "original")
    ext = data.get("ext", "tif").lower()
    mime, asset_type = detect_mime_and_type(f"{original_name}.{ext}")
    storage, storage_loc = get_storage()
    stream = storage.open(key)

    # raster/metadata
    buf = io.BytesIO(stream.read()); buf.seek(0)
    sha = processor.sha256_stream(buf); buf.seek(0)
    size = len(buf.getvalue())
    if asset_type == AssetType.GEOTIFF:
        width, height, crs, bounds, transform, mpp = processor.geotiff_meta(buf)
        is_geo = True; exif = {}
    else:
        width, height, exif = processor.image_meta(buf)
        is_geo = False; crs=bounds=transform=mpp=None

    a = Asset(
        uuid=uuid_str,
        original_name=secure_filename(original_name),
        ext=ext, mime=mime,
        asset_type=asset_type, storage=storage_loc,
        storage_key=key, sha256=sha, size_bytes=size,
        width=width, height=height, is_geo=is_geo,
        crs=crs, bounds=bounds, transform=transform, mpp=mpp, exif=exif
    )
    db.session.add(a); db.session.commit()
    return jsonify({"id": a.id, "uuid": a.uuid})

@media_api.get("/<int:asset_id>")
def get_asset(asset_id: int):
    a = Asset.query.get_or_404(asset_id)
    return jsonify({
        "id": a.id, "uuid": a.uuid, "name": a.original_name, "mime": a.mime,
        "type": a.asset_type, "w": a.width, "h": a.height,
        "is_geo": a.is_geo, "crs": a.crs, "bounds": a.bounds, "mpp": a.mpp
    })

@media_api.get("/<int:asset_id>/tile/<int:z>/<int:x>/<int:y>.png")
def tile(asset_id: int, z: int, x: int, y: int):
    a = Asset.query.get_or_404(asset_id)
    if a.asset_type != "geotiff":
        return jsonify({"error": "Not a GeoTIFF"}), 400
    storage, _ = get_storage()
    fileobj = storage.open(a.storage_key)
    data = tiler.tile_from_geotiff(fileobj, z, x, y, tile_size=256)
    return Response(data, mimetype="image/png")

@media_api.delete("/<int:asset_id>")
def delete_asset(asset_id: int):
    a = Asset.query.get_or_404(asset_id)
    db.session.delete(a); db.session.commit()
    return jsonify({"ok": True})
