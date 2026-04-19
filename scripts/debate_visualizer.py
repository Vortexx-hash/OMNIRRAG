"""
Debate Visualizer — step-by-step replay of a multi-agent debate.

Runs the orchestrator manually (bypassing the black-box `run()` method) so
every round is printed in detail:  initial positions, per-round confidence
changes, support map snapshots, and isolation events.

Usage:
    python scripts/debate_visualizer.py [scenario]

Scenarios  (pass the name as the first argument, default: bolivia):
    bolivia   — constitutional vs administrative capital (ambiguity + outlier)
    medical   — diabetes treatment consensus with one fringe agent
    unresolved — two equally-matched camps, no clear winner
"""

from __future__ import annotations

import sys
import textwrap
from dataclasses import dataclass

# Make sure the project root is on sys.path when the script is run directly.
sys.path.insert(0, __file__.rsplit("scripts", 1)[0].rstrip("/\\") or ".")

import hashlib
import math

from models.schemas import AgentPosition, Chunk
from pipeline.debate.agent_bank import DebateAgent, _word_overlap
from pipeline.debate.early_stop import should_stop
from pipeline.shared.constants import (
    AGENT_STATUS_ISOLATED,
    AGENT_STATUS_REVISED,
    AGENT_STATUS_STABLE,
    MAX_DEBATE_ROUNDS,
)

# ──────────────────────────────────────────────────────────────────────────────
# Tiny helpers (no ML dependencies)
# ──────────────────────────────────────────────────────────────────────────────

