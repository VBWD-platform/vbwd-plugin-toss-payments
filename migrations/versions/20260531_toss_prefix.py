"""S43.5 — `toss_cash_receipts` → `toss_payments_cash_receipts`.

The main `toss_payments` table stays (== plugin_id, the primary table); only the
secondary receipts ledger gets the full plugin prefix.

PRESERVES DATA: pure `ALTER TABLE … RENAME` (+ dependent renames), no
drop/recreate. Runs on PROD via `deploy.sh --migrate` in CI: guarded +
idempotent.
"""
import sqlalchemy as sa
from alembic import op

revision = "20260531_toss_prefix"
down_revision = "20260424_1000_toss"
branch_labels = None
depends_on = None

_RENAMES = {"toss_cash_receipts": "toss_payments_cash_receipts"}


def _table_exists(conn, name: str) -> bool:
    return sa.inspect(conn).has_table(name)


def _rename_dependents(conn, table: str, frm: str, to: str) -> None:
    constraints = (
        conn.execute(
            sa.text(
                "SELECT conname FROM pg_constraint WHERE conrelid = to_regclass(:t)"
            ),
            {"t": table},
        )
        .scalars()
        .all()
    )
    for name in constraints:
        if frm in name:
            op.execute(
                f'ALTER TABLE "{table}" RENAME CONSTRAINT "{name}" '
                f'TO "{name.replace(frm, to, 1)}"'
            )
    plain_indexes = (
        conn.execute(
            sa.text(
                "SELECT i.relname FROM pg_index x "
                "JOIN pg_class i ON i.oid = x.indexrelid "
                "WHERE x.indrelid = to_regclass(:t) "
                "AND x.indexrelid NOT IN "
                "(SELECT conindid FROM pg_constraint WHERE conindid <> 0)"
            ),
            {"t": table},
        )
        .scalars()
        .all()
    )
    for name in plain_indexes:
        if frm in name:
            op.execute(f'ALTER INDEX "{name}" RENAME TO "{name.replace(frm, to, 1)}"')


def upgrade() -> None:
    conn = op.get_bind()
    for old, new in _RENAMES.items():
        if _table_exists(conn, old) and not _table_exists(conn, new):
            op.rename_table(old, new)
            _rename_dependents(conn, new, old, new)


def downgrade() -> None:
    conn = op.get_bind()
    for old, new in _RENAMES.items():
        if _table_exists(conn, new) and not _table_exists(conn, old):
            _rename_dependents(conn, new, new, old)
            op.rename_table(new, old)
