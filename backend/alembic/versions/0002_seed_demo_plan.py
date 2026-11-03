"""Seed the immutable fictional game-discovery demonstration plan."""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0002_seed_demo_plan"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    frozen_at = datetime.now(timezone.utc)
    op.bulk_insert(
        sa.table(
            "initiatives",
            sa.column("id", sa.String),
            sa.column("title", sa.String),
            sa.column("business_question", sa.String),
            sa.column("proposed_decision", sa.String),
            sa.column("alternatives", sa.JSON),
            sa.column("stakeholder_role", sa.String),
            sa.column("eligible_population", sa.String),
            sa.column("timing", sa.String),
            sa.column("wrong_decision_consequences", sa.String),
            sa.column("created_at", sa.DateTime(timezone=True)),
        ),
        [
            {
                "id": "demo-game-discovery",
                "title": "Fictional game-discovery module offer",
                "business_question": "Did offering the fictional module change qualified game-session behavior?",
                "proposed_decision": "Continue, redesign, collect more evidence, or stop",
                "alternatives": ["Existing discovery only", "Redesign and retest", "No rollout"],
                "stakeholder_role": "Content & Games Product Lead",
                "eligible_population": "Households meeting eligibility rules recorded before assignment",
                "timing": "One fixed 28-day observation window after household assignment",
                "wrong_decision_consequences": "A false positive may worsen household experience or playback quality; a false negative may delay a useful discovery experience.",
                "created_at": frozen_at,
            }
        ],
    )
    op.bulk_insert(
        sa.table(
            "measurement_plans",
            sa.column("id", sa.String),
            sa.column("initiative_id", sa.String),
            sa.column("version", sa.Integer),
            sa.column("status", sa.String),
            sa.column("specification", sa.JSON),
            sa.column("created_at", sa.DateTime(timezone=True)),
            sa.column("frozen_at", sa.DateTime(timezone=True)),
        ),
        [
            {
                "id": "demo-game-discovery-v1",
                "initiative_id": "demo-game-discovery",
                "version": 1,
                "status": "frozen",
                "specification": {
                    "question": "Among eligible households, what is the effect of offering the module on qualified game sessions in 28 days?",
                    "estimand": "Household intention-to-treat difference in qualified-session rates, treatment minus control",
                    "population": "All households meeting eligibility rules before assignment",
                    "eligibility_fixed_before_assignment": True,
                    "randomization_unit": "household",
                    "allocation_treatment": 0.5,
                    "observation_window_days": 28,
                    "primary_outcome": "Proportion of assigned households with at least one qualified game session",
                    "practical_threshold": 0.01,
                    "diagnostics": ["Exposure / assigned households", "Module interaction / assigned households", "Repeat engagement / observed households", "Outcome completeness / assigned households"],
                    "guardrails": ["Playback-quality failure / eligible playback sessions", "Stability event / assigned households"],
                    "baseline_rate": 0.1,
                    "target_effect": 0.01,
                    "alpha": 0.05,
                    "desired_power": 0.8,
                    "attrition": 0.05,
                    "missingness_rule": "Unknown outcomes stay missing; report completeness by assignment arm and extreme bounds.",
                    "spillover_assumption": "Assume no material interference across households; investigate shared accounts and cross-household contamination.",
                    "fixed_horizon_no_early_stop": True,
                },
                "created_at": frozen_at,
                "frozen_at": frozen_at,
            }
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM measurement_plans WHERE id = 'demo-game-discovery-v1'")
    op.execute("DELETE FROM initiatives WHERE id = 'demo-game-discovery'")