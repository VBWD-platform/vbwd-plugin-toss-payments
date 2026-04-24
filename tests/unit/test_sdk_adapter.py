"""Unit tests for TossPaymentsSDKAdapter (TDD-first)."""
import base64
from decimal import Decimal
from unittest.mock import MagicMock


class TestAuthHeaders:
    def test_basic_auth_uses_secret_with_trailing_colon(self, adapter):
        headers = adapter._auth_headers()
        token = headers["Authorization"].split(" ")[1]
        decoded = base64.b64decode(token).decode()
        assert decoded == "test_sk_abc:"

    def test_content_type_json(self, adapter):
        assert adapter._auth_headers()["Content-Type"] == "application/json"


class TestConfirmPayment:
    def test_success(self, adapter, mocker):
        fake = MagicMock()
        fake.status_code = 200
        fake.json.return_value = {
            "paymentKey": "PAY-1",
            "orderId": "INV-1",
            "totalAmount": 10000,
            "method": "카드",
            "status": "DONE",
        }
        mocker.patch(
            "plugins.toss_payments.toss_payments.sdk_adapter.requests.post",
            return_value=fake,
        )

        resp = adapter.confirm_payment(
            payment_key="PAY-1", order_id="INV-1", amount=10000
        )
        assert resp.success is True
        assert resp.data["method"] == "카드"

    def test_4xx_returns_provider_code(self, adapter, mocker):
        fake = MagicMock()
        fake.status_code = 400
        fake.json.return_value = {
            "code": "INVALID_SECRET_KEY",
            "message": "시크릿 키가 올바르지 않습니다",
        }
        mocker.patch(
            "plugins.toss_payments.toss_payments.sdk_adapter.requests.post",
            return_value=fake,
        )
        resp = adapter.confirm_payment("PAY-1", "INV-1", 10000)
        assert resp.success is False
        assert resp.error_code == "INVALID_SECRET_KEY"

    def test_network_error(self, adapter, mocker):
        import requests

        mocker.patch(
            "plugins.toss_payments.toss_payments.sdk_adapter.requests.post",
            side_effect=requests.ConnectionError("down"),
        )
        resp = adapter.confirm_payment("PAY-1", "INV-1", 10000)
        assert resp.success is False
        assert "network" in (resp.error or "")


class TestCancelPayment:
    def test_partial_cancel_sends_amount(self, adapter, mocker):
        captured = {}

        def _fake_post(url, json, headers, timeout):
            captured["json"] = json
            fake = MagicMock()
            fake.status_code = 200
            fake.json.return_value = {"status": "PARTIAL_CANCELED"}
            return fake

        mocker.patch(
            "plugins.toss_payments.toss_payments.sdk_adapter.requests.post",
            side_effect=_fake_post,
        )
        adapter.cancel_payment("PAY-1", amount=Decimal("5000"))
        assert captured["json"]["cancelAmount"] == 5000
        assert "cancelReason" in captured["json"]

    def test_full_cancel_omits_amount(self, adapter, mocker):
        captured = {}

        def _fake_post(url, json, headers, timeout):
            captured["json"] = json
            fake = MagicMock()
            fake.status_code = 200
            fake.json.return_value = {"status": "CANCELED"}
            return fake

        mocker.patch(
            "plugins.toss_payments.toss_payments.sdk_adapter.requests.post",
            side_effect=_fake_post,
        )
        adapter.cancel_payment("PAY-1")
        assert "cancelAmount" not in captured["json"]


class TestCashReceipt:
    def test_issue_sends_identifier(self, adapter, mocker):
        captured = {}

        def _fake_post(url, json, headers, timeout):
            captured["json"] = json
            fake = MagicMock()
            fake.status_code = 200
            fake.json.return_value = {"receiptKey": "RK-1"}
            return fake

        mocker.patch(
            "plugins.toss_payments.toss_payments.sdk_adapter.requests.post",
            side_effect=_fake_post,
        )
        adapter.issue_cash_receipt(
            payment_key="PAY-1",
            identifier_type="phone",
            identifier="01012345678",
            receipt_type="소득공제",
        )
        assert captured["json"]["customerIdentityNumber"] == "01012345678"
        assert captured["json"]["type"] == "소득공제"


class TestVerifyWebhook:
    def test_accepts_valid(self, adapter):
        import hashlib
        import hmac

        body = b'{"orderId":"INV-1"}'
        sig = hmac.new(b"test_sk_abc", body, hashlib.sha256).hexdigest()
        assert adapter.verify_webhook(body, sig) is True

    def test_rejects_wrong(self, adapter):
        assert adapter.verify_webhook(b"body", "dead") is False

    def test_rejects_empty(self, adapter):
        assert adapter.verify_webhook(b"body", "") is False
