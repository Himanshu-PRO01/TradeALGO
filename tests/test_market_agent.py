import pandas as pd
from algobot.market_agent import SourceResult, candidate_strategies, merge_sources

def test_candidate_strategies_validate():
    configs=candidate_strategies()
    assert len(configs)>=3
    assert all(c["strategy"]["name"]=="rules" for c in configs)

def test_merge_sources_uses_successful_source():
    idx=pd.date_range("2026-01-01",periods=3,freq="D")
    source=SourceResult("test","price",True,3,data=pd.DataFrame({
        "open":[1,2,3],"high":[2,3,4],"low":[0,1,2],"close":[1.5,2.5,3.5],"volume":[10,20,30]},index=idx))
    out=merge_sources([SourceResult("bad","price",False),source])
    assert len(out)==3
