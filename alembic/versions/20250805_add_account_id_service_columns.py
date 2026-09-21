from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'add_account_id_service_columns'
down_revision = 'add_detection_specs'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    # Add columns to pii_scanner.results if they don't exist
    results_columns = [col['name'] for col in inspector.get_columns('results', schema='pii_scanner')]
    if 'account_id' not in results_columns:
        op.add_column('results', sa.Column('account_id', sa.Text), schema='pii_scanner')
    if 'service' not in results_columns:
        op.add_column('results', sa.Column('service', sa.Text), schema='pii_scanner')

    # Add columns to pii_scanner.task_status if they don't exist
    status_columns = [col['name'] for col in inspector.get_columns('task_status', schema='pii_scanner')]
    if 'account_id' not in status_columns:
        op.add_column('task_status', sa.Column('account_id', sa.Text), schema='pii_scanner')
    if 'service' not in status_columns:
        op.add_column('task_status', sa.Column('service', sa.Text), schema='pii_scanner')

def downgrade():
    op.drop_column('results', 'account_id', schema='pii_scanner')
    op.drop_column('results', 'service', schema='pii_scanner')

    op.drop_column('task_status', 'account_id', schema='pii_scanner')
    op.drop_column('task_status', 'service', schema='pii_scanner')
