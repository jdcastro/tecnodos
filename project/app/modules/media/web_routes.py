# media/web_routes.py
from flask import render_template, request, redirect, url_for, flash
from . import media
from .models import Asset
from .forms import MediaSearchForm, MediaUploadForm

@media.get("")
def index():
    form = MediaSearchForm(request.args)
    q = form.q.data or ""
    query = Asset.query
    if q:
        like = f"%{q}%"
        query = query.filter(Asset.original_name.ilike(like))
    items = query.order_by(Asset.created_at.desc()).limit(60).all()
    return render_template("media/index.j2", items=items, form=form)

@media.get("/upload")
def upload():
    form = MediaUploadForm()
    return render_template("media/upload.j2", form=form)

@media.get("/<int:asset_id>")
def detail(asset_id: int):
    a = Asset.query.get_or_404(asset_id)
    return render_template("media/detail.j2", a=a)
