"""empty message

Revision ID: 6d0c92b3fc6f
Revises: 
Create Date: 2021-06-18 16:22:53.287372

"""
import os
import csv
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6d0c92b3fc6f'
down_revision = None
branch_labels = None
depends_on = None

with open(os.environ['STOPS_CSV_PATH']) as f:
    a = []
    for row in csv.reader(f):
        s = {}
        s['id'] = row[0]
        s['name'] = row[2]
        a.append(s)


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    station_table = op.create_table('station',
    sa.Column('id', sa.String(length=8), nullable=False),
    sa.Column('name', sa.String(length=40), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_station'))
    )
    op.create_table('station_line_pair',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('station_id', sa.String(length=8), nullable=True),
    sa.Column('line_id', sa.String(length=2), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_station_line_pair'))
    )
    op.create_table('trip',
    sa.Column('id', sa.String(length=30), nullable=False),
    sa.Column('route_id', sa.String(length=30), nullable=True),
    sa.Column('line_id', sa.String(length=2), nullable=True),
    sa.Column('has_started', sa.Boolean(), nullable=True),
    sa.Column('start_time', sa.DateTime(), nullable=True),
    sa.Column('has_finished', sa.Boolean(), nullable=True),
    sa.Column('has_predictions', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_trip'))
    )
    op.create_table('visit',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('trip_id', sa.String(length=30), nullable=True),
    sa.Column('route_id', sa.String(length=30), nullable=True),
    sa.Column('station_id', sa.String(length=8), nullable=True),
    sa.Column('station_name', sa.String(length=40), nullable=True),
    sa.Column('line_id', sa.String(length=2), nullable=True),
    sa.Column('direction', sa.String(length=1), nullable=True),
    sa.Column('arrival_time', sa.DateTime(), nullable=True),
    sa.Column('pred_arrival_time', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['trip_id'], ['trip.id'], name=op.f('fk_visit_trip_id_trip')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_visit'))
    )
    op.create_table('delay',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.Column('visit_id', sa.Integer(), nullable=True),
    sa.Column('trip_id', sa.String(length=30), nullable=True),
    sa.Column('route_id', sa.String(length=30), nullable=True),
    sa.Column('station_id', sa.String(length=8), nullable=True),
    sa.Column('station_name', sa.String(length=40), nullable=True),
    sa.Column('line_id', sa.String(length=2), nullable=True),
    sa.Column('delay_amount', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['trip_id'], ['trip.id'], name=op.f('fk_delay_trip_id_trip')),
    sa.ForeignKeyConstraint(['visit_id'], ['visit.id'], name=op.f('fk_delay_visit_id_visit')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_delay'))
    )
    with op.batch_alter_table('delay', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_delay_timestamp'), ['timestamp'], unique=False)

    op.bulk_insert(station_table, a)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('delay', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_delay_timestamp'))

    op.drop_table('delay')
    op.drop_table('visit')
    op.drop_table('trip')
    op.drop_table('station_line_pair')
    op.drop_table('station')
    # ### end Alembic commands ###
