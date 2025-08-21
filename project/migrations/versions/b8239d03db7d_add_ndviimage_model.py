"""add ndviimage model

Revision ID: b8239d03db7d
Revises: 1d4d593cc253
Create Date: 2025-08-21 16:24:50.834189

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b8239d03db7d"
down_revision = "1d4d593cc253"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ndvi_images",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("png_path", sa.String(length=300), nullable=False),
        sa.Column("npy_path", sa.String(length=300), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("upload_date", sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table("ndvi_images")