def _fake_embed(text: str, dim: int = 16) -> list[float]:
    vec = [0.0] * dim
    for word in text.lower().split():
        h = int(hashlib.md5(word.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
    mag = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / mag for x in vec]


def make_chunk(cid: str, text: str, *, tier: int = 2, score: float = 0.8) -> Chunk:
    return Chunk(id=cid, source_doc_id="doc", text=text,
                 embedding=_fake_embed(text), credibility_score=score,
                 credibility_tier=tier)


# ──────────────────────────────────────────────────────────────────────────────
# Scenarios
# ──────────────────────────────────────────────────────────────────────────────

SCENARIOS: dict[str, list[Chunk]] = {

    "bolivia": [
        make_chunk("sucre1",
            "Sucre is the constitutional capital of Bolivia and the official seat of the judiciary.",
            tier=1, score=0.95),
        make_chunk("sucre2",
            "Sucre has been recognized as the constitutional capital since the 1826 constitution.",
            tier=2, score=0.80),
        make_chunk("lapaz1",
            "La Paz is the administrative capital of Bolivia and the seat of the executive government.",
            tier=1, score=0.95),
        make_chunk("lapaz2",
            "La Paz serves as the administrative capital where the government ministries operate.",
            tier=2, score=0.75),
        make_chunk("outlier",
            "Santa Cruz is the capital of Bolivia and the largest economic hub.",
            tier=4, score=0.15),
    ],

    "medical": [
        make_chunk("met1",
            "Metformin is the first-line treatment for type 2 diabetes per clinical guidelines.",
            tier=1, score=0.95),
        make_chunk("met2",
            "Metformin is recommended as the standard first-line diabetes medication worldwide.",
            tier=2, score=0.85),
        make_chunk("met3",
            "Standard diabetes treatment guidelines recommend metformin as the first-line therapy.",
            tier=2, score=0.80),
        make_chunk("insulin1",
            "Insulin therapy is the primary treatment for type 1 diabetes management.",
            tier=2, score=0.80),
        make_chunk("fringe",
            "Bleach and household chemicals can cure diabetes with no side effects.",
            tier=4, score=0.10),
    ],

    "unresolved": [
        make_chunk("camp_a1",
            "Nuclear energy is the safest and cleanest source of baseload electricity.",
            tier=2, score=0.80),
        make_chunk("camp_a2",
            "Nuclear power plants produce the lowest carbon emissions per kilowatt hour.",
            tier=1, score=0.90),
        make_chunk("camp_b1",
            "Renewable energy from wind and solar is the safest electricity generation method.",
            tier=2, score=0.80),
        make_chunk("camp_b2",
            "Wind and solar power are the cleanest and safest energy sources available today.",
            tier=1, score=0.90),
    ],
}


# ──────────────────────────────────────────────────────────────────────────────
# Formatting helpers
# ──────────────────────────────────────────────────────────────────────────────

W = 80   # total line width

def _hr(char: str = "-", width: int = W) -> str:
    return char * width

def _box_title(title: str) -> str:
    pad = (W - len(title) - 2) // 2
    return f"{'=' * pad} {title} {'=' * (W - pad - len(title) - 2)}"

def _wrap(text: str, indent: int = 4, width: int = W) -> str:
    return textwrap.fill(text, width=width,
                         initial_indent=" " * indent,
                         subsequent_indent=" " * (indent + 2))

def _status_icon(status: str) -> str:
    return {"stable": "[OK]", "revised": "[REV]", "isolated": "[ISO]"}.get(status, "[?]")

def _conf_bar(conf: float, width: int = 20) -> str:
    filled = round(conf * width)
    return f"[{'#' * filled}{'.' * (width - filled)}] {conf:.2f}"

def _overlap_matrix(positions: list[AgentPosition]) -> str:
    ids = [p.agent_id.replace("agent_", "") for p in positions]
    header = "         " + "  ".join(f"{i:>7}" for i in ids)
    lines = [header, "         " + "-" * (len(ids) * 9)]
    for p in positions:
        row = f"{p.agent_id.replace('agent_', ''):>8} |"
        for q in positions:
            ov = _word_overlap(p.position_text, q.position_text)
            marker = f" {ov:.2f}  "
            if p.agent_id == q.agent_id:
                marker = "  self  "
            row += marker
        lines.append(row)
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Replay engine
# ──────────────────────────────────────────────────────────────────────────────

def run_visualized(chunks: list[Chunk]) -> None:
    print()
    print(_box_title("DEBATE VISUALIZER"))
    print(f"  Chunks: {len(chunks)}    Max rounds: {MAX_DEBATE_ROUNDS}")
    from pipeline.debate.agent_bank import _DEBATE_MODEL
    print(f"  NOTE: Agents use real LLM reasoning ({_DEBATE_MODEL})")
    print(_hr())

    # ── Setup ──────────────────────────────────────────────────────────────
    print()
    print("  CHUNKS ENTERING DEBATE")
    print(_hr("-"))
    for c in chunks:
        print(f"  [{c.id:>10}]  tier={c.credibility_tier}  score={c.credibility_score:.2f}")
        print(_wrap(c.text, indent=14))
    print()

    # ── Instantiate agents ─────────────────────────────────────────────────
    agents: list[DebateAgent] = [
        DebateAgent(agent_id=f"agent_{c.id}", chunk=c) for c in chunks
    ]
    agent_ids = [a._agent_id for a in agents]

    # ── Initial positions ──────────────────────────────────────────────────
    positions: list[AgentPosition] = [a.generate_initial_position() for a in agents]

    print(_box_title("INITIAL POSITIONS  (agents read only their own chunk)"))
    print()
    for p in positions:
        tier_src = next(c.credibility_tier for c in chunks if c.id == p.chunk_id)
        print(f"  {_status_icon(p.status)} {p.agent_id:<20}  conf={_conf_bar(p.confidence)}  tier={tier_src}")
        print(_wrap(f'"{p.position_text}"', indent=6))
        if p.reasoning:
            print(_wrap(f'[LLM] {p.reasoning}', indent=8))
    print()

    # ── Round loop ─────────────────────────────────────────────────────────
    rounds_run = 0
    isolated_ids: list[str] = []

    for round_idx in range(MAX_DEBATE_ROUNDS):
        # Build support map
        support_map = _compute_support_map(positions)
        isolated_ids = _identify_isolated(support_map, agent_ids)

        # Early stop check
        single_agent = len(agent_ids) <= 1
        stop_now = should_stop(positions, isolated_ids) and (
            round_idx == 0 and single_agent or round_idx > 0
        )
        if stop_now:
            print(f"  [STOP]  Early stop triggered before round {round_idx + 1}.")
            break

        # Print round header
        print(_hr())
        print(f"  ROUND {round_idx + 1}")
        print(_hr("-"))

        # Word overlap matrix
        print()
        print("  Word-overlap matrix (Jaccard similarity between position texts):")
        print(_overlap_matrix(positions))
        print()

        # Support map snapshot
        print("  Support map (claim -> supporters):")
        for claim, supporters in support_map.items():
            supporters_str = ", ".join(s.replace("agent_", "") for s in supporters)
            print(f"    [{supporters_str}]  ->  {claim[:70]!r}")
        if isolated_ids:
            print(f"  !! Isolated agents: {[i.replace('agent_','') for i in isolated_ids]}")
        print()

        # Run one round
        position_by_agent = {p.agent_id: p for p in positions}
        new_positions: list[AgentPosition] = []
        print("  Agents respond to broadcast:")
        print(_hr("-"))
        for agent in agents:
            old_p = position_by_agent[agent._agent_id]
            new_p = agent.respond_to_broadcast(old_p, positions)
            delta = new_p.confidence - old_p.confidence
            delta_str = f"  d{delta:+.2f}" if abs(delta) > 1e-9 else "  d 0.00"
            change_tag = f"  [{new_p.status.upper()}]" if new_p.status != AGENT_STATUS_STABLE else ""
            print(f"  {_status_icon(new_p.status)} {new_p.agent_id:<20}  "
                  f"conf {old_p.confidence:.2f} -> {new_p.confidence:.2f}{delta_str}{change_tag}")
            if new_p.reasoning:
                print(_wrap(f'  Reasoning: {new_p.reasoning}', indent=6))
            new_positions.append(new_p)

        positions = new_positions
        rounds_run += 1
        print()

    # ── Final pass ─────────────────────────────────────────────────────────
    support_map = _compute_support_map(positions)
    isolated_ids = _identify_isolated(support_map, agent_ids)

    # Mark isolated in final positions
    final_positions = []
    for p in positions:
        if p.agent_id in isolated_ids:
            final_positions.append(AgentPosition(
                agent_id=p.agent_id, chunk_id=p.chunk_id,
                position_text=p.position_text, confidence=p.confidence,
                status=AGENT_STATUS_ISOLATED,
            ))
        else:
            final_positions.append(p)

    print()
    print(_box_title(f"FINAL RESULTS  (after {rounds_run} round(s))"))
    print()
    for p in final_positions:
        tier_src = next(c.credibility_tier for c in chunks if c.id == p.chunk_id)
        print(f"  {_status_icon(p.status)} {p.agent_id:<20}  "
              f"{_conf_bar(p.confidence)}  tier={tier_src}  [{p.status.upper()}]")
        print(_wrap(f'"{p.position_text}"', indent=6))
    print()

    # Support map summary
    print("  Final support map:")
    for claim, supporters in support_map.items():
        supporters_str = ", ".join(s.replace("agent_", "") for s in supporters)
        print(f"    [{supporters_str}]  ->  {claim[:65]!r}")
    print()

    if isolated_ids:
        print(f"  [ISO]  ISOLATED: {[i.replace('agent_','') for i in isolated_ids]}")
    else:
        print("  [OK]  No isolated agents -- all positions have cross-support.")

    # Outcome interpretation
    non_isolated = [p for p in final_positions if p.agent_id not in isolated_ids]
    unique_claims = len({p.position_text for p in non_isolated})
    print()
    print(_hr("-"))
    if isolated_ids and unique_claims == 1:
        print("  OUTCOME -> Case 2 (Strong winner): one surviving claim, outlier(s) isolated.")
    elif unique_claims >= 2:
        print("  OUTCOME -> Case 1 (Ambiguity): multiple surviving claims - present all with qualifiers.")
    elif unique_claims == 1:
        print("  OUTCOME -> Case 2 (Strong winner): unanimous agreement.")
    else:
        print("  OUTCOME -> Case 3 (Unresolved): insufficient convergence.")
    print(_hr())
    print()


# ──────────────────────────────────────────────────────────────────────────────
# Support map / isolation helpers (mirrors orchestrator logic exactly)
# ──────────────────────────────────────────────────────────────────────────────

def _compute_support_map(positions: list[AgentPosition]) -> dict[str, list[str]]:
    THRESHOLD = 0.2
    text_to_agents: dict[str, list[str]] = {}
    for p in positions:
        text_to_agents.setdefault(p.position_text, []).append(p.agent_id)

    support_map: dict[str, list[str]] = {}
    for p in positions:
        if p.position_text in support_map:
            continue
        supporters = list(text_to_agents.get(p.position_text, []))
        for other in positions:
            if other.agent_id not in supporters and other.position_text != p.position_text:
                if _word_overlap(p.position_text, other.position_text) >= THRESHOLD:
                    supporters.append(other.agent_id)
        support_map[p.position_text] = supporters
    return support_map


def _identify_isolated(
    support_map: dict[str, list[str]], agent_ids: list[str]
) -> list[str]:
    if len(agent_ids) <= 1:
        return []
    agents_with_crosssupport: set[str] = set()
    for supporters in support_map.values():
        if len(supporters) > 1:
            for aid in supporters:
                agents_with_crosssupport.add(aid)
    return [aid for aid in agent_ids if aid not in agents_with_crosssupport]


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "bolivia"
    if name not in SCENARIOS:
        print(f"Unknown scenario {name!r}. Available: {list(SCENARIOS)}")
        sys.exit(1)
    run_visualized(SCENARIOS[name])
