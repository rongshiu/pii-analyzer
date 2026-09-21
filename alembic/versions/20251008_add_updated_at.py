from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'add_updated_at_column'
down_revision = 'add_account_id_service_columns'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    # pii_scanner.task_status
    status_columns = [col['name'] for col in inspector.get_columns('task_status', schema='pii_scanner')]
    if 'updated_at' not in status_columns:
        op.add_column(
            'task_status',
            sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.func.now(), nullable=False),
            schema='pii_scanner'
        )

def downgrade():
    op.drop_column('task_status', 'updated_at', schema='pii_scanner')
