from __future__ import annotations

from ai_client import structured_response
from models import JDAnalysis


SYSTEM = """You are a rigorous job description analyzer. Extract only information explicitly present in the input.
Split requirements into atomic items numbered R1, R2, ...; do not add industry common sense.
importance is 1-5, with explicit must/required items highest. role_category must use the given enum."""


def parse_jd(jd_text: str) -> JDAnalysis:
    if len(jd_text.strip()) < 80:
        raise ValueError("JD text is too short. Please paste the full job description.")
    return structured_response(SYSTEM, jd_text, JDAnalysis)
