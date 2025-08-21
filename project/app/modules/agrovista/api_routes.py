from flask import jsonify, request, send_file, abort
import math
from . import agrovista_api as api
from .controller import process_upload, load_ndvi
from .helpers import DATA_DIR, polygon_mask, average_protein

def _validate_id(value: str) -> str:
    if not value or not value.isalnum():
        abort(400, description="invalid id")
    return value

def _validate_vertices(vertices):
    if not isinstance(vertices, list) or len(vertices) < 3:
        abort(400, description="invalid vertices")
    out = []
    for p in vertices:
        if (not isinstance(p, (list, tuple))) or len(p) != 2:
            abort(400, description="invalid vertex")
        x, y = p
        if not (isinstance(x, (int, float)) and isinstance(y, (int, float))):
            abort(400, description="invalid vertex")
        if any(math.isnan(v) or math.isinf(v) for v in (x, y)):
            abort(400, description="invalid vertex")
        out.append([float(x), float(y)])
    return out

@api.route("/upload", methods=["POST"])
def upload():
    try:
        meta = process_upload(request.files.get("file"))
        return jsonify(meta), 201
    except ValueError as e:
        abort(400, description=str(e))
    except Exception:
        abort(500, description="processing error")

@api.route("/image/<img_id>.png", methods=["GET"])
def image(img_id: str):
    _validate_id(img_id)
    path = DATA_DIR / f"{img_id}.png"
    if not path.exists():
        abort(404)
    return send_file(path, mimetype="image/png", max_age=3600)

@api.route("/protein", methods=["POST"])
def protein():
    data = request.get_json(force=True, silent=False) or {}
    img_id = _validate_id(str(data.get("id", "")))
    vertices = _validate_vertices(data.get("vertices", []))
    ndvi = load_ndvi(img_id)
    mask = polygon_mask(ndvi.shape, vertices)
    avg = average_protein(ndvi, mask)
    if math.isnan(avg):
        abort(400, description="invalid area")
    return jsonify(protein=round(avg, 2))
