"""add call_count to contact and remove custom_fields

Revision ID: f9b6383f50b4
Revises: 56eb00cb1ac7
Create Date: 2025-07-07 13:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f9b6383f50b4'
down_revision = '56eb00cb1ac7'
branch_labels = None
depends_on = None


def upgrade():
    # Agregar columna call_count
    op.add_column('contact', sa.Column('call_count', sa.Integer(), nullable=False, server_default='1'))

    # Eliminar columna custom_fields si existe
    with op.batch_alter_table('contact') as batch_op:
        try:
            batch_op.drop_column('custom_fields')
        except Exception:
            pass  # Si no existe, no hace nada


def downgrade():
    # Volver a agregar custom_fields
    op.add_column('contact', sa.Column('custom_fields', sa.Text(), nullable=True))

    # Eliminar call_count
    op.drop_column('contact', 'call_count')