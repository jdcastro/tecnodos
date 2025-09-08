import os
from flask import flash, render_template, request, send_from_directory, url_for
from . import media as web
from app.core.controller import login_required
from .controller import MediaController
from .helpers import _media_root
from .models import Asset


def get_dashboard_menu():
    """Define el menu superior en los templates"""
    return {
        "menu": [
            {"name": "Home", "url": url_for("core.dashboard")},
            {"name": "Logout", "url": url_for("core.logout")},
            {"name": "Profile", "url": url_for("core.profile")},
        ]
    }


@web.route("/hello", methods=["GET"])
def hello():
    return render_template("media/hello.j2")


@web.route("/", methods=["GET"])
@login_required
def library():
    """Vista: Biblioteca de medios con filtro/búsqueda/paginación."""
    context = {
        "dashboard": True,
        "title": "Biblioteca de Medios",
        "description": "Administra imágenes y archivos de medios.",
        "author": "TecnoAgro",
        "site_title": "Medios",
        "data_menu": get_dashboard_menu(),
    }
    # Parámetros
    q = request.args.get("q", type=str)
    type_filter = request.args.get("type", default="all", type=str)
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=24, type=int)

    query = Asset.query
    if q:
        like = f"%{q}%"
        query = query.filter(Asset.original_name.ilike(like))
    if type_filter in ("image", "geotiff"):
        query = query.filter(Asset.asset_type == type_filter)

    query = query.order_by(Asset.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    items = pagination.items

    return render_template(
        "media/library.j2",
        items=items,
        pagination=pagination,
        q=q or "",
        type_filter=type_filter,
        per_page=per_page,
        **context,
        request=request,
    )


@web.route("/upload", methods=["GET", "POST"])
@login_required
def upload_local():
    """Vista: Subida de archivos desde el equipo (solo UI)."""
    context = {
        "dashboard": True,
        "title": "Subir desde tu equipo",
        "description": "Selecciona imágenes para subir (TIFF, PNG, JPG, JPEG).",
        "author": "TecnoAgro",
        "site_title": "Medios",
        "data_menu": get_dashboard_menu(),
    }
    if request.method == "POST":
        file = request.files.get("media_files")
        if not file:
            flash("Debes seleccionar un archivo.", "error")
            return render_template("media/upload_local.j2", **context, request=request), 400
        try:
            ctrl = MediaController()
            asset = ctrl.save_local_upload(file)
            flash("Archivo subido correctamente.", "success")
            return render_template("media/upload_local.j2", **context, request=request)
        except ValueError as e:
            flash(str(e), "error")
            return render_template("media/upload_local.j2", **context, request=request), 400
        except Exception:
            flash("Error subiendo el archivo.", "error")
            return render_template("media/upload_local.j2", **context, request=request), 500
    return render_template("media/upload_local.j2", **context, request=request)


@web.route("/upload/s3", methods=["GET"])
@login_required
def upload_s3():
    """Vista: Importar desde S3 (solo UI, no implementado)."""
    context = {
        "dashboard": True,
        "title": "Importar desde S3",
        "description": "Configura el origen en S3 para importar medios.",
        "author": "TecnoAgro",
        "site_title": "Medios",
        "data_menu": get_dashboard_menu(),
    }
    return render_template("media/upload_s3.j2", **context, request=request)


@web.route("/file/<path:key>", methods=["GET"])
@login_required
def serve_file(key: str):
    # Only allow to serve under the media root
    base = _media_root()
    directory = os.path.join(base, os.path.dirname(key))
    filename = os.path.basename(key)
    return send_from_directory(directory, filename)


@web.route("/download/<path:key>", methods=["GET"])
@login_required
def download_file(key: str):
    base = _media_root()
    directory = os.path.join(base, os.path.dirname(key))
    filename = os.path.basename(key)
    return send_from_directory(directory, filename, as_attachment=True)
