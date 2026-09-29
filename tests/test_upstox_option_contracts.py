from unittest.mock import patch

import pytest

from algobot.upstox_option_contracts import OptionContractRef, UpstoxOptionContracts


def test_nearest_strike():
    assert UpstoxOptionContracts.nearest_strike([24400, 24450, 24500], 24476) == 24500


def test_by_strike_filters_side():
    resolver = UpstoxOptionContracts("token")
    contracts = [
        OptionContractRef("NSE_FO|1", "NIFTY 24500 CE", 24500, "CE", "2026-10-01"),
        OptionContractRef("NSE_FO|2", "NIFTY 24500 PE", 24500, "PE", "2026-10-01"),
        OptionContractRef("NSE_FO|3", "NIFTY 24550 CE", 24550, "CE", "2026-10-01"),
    ]
    assert list(resolver.by_strike(contracts, "CE")) == [24500, 24550]


@patch("algobot.upstox_option_contracts.requests.get")
def test_fetch_parses_upstox_contracts(mock_get):
    mock_get.return_value.raise_for_status.return_value = None
    mock_get.return_value.json.return_value = {
        "data": [{
            "instrument_key": "NSE_FO|123",
            "trading_symbol": "NIFTY 24500 CE 01 OCT 26",
            "strike_price": 24500,
            "instrument_type": "CE",
            "expiry": "2026-10-01",
            "lot_size": 65,
            "weekly": True,
        }]
    }
    resolver = UpstoxOptionContracts("token")
    contracts = resolver.fetch("current_week")
    assert contracts[0].instrument_key == "NSE_FO|123"
    mock_get.assert_called_once()


def test_empty_token_rejected():
    with pytest.raises(Exception):
        UpstoxOptionContracts("")
