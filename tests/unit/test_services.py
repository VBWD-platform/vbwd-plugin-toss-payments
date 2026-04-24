"""Unit tests for Toss services + cash-receipt PII hashing."""
import hashlib
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from plugins.toss_payments.toss_payments.services import (
    TossCashReceiptService,
    TossPaymentService,
    TossWebhookHandler,
    hash_identifier,
    map_toss_status,
)


class TestStatusMapping:
    @pytest.mark.parametrize(
        "provider,expected",
        [
            ("DONE", "completed"),
            ("done", "completed"),
            ("CANCELED", "cancelled"),
            ("PARTIAL_CANCELED", "refunded"),
            ("ABORTED", "failed"),
            ("EXPIRED", "failed"),
            ("READY", "pending"),
            ("IN_PROGRESS", "processing"),
            ("WAITING_FOR_DEPOSIT", "pending"),
            ("", "failed"),
            ("UNKNOWN", "failed"),
        ],
    )
    def test_maps(self, provider, expected):
        assert map_toss_status(provider) == expected


class TestHashIdentifier:
    def test_phone_hash_deterministic(self):
        h1 = hash_identifier("01012345678")
        h2 = hash_identifier("01012345678")
        assert h1 == h2
        assert h1 == hashlib.sha256(b"01012345678").hexdigest()

    def test_different_inputs_different_hashes(self):
        assert hash_identifier("01012345678") != hash_identifier("01087654321")


class TestPaymentService:
    def test_record_payment_confirmed(self):
        session = MagicMock()
        session.query.return_value.filter_by.return_value.one_or_none.return_value = None
        service = TossPaymentService(session=session)

        payment = service.record_payment_confirmed(
            order_id="INV-1",
            payment_key="PAY-1",
            method="카드",
            amount=Decimal("10000"),
            provider_status="DONE",
        )
        assert payment.status == "completed"
        assert payment.last_provider_status == "DONE"
        assert payment.payment_key == "PAY-1"
        session.commit.assert_called_once()

    def test_apply_provider_update_idempotent(self):
        existing = MagicMock()
        existing.status = "completed"
        existing.last_provider_status = "DONE"
        session = MagicMock()
        session.query.return_value.filter_by.return_value.one_or_none.return_value = existing

        service = TossPaymentService(session=session)
        service.apply_provider_update("INV-1", {"status": "DONE"})
        session.commit.assert_not_called()


class TestCashReceiptService:
    def test_identifier_stored_as_hash_not_plaintext(self):
        session = MagicMock()
        service = TossCashReceiptService(session=session)
        receipt = service.record_receipt(
            payment_key="PAY-1",
            identifier_type="phone",
            identifier="01012345678",
            receipt_type="소득공제",
        )
        assert receipt.identifier_hash == hash_identifier("01012345678")
        assert "01012345678" not in receipt.identifier_hash

    def test_rejects_invalid_identifier_type(self):
        service = TossCashReceiptService(session=MagicMock())
        with pytest.raises(ValueError, match="identifier_type"):
            service.record_receipt(
                payment_key="PAY-1",
                identifier_type="email",
                identifier="x@y.com",
                receipt_type="소득공제",
            )

    def test_rejects_invalid_receipt_type(self):
        service = TossCashReceiptService(session=MagicMock())
        with pytest.raises(ValueError, match="receipt_type"):
            service.record_receipt(
                payment_key="PAY-1",
                identifier_type="phone",
                identifier="01012345678",
                receipt_type="UNKNOWN",
            )


class TestWebhookHandler:
    def test_rejects_missing_order_id(self):
        handler = TossWebhookHandler(service=MagicMock())
        with pytest.raises(ValueError, match="orderId"):
            handler.handle({"status": "DONE"})

    def test_accepts_orderId_camelCase(self):
        svc = MagicMock()
        TossWebhookHandler(service=svc).handle(
            {"orderId": "INV-1", "status": "DONE"}
        )
        svc.apply_provider_update.assert_called_once()

    def test_accepts_snake_case_alias(self):
        svc = MagicMock()
        TossWebhookHandler(service=svc).handle(
            {"order_id": "INV-1", "status": "DONE"}
        )
        svc.apply_provider_update.assert_called_once()
