"""Golden inputs for the eval harness: realistic JDs with known expectations,
and a fixture fact library with deliberate strengths and gaps."""
from __future__ import annotations

from models import Fact, FactType

# The fixture library clearly supports Python/FastAPI/PostgreSQL/AWS and LLM/RAG
# work, and deliberately contains nothing about Kubernetes or Go — so a correct
# matcher must not mark those requirements "strong".
FIXTURE_FACTS = [
    Fact(id=1, fact_type=FactType.EXPERIENCE, title="Backend engineer, payments platform",
         organization="Acme Corp",
         content="Designed and operated payment APIs in Python/FastAPI backed by PostgreSQL on AWS; "
                 "owned schema design, query optimization, and on-call.",
         skills=["Python", "FastAPI", "PostgreSQL", "AWS"],
         metrics=["processed $2M in daily volume", "cut p99 latency 40%"], confirmed=True),
    Fact(id=2, fact_type=FactType.PROJECT, title="RAG support chatbot (side project)",
         content="Built a retrieval-augmented chatbot over product docs using OpenAI embeddings, "
                 "a local vector store, and prompt templates; wrote an eval script comparing retrieval settings.",
         skills=["Python", "LLM", "RAG", "embeddings"],
         metrics=["answered 85% of test questions correctly"], confirmed=True),
    Fact(id=3, fact_type=FactType.EXPERIENCE, title="Software engineering intern",
         organization="Beta Inc",
         content="Built an internal analytics dashboard in React and TypeScript consuming a REST API.",
         skills=["React", "TypeScript"], metrics=[], confirmed=True),
    Fact(id=4, fact_type=FactType.ACHIEVEMENT, title="University hackathon winner",
         content="Won first place among 40 teams with a scikit-learn pipeline predicting bus delays.",
         skills=["Python", "scikit-learn"], metrics=["1st of 40 teams"], confirmed=True),
    Fact(id=5, fact_type=FactType.EDUCATION, title="B.S. Computer Science",
         organization="State University", content="Bachelor of Science in Computer Science.",
         skills=[], metrics=[], confirmed=True),
    Fact(id=6, fact_type=FactType.SKILL, title="CI/CD tooling",
         content="Set up GitHub Actions pipelines with Docker builds and automated test gates for team repos.",
         skills=["Docker", "GitHub Actions"], metrics=[], confirmed=True),
]

GOLDEN_JDS = [
    {
        "name": "backend_swe",
        "expected_category": "Software Engineer",
        "min_requirements": 5,
        # Requirements mentioning this term must NOT be scored "strong" —
        # the fixture facts contain no Kubernetes experience.
        "gap_term": "Kubernetes",
        # Requirements mentioning this term should cite this fixture fact as evidence.
        "strong_term": "Python",
        "expected_fact_id": 1,
        "text": """
Software Engineer, Backend — Meridian Pay

Meridian Pay builds payment infrastructure for marketplaces. We're hiring a backend
engineer to own core money-movement services.

What you'll do:
- Design, build, and operate REST APIs in Python that move money reliably at scale
- Model financial data in PostgreSQL and keep queries fast as volume grows
- Deploy and operate services on AWS with infrastructure-as-code
- Participate in on-call and drive down incident rates

Requirements:
- 2+ years building backend services in Python (FastAPI, Django, or Flask)
- Strong SQL and schema design skills, ideally PostgreSQL
- Production experience on AWS
- Experience deploying and operating workloads on Kubernetes
- Solid testing habits and comfort with CI/CD pipelines

Nice to have:
- Payments or fintech domain experience
- Experience with event-driven architectures
""",
    },
    {
        "name": "ai_engineer",
        "expected_category": "AI Engineer",
        "min_requirements": 5,
        "gap_term": "Go",
        "strong_term": "RAG",
        "expected_fact_id": 2,
        "text": """
AI Engineer — Northstar Labs

Northstar Labs ships LLM-powered features for enterprise knowledge work. You'll take
LLM applications from prototype to production.

What you'll do:
- Build retrieval-augmented generation (RAG) pipelines over customer document sets
- Design prompt and evaluation strategies; measure quality with LLM-as-judge metrics
- Ship Python services that call foundation-model APIs with structured outputs
- Instrument LLM features with tracing and observability

Requirements:
- Strong Python engineering skills
- Hands-on experience building LLM applications (RAG, embeddings, vector search)
- Experience evaluating LLM output quality systematically
- Experience writing high-performance services in Go
- Familiarity with cloud deployment (AWS or GCP)

Nice to have:
- Experience with LangChain, LangGraph, or similar orchestration frameworks
- Prior work on developer tools
""",
    },
]
