from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_sheet_name_to_results"
down_revision = "add_exec_attempt_column"  # previous migration id
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "results",
        sa.Column("sheet_name", sa.String(length=255), nullable=True),
        schema="pii_scanner",
    )


def downgrade():
    op.drop_column("results", "sheet_name", schema="pii_scanner")
