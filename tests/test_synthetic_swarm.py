import math

from algobot.config import validate_config
from algobot.synthetic_swarm import PERSONAS, JourneyResult, plan_journey, run_swarm, summarize_website_journeys

def cfg():
    return validate_config({
        "name":"swarm-demo","capital":100000,"data":{"path":""},
        "strategy":{"name":"rules","params":{
            "indicators":[{"name":"ema_fast","type":"ema","period":9},{"name":"ema_slow","type":"ema","period":21}],
            "entry_long":"ema_fast > ema_slow","exit_long":"ema_fast < ema_slow",
            "entry_short":"ema_fast < ema_slow","exit_short":"ema_fast > ema_slow"},
            "quantity":1,"allow_short":True,"stop_loss_pct":1.0,"target_pct":2.0},
        "risk":{"max_daily_loss":3000,"max_trades_per_day":4,"max_position_value":100000,
                "trading_start":"09:20","no_new_entries_after":"14:45","square_off_time":"15:15"},
        "costs":{"brokerage_pct":0.03,"brokerage_cap":20,"stt_sell_pct":0.025,
                 "exchange_txn_pct":0.003,"sebi_fee_pct":0.0001,"stamp_buy_pct":0.003,
                 "gst_pct":18,"slippage_bps":2},
    })

def test_swarm_is_reproducible_and_has_memory():
    a=run_swarm(cfg(),agents=4,rounds=3,days_per_round=3,seed=42)
    b=run_swarm(cfg(),agents=4,rounds=3,days_per_round=3,seed=42)
    assert a==b
    assert len(a.agents)==4 and a.episodes==12
    assert all(len(x.memory.observations)==3 for x in a.agents)

def test_journey_planner_is_allow_listed():
    pages=plan_journey(PERSONAS[-1],budget=20)
    assert pages
    assert all(p in {"5_Backtest.py","6_Reality_check.py","7_Test_lab.py","15_Strategy_Scanner.py",
                     "16_Paper_Trading.py","17_Sandbox_Rehearsal.py","23_Live_Markets.py"} for p in pages)

def test_website_report_surfaces_repeated_failures():
    report=summarize_website_journeys([
        JourneyResult("a","5_Backtest.py",False,"boom",1,1,()),
        JourneyResult("b","5_Backtest.py",False,"boom",1,1,()),
        JourneyResult("c","6_Reality_check.py",True,None,2,0,()),
    ])
    assert math.isclose(report.pass_rate, 100/3, rel_tol=0, abs_tol=1e-12)
    assert report.repeated_failures
