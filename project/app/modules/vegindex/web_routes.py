from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for

from . import vegindex as web
from .controller import compute_from_source


@web.route("/hello")
def hello():
    return render_template("vegindex/upload.j2")


@web.route("/analyze", methods=["POST"])
def analyze():
    source = request.form.get("source", "").strip()
    bbox_text = request.form.get("bbox", "").strip()
    bbox = None
    if bbox_text:
        try:
            parts = [int(x) for x in bbox_text.split(",")]
            if len(parts) != 4:
                raise ValueError
            bbox = parts
        except Exception:
            flash("BBox must be four integers: xmin,ymin,xmax,ymax", "error")
            return redirect(url_for("vegindex.hello"))

    if not source:
        flash(
            "Source is required. Example: local:/data/image.tif or s3://bucket/key",
            "error",
        )
        return redirect(url_for("vegindex.hello"))

    try:
        result = compute_from_source(source=source, bbox=bbox)
        return render_template(
            "vegindex/result.j2", result=result, source=source, bbox=bbox
        )
    except Exception as e:
        flash(str(e), "error")
        return redirect(url_for("vegindex.hello"))
