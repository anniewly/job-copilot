# Job Copilot MVP

A local, single-user AI job application workbench. It keeps "confirmed facts", "job requirements", and "generated copy" separate, and requires every generated statement to carry fact evidence.

## Quick start

Python 3.13 recommended (3.11 minimum).

```bash
/opt/anaconda3/bin/python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY
streamlit run app.py
```

Data is stored in `data/job_copilot.db` by default. The default model is `claude-opus-5`, overridable via `ANTHROPIC_MODEL`.

## Workflow

1. Upload or paste your resume in "Experience Facts" — AI extracts draft facts for you to review and save. You can also add facts manually.
2. Paste a JD and run parse & match.
3. Review each requirement, gap, and fact citation.
4. Generate the resume or cover letter, check citations, export to Word.
5. Update status and notes in "Applications".

## Trust boundaries

- Unconfirmed facts are never sent to the material generators.
- Matches, resume bullets, and cover letter paragraphs all store fact IDs.
- The code rejects unknown fact IDs, uncovered JD requirements, and unsupported paragraphs.
- AI output still requires human review; fact-ID validation prevents unsourced citations but does not replace semantic checking.

## Modules

- `app.py`: Streamlit UI
- `database.py`: SQLite
- `models.py`: Pydantic data contracts
- `jd_parser.py` / `matcher.py`: JD parsing and evidence matching
- `resume_generator.py` / `cover_letter.py`: material generation with citation validation
- `document_export.py`: Word export
