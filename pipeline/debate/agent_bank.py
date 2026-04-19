"""
Debate Agent — Stage 6 / 7.

A single agent is instantiated per DPP-selected chunk. Each agent:
- Holds exactly one chunk (strict isolation — no access to other chunks)
- Generates an initial position from its chunk at init
- Receives broadcast positions from other agents each round
- May revise its position or hold stable based on the broadcast

Agents see other agents' POSITIONS only, never their source chunks.
"""

from __future__ import annotations

import json
import math

import openai

from models.schemas import AgentPosition, Chunk
from pipeline.shared.constants import AGENT_STATUS_REVISED, AGENT_STATUS_STABLE

# Verbs used to find the most representative sentence in a chunk (fallback)
_REPRESENTATIVE_VERBS = {"is", "was", "are", "were", "has", "have", "can", "show", "suggest"}

_OPENAI_API_KEY = (
    "sk-proj-bTINwT5Ubukg9w-YJzMyrO5J3TJgo4hsGna91D5UqY55AQ2GH1HUysTrlmw6tKLM9k047zd1mm"
    "T3BlbkFJH2L8pz3dWqZqkNgZ6hiIDYLAPhBq7vC1ARdOhg3ugo9qSuU6pxCXwGM6YwvJCnOc668QBqfHgA"
)
_DEBATE_MODEL = "o3"


def _word_overlap(a: str, b: str) -> float:
    """
    Compute the Jaccard word overlap between two strings.

    word_overlap(a, b) = |words(a) ∩ words(b)| / max(|words(a) ∪ words(b)|, 1)
    where words(s) = set of lowercase tokens split by whitespace.
    """
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / max(len(union), 1)


def _extract_initial_text_fallback(chunk: Chunk) -> str:
    """Rule-based fallback: first sentence containing a representative verb."""
    sentences = chunk.text.split(". ")
    for sentence in sentences:
        tokens = set(sentence.lower().split())
        if tokens & _REPRESENTATIVE_VERBS:
            return sentence.rstrip()
    return chunk.text[:200].rstrip()


class DebateAgent:
    """A debate participant grounded in a single evidence chunk."""

    def __init__(self, agent_id: str, chunk: Chunk) -> None:
        self._agent_id = agent_id
        self._chunk = chunk
        self._client = openai.OpenAI(api_key=_OPENAI_API_KEY)

    def generate_initial_position(self) -> AgentPosition:
        """
        Produce an initial claim from the agent's chunk using an LLM call.
        Falls back to rule-based heuristic if the LLM response is malformed.
        """
        system_prompt = (
            "You are a debate agent grounded strictly in a single evidence chunk. "
            "Extract the single most important factual claim from the text below as a concise "
            "statement (1-2 sentences max). Do not add any facts not present in the text."
        )
        user_prompt = f"Evidence: {self._chunk.text}\n\nRespond with JSON only: {{\"position_text\": \"your claim here\", \"reasoning\": \"why this is the key claim\"}}"

        position_text = None
        reasoning = ""

        try:
            response = self._client.chat.completions.create(
                model=_DEBATE_MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            data = json.loads(response.choices[0].message.content)
            position_text = data.get("position_text", "").strip() or None
            reasoning = data.get("reasoning", "")
        except Exception:
            pass

        if not position_text:
            position_text = _extract_initial_text_fallback(self._chunk)
            reasoning = ""

        return AgentPosition(
            agent_id=self._agent_id,
            chunk_id=self._chunk.id,
            position_text=position_text,
            confidence=self._chunk.credibility_score,
            status=AGENT_STATUS_STABLE,
            reasoning=reasoning,
        )

    def respond_to_broadcast(
        self,
        current_position: AgentPosition,
        all_positions: list[AgentPosition],
    ) -> AgentPosition:
        """
        Given the current round's broadcast, return an updated position.
        Status must be AGENT_STATUS_REVISED if confidence changed,
        AGENT_STATUS_STABLE if unchanged.

        Uses LLM to assess confidence update; falls back to rule-based word overlap.
        """
        others = [p for p in all_positions if p.agent_id != self._agent_id]

        if not others:
            return AgentPosition(
                agent_id=current_position.agent_id,
                chunk_id=current_position.chunk_id,
                position_text=current_position.position_text,
                confidence=current_position.confidence,
                status=AGENT_STATUS_STABLE,
                reasoning="",
            )

        total_others = len(others)
        others_text = "\n".join(
            f"- [{p.agent_id}]: {p.position_text} (confidence: {p.confidence:.2f})"
            for p in others
        )

        system_prompt = (
            "You are a debate agent. You are grounded strictly in your own evidence — "
            "you cannot add facts not present in your chunk.\n\n"
            f"Your evidence chunk:\n{self._chunk.text}\n\n"
            f'Your current position: "{current_position.position_text}"\n'
            f"Current confidence: {current_position.confidence:.2f}\n\n"
            f"Other agents' positions:\n{others_text}\n\n"
            "Rules:\n"
            "- If 0 other agents have related claims → decrease confidence by 0.25 (floor 0.3)\n"
            f"- If a majority of other agents (≥ {math.ceil(total_others / 2)}) support a similar claim → increase confidence by 0.10 (cap 0.95)\n"
            "- Otherwise (contested) → keep confidence unchanged\n"
            "- You CANNOT change position_text."
        )
        user_prompt = (
            'Respond with JSON only:\n'
            '{"confidence": 0.XX, "status": "stable" or "revised", '
            '"reasoning": "brief explanation of why confidence changed or held"}'
        )

        new_confidence = None
        new_status_str = None
        reasoning = ""

        try:
            response = self._client.chat.completions.create(
                model=_DEBATE_MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            data = json.loads(response.choices[0].message.content)
            parsed_conf = data.get("confidence")
            parsed_status = data.get("status", "")
            reasoning = data.get("reasoning", "")

            # Validate parsed values
            if (
                isinstance(parsed_conf, (int, float))
                and 0.0 <= float(parsed_conf) <= 1.0
                and parsed_status in {"stable", "revised"}
            ):
                new_confidence = float(parsed_conf)
                new_status_str = parsed_status
            # else: fall through to rule-based
        except Exception:
            pass

        if new_confidence is None:
            # Rule-based fallback (complete implementation)
            supporters = [
                p for p in others
                if _word_overlap(current_position.position_text, p.position_text) >= 0.2
            ]
            if len(supporters) == 0:
                new_confidence = max(0.3, current_position.confidence - 0.25)
            elif len(supporters) >= (total_others + 1) // 2:
                new_confidence = min(0.95, current_position.confidence + 0.1)
            else:
                new_confidence = current_position.confidence
            new_status_str = (
                AGENT_STATUS_REVISED
                if abs(new_confidence - current_position.confidence) > 1e-9
                else AGENT_STATUS_STABLE
            )
            reasoning = ""

        new_status = new_status_str if new_status_str else AGENT_STATUS_STABLE

        return AgentPosition(
            agent_id=current_position.agent_id,
            chunk_id=current_position.chunk_id,
            position_text=current_position.position_text,  # text never changes
            confidence=new_confidence,
            status=new_status,
            reasoning=reasoning,
        )

    def _can_revise(self, current_position: AgentPosition) -> bool:
        """
        Return True if the agent is able to revise.
        Agents are always evidence-bounded; they cannot acquire new facts.
        Isolated agents are not permitted to revise.
        """
        return current_position.status != AGENT_STATUS_ISOLATED
