from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_detection_specs'
down_revision = 'add_results_and_task_status'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'detection_specifications',
        sa.Column('account_id', sa.Text, nullable=False),
        sa.Column('service', sa.Text, nullable=False),
        sa.Column('data_elements', sa.ARRAY(sa.Text), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('account_id', 'service', name='pk_detection_specifications'),
        schema='pii_scanner'
    )

def downgrade():
    op.drop_table('detection_specifications', schema='pii_scanner')
