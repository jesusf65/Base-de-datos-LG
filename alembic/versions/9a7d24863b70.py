"""create contact table

Revision ID: 9a7d24863b70
Revises: None
Create Date: 2025-07-01 12:30:00.000000

"""

from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
import uuid

# revision identifiers, used by Alembic.
revision = '9a7d24863b70'
down_revision ='c85bf88d3166'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'contact',
        sa.Column('uuid', pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('contact_id', sa.String(50), nullable=False),
        sa.Column('contact_name', sa.String(50), nullable=False),
        sa.Column('create_date', sa.String(50), nullable=False),
        sa.Column('asign_to', sa.String(50), nullable=False),
        sa.Column('phone_number', sa.String(50), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('tags', sa.String(50), nullable=False),
        sa.Column('custom_fields', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, default=None),
    )


def downgrade():
    op.drop_table('contact')