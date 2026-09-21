from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_results_index"  # pick any unique id / hash
down_revision = "add_sheet_name_to_results"        # <-- your latest migration id
branch_labels = None
depends_on = None


def upgrade():
    # Composite index to optimize:
    #   WHERE s.task_id = :task_id
    #   JOIN r ON r.task_id = s.task_id
    #   ORDER BY r.created_at DESC, r.start
    op.create_index(
        "idx_results_task_created_start",
        "results",
        ["task_id", "created_at", "start"],
        schema="pii_scanner",
    )


def downgrade():
    op.drop_index(
        "idx_results_task_created_start",
        table_name="results",
        schema="pii_scanner",
    )
