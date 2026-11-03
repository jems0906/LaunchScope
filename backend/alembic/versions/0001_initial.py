"""Create the versioned measurement and decision records."""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "initiatives",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("business_question", sa.String(length=1000), nullable=False),
        sa.Column("proposed_decision", sa.String(length=500), nullable=False),
        sa.Column("alternatives", sa.JSON(), nullable=False),
        sa.Column("stakeholder_role", sa.String(length=160), nullable=False),
        sa.Column("eligible_population", sa.String(length=1000), nullable=False),
        sa.Column("timing", sa.String(length=500), nullable=False),
        sa.Column("wrong_decision_consequences", sa.String(length=2000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "measurement_plans",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("initiative_id", sa.String(length=36), sa.ForeignKey("initiatives.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("specification", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("frozen_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("initiative_id", "version", name="uq_plan_initiative_version"),
    )
    op.create_table(
        "design_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("plan_id", sa.String(length=36), sa.ForeignKey("measurement_plans.id"), nullable=False),
        sa.Column("algorithm_version", sa.String(length=100), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("inputs", sa.JSON(), nullable=False),
        sa.Column("results", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "simulation_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("plan_id", sa.String(length=36), sa.ForeignKey("measurement_plans.id"), nullable=False),
        sa.Column("scenario", sa.String(length=32), nullable=False),
        sa.Column("generator_version", sa.String(length=100), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("dataset_manifest", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "analysis_results",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("simulation_run_id", sa.String(length=36), sa.ForeignKey("simulation_runs.id"), unique=True, nullable=False),
        sa.Column("analysis_version", sa.String(length=100), nullable=False),
        sa.Column("results", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "decision_memos",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("plan_id", sa.String(length=36), sa.ForeignKey("measurement_plans.id"), nullable=False),
        sa.Column("analysis_result_id", sa.String(length=36), sa.ForeignKey("analysis_results.id"), nullable=False),
        sa.Column("recommendation", sa.String(length=64), nullable=False),
        sa.Column("rationale", sa.String(length=4000), nullable=False),
        sa.Column("limitations", sa.JSON(), nullable=False),
        sa.Column("evidence_references", sa.JSON(), nullable=False),
        sa.Column("review_state", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("decision_memos")
    op.drop_table("analysis_results")
    op.drop_table("simulation_runs")
    op.drop_table("design_runs")
    op.drop_table("measurement_plans")
    op.drop_table("initiatives")