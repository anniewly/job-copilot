from __future__ import annotations

from io import BytesIO

from ai_client import structured_response
from database import delete_fact, list_facts, save_fact, set_fact_confirmed
from models import Fact, ResumeExtraction

__all__ = [
    "Fact", "save_fact", "list_facts", "set_fact_confirmed", "delete_fact",
    "extract_facts_from_resume", "read_resume_file",
]


EXTRACT_SYSTEM = """You are a rigorous resume fact extractor. Extract only information explicitly present in the resume.
Produce one atomic fact per job, project, education entry, or notable achievement.
content must describe what the person actually did, in third person, staying faithful to the resume's wording.
Copy metrics verbatim into metrics; list technologies and skills actually named for that entry in skills.
Never invent, merge unrelated entries, embellish, or add information not in the resume.
Use start_date and end_date only when dates are given; use the first day of a month when only month and year appear."""


def extract_facts_from_resume(resume_text: str = "", pdf_bytes: bytes | None = None) -> list[Fact]:
    if not resume_text.strip() and not pdf_bytes:
        raise ValueError("Provide resume text or a PDF file.")
    prompt = resume_text.strip() or "Extract facts from the attached resume."
    extraction = structured_response(EXTRACT_SYSTEM, prompt, ResumeExtraction, pdf_bytes=pdf_bytes, name="extract_resume_facts")
    if not extraction.facts:
        raise ValueError("No facts could be extracted. Check that the input is a resume.")
    return [Fact(**f.model_dump(), confirmed=False) for f in extraction.facts]


def read_resume_file(filename: str, data: bytes) -> tuple[str, bytes | None]:
    """Return (text, pdf_bytes) for an uploaded resume file."""
    name = filename.lower()
    if name.endswith(".pdf"):
        return "", data
    if name.endswith(".docx"):
        from docx import Document

        document = Document(BytesIO(data))
        return "\n".join(p.text for p in document.paragraphs if p.text.strip()), None
    return data.decode("utf-8", errors="replace"), None
