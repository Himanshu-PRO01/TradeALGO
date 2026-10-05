"""Self-contained MiroFish-inspired market swarm for safe strategy research.

This is an independent implementation: synthetic market/news world, agent personas,
long-term memory, knowledge graph, agent-to-agent interaction, belief updates and
a deterministic research report. It never touches brokers or live order APIs.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable
import random
import re


@dataclass(frozen=True)
class MarketEvent:
    tick: int
    kind: str
    headline: str
    impact: float
    regime: str


@dataclass
class Graph:
    nodes: dict[str, dict] = field(default_factory=dict)
    edges: dict[tuple[str, str, str], float] = field(default_factory=dict)

    def node(self, node_id: str, **attrs) -> None:
        self.nodes.setdefault(node_id, {}).update(attrs)

    def edge(self, source: str, relation: str, target: str, weight: float = 1.0) -> None:
        self.node(source)
        self.node(target)
        key = (source, relation, target)
        self.edges[key] = self.edges.get(key, 0.0) + float(weight)

    def neighbors(self, source: str) -> list[tuple[str, str, float]]:
        return [(t, r, w) for (s, r, t), w in self.edges.items() if s == source]


@dataclass
class AgentMemory:
    observations: list[str] = field(default_factory=list)
    beliefs: dict[str, float] = field(default_factory=lambda: {
        "bullish": 0.5, "strategy_quality": 0.5, "risk_safety": 0.5
    })
    source_trust: dict[str, float] = field(default_factory=dict)

    def remember(self, text: str, limit: int = 40) -> None:
        self.observations.append(text)
        if len(self.observations) > limit:
            del self.observations[:-limit]

    def learn(self, key: str, evidence: float, rate: float = 0.2) -> None:
        old = self.beliefs.get(key, 0.5)
        self.beliefs[key] = max(0.0, min(1.0, old + rate * (evidence - old)))


@dataclass(frozen=True)
class AgentPersona:
    name: str
    role: str
    risk: float
    contrarian: float
    social: float
    skepticism: float


PERSONAS = (
    AgentPersona("beginner", "learn safely", .30, .10, .70, .25),
    AgentPersona("risk_manager", "protect capital", .10, .25, .55, .80),
    AgentPersona("momentum", "find trends", .75, .05, .65, .45),
    AgentPersona("contrarian", "challenge consensus", .60, .90, .75, .60),
    AgentPersona("optimizer", "compare evidence", .65, .35, .80, .70),
    AgentPersona("impatient", "act quickly", .90, .00, .85, .20),
    AgentPersona("power_user", "stress workflows", .70, .40, .90, .75),
    AgentPersona("adversarial", "find failure modes", .50, .80, .95, .95),
)


@dataclass
class Agent:
    agent_id: str
    persona: AgentPersona
    memory: AgentMemory = field(default_factory=AgentMemory)
    stance: float = 0.0
    influence: float = 1.0
    pnl: float = 0.0
    messages: int = 0


@dataclass(frozen=True)
class Message:
    tick: int
    sender: str
    recipient: str
    text: str
    stance: float
    weight: float


@dataclass(frozen=True)
class MiroFishReport:
    ticks: int
    agents: int
    events: int
    messages: int
    consensus: float
    consensus_strength: float
    mean_strategy_belief: float
    mean_risk_belief: float
    graph_nodes: int
    graph_edges: int
    failure_modes: tuple[str, ...]
    key_findings: tuple[str, ...]


def build_world(ticks: int, seed: int = 1) -> list[MarketEvent]:
    if ticks < 1:
        raise ValueError("ticks must be >= 1")
    rng = random.Random(seed)
    regimes = ["trend", "chop", "mean_reversion", "volatile", "shock"]
    headlines = {
        "trend": ("Momentum broadens as buyers remain persistent.", .65),
        "chop": ("Index stalls as conviction disappears.", -.05),
        "mean_reversion": ("Sharp move begins to retrace toward its range.", -.35),
        "volatile": ("Volatility jumps and stop-outs become more likely.", .15),
        "shock": ("Unexpected macro headline hits risk appetite.", rng.choice([-.9, .9])),
    }
    events = []
    current = "trend"
    for tick in range(ticks):
        if tick == 0 or rng.random() < .22:
            current = rng.choice(regimes)
        headline, impact = headlines[current]
        if current == "shock":
            impact = rng.choice([-.9, .9])
        events.append(MarketEvent(tick, current, headline, float(impact), current))
    return events


def _initial_agents(count: int) -> list[Agent]:
    if count < 1:
        raise ValueError("agents must be >= 1")
    return [Agent(f"agent-{i+1:03d}", PERSONAS[i % len(PERSONAS)]) for i in range(count)]


def _message(a: Agent, b: Agent, event: MarketEvent) -> Message:
    base = event.impact
    if a.persona.contrarian > .7:
        base *= -1
    elif a.persona.name == "momentum":
        base *= 1.25
    noise = (1.0 - a.persona.skepticism) * 0.12
    stance = max(-1.0, min(1.0, base + noise))
    if stance > .25:
        text = f"{event.kind}: I lean bullish, but evidence is {abs(stance):.2f}."
    elif stance < -.25:
        text = f"{event.kind}: downside risk is rising; I lean defensive."
    else:
        text = f"{event.kind}: signal is mixed; I would wait for confirmation."
    return Message(event.tick, a.agent_id, b.agent_id, text, stance, a.influence)


def run_mirofish(
    *,
    agents: int = 8,
    ticks: int = 24,
    seed: int = 700,
    strategy_score: float = 0.5,
    risk_score: float = 0.5,
) -> tuple[MiroFishReport, list[Agent], list[Message], Graph, list[MarketEvent]]:
    """Run a bounded social market simulation with no external side effects."""
    cohort = _initial_agents(agents)
    events = build_world(ticks, seed)
    graph = Graph()
    messages: list[Message] = []
    for a in cohort:
        graph.node(a.agent_id, role=a.persona.role)

    for event in events:
        graph.node(f"event-{event.tick}", kind=event.kind, impact=event.impact)
        for a in cohort:
            # Experience changes beliefs before social exchange.
            evidence = (event.impact + 1.0) / 2.0
            if a.persona.contrarian > .7:
                evidence = 1.0 - evidence
            a.memory.learn("bullish", evidence, .12)
            a.memory.learn("strategy_quality", strategy_score, .10)
            a.memory.learn("risk_safety", risk_score, .10)
            a.stance = (a.memory.beliefs["bullish"] - .5) * 2
            a.pnl += a.stance * event.impact * (1.0 - a.persona.risk * .15)
            a.memory.remember(f"tick {event.tick}: {event.headline}")
            graph.edge(a.agent_id, "observed", f"event-{event.tick}")

        # Sparse directed debate: each agent talks to the next two peers.
        for i, a in enumerate(cohort):
            for offset in (1, 2):
                if len(cohort) <= offset:
                    continue
                b = cohort[(i + offset) % len(cohort)]
                msg = _message(a, b, event)
                messages.append(msg)
                a.messages += 1
                graph.edge(a.agent_id, "influences", b.agent_id, max(.1, a.persona.social))
                b.memory.learn("bullish", (msg.stance + 1.0) / 2.0,
                               .06 * max(.2, a.persona.social))
                b.memory.remember(f"heard {a.agent_id}: {msg.text}")
                b.stance = (b.memory.beliefs["bullish"] - .5) * 2

    stances = [a.stance for a in cohort]
    consensus = sum(stances) / len(stances)
    strength = 1.0 - min(1.0, (max(stances) - min(stances)) / 2.0)
    failures = []
    if strategy_score < .5:
        failures.append("agents received negative strategy evidence")
    if risk_score < .5:
        failures.append("risk belief deteriorated")
    if strength < .35:
        failures.append("agent opinions remained highly fragmented")
    if any(e.kind == "shock" for e in events):
        failures.append("shock regime produced disagreement that needs out-of-sample validation")
    findings = [
        f"final collective stance={consensus:+.2f}",
        f"consensus strength={strength:.2f}",
        f"social graph connected {len(messages)} agent-to-agent messages",
        f"mean simulated agent P&L={sum(a.pnl for a in cohort)/len(cohort):+.2f}",
    ]
    report = MiroFishReport(
        ticks, len(cohort), len(events), len(messages), float(consensus),
        float(strength),
        float(sum(a.memory.beliefs["strategy_quality"] for a in cohort) / len(cohort)),
        float(sum(a.memory.beliefs["risk_safety"] for a in cohort) / len(cohort)),
        len(graph.nodes), len(graph.edges), tuple(failures), tuple(findings),
    )
    return report, cohort, messages, graph, events


def agent_chat(agent: Agent, question: str, graph: Graph | None = None) -> str:
    """Deterministic post-simulation agent chat; never executes a trade."""
    q = re.sub(r"\s+", " ", question.strip())[:500]
    if not q:
        return "Ask me about my simulated beliefs, evidence, risk view, or disagreements."
    evidence = agent.memory.observations[-3:]
    risk = agent.memory.beliefs["risk_safety"]
    quality = agent.memory.beliefs["strategy_quality"]
    tone = "I am cautious" if risk < .5 else "I am reasonably comfortable with the risk evidence"
    if quality < .5:
        verdict = "I would not trust the strategy yet."
    else:
        verdict = "I would treat the strategy as a research candidate, not a guaranteed winner."
    neighbors = len(graph.neighbors(agent.agent_id)) if graph else 0
    return (f"As the {agent.persona.role} agent, {tone}. Strategy belief={quality:.2f}, "
            f"risk belief={risk:.2f}, connected influences={neighbors}. {verdict} "
            f"My recent evidence: {' | '.join(evidence[-2:]) if evidence else 'none yet'} "
            f"Question received: {q}")
