"""Market Research Agent v2: multi-source research, parameter search and walk-forward validation."""
from __future__ import annotations
import datetime as dt, itertools, os
from dataclasses import dataclass
from typing import Optional
import numpy as np, pandas as pd, requests
from .market_agent import (
    SourceResult, NewsItem, _base_config, fetch_yfinance, fetch_news,
    merge_sources, validate_config as _unused,
)
from .audit import run_audit
from .engine import run_backtest
from .strategy import build_strategy

@dataclass
class WFWindow:
    train_start:str; train_end:str; test_start:str; test_end:str
    selected:str; train_score:float; oos_return:float; oos_pnl:float
    oos_trades:int; oos_dd:float

@dataclass
class ResearchV2:
    candidates:list; selected:object|None; windows:list[WFWindow]
    source_validation:dict; created_at:str

def variants():
    out=[]
    for f,s,r,t in itertools.product((8,9,12),(18,21,26),(12,14,16),(48,50,52)):
        if f>=s: continue
        out.append(_base_config(
            f"EMA {f}/{s} RSI{r}@{t}",
            [{"name":"ema_fast","type":"ema","period":f},{"name":"ema_slow","type":"ema","period":s},{"name":"rsi_14","type":"rsi","period":r}],
            f"ema_fast > ema_slow and ema_fast_prev <= ema_slow_prev and rsi_14 > {t}","ema_fast < ema_slow",
            f"ema_fast < ema_slow and ema_fast_prev >= ema_slow_prev and rsi_14 < {100-t}","ema_fast > ema_slow"))
    for n in (15,20,25,30):
        out.append(_base_config(f"Breakout {n}",
            [{"name":"high_n","type":"highest","period":n},{"name":"low_n","type":"lowest","period":n}],
            "close > high_n and close_prev <= high_n_prev","close < low_n",
            "close < low_n and close_prev >= low_n_prev","close > high_n"))
    for low,ex,ep in itertools.product((25,30,35),(50,55,60),(40,50,60)):
        out.append(_base_config(f"RSI MR {low}/{ex} EMA{ep}",
            [{"name":"rsi_14","type":"rsi","period":14},{"name":"ema_filter","type":"ema","period":ep}],
            f"rsi_14 < {low} and close > ema_filter",f"rsi_14 > {ex}",
            f"rsi_14 > {100-low} and close < ema_filter",f"rsi_14 < {100-ex}"))
    return out

def score(m):
    t=int(m.get("trades") or 0); ret=float(m.get("return_pct") or 0)
    dd=abs(float(m.get("max_drawdown_pct") or 0)); sh=float(m.get("sharpe_daily") or 0)
    pf=m.get("profit_factor"); pf=0 if pf is None or not np.isfinite(pf) else min(float(pf),4)
    return ret+3*pf+2*sh-.55*dd-(25 if t<30 else 8 if t<100 else 0)

def wf(df, cs, train=.55, test=.15, step=.15):
    n=len(df); tr=max(80,int(n*train)); te=max(30,int(n*test)); st=max(te,int(n*step))
    windows=[]; by={}
    for start in range(0,max(0,n-tr-te+1),st):
        a=df.iloc[start:start+tr]; b=df.iloc[start+tr:start+tr+te]; ranked=[]
        for c in cs:
            try:
                m=run_backtest(a,c,build_strategy(c)).metrics
                if int(m.get("trades") or 0)>=5: ranked.append((score(m),c))
            except Exception: pass
        if not ranked: continue
        ranked.sort(key=lambda x:x[0],reverse=True); s,c=ranked[0]
        try: m=run_backtest(b,c,build_strategy(c)).metrics
        except Exception: continue
        by.setdefault(c["name"],[]).append(m)
        windows.append(WFWindow(str(a.index[0]),str(a.index[-1]),str(b.index[0]),str(b.index[-1]),c["name"],s,
            float(m.get("return_pct") or 0),float(m.get("net_pnl") or 0),int(m.get("trades") or 0),float(m.get("max_drawdown_pct") or 0)))
    return windows,by

def source_check(sources):
    p=[s for s in sources if s.ok and s.kind=="price" and s.data is not None]
    if len(p)<2:return {"status":"LIMITED","overlap":0,"mean_diff":None,"max_diff":None}
    base=p[0].data["close"].rename("a"); vals=[]; overlap=0
    for s in p[1:]:
        x=pd.concat([base,s.data["close"].rename("b")],axis=1,join="inner").dropna()
        if len(x):
            vals.extend((((x.b-x.a)/x.a).abs()*100).tolist()); overlap+=len(x)
    if not vals:return {"status":"LIMITED","overlap":0,"mean_diff":None,"max_diff":None}
    mean,maxd=float(np.mean(vals)),float(np.max(vals))
    return {"status":"PASS" if mean<=.25 and maxd<=2 else "WARN","overlap":overlap,"mean_diff":mean,"max_diff":maxd}

def run_v2(df,symbol,period="custom",audit=True):
    cs=variants(); windows,by=wf(df,cs); rows=[]
    for c in cs:
        try:
            m=run_backtest(df,c,build_strategy(c)).metrics
            o=by.get(c["name"]); om=None
            if o: om={"return_pct":float(np.mean([x.get("return_pct",0) for x in o])),
                      "net_pnl":float(sum(x.get("net_pnl",0) for x in o)),
                      "trades":int(sum(x.get("trades",0) for x in o)),
                      "max_drawdown_pct":float(min(x.get("max_drawdown_pct",0) for x in o))}
            a=run_audit(df,c,trials=len(cs),n_random=30,n_mc=300) if audit and int(m.get("trades") or 0)>=30 else None
            s=score(m)+(1.5*om["return_pct"]-.4*abs(om["max_drawdown_pct"]) if om else -10)
            if a:s-=25*sum(x.status=="FAIL" for x in a.checks)+6*sum(x.status=="WARN" for x in a.checks)
            rows.append({"name":c["name"],"config":c,"metrics":m,"oos":om,"audit":a,"score":s})
        except Exception as e: rows.append({"name":c["name"],"config":c,"metrics":{"trades":0,"return_pct":0},"oos":None,"audit":None,"score":-9999,"error":str(e)})
    rows.sort(key=lambda x:x["score"],reverse=True)
    return ResearchV2(rows,rows[0] if rows else None,windows,{},dt.datetime.now(dt.timezone.utc).isoformat())
