"""Shared fixtures for Toss Payments plugin tests."""
import pytest

from vbwd.sdk.interface import SDKConfig


@pytest.fixture
def toss_config() -> dict:
    return {
        "sandbox": True,
        "test_client_key": "test_ck_abc",
        "test_secret_key": "test_sk_abc",
        "test_api_url": "https://api.tosspayments.com/v1",
        "enabled_methods": ["CARD", "KAKAOPAY"],
        "currency": "KRW",
    }


@pytest.fixture
def sdk_config(toss_config) -> SDKConfig:
    return SDKConfig(
        api_key=toss_config["test_secret_key"],
        sandbox=True,
    )


@pytest.fixture
def adapter(sdk_config, toss_config):
    from plugins.toss_payments.toss_payments.sdk_adapter import (
        TossPaymentsSDKAdapter,
    )

    return TossPaymentsSDKAdapter(
        config=sdk_config,
        client_key=toss_config["test_client_key"],
        api_url=toss_config["test_api_url"],
    )
