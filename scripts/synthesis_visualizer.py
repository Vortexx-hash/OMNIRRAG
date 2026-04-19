"""
Synthesis Visualizer — end-to-end pipeline from debate results to final answer.

Shows conflict classification and the final answer produced by o3.

Usage:
    python scripts/synthesis_visualizer.py [bolivia|medical|unresolved]

Scenarios (pass the name as the first argument, default: bolivia):
    bolivia    — constitutional vs administrative capital (ambiguity + outlier)
    medical    — diabetes treatment consensus with one fringe agent
    unresolved — two equally-matched camps, no clear winner
"""

from __future__ import annotations

import hashlib
import math
import sys
import textwrap

# Make sure the project root is on sys.path when the script is run directly.
sys.path.insert(0, __file__.rsplit("scripts", 1)[0].rstrip("/\\") or ".")

from models.schemas import AgentPosition, Chunk
from pipeline.debate.orchestrator import DebateOrchestrator
from pipeline.shared.constants import (
    CONFLICT_AMBIGUITY,
    CONFLICT_NOISE,
    CONFLICT_OUTLIER,
    CONFLICT_OVERSIMPLIFICATION,
    DECISION_CASE_AMBIGUITY,
    DECISION_CASE_STRONG_WINNER,
    DECISION_CASE_UNRESOLVED,
)
from pipeline.synthesis.answer_synthesizer import AnswerSynthesizer
from pipeline.synthesis.conflict_report import generate_conflict_reports


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
# Scenarios (copied from debate_visualizer.py — avoid importing from scripts/)
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

_CASE_DESCRIPTIONS = {
    DECISION_CASE_AMBIGUITY:      "Ambiguity -- multiple valid claims with scope qualifiers",
    DECISION_CASE_STRONG_WINNER:  "Strong winner -- one claim dominates",
    DECISION_CASE_UNRESOLVED:     "Unresolved -- conflicting evidence, no clear winner",
}

_TYPE_LABELS = {
    CONFLICT_AMBIGUITY:          "AMBIGUITY",
    CONFLICT_OUTLIER:            "OUTLIER",
    CONFLICT_OVERSIMPLIFICATION: "OVERSIMPLIFICATION",
    CONFLICT_NOISE:              "NOISE",
}


# ──────────────────────────────────────────────────────────────────────────────
# Formatting helpers
# ──────────────────────────────────────────────────────────────────────────────

W = 80


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


# ──────────────────────────────────────────────────────────────────────────────
# Main visualizer
# ──────────────────────────────────────────────────────────────────────────────

def run_synthesis_visualizer(scenario_name: str, chunks: list[Chunk]) -> None:
    print()
    print(_box_title("SYNTHESIS VISUALIZER"))
    print(f"  Scenario: {scenario_name}   Model: o3")
    print(_hr())

    # ── Run debate ─────────────────────────────────────────────────────────────
    print()
    print("  Running debate (DebateOrchestrator) ... this calls o3 for each agent.")
    print()

    orchestrator = DebateOrchestrator()
    debate_result = orchestrator.run(chunks)

    # ── Section 1: Debate summary ──────────────────────────────────────────────
    print(_hr())
    print("  DEBATE SUMMARY (from live run)")
    print(_hr("-"))
    print(f"  Rounds: {debate_result.rounds_completed}")
    if debate_result.isolated_agent_ids:
        print(f"  Isolated agents: {debate_result.isolated_agent_ids}")
    print()

    chunk_map = {c.id: c for c in chunks}
    for p in debate_result.final_positions:
        tier = chunk_map[p.chunk_id].credibility_tier if p.chunk_id in chunk_map else "?"
        print(f"  {_status_icon(p.status)} {p.agent_id:<22}  "
              f"conf={_conf_bar(p.confidence)}  tier={tier}")
        print(_wrap(f'"{p.position_text}"', indent=6))
    print()

    # ── Section 2: Conflict classification ────────────────────────────────────
    print(_hr())
    print("  CONFLICT CLASSIFICATION")
    print(_hr("-"))

    reports = generate_conflict_reports(
        positions=debate_result.final_positions,
        support_map=debate_result.support_map,
        isolated_agent_ids=debate_result.isolated_agent_ids,
        chunks=chunks,
        relation_pairs=[],  # no relation builder in visualizer
    )

    for r in reports:
        type_label = _TYPE_LABELS.get(r.conflict_type, r.conflict_type.upper())
        print(f"  [{type_label}]  chunks={r.chunk_ids}  "
              f"evidence_strength={r.evidence_strength:.2f}  case={r.decision_case}")
        # Show position text (from debate positions matching first chunk_id)
        if r.chunk_ids:
            matching = [p for p in debate_result.final_positions
                        if p.chunk_id in r.chunk_ids]
            if matching:
                print(_wrap(f'Position: "{matching[0].position_text}"', indent=4))
        print()

    # Overall decision case
    from pipeline.synthesis.conflict_report import determine_decision_case
    overall_case = determine_decision_case(reports)
    case_desc = _CASE_DESCRIPTIONS.get(overall_case, f"Case {overall_case}")
    print(f"  Overall decision case: Case {overall_case} -- {case_desc}")
    print()

    # ── Section 3: Final answer ────────────────────────────────────────────────
    print(_hr())
    print("  FINAL ANSWER (o3 synthesis)")
    print(_hr("-"))
    print()
    print("  Calling o3 for final synthesis ...")
    print()

    synthesizer = AnswerSynthesizer()
    synthesis_result = synthesizer.synthesize(
        reports=reports,
        positions=debate_result.final_positions,
        chunks=chunks,
    )

    # Wrap answer at 76 chars with 4-space indent
    for line in textwrap.wrap(synthesis_result.answer, width=76,
                              initial_indent="    ", subsequent_indent="    "):
        print(line)
    print()
    print(f"  Conflict handling tags: {synthesis_result.conflict_handling_tags}")
    print(f"  Sources cited:          {synthesis_result.sources_cited}")
    print()
    print(_hr("="))
    print()


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "bolivia"
    if name not in SCENARIOS:
        print(f"Unknown scenario {name!r}. Available: {list(SCENARIOS)}")
        sys.exit(1)
    run_synthesis_visualizer(name, SCENARIOS[name])
