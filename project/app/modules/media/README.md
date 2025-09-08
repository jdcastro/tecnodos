# TecnoAgro Media Module

Upload and manage TIFF/GeoTIFF, JPG, PNG. Local and S3 backends. Simple XYZ tiler for GeoTIFFs.

## Env
- MEDIA_BACKEND=local|s3
- MEDIA_S3_BUCKET=...
- MEDIA_S3_PREFIX=media/
- AWS_REGION=us-east-1
- LOCAL_MEDIA_DIR=/data/media
- PUBLIC_MEDIA_BASE=/media

## Python deps
Add to your requirements:
- Pillow
- rasterio
- boto3
- flask-wtf

## Register blueprints
from app.modules.media import media, media_api
app.register_blueprint(media)
app.register_blueprint(media_api)
