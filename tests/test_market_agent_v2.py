import pandas as pd
from algobot.market_agent_v2 import variants, source_check

def test_variant_space_is_bounded_and_transparent():
    configs=variants()
    assert len(configs)==23
    assert len({c["name"] for c in configs})==len(configs)
    assert all(c["strategy"]["name"]=="rules" for c in configs)

def test_source_check_reports_limited_without_two_price_sources():
    df=pd.DataFrame({"close":[100,101,102]},index=pd.date_range("2026-01-01",periods=3))
    class S: pass
    s=S(); s.ok=True; s.kind="price"; s.data=df
    result=source_check([s])
    assert result["status"]=="LIMITED"

def test_source_check_compares_overlapping_prices():
    idx=pd.date_range("2026-01-01",periods=3)
    class S: pass
    a=S(); a.ok=True; a.kind="price"; a.data=pd.DataFrame({"close":[100,101,102]},index=idx)
    b=S(); b.ok=True; b.kind="price"; b.data=pd.DataFrame({"close":[100,101.01,102]},index=idx)
    result=source_check([a,b])
    assert result["overlap"]==3
    assert result["status"]=="PASS"
