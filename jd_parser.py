from __future__ import annotations

from ai_client import structured_response
from models import JDAnalysis


SYSTEM = """You are a rigorous job description analyzer. Extract only information explicitly present in the input.
summary is a 1-2 sentence description of the role. Every explicit responsibility, requirement, and
nice-to-have becomes one atomic requirement item numbered R1, R2, ...; do not add industry common sense.
A real job description never yields an empty requirements list or an empty summary.
importance is 1-5, with explicit must/required items highest. role_category must use the given enum."""


def parse_jd(jd_text: str) -> JDAnalysis:
    if len(jd_text.strip()) < 80:
        raise ValueError("JD text is too short. Please paste the full job description.")
    jd = structured_response(SYSTEM, jd_text, JDAnalysis, name="parse_jd")
    if not jd.requirements:  # rare degenerate output; retry once before failing
        jd = structured_response(SYSTEM, jd_text, JDAnalysis, name="parse_jd_retry")
    if not jd.requirements:
        raise ValueError("Could not extract any requirements from this JD. Try again or check the text.")
    return jd
