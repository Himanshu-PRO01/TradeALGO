from unittest.mock import patch

from algobot.upstox_bod_instruments import UpstoxBODResolver


def test_expiry_normalizes_epoch_milliseconds():
    assert UpstoxBODResolver._expiry(1706207399000) == "2024-01-25"


def test_find_options_filters_nifty_contracts():
    rows = [
        {
            "segment": "NSE_FO",
            "underlying_symbol": "NIFTY",
            "instrument_type": "CE",
            "expiry": "2026-10-01",
            "instrument_key": "NSE_FO|123",
            "trading_symbol": "NIFTY 25000 CE 01 OCT 26",
            "strike_price": 25000,
            "lot_size": 65,
        },
        {
            "segment": "NSE_FO",
            "underlying_symbol": "BANKNIFTY",
            "instrument_type": "CE",
            "expiry": "2026-10-01",
            "instrument_key": "NSE_FO|456",
            "trading_symbol": "BANKNIFTY 58000 CE 01 OCT 26",
            "strike_price": 58000,
            "lot_size": 35,
        },
    ]
    with patch.object(UpstoxBODResolver, "_download", return_value=rows):
        result = UpstoxBODResolver().find_options("CE", "2026-10-01")
    assert len(result) == 1
    assert result[0].instrument_key == "NSE_FO|123"
