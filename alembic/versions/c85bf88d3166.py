"""create calls table

Revision ID: c85bf88d3166
Revises: None
Create Date: 2025-07-01 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
import uuid

# revision identifiers, used by Alembic.
revision = 'c85bf88d3166'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'calls',
        sa.Column('uuid', pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('call_id', sa.String(50), nullable=False),
        sa.Column('time_stamp', sa.String(50), nullable=False),
        sa.Column('direction', sa.String(50), nullable=False),
        sa.Column('direct_link', sa.String(50), nullable=False),
        sa.Column('id_user', sa.String(50), nullable=False),
        sa.Column('phone_number', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, default=None),
    )

def downgrade():
    op.drop_table('calls')