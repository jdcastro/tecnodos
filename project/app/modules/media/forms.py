# media/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, FileField, SubmitField
from wtforms.validators import Optional

class MediaSearchForm(FlaskForm):
    q = StringField("Search", validators=[Optional()])
    submit = SubmitField("Search")

class MediaUploadForm(FlaskForm):
    file = FileField("File")
    submit = SubmitField("Upload")
