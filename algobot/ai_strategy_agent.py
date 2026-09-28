from __future__ import annotations
import json,re
from dataclasses import dataclass
from typing import Optional
from .ai_provider import AIProvider,ProviderError,get_provider
from . import ai_prompts as p
from .research_context import clean_metrics
UNAVAILABLE_MESSAGE="AI provider not configured. Deterministic strategy tools remain available."
MAX_VALUES_PER_PARAM=12
FIELDS=("name","market","timeframe","direction","entry_level","confirmation","stop_loss","take_profit","skip_trade","position_sizing","notes")
class AgentError(ValueError): pass
@dataclass
class AgentResult:
    available:bool; ok:bool; message:str; data:Optional[dict]=None
def _parse(raw,required):
    raw=raw.strip()
    if raw.startswith("```"):
        lines=raw.splitlines()
        if lines and lines[0].startswith("```"): lines=lines[1:]
        if lines and lines[-1].strip()=="```": lines=lines[:-1]
        raw="\\n".join(lines).strip()
    if raw.lower().startswith("json") and raw[4:].lstrip().startswith("{"): raw=raw[4:].lstrip()
    try: x=json.loads(raw)
    except json.JSONDecodeError as e: raise AgentError(f"The AI response was not valid JSON: {e}")
    if not isinstance(x,dict): raise AgentError("The AI response must be a JSON object.")
    missing=[k for k in required if k not in x]
    if missing: raise AgentError("The AI response is missing required field(s): "+", ".join(missing))
    return x
def _texts(x):
    if isinstance(x,str): return [x]
    if isinstance(x,dict): return [s for k,v in x.items() if k!="cited_metrics" for s in _texts(v)]
    if isinstance(x,list): return [s for v in x for s in _texts(v)]
    return []
def _guard(x):
    for s in _texts(x):
        if re.search(r"\bwill (definitely |certainly |surely )?(work|succeed|be profitable|make money)\b|\bguaranteed\b|\brisk[- ]free\b",s,re.I): raise AgentError("The AI claimed certainty about future results. Rejected.")
def _cite(x,truth):
    for k,v in x.get("cited_metrics",{}).items():
        if k not in truth: raise AgentError(f"The AI cited metric '{k}', which is not part of the real result. Rejected.")
        t=truth[k]
        if isinstance(v,(int,float)) and isinstance(t,(int,float)) and abs(float(v)-float(t))>max(1e-6,abs(float(t))*1e-4): raise AgentError(f"The AI cited {k}={v}, but the real result says {t}. Rejected.")
        if not isinstance(v,(int,float)) and v!=t: raise AgentError(f"The AI cited {k}={v!r}, but the real result says {t!r}. Rejected.")
class StrategyAgent:
    def __init__(self,provider:Optional[AIProvider]=None): self.provider=provider if provider is not None else get_provider()
    @property
    def available(self): return self.provider is not None
    def _call(self,system,payload,required,truth=None,allowed=None):
        if not self.provider: return AgentResult(False,False,UNAVAILABLE_MESSAGE)
        try:
            out=_parse(self.provider.generate(system,json.dumps(payload,sort_keys=True,default=str)),required)
            if allowed:
                unknown=set(out)-set(allowed)
                if unknown: raise AgentError("Unknown response field(s): "+", ".join(sorted(unknown)))
            if truth is not None: _cite(out,truth)
            _guard(out)
            return AgentResult(True,True,"AI response validated.",out)
        except ProviderError as e: return AgentResult(True,False,str(e))
        except AgentError as e: return AgentResult(True,False,str(e))
    def understand_strategy_idea(self,idea,rules=None): return self._call(p.UNDERSTAND,{"idea":idea,"rules":rules or {}},("known","missing","assumed","user_decision_required","clarifying_questions"))
    def identify_missing_rules(self,rules): return self.understand_strategy_idea("Identify missing rules.",rules)
    def propose_strategy_candidates(self,parent_rules,requested_change,past_experiments=None,lessons=None):
        r=self._call(p.CANDIDATE,{"parent_rules":parent_rules,"requested_change":requested_change,"allowed_rule_fields":FIELDS,"past_experiments":past_experiments or [],"previous_research_lessons":lessons or []},("change_summary","reasoning","rules","assumptions"),allowed=("change_summary","reasoning","rules","assumptions"))
        if r.ok and (not isinstance(r.data.get("rules"),dict) or set(r.data["rules"])-set(FIELDS)): return AgentResult(True,False,"The AI proposed an unknown rule field. Rejected.")
        return r
    def explain_backtest(self,metrics,rejections=None,events=None):
        m=clean_metrics(metrics); return self._call(p.EXPLAIN,{"metrics":m,"rejections":rejections or {},"events":events or []},("what_happened","what_worked","what_did_not_work","risks","next_investigations","additional_tests_needed","cited_metrics"),truth=m)
    def propose_experiments(self,rules,past_experiments=None,lessons=None):
        r=self._call(p.EXPERIMENT,{"rules":rules,"past_experiments":past_experiments or [],"previous_research_lessons":lessons or []},("parameter_ranges","reasoning","risks_to_watch"))
        if r.ok:
            for k,v in r.data["parameter_ranges"].items():
                if not isinstance(v,list) or not v or len(v)>MAX_VALUES_PER_PARAM or not all(isinstance(x,(int,float)) and not isinstance(x,bool) for x in v): return AgentResult(True,False,f"Parameter '{k}' is invalid or exceeds the bounded search limit.")
        return r
    def analyze_optimization(self,summary,train_test=None):
        s=clean_metrics(summary); return self._call(p.OPTIMIZE,{"candidate_summary":s,"train_vs_test":train_test or {}},("summary","overfitting_flags","recommendation","cited_metrics"),truth=s)
    def answer_research_question(self,question,facts,history=None,past_experiments=None,learned_lessons=None):
        if not question.strip(): return AgentResult(self.available,False,"Type a question first.")
        f=clean_metrics(facts); return self._call(p.CHAT,{"question":question.strip(),"facts":f,"history":(history or [])[-6:],"past_experiments":past_experiments or [],"previous_research_lessons":learned_lessons or []},("answer","hypotheses","suggested_tests","data_limits","cited_metrics"),truth=f)
    def explain_reality_check(self,facts,checks):
        f=clean_metrics(facts); r=self._call(p.REALITY,{"facts":f,"checks":checks},("explanation","gaps","next_steps","cited_metrics"),truth=f)
        if r.ok and int(f.get("reality.checks_failed",0)) and re.search(r"probably fine|safe to trade|ready to trade|good to go",r.data["explanation"],re.I): return AgentResult(True,False,"The AI attempted to override a failed Reality Check. Rejected.")
        return r
    def analyze_forward_test(self,facts):
        f=clean_metrics(facts); return self._call(p.FORWARD,{"facts":f},("summary","consistency","differences_from_backtest","concerns","cited_metrics"),truth=f)
