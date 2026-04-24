"""Idempotent demo data for Toss Payments."""
from decimal import Decimal

from vbwd.extensions import db

from plugins.toss_payments.toss_payments.models import TossPayment


def populate_db() -> None:
    existing = (
        db.session.query(TossPayment).filter_by(order_id="DEMO-TOSS-0001").one_or_none()
    )
    if existing is not None:
        return
    db.session.add(
        TossPayment(
            order_id="DEMO-TOSS-0001",
            payment_key="PAY-DEMO-1",
            method="카드",
            amount=Decimal("10000"),
            currency="KRW",
            status="completed",
            last_provider_status="DONE",
            extra_data={"demo": True},
        )
    )
    db.session.commit()


if __name__ == "__main__":
    populate_db()
