from __future__ import annotations

from flask import jsonify, request

from . import vegindex_api as api
from .controller import compute_from_source


@api.route("/ping", methods=["GET"])
def ping():
    return jsonify(message="pong from vegindex API")


@api.route("/compute", methods=["POST"])
def compute():
    payload = request.get_json(silent=True) or {}
    source = payload.get("source")
    bbox = payload.get("bbox")
    if not source:
        return (
            jsonify(
                error="source is required (e.g., local:/path.tif or s3://bucket/key)"
            ),
            400,
        )
    try:
        result = compute_from_source(source=source, bbox=bbox)
        return jsonify(result)
    except Exception as exc:
        return jsonify(error=str(exc)), 400
