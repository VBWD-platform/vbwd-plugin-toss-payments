"""Create toss_payments + toss_cash_receipts tables.

Revision ID: 20260424_1000_toss
Revises: 20260422_1400_mp
Create Date: 2026-04-24

Sprint 34 — Toss Payments Korea.
"""
from alembic import op
import sqlalchemy as sa


revision = "20260424_1000_toss"
down_revision = "20260422_1400_mp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "toss_payments",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("order_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("payment_key", sa.String(length=128), nullable=True),
        sa.Column("method", sa.String(length=32), nullable=True),
        sa.Column("amount", sa.Numeric(14, 0), nullable=False),
        sa.Column(
            "currency", sa.String(length=3), nullable=False, server_default="KRW"
        ),
        sa.Column(
            "status", sa.String(length=24), nullable=False, server_default="pending"
        ),
        sa.Column("last_provider_status", sa.String(length=32), nullable=True),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_toss_payments_payment_key",
        "toss_payments",
        ["payment_key"],
        unique=False,
    )

    op.create_table(
        "toss_cash_receipts",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("receipt_id", sa.String(length=128), nullable=True),
        sa.Column("payment_key", sa.String(length=128), nullable=False),
        sa.Column("identifier_type", sa.String(length=16), nullable=False),
        sa.Column("identifier_hash", sa.String(length=64), nullable=False),
        sa.Column("receipt_type", sa.String(length=16), nullable=False),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="issued"
        ),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_toss_cash_receipts_receipt_id",
        "toss_cash_receipts",
        ["receipt_id"],
        unique=False,
    )
    op.create_index(
        "ix_toss_cash_receipts_payment_key",
        "toss_cash_receipts",
        ["payment_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_toss_cash_receipts_payment_key", table_name="toss_cash_receipts")
    op.drop_index("ix_toss_cash_receipts_receipt_id", table_name="toss_cash_receipts")
    op.drop_table("toss_cash_receipts")
    op.drop_index("ix_toss_payments_payment_key", table_name="toss_payments")
    op.drop_table("toss_payments")
