from flask import Blueprint


from app.extensions import db


agrovista = Blueprint(
    "agrovista",
    __name__,
    url_prefix="/dashboard/agrovista",
    template_folder="templates",
)
agrovista_api = Blueprint("agrovista_api", __name__, url_prefix="/api/agrovista")


@agrovista_api.record_once
def _create_tables(state):
    """Ensure database tables are present when the blueprint is registered."""
    with state.app.app_context():
        db.create_all()


from . import web_routes, api_routes, models
