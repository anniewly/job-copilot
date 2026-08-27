from __future__ import annotations

import json

from ai_client import structured_response
from models import Fact, JDAnalysis, MatchReport, ResumeDraft


SYSTEM = """You are a trustworthy resume editor. Use only information verbatim-supportable by confirmed_facts.
Structure the resume like a real one: sections (e.g. Experience, Projects, Education), each containing entries.
One entry per job / project / degree, grouping the bullets that belong to it. Never mix facts from different
jobs or projects into one entry. Each entry's title, organization, and date_range must come from the facts
cited in its fact_ids; leave date_range empty if the facts carry no dates.
Every bullet must cite at least one fact_id; every skill must be supported by skill_fact_ids.
Never invent employers, dates, technologies, responsibilities, metrics, or achievements.
Preserve the meaning of the original facts; reordering and rephrasing for the JD is allowed.
Order entries reverse-chronologically when dates allow, and lead with the most JD-relevant bullets.
Target a single page: summary of 2-3 sentences; at most 5 bullets per entry (4-5 only for the most
JD-relevant experience, fewer for older or less relevant ones); each bullet one line, under 20 words.
Do not put gaps into the resume. Do not use first person."""

MAX_BULLETS_PER_ENTRY = 5


def generate_resume(jd: JDAnalysis, report: MatchReport, facts: list[Fact]) -> ResumeDraft:
    confirmed = [f for f in facts if f.confirmed and f.id is not None]
    payload = {
        "job": jd.model_dump(mode="json"),
        "match_report": report.model_dump(mode="json"),
        "confirmed_facts": [f.model_dump(mode="json") for f in confirmed],
    }
    draft = structured_response(SYSTEM, json.dumps(payload, ensure_ascii=False), ResumeDraft, name="generate_resume")
    _validate_fact_ids(draft, {f.id for f in confirmed})
    for section in draft.sections:
        for entry in section.entries:
            entry.bullets = entry.bullets[:MAX_BULLETS_PER_ENTRY]
    return draft


def _validate_fact_ids(draft: ResumeDraft, valid_ids: set[int]) -> None:
    cited = list(draft.summary_fact_ids) + list(draft.skill_fact_ids)
    for section in draft.sections:
        for entry in section.entries:
            cited.extend(entry.fact_ids)
            for bullet in entry.bullets:
                cited.extend(bullet.fact_ids)
    if not set(cited) <= valid_ids:
        raise ValueError("Resume draft cites an unconfirmed or nonexistent fact.")
