from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'abc123456789'  # Este Alembic lo pone automáticamente
down_revision = 'f9b6383f50b4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'call_crm',
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_from', sa.String(length=100), nullable=False),
        sa.Column('stamp_time', sa.String(length=100), nullable=True),
        sa.Column('status_call', sa.String(length=100), nullable=False),
        sa.Column('duration', sa.String(length=100), nullable=False),
        sa.Column('contact_id', sa.String(length=100), nullable=False),
        sa.Column('direction', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('uuid')
    )


def downgrade():
    op.drop_table('call_crm')