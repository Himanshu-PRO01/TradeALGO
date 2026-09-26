"""TradingView widget embeds (Indian market) used by the Trading Desk dashboard.

TradingView doesn't allow framing a personal saved chart (tradingview.com/chart/<id>/) --
that page needs a logged-in session and blocks iframing. Instead we use TradingView's
public, no-login "widget" scripts, each wrapped the same way:

    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script src="https://s3.tradingview.com/external-embedding/embed-widget-<name>.js" async>
        { ...config as JSON... }
      </script>
    </div>

Every function here returns (html, height) ready for `st.iframe(html, height=height)`, and
every config is themed dark to match algobot/palette.py.
"""
from __future__ import annotations

import json

from .palette import BG, BORDER, MUTED, PANEL, TEXT

# A default Indian-market watchlist: benchmark indices + a handful of large caps.
DEFAULT_WATCHLIST = [
    {"name": "NSE:NIFTY", "displayName": "Nifty 50"},
    {"name": "NSE:BANKNIFTY", "displayName": "Bank Nifty"},
    {"name": "BSE:SENSEX", "displayName": "Sensex"},
    {"name": "NSE:FINNIFTY", "displayName": "Fin Nifty"},
    {"name": "NSE:RELIANCE", "displayName": "Reliance"},
    {"name": "NSE:HDFCBANK", "displayName": "HDFC Bank"},
    {"name": "NSE:ICICIBANK", "displayName": "ICICI Bank"},
    {"name": "NSE:TCS", "displayName": "TCS"},
    {"name": "NSE:INFY", "displayName": "Infosys"},
]


def _wrap(widget_src: str, config: dict, height: int, extra_style: str = "") -> str:
    """Common container markup shared by every TradingView widget embed."""
    return f"""
<div class="tradingview-widget-container" style="height:{height}px;min-height:{height}px;width:100%;overflow:hidden;border-radius:8px;border:1px solid {BORDER};background:{PANEL};{extra_style}">
  <div class="tradingview-widget-container__widget" style="height:100%;width:100%"></div>
  <script type="text/javascript"
          src="https://s3.tradingview.com/external-embedding/embed-widget-{widget_src}.js"
          async>
    {json.dumps(config)}
  </script>
</div>
"""


def ticker_tape(symbols: list[dict] | None = None) -> tuple[str, int]:
    """Scrolling strip of Indian index/stock quotes -- goes at the very top of the page."""
    symbols = symbols or DEFAULT_WATCHLIST
    config = {
        "symbols": [{"proName": s["name"], "title": s["displayName"]} for s in symbols],
        "showSymbolLogo": True,
        "isTransparent": False,
        "displayMode": "adaptive",
        "colorTheme": "dark",
        "locale": "en",
    }
    height = 46
    return _wrap("ticker-tape", config, height), height


def watchlist(symbols: list[dict] | None = None, height: int = 460) -> tuple[str, int]:
    """A quotes table (Symbol / Last / Chg / Chg%) -- the 'Daftar Pantau' style sidebar panel."""
    symbols = symbols or DEFAULT_WATCHLIST
    config = {
        "title": "Indian Market",
        "width": "100%",
        "height": "100%",
        "locale": "en",
        "showSymbolLogo": True,
        "colorTheme": "dark",
        "isTransparent": False,
        "symbolsGroups": [
            {"name": "Watchlist", "symbols": [{"name": s["name"], "displayName": s["displayName"]} for s in symbols]}
        ],
    }
    return _wrap("market-quotes", config, height), height


def advanced_chart(symbol: str, interval: str, height: int, studies: list[str] | None = None) -> tuple[str, int]:
    """The main candlestick chart -- what Trading_Desk.py already used, kept as-is here."""
    config = {
        "autosize": False,
        "height": height,
        "symbol": symbol,
        "interval": interval,
        "timezone": "Asia/Kolkata",
        "theme": "dark",
        "style": "1",
        "withdateranges": True,
        "hide_side_toolbar": False,
        "allow_symbol_change": False,
        "save_image": True,
        "hide_volume": False,
        "details": True,
        "calendar": False,
        "support_host": "https://www.tradingview.com",
        "studies": studies or ["MASimple@tv-basicstudies", "RSI@tv-basicstudies"],
    }
    return _wrap("advanced-chart", config, height), height


def symbol_info(symbol: str, height: int = 170) -> tuple[str, int]:
    """Compact price/OHLC header for the selected symbol."""
    config = {
        "symbol": symbol,
        "width": "100%",
        "locale": "en",
        "colorTheme": "dark",
        "isTransparent": False,
    }
    return _wrap("symbol-info", config, height), height


def news_timeline(symbol: str | None = None, height: int = 460) -> tuple[str, int]:
    """News feed -- either for one symbol, or the general Indian-market feed when symbol is None."""
    config = {
        "feedMode": "symbol" if symbol else "market",
        "colorTheme": "dark",
        "isTransparent": False,
        "displayMode": "regular",
        "width": "100%",
        "height": "100%",
        "locale": "en",
    }
    if symbol:
        config["symbol"] = symbol
    else:
        config["market"] = "india"
    return _wrap("timeline", config, height), height
