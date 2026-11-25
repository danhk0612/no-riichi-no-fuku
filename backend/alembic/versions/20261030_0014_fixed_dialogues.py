"""Add independent character fixed dialogue storage."""
from alembic import op
import sqlalchemy as sa

revision = '20261030_0014'
down_revision = '20261021_0013'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('character_fixed_dialogues',
        sa.Column('cpu_id', sa.Integer(), sa.ForeignKey('cpu_characters.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('slots', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('revision >= 1', name='ck_fixed_dialogue_revision'))


def downgrade():
    op.drop_table('character_fixed_dialogues')
