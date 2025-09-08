from __future__ import annotations

from flask import jsonify, request

from app.core.controller import login_required
from app.extensions import db

from . import media_api as api
from .controller import MediaController
from .models import Asset


@api.route("/ping", methods=["GET"])
def ping():
    return jsonify(message="pong from media API")


@api.route("/assets", methods=["GET"])
@login_required
def list_assets():
    items = (
        Asset.query.order_by(Asset.created_at.desc())
        .with_entities(
            Asset.id,
            Asset.uuid,
            Asset.original_name,
            Asset.ext,
            Asset.mime,
            Asset.asset_type,
            Asset.storage,
            Asset.storage_key,
            Asset.size_bytes,
            Asset.width,
            Asset.height,
            Asset.is_geo,
            Asset.created_at,
        )
        .all()
    )

    def to_dict(row):
        return {
            "id": row.id,
            "uuid": row.uuid,
            "original_name": row.original_name,
            "ext": row.ext,
            "mime": row.mime,
            "asset_type": row.asset_type,
            "storage": row.storage,
            "storage_key": row.storage_key,
            "size_bytes": row.size_bytes,
            "width": row.width,
            "height": row.height,
            "is_geo": row.is_geo,
            "created_at": row.created_at.isoformat(),
        }

    return jsonify([to_dict(x) for x in items]), 200


@api.route("/upload", methods=["POST"])
@login_required
def upload_local_api():
    if "file" not in request.files:
        return jsonify({"message": "No file part"}), 400
    file = request.files["file"]
    try:
        ctrl = MediaController()
        asset = ctrl.save_local_upload(file)
        return jsonify({
            "message": "Uploaded",
            "asset_id": asset.id,
            "uuid": asset.uuid,
            "storage_key": asset.storage_key,
        }), 201
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Upload failed"}), 500


@api.route("/assets/<int:asset_id>", methods=["DELETE"])
@login_required
def delete_asset(asset_id: int):
    try:
        ctrl = MediaController()
        ok = ctrl.delete_asset(asset_id)
        if not ok:
            return jsonify({"message": "Asset not found"}), 404
        return jsonify({"message": "Deleted"}), 200
    except Exception:
        db.session.rollback()
        return jsonify({"message": "Delete failed"}), 500
