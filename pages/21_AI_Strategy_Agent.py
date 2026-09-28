import os
import streamlit as st
from algobot import ui
from algobot.ai_strategy_agent import StrategyAgent
from algobot.research_context import backtest_facts, reality_check_facts, reality_check_details
from algobot.strategy_versions import StrategyVersionStore

ui.setup("AI Strategy Agent","🤖")
ui.header("AI Strategy Agent","AI-assisted research without direct trading execution.",mode="research:AI")

rules=st.session_state.get("strategy_rules")
if not rules:
    st.info("Create a strategy in Strategy Builder first.")
    st.page_link("pages/10_Strategy_Builder.py",label="Strategy Builder",icon="🧠")
    ui.workflow_nav("ai")
    ui.footer_note()
    st.stop()

strategy_id="demo"
path=os.environ.get("ALGOBOT_STRATEGY_VERSIONS","data/strategy_versions.sqlite")
os.makedirs(os.path.dirname(path) or ".",exist_ok=True)
store=StrategyVersionStore(path)
if not store.list_versions(strategy_id):
    store.create_original(strategy_id,rules)

agent=StrategyAgent()
if not agent.available:
    st.warning("AI provider not configured. Deterministic strategy tools remain available.")

st.subheader("1. Strategy understanding")
idea=st.text_area("Describe the strategy or question for AI",key="ai_idea")
if st.button("Analyze strategy",key="ai_analyze_idea") and idea.strip():
    r=agent.understand_strategy_idea(idea,rules)
    if r.ok: st.session_state["ai_idea_result"]=r.data
    else: st.warning(r.message)
if st.session_state.get("ai_idea_result"): st.json(st.session_state["ai_idea_result"])

st.divider()
st.subheader("2. AI Strategy Rewrite — explicit opt-in")
enabled=store.get_rewrite_enabled(strategy_id)
toggle=st.toggle("AI Rewrite Strategy",value=enabled,key="ai_rewrite_toggle")
if toggle!=enabled: store.set_rewrite_enabled(strategy_id,toggle)
st.caption("OFF always uses the original. ON uses the latest approved candidate, if one exists.")

change=st.text_area("Requested change",key="ai_change_request")
if st.button("Propose AI candidate",key="ai_propose_candidate") and change.strip():
    r=agent.propose_strategy_candidates(rules,change)
    if r.ok: st.session_state["ai_candidate"]=r.data
    else: st.warning(r.message)
candidate=st.session_state.get("ai_candidate")
if candidate:
    st.json(candidate)
    if st.button("Create separate version",key="ai_create_candidate"):
        c=store.create_ai_candidate(strategy_id,"v1",candidate["rules"],candidate["change_summary"],prompt=change)
        st.session_state["ai_candidate_label"]=c.version_label
        st.success(f"Created {c.version_label}. Original v1 was not modified.")
for v in store.list_versions(strategy_id):
    if v.ai_generated:
        c1,c2,c3=st.columns(3)
        c1.write(f"**{v.version_label}** · {v.status}")
        if c2.button("Approve",key=f"approve_{v.version_label}",disabled=v.status=="rejected"):
            store.approve(strategy_id,v.version_label); st.rerun()
        if c3.button("Reject",key=f"reject_{v.version_label}",disabled=v.status=="rejected"):
            store.reject(strategy_id,v.version_label); st.rerun()
st.info(f"Active research version: **{store.get_active(strategy_id) or 'none'}**")

st.divider()
st.subheader("3. AI Backtest Analysis")
result=st.session_state.get("result")
if result is None:
    st.caption("Run Backtest first. AI analyzes deterministic results; it does not calculate them.")
else:
    if st.button("Analyze current backtest",key="ai_analyze_backtest"):
        r=agent.explain_backtest(result.metrics,result.rejections)
        if r.ok: st.session_state["ai_backtest"]=r.data
        else: st.warning(r.message)
    if st.session_state.get("ai_backtest"): st.json(st.session_state["ai_backtest"])

st.divider()
st.subheader("4. Research chat")
question=st.text_input("Ask a question about the current research",key="ai_chat_question")
if st.button("Ask AI",key="ai_chat_ask") and question.strip():
    facts=backtest_facts(result) if result is not None else {}
    r=agent.answer_research_question(question,facts)
    if r.ok: st.session_state["ai_chat"]=r.data
    else: st.warning(r.message)
if st.session_state.get("ai_chat"): st.json(st.session_state["ai_chat"])

st.divider()
st.subheader("5. Controlled optimization proposal")
if st.button("Propose bounded experiment",key="ai_propose_experiment"):
    r=agent.propose_experiments(rules)
    if r.ok: st.session_state["ai_experiment"]=r.data
    else: st.warning(r.message)
if st.session_state.get("ai_experiment"): st.json(st.session_state["ai_experiment"])

st.divider()
st.subheader("6. Reality Check explanation")
report=st.session_state.get("audit_report")
if report is None:
    st.caption("Run Reality Check first.")
else:
    st.error(report.verdict)
    if st.button("Explain Reality Check",key="ai_explain_reality"):
        r=agent.explain_reality_check(reality_check_facts(report),reality_check_details(report))
        if r.ok: st.session_state["ai_reality"]=r.data
        else: st.warning(r.message)
    if st.session_state.get("ai_reality"): st.json(st.session_state["ai_reality"])

store.close_db()
ui.workflow_nav("ai")
ui.footer_note()
