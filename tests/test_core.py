from pathlib import Path

import database as db
from document_export import cover_letter_docx, resume_docx
from models import (
    CoverLetterDraft, Fact, FactType, Profile, ResumeBullet, ResumeDraft,
    ResumeEntry, ResumeSection,
)
from resume_generator import _validate_fact_ids


def test_database_roundtrip(tmp_path: Path):
    path = tmp_path / "test.db"
    db.init_db(path)
    fact_id = db.save_fact(
        Fact(fact_type=FactType.PROJECT, title="Search", content="Built retrieval",
             skills=["Python"], confirmed=True),
        path,
    )
    facts = db.list_facts(True, path)
    assert facts[0].id == fact_id
    assert facts[0].skills == ["Python"]


def test_resume_rejects_unknown_fact():
    draft = ResumeDraft(
        summary="Summary", summary_fact_ids=[1],
        skills=["Python"], skill_fact_ids=[1],
        sections=[ResumeSection(heading="Experience", entries=[
            ResumeEntry(title="Engineer", organization="Acme", fact_ids=[1], bullets=[
                ResumeBullet(text="Built system", fact_ids=[99])
            ])
        ])],
    )
    try:
        _validate_fact_ids(draft, {1})
        assert False, "expected validation failure"
    except ValueError:
        pass


def test_docx_exports():
    resume = ResumeDraft(
        summary="Summary", summary_fact_ids=[1],
        skills=["Python"], skill_fact_ids=[1],
        sections=[ResumeSection(heading="Experience", entries=[
            ResumeEntry(title="Engineer", organization="Acme",
                        date_range="Jun 2023 – Present", fact_ids=[1], bullets=[
                ResumeBullet(text="Built system", fact_ids=[1])
            ])
        ])],
    )
    letter = CoverLetterDraft(
        salutation="Dear Hiring Team,", paragraphs=["I built a system."],
        paragraph_fact_ids=[[1]], closing="Sincerely,",
    )
    profile = Profile(name="Jane Doe", email="jane@example.com", phone="555-0100")
    assert resume_docx(resume, profile).startswith(b"PK")
    assert resume_docx(resume).startswith(b"PK")  # profile optional
    assert cover_letter_docx(letter).startswith(b"PK")
