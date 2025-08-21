from datetime import datetime
from app.extensions import db


class NDVIImage(db.Model):
    """Modelo para almacenar metadatos de imágenes NDVI procesadas."""

    __tablename__ = "ndvi_images"

    id = db.Column(db.String(32), primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    png_path = db.Column(db.String(300), nullable=False)
    npy_path = db.Column(db.String(300), nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:  # pragma: no cover - simple representation
        return f"<NDVIImage {self.id}>"
