"""Plugin tests — KRW-only guard + Liskov initialize."""
from decimal import Decimal
from uuid import uuid4

from vbwd.plugins.base import PluginStatus

from plugins.toss_payments import TossPaymentsPlugin, DEFAULT_CONFIG


class TestTossPaymentsPlugin:
    def test_metadata(self):
        plugin = TossPaymentsPlugin()
        assert plugin.metadata.name == "toss_payments"

    def test_initialize_merges(self):
        plugin = TossPaymentsPlugin()
        plugin.initialize({"test_client_key": "test_ck_x"})
        assert plugin.status == PluginStatus.INITIALIZED
        assert plugin._config["test_client_key"] == "test_ck_x"
        assert plugin._config["currency"] == DEFAULT_CONFIG["currency"]

    def test_rejects_non_krw(self):
        plugin = TossPaymentsPlugin()
        plugin.initialize({})
        result = plugin.create_payment_intent(
            amount=Decimal("100"),
            currency="USD",
            subscription_id=uuid4(),
            user_id=uuid4(),
        )
        assert result.success is False
        assert "KRW" in (result.error_message or "")

    def test_rejects_non_integer_krw(self):
        plugin = TossPaymentsPlugin()
        plugin.initialize({})
        result = plugin.create_payment_intent(
            amount=Decimal("100.50"),
            currency="KRW",
            subscription_id=uuid4(),
            user_id=uuid4(),
        )
        assert result.success is False
        assert "integer" in (result.error_message or "")
