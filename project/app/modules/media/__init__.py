# media/__init__.py
from flask import Blueprint

media = Blueprint(
    "media",
    __name__,
    url_prefix="/dashboard/media",
    template_folder="templates",
    static_folder="static"
)

media_api = Blueprint(
    "media_api",
    __name__,
    url_prefix="/api/media"
)

# Import routes to register them with the blueprints
from . import web_routes  # noqa: E402,F401
from . import api_routes  # noqa: E402,F401
