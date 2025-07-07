"""create calls table

Revision ID: 56eb00cb1ac7
Revises: 9a7d24863b70
Create Date: 2025-07-07 12:30:00.000000

"""

from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
import uuid

# revision identifiers, used by Alembic.
revision = '56eb00cb1ac7'
down_revision = '9a7d24863b70'
branch_labels = None
depends_on = None


def upgrade():
    # Crear tabla calls
    op.create_table(
        'calls',
        sa.Column('uuid', pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('call_id', sa.String(50), nullable=False),
        sa.Column('contact_uuid', pg.UUID(as_uuid=True), nullable=True),
        sa.Column('time_stamp', sa.String(50), nullable=False),
        sa.Column('direction', sa.String(50), nullable=False),
        sa.Column('direct_link', sa.String(50), nullable=False),
        sa.Column('id_user', sa.String(50), nullable=False),
        sa.Column('phone_number', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, default=None),
    )
    
    # Crear foreign key constraint
    op.create_foreign_key(
        'fk_calls_contact_uuid',
        'calls', 'contact',
        ['contact_uuid'], ['uuid']
    )
    
    # Actualizar tabla contact: cambiar tags de String a Text
    op.alter_column('contact', 'tags',
                   existing_type=sa.String(50),
                   type_=sa.Text(),
                   nullable=False)


def downgrade():
    # Revertir cambio en contact
    op.alter_column('contact', 'tags',
                   existing_type=sa.Text(),
                   type_=sa.String(50),
                   nullable=False)
    
    # Eliminar foreign key constraint
    op.drop_constraint('fk_calls_contact_uuid', 'calls', type_='foreignkey')
    
    # Eliminar tabla calls
    op.drop_table('calls')