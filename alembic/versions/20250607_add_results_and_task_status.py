from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'add_results_and_task_status'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # Create schema if not exists
    op.execute("CREATE SCHEMA IF NOT EXISTS pii_scanner")

    # Re-initialize inspector **after** schema is created
    inspector = inspect(bind)

    # Create results table if not exists
    if 'results' not in inspector.get_table_names(schema='pii_scanner'):
        op.create_table(
            'results',
            sa.Column('task_id', sa.Text),
            sa.Column('connection_id', sa.Text),
            sa.Column('file_type', sa.Text),
            sa.Column('file_path', sa.Text),
            sa.Column('chunk_index', sa.Integer),
            sa.Column('column_name', sa.Text),
            sa.Column('page_number', sa.Integer),
            sa.Column('data_element', sa.Text),
            sa.Column('start', sa.BigInteger),
            sa.Column('end', sa.BigInteger),
            sa.Column('pii_text', sa.Text),
            sa.Column('score', sa.Float),
            sa.Column('error', sa.Text),
            sa.Column('created_at', sa.TIMESTAMP),
            schema='pii_scanner'
        )

    # Re-inspect now that table might exist
    inspector = inspect(bind)

    indexes = [ix['name'] for ix in inspector.get_indexes('results', schema='pii_scanner')]
    if 'idx_results_task_id' not in indexes:
        op.create_index('idx_results_task_id', 'results', ['task_id'], schema='pii_scanner')

    if 'task_status' not in inspector.get_table_names(schema='pii_scanner'):
        op.create_table(
            'task_status',
            sa.Column('task_id', sa.Text),
            sa.Column('file_path', sa.Text),
            sa.Column('file_type', sa.Text),
            sa.Column('start_time', sa.TIMESTAMP),
            sa.Column('end_time', sa.TIMESTAMP),
            sa.Column('duration_seconds', sa.Float),
            sa.Column('status', sa.Text),
            sa.Column('error_message', sa.Text),
            sa.Column('completion_api_status', sa.Text),
            sa.Column('created_at', sa.TIMESTAMP),
            schema='pii_scanner'
        )

    inspector = inspect(bind)
    indexes = [ix['name'] for ix in inspector.get_indexes('task_status', schema='pii_scanner')]
    if 'idx_task_status_task_id' not in indexes:
        op.create_index('idx_task_status_task_id', 'task_status', ['task_id'], schema='pii_scanner')



def downgrade():
    op.drop_index('idx_task_status_task_id', table_name='task_status', schema='pii_scanner')
    op.drop_table('task_status', schema='pii_scanner')

    op.drop_index('idx_results_task_id', table_name='results', schema='pii_scanner')
    op.drop_table('results', schema='pii_scanner')

    op.execute("DROP SCHEMA IF EXISTS pii_scanner CASCADE")
