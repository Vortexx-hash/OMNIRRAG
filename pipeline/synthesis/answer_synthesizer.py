"""
Final Answer Synthesizer — Stage 9.

Combines conflict reports, stable agent positions, evidence chunks, and
credibility scores (soft signal) into a natural language answer.

Decision cases:
  Case 1 — Ambiguity:     present all surviving answers with scope qualifiers
  Case 2 — Strong winner: return single best-supported answer
  Case 3 — Unresolved:    state insufficient evidence

See SKILLS.md: Conflict Classification Rules.
"""

from __future__ import annotations

import json
import textwrap

import os

import openai
from dotenv import load_dotenv

load_dotenv()

from models.schemas import AgentPosition, Chunk, ConflictReport, SynthesisResult
from pipeline.shared.constants import (
    CONFLICT_AMBIGUITY,
    CONFLICT_NOISE,
    CONFLICT_OUTLIER,
    CONFLICT_OVERSIMPLIFICATION,
    DECISION_CASE_AMBIGUITY,
    DECISION_CASE_STRONG_WINNER,
    DECISION_CASE_UNRESOLVED,
    SCOPE_QUALIFIERS,
    SYNTHESIS_MODEL as _SYNTHESIS_MODEL,
)
from pipeline.synthesis.conflict_report import determine_decision_case


def _get_qualifier(text: str) -> str:
    """Return the first matching scope qualifier found in text, or 'general'."""
    text_lower = text.lower()
    for q in SCOPE_QUALIFIERS:
        if q in text_lower:
            return q
    return "general"


def _chunk_excerpt(chunk: Chunk, max_len: int = 200) -> str:
    return chunk.text[:max_len]


