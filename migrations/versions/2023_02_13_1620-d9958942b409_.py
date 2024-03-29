"""empty message

Revision ID: d9958942b409
Revises: 906fc06853c3
Create Date: 2023-02-13 16:20:17.144306

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd9958942b409'
down_revision = '906fc06853c3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('secrets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('key', sa.String(), nullable=True),
    sa.Column('value', sa.String(), nullable=True),
    sa.Column('user', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['user'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_secrets_id'), 'secrets', ['id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_secrets_id'), table_name='secrets')
    op.drop_table('secrets')
    # ### end Alembic commands ###
