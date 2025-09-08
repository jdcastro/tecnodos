from flask import Blueprint

media = Blueprint("media", __name__, url_prefix='/dashboard/media', template_folder='templates')
media_api = Blueprint("media_api", __name__, url_prefix='/api/media')

from . import web_routes, api_routes