class AnswerSynthesizer:
    """Produces a conflict-aware natural language answer from pipeline outputs."""

    def __init__(self) -> None:
        self._client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    def synthesize(
        self,
        reports: list[ConflictReport],
        positions: list[AgentPosition],
        chunks: list[Chunk],
    ) -> SynthesisResult:
        """
        Return a SynthesisResult.
        Credibility scores are read from chunk records as a soft weighting signal.
        synthesize() never raises — falls back to template-based answer on LLM failure.
        """
        decision_case = determine_decision_case(reports)

        valid_chunk_ids = {c.id for c in chunks}

        try:
            if decision_case == DECISION_CASE_AMBIGUITY:
                answer, sources, tags = self._case_1_ambiguity(reports, chunks)
            elif decision_case == DECISION_CASE_STRONG_WINNER:
                answer, sources, tags = self._case_2_strong_winner(reports, chunks)
            else:
                answer, sources, tags = self._case_3_unresolved(reports, chunks)
        except Exception:
            # Fallback: template-based answer
            answer, sources, tags = self._fallback_answer(reports, decision_case)

        # Filter out any hallucinated chunk IDs the LLM may have invented
        sources = [s for s in sources if s in valid_chunk_ids]

        return self._build_synthesis_result(answer, decision_case, reports, sources, tags)

    # ──────────────────────────────────────────────────────────────────────────
    # Case handlers
    # ──────────────────────────────────────────────────────────────────────────

    def _case_1_ambiguity(
        self,
        reports: list[ConflictReport],
        chunks: list[Chunk],
    ) -> tuple[str, list[str], list[str]]:
        """Present multiple valid answers, each labelled with its scope qualifier."""
        chunk_map = {c.id: c for c in chunks}

        # Only include pure ambiguity clusters — oversimplification/outlier are noted
        # in tags but must not appear as valid answers in Case 1.
        surviving = [r for r in reports if r.conflict_type == CONFLICT_AMBIGUITY]
        oversimpl = [r for r in reports if r.conflict_type == CONFLICT_OVERSIMPLIFICATION]
        outliers  = [r for r in reports if r.conflict_type == CONFLICT_OUTLIER]

        # Build claim lines grouped by qualifier
        claim_lines: list[str] = []
        all_cited_ids: list[str] = []
        for r in surviving:
            chunk_texts = [chunk_map[cid].text for cid in r.chunk_ids if cid in chunk_map]
            combined_text = " ".join(chunk_texts)
            qualifier = _get_qualifier(combined_text)
            source_ids = [cid for cid in r.chunk_ids if cid in chunk_map]
            all_cited_ids.extend(source_ids)
            claim_lines.append(
                f"- Qualifier: '{qualifier}' | Evidence: {combined_text[:200]} "
                f"(strength: {r.evidence_strength:.2f})"
            )

        rejected_note = ""
        if oversimpl or outliers:
            rejected_texts = []
            for r in (oversimpl + outliers):
                for cid in r.chunk_ids:
                    if cid in chunk_map:
                        rejected_texts.append(chunk_map[cid].text[:80])
            rejected_note = (
                f"\n\nNOTE — the following claims were rejected (oversimplification/outlier) "
                f"and must NOT appear in the answer:\n"
                + "\n".join(f"  - {t}" for t in rejected_texts)
            )

        tags_hint = ["scope_conflict_preserved"]
        if outliers:
            tags_hint.append("outlier_rejected")
        if oversimpl:
            tags_hint.append("oversimplification_noted")

        system_prompt = (
            "You are a conflict-aware answer synthesizer. The evidence contains multiple "
            "valid answers that are each correct within their own scope. Write a single, "
            "cohesive paragraph that presents ALL of the following surviving claims clearly, "
            "each labelled with its qualifier (e.g. 'constitutional', 'administrative'). "
            "Do not favour one over another. Do not invent facts.\n\n"
            "Surviving claims to include:\n"
            + "\n".join(claim_lines)
            + rejected_note
            + f'\n\nRespond JSON only:\n'
            f'{{"answer": "cohesive paragraph here", '
            f'"sources_cited": {json.dumps(all_cited_ids)}, '
            f'"conflict_handling_tags": {json.dumps(tags_hint)}}}'
        )

        return self._call_llm(system_prompt, fallback_answer=self._fallback_case1(surviving, chunk_map))

    def _case_2_strong_winner(
        self,
        reports: list[ConflictReport],
        chunks: list[Chunk],
    ) -> tuple[str, list[str], list[str]]:
        """Return the single best-supported answer."""
        chunk_map = {c.id: c for c in chunks}

        surviving = [
            r for r in reports
            if r.conflict_type not in (CONFLICT_OUTLIER, CONFLICT_NOISE)
        ]
        rejected = [
            r for r in reports
            if r.conflict_type in (CONFLICT_OUTLIER, CONFLICT_OVERSIMPLIFICATION)
        ]

        # Pick the winning cluster (highest evidence_strength among surviving)
        winner = max(surviving, key=lambda r: r.evidence_strength) if surviving else None

        winner_text = ""
        winner_strength = 0.0
        winner_chunk_texts: list[str] = []
        winning_ids: list[str] = []

        if winner:
            winner_strength = winner.evidence_strength
            winning_ids = [cid for cid in winner.chunk_ids if cid in chunk_map]
            winner_chunk_texts = [
                f"[{cid}] tier={chunk_map[cid].credibility_tier}: {_chunk_excerpt(chunk_map[cid])}"
                for cid in winning_ids
            ]
            combined = " ".join(chunk_map[cid].text for cid in winning_ids if cid in chunk_map)
            winner_text = combined[:300]

        rejected_texts = []
        for r in rejected:
            texts = [chunk_map[cid].text[:100] for cid in r.chunk_ids if cid in chunk_map]
            rejected_texts.extend(texts)

        has_outlier = any(r.conflict_type == CONFLICT_OUTLIER for r in rejected)
        has_oversimpl = any(r.conflict_type == CONFLICT_OVERSIMPLIFICATION for r in rejected)
        tags_hint = '"outlier_rejected"' if has_outlier else '"oversimplification_noted"'

        system_prompt = (
            "You are a conflict-aware answer synthesizer. One claim won the debate; "
            "others were rejected.\n\n"
            f"Winning claim: {winner_text} (evidence_strength: {winner_strength:.2f})\n"
            f"Rejected claims: {rejected_texts}\n\n"
            "Evidence for winner:\n"
            + "\n".join(winner_chunk_texts)
            + f'\n\nRespond JSON only:\n{{"answer": "...", "sources_cited": {json.dumps(winning_ids)}, '
            f'"conflict_handling_tags": [{tags_hint}]}}'
        )

        fallback = self._fallback_case2(winner, winning_ids, chunk_map, has_outlier, has_oversimpl)
        return self._call_llm(system_prompt, fallback_answer=fallback)

    def _case_3_unresolved(
        self,
        reports: list[ConflictReport],
        chunks: list[Chunk],
    ) -> tuple[str, list[str], list[str]]:
        """Return a statement indicating insufficient evidence to decide."""
        chunk_map = {c.id: c for c in chunks}
        surviving = [
            r for r in reports
            if r.conflict_type not in (CONFLICT_OUTLIER, CONFLICT_NOISE)
        ]

        claim_lines = []
        all_ids: list[str] = []
        for r in surviving:
            texts = [chunk_map[cid].text[:150] for cid in r.chunk_ids if cid in chunk_map]
            source_ids = [cid for cid in r.chunk_ids if cid in chunk_map]
            all_ids.extend(source_ids)
            claim_lines.append(
                f"- (strength: {r.evidence_strength:.2f}) {' '.join(texts)}"
            )

        system_prompt = (
            "You are a conflict-aware answer synthesizer. The evidence produced no "
            "clear single winner — either claims genuinely conflict, or multiple sources "
            "say essentially the same thing without explicit scope qualifiers.\n\n"
            "Surviving claims (review carefully):\n"
            + "\n".join(claim_lines)
            + "\n\nInstructions:\n"
            "- If the surviving claims all say the SAME thing with different wording, "
            "consolidate them into one clear answer and note it is well-supported.\n"
            "- If the surviving claims GENUINELY conflict (different facts, not just "
            "different wording), state that the evidence is inconclusive and briefly "
            "summarise what the competing positions are.\n"
            f'\n\nRespond JSON only:\n'
            f'{{"answer": "your answer here", '
            f'"sources_cited": {json.dumps(all_ids)}, '
            f'"conflict_handling_tags": ["unresolved_conflict"]}}'
        )

        fallback = (
            "The available evidence presents conflicting claims and does not allow a "
            "definitive answer. Multiple competing positions were found with no clear winner.",
            all_ids,
            ["unresolved_conflict"],
        )
        return self._call_llm(system_prompt, fallback_answer=fallback)

    # ──────────────────────────────────────────────────────────────────────────
    # LLM call helper
    # ──────────────────────────────────────────────────────────────────────────

    def _call_llm(
        self,
        system_prompt: str,
        fallback_answer: tuple[str, list[str], list[str]],
    ) -> tuple[str, list[str], list[str]]:
        """
        Call the synthesis LLM and parse the JSON response.
        Returns (answer, sources_cited, conflict_handling_tags).
        Falls back to fallback_answer on any failure.
        """
        try:
            response = self._client.chat.completions.create(
                model=_SYNTHESIS_MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Synthesize the final answer now."},
                ],
            )
            data = json.loads(response.choices[0].message.content)
            answer = data.get("answer", "").strip()
            sources = data.get("sources_cited", [])
            tags = data.get("conflict_handling_tags", [])
            if answer:
                return answer, sources, tags
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Synthesis LLM call failed: %s", exc)

        return fallback_answer

    # ──────────────────────────────────────────────────────────────────────────
    # Fallback builders (no LLM needed)
    # ──────────────────────────────────────────────────────────────────────────

    def _fallback_case1(
        self,
        surviving: list[ConflictReport],
        chunk_map: dict[str, Chunk],
    ) -> tuple[str, list[str], list[str]]:
        parts = []
        all_ids: list[str] = []
        for r in surviving:
            ids = [cid for cid in r.chunk_ids if cid in chunk_map]
            all_ids.extend(ids)
            texts = [chunk_map[cid].text[:100] for cid in ids]
            qualifier = _get_qualifier(" ".join(texts))
            parts.append(f"({qualifier.capitalize()}) {' '.join(texts)}")
        answer = " | ".join(parts) if parts else "Multiple competing claims found."
        return answer, all_ids, ["scope_conflict_preserved"]

    def _fallback_case2(
        self,
        winner: ConflictReport | None,
        winning_ids: list[str],
        chunk_map: dict[str, Chunk],
        has_outlier: bool,
        has_oversimpl: bool,
    ) -> tuple[str, list[str], list[str]]:
        if winner and winning_ids:
            text = " ".join(chunk_map[cid].text[:100] for cid in winning_ids if cid in chunk_map)
            answer = text.strip() or "One claim was supported by the evidence."
        else:
            answer = "One claim was supported by the evidence."
        tag = "outlier_rejected" if has_outlier else "oversimplification_noted"
        return answer, winning_ids, [tag]

    def _fallback_answer(
        self,
        reports: list[ConflictReport],
        decision_case: int,
    ) -> tuple[str, list[str], list[str]]:
        if decision_case == DECISION_CASE_AMBIGUITY:
            return (
                "Multiple valid answers exist; context determines which applies.",
                [],
                ["scope_conflict_preserved"],
            )
        if decision_case == DECISION_CASE_STRONG_WINNER:
            return (
                "One claim was supported by the evidence.",
                [],
                ["outlier_rejected"],
            )
        return (
            "The available evidence presents conflicting claims and does not allow a definitive answer.",
            [],
            ["unresolved_conflict"],
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Result builder
    # ──────────────────────────────────────────────────────────────────────────

    def _build_synthesis_result(
        self,
        answer: str,
        decision_case: int,
        reports: list[ConflictReport],
        sources: list[str],
        tags: list[str],
    ) -> SynthesisResult:
        return SynthesisResult(
            answer=answer,
            decision_case=decision_case,
            conflict_reports=reports,
            conflict_handling_tags=tags,
            sources_cited=sources,
        )
