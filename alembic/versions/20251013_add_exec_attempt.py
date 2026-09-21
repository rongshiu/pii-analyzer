from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_exec_attempt_column"
down_revision = "make_task_id_unique"   # <- link to your previous revision
branch_labels = None
depends_on = None


def upgrade():
    # 1) Add new column with default value = 1
    op.add_column(
        "task_status",
        sa.Column("exec_attempt", sa.Integer(), nullable=False, server_default="1"),
        schema="pii_scanner",
    )

    # 2) Optional: remove the server default for future inserts (so app sets it explicitly)
    op.alter_column(
        "task_status",
        "exec_attempt",
        server_default=None,
        schema="pii_scanner",
    )


def downgrade():
    op.drop_column("task_status", "exec_attempt", schema="pii_scanner")
