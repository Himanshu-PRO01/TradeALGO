from algobot.mirofish_sim import agent_chat, run_mirofish, build_world


def test_mirofish_social_simulation_is_deterministic():
    a = run_mirofish(agents=6, ticks=10, seed=42, strategy_score=.4, risk_score=.7)
    b = run_mirofish(agents=6, ticks=10, seed=42, strategy_score=.4, risk_score=.7)
    assert a[0] == b[0]
    assert len(a[2]) == 6 * 2 * 10
    assert a[0].graph_nodes >= 16
    assert a[0].graph_edges > 0


def test_world_contains_events_and_is_seeded():
    assert build_world(8, seed=9) == build_world(8, seed=9)


def test_agent_chat_is_read_only_and_memory_based():
    report, agents, messages, graph, events = run_mirofish(agents=2, ticks=4, seed=3)
    answer = agent_chat(agents[0], "Should I trust this strategy?", graph)
    assert "strategy" in answer.lower()
    assert "guaranteed" in answer.lower() or "research candidate" in answer.lower()
