"""Oracle: the toss receipts table is `toss_payments_`-prefixed (sprint S43.5)."""
from plugins.toss_payments.toss_payments.models import TossCashReceipt


def test_toss_cash_receipts_is_plugin_prefixed():
    assert TossCashReceipt.__tablename__ == "toss_payments_cash_receipts"
