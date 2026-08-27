from __future__ import annotations

import json

from ai_client import structured_response
from models import CoachReport, Fact, JDAnalysis, MatchReport


SYSTEM = """You are a resume coach interviewing a candidate to surface real experience they forgot to write down.
From the match report, find the highest-impact weaknesses: gap requirements, partial matches, and matched
facts that lack measurable outcomes. Ask one direct, specific question per weakness, like a human coach:
"Have you used X anywhere, even in a side project?" or "What measurably improved after you did Y?".
why must state plainly what a good answer would unlock on the resume.
Set related_fact_id only when the question strengthens a specific existing fact; use only fact IDs from the input.
requirement_id must be an ID from the input requirements.
At most 8 questions, most important first. Never coach the candidate to invent or exaggerate; a truthful
"I have not done this" must always be an acceptable answer."""


def coach_questions(jd: JDAnalysis, report: MatchReport, facts: list[Fact]) -> CoachReport:
    confirmed = [f for f in facts if f.confirmed and f.id is not None]
    payload = {
        "job": jd.model_dump(mode="json"),
        "match_report": report.model_dump(mode="json"),
        "confirmed_facts": [f.model_dump(mode="json") for f in confirmed],
    }
    result = structured_response(SYSTEM, json.dumps(payload, ensure_ascii=False), CoachReport, name="coach_questions")
    requirement_ids = {r.id for r in jd.requirements}
    valid_fact_ids = {f.id for f in confirmed}
    result.questions = [
        q for q in result.questions
        if q.requirement_id in requirement_ids
        and (q.related_fact_id is None or q.related_fact_id in valid_fact_ids)
    ][:8]
    if not result.questions:
        raise ValueError("The coach found nothing to ask about — your match already looks solid.")
    return result
