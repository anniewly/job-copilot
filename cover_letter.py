from __future__ import annotations

import json

from ai_client import structured_response
from models import CoverLetterDraft, Fact, JDAnalysis, MatchReport


SYSTEM = """You are a trustworthy cover letter editor. Use only information from confirmed_facts.
Every body paragraph must have corresponding paragraph_fact_ids, matching paragraphs exactly in count.
Never fabricate experience, skills, achievements, motivation, or knowledge of the company.
If facts are limited, keep it short."""


def generate_cover_letter(company: str, jd: JDAnalysis, report: MatchReport,
                          facts: list[Fact]) -> CoverLetterDraft:
    confirmed = [f for f in facts if f.confirmed and f.id is not None]
    payload = {
        "company": company, "job": jd.model_dump(mode="json"),
        "match_report": report.model_dump(mode="json"),
        "confirmed_facts": [f.model_dump(mode="json") for f in confirmed],
    }
    draft = structured_response(SYSTEM, json.dumps(payload, ensure_ascii=False), CoverLetterDraft, name="generate_cover_letter")
    if len(draft.paragraphs) != len(draft.paragraph_fact_ids):
        raise ValueError("Cover letter paragraph and citation counts do not match.")
    valid_ids = {f.id for f in confirmed}
    if any(not ids or not set(ids) <= valid_ids for ids in draft.paragraph_fact_ids):
        raise ValueError("Cover letter cites an unconfirmed or nonexistent fact.")
    return draft
