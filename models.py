from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class FactType(StrEnum):
    EXPERIENCE = "experience"
    PROJECT = "project"
    SKILL = "skill"
    ACHIEVEMENT = "achievement"
    EDUCATION = "education"


class Fact(BaseModel):
    id: int | None = None
    fact_type: FactType
    title: str
    organization: str = ""
    start_date: date | None = None
    end_date: date | None = None
    content: str
    skills: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    confirmed: bool = False
    created_at: datetime | None = None


class Profile(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    website: str = ""

    def contact_line(self) -> str:
        return " · ".join(x for x in [self.email, self.phone, self.location, self.website] if x)


class ExtractedFact(BaseModel):
    fact_type: FactType
    title: str
    organization: str = ""
    start_date: date | None = None
    end_date: date | None = None
    content: str
    skills: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)


class ResumeExtraction(BaseModel):
    facts: list[ExtractedFact]


class JDRequirement(BaseModel):
    id: str = Field(description="Stable short identifier such as R1")
    text: str
    kind: Literal["responsibility", "required", "preferred"]
    skills: list[str] = Field(default_factory=list)
    importance: int = Field(default=3, ge=1, le=5)


class JDAnalysis(BaseModel):
    role_title: str
    role_category: Literal[
        "Software Engineer", "AI Engineer", "Forward Deployed Engineer",
        "Solutions Architect", "Other"
    ]
    seniority: str = ""
    summary: str
    requirements: list[JDRequirement]


class EvidenceMatch(BaseModel):
    requirement_id: str
    status: Literal["strong", "partial", "gap"]
    score: int = Field(ge=0, le=100)
    fact_ids: list[int] = Field(default_factory=list)
    rationale: str
    suggestion: str


class MatchReport(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    matches: list[EvidenceMatch]
    top_strengths: list[str] = Field(default_factory=list)
    critical_gaps: list[str] = Field(default_factory=list)


class ResumeBullet(BaseModel):
    text: str
    fact_ids: list[int] = Field(min_length=1)
    requirement_ids: list[str] = Field(default_factory=list)


class ResumeEntry(BaseModel):
    title: str = Field(description="Job title, project name, or degree")
    organization: str = ""
    date_range: str = Field(default="", description='Display string such as "Jun 2023 – Present"; empty if unknown')
    fact_ids: list[int] = Field(min_length=1, description="Facts this entry's title/organization/dates come from")
    bullets: list[ResumeBullet] = Field(default_factory=list)


class ResumeSection(BaseModel):
    heading: str
    entries: list[ResumeEntry]


class ResumeDraft(BaseModel):
    summary: str
    summary_fact_ids: list[int] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    skill_fact_ids: list[int] = Field(default_factory=list)
    sections: list[ResumeSection]


class CoverLetterDraft(BaseModel):
    salutation: str
    paragraphs: list[str]
    paragraph_fact_ids: list[list[int]]
    closing: str

