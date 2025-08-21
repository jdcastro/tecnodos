from flask import render_template
from . import agrovista as web


@web.route("/", methods=["GET"])
def hello():
    return render_template("agrovista/index.j2")
