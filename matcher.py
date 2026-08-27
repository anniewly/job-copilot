from __future__ import annotations

import json

from ai_client import structured_response
from models import Fact, JDAnalysis, MatchReport


SYSTEM = """You are a job evidence matcher. Rely only on the provided confirmed facts.
Each requirement must have exactly one match. fact_ids may only reference IDs present in the input.
When evidence is insufficient, mark partial or gap; never infer, exaggerate, or fabricate.
overall_score is weighted by requirement importance; gap items must have empty fact_ids.
suggestion should be an actionable resume edit and must never compensate for experience that does not exist."""


def match(jd: JDAnalysis, facts: list[Fact]) -> MatchReport:
    confirmed = [f for f in facts if f.confirmed and f.id is not None]
    if not confirmed:
        raise ValueError("At least one confirmed experience fact is required.")
    payload = {
        "job": jd.model_dump(mode="json"),
        "confirmed_facts": [f.model_dump(mode="json") for f in confirmed],
    }
    report = structured_response(SYSTEM, json.dumps(payload, ensure_ascii=False), MatchReport, name="match_requirements")
    valid_ids = {f.id for f in confirmed}
    requirement_ids = {r.id for r in jd.requirements}
    seen = set()
    for item in report.matches:
        if item.requirement_id not in requirement_ids:
            raise ValueError(f"Model referenced an unknown requirement: {item.requirement_id}")
        if item.requirement_id in seen:
            raise ValueError(f"Model matched a requirement twice: {item.requirement_id}")
        if not set(item.fact_ids) <= valid_ids:
            raise ValueError("Model referenced an unconfirmed or nonexistent fact.")
        if item.status == "gap" and item.fact_ids:
            raise ValueError("Gap items must not cite facts.")
        seen.add(item.requirement_id)
    if seen != requirement_ids:
        raise ValueError("Match report does not cover all job requirements.")
    return report
