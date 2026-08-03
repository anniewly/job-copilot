from __future__ import annotations

import json
import os

import streamlit as st
from dotenv import load_dotenv

import database as db
from coach import coach_questions
from cover_letter import generate_cover_letter
from document_export import cover_letter_docx, resume_docx
from jd_parser import parse_jd
from matcher import match
from models import Fact, FactType, JDAnalysis, MatchReport, Profile
from resume_generator import generate_resume
from resume_profile import extract_facts_from_resume, read_resume_file

load_dotenv()
db.init_db()
profile = Profile.model_validate_json(db.get_setting("profile") or "{}")

st.set_page_config(page_title="Job Copilot", page_icon="🧭", layout="wide")
st.title("Job Copilot")
st.caption("Generate trustworthy, reviewable job application materials grounded in your confirmed experience facts.")

with st.sidebar:
    st.subheader("Status")
    if os.getenv("ANTHROPIC_API_KEY"):
        st.success(f"AI configured · {os.getenv('ANTHROPIC_MODEL', 'claude-opus-5')}")
    else:
        st.warning("ANTHROPIC_API_KEY not set")
    st.caption(f"Facts: {len(db.list_facts(confirmed_only=True))}")

    with st.expander("Profile (resume header)", expanded=not profile.name):
        with st.form("profile_form"):
            p_name = st.text_input("Name", value=profile.name)
            p_email = st.text_input("Email", value=profile.email)
            p_phone = st.text_input("Phone", value=profile.phone)
            p_location = st.text_input("Location", value=profile.location)
            p_website = st.text_input("Website / LinkedIn", value=profile.website)
            if st.form_submit_button("Save profile"):
                db.set_setting("profile", Profile(
                    name=p_name.strip(), email=p_email.strip(), phone=p_phone.strip(),
                    location=p_location.strip(), website=p_website.strip(),
                ).model_dump_json())
                st.rerun()

facts_tab, analyze_tab, materials_tab, tracker_tab = st.tabs(
    ["1. Experience Facts", "2. JD Analysis & Match", "3. Materials", "4. Applications"]
)

with facts_tab:
    st.subheader("Import from your resume")
    uploaded = st.file_uploader("Upload resume", type=["pdf", "docx", "txt", "md"])
    pasted = st.text_area("…or paste resume text", height=150, key="resume_paste")
    if st.button("Extract facts", type="primary"):
        try:
            with st.spinner("Extracting facts from your resume…"):
                if uploaded is not None:
                    text, pdf_bytes = read_resume_file(uploaded.name, uploaded.getvalue())
                else:
                    text, pdf_bytes = pasted, None
                st.session_state.fact_drafts = extract_facts_from_resume(text, pdf_bytes)
        except Exception as exc:
            st.error(str(exc))

    if "fact_drafts" in st.session_state:
        st.write(f"Extracted {len(st.session_state.fact_drafts)} facts. "
                 "Review them, untick anything wrong, then save.")
        for i, draft in enumerate(st.session_state.fact_drafts):
            cols = st.columns([1, 11])
            cols[0].checkbox("Include", value=True, key=f"draft_keep_{i}", label_visibility="collapsed")
            with cols[1].expander(f"{draft.fact_type.value} · {draft.title}", expanded=False):
                st.write(draft.content)
                if draft.organization:
                    st.caption("Organization: " + draft.organization)
                st.caption("Skills: " + (", ".join(draft.skills) or "—"))
                st.caption("Metrics: " + (", ".join(draft.metrics) or "—"))
        if st.button("Save selected facts", type="primary"):
            saved = 0
            for i, draft in enumerate(st.session_state.fact_drafts):
                if st.session_state.get(f"draft_keep_{i}"):
                    db.save_fact(draft.model_copy(update={"confirmed": True}))
                    saved += 1
            del st.session_state.fact_drafts
            st.success(f"Saved {saved} facts.")
            st.rerun()

    st.divider()
    st.subheader("Add an experience fact manually")
    with st.form("fact_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        fact_type = c1.selectbox("Type", list(FactType), format_func=lambda x: x.value)
        title = c2.text_input("Title *", placeholder="e.g. Payment platform backend refactor")
        organization = st.text_input("Company / Project")
        content = st.text_area("Verifiable fact *", placeholder="Describe what you actually did; no embellishment here.")
        skills = st.text_input("Skills (comma-separated)")
        metrics = st.text_input("Quantified results (comma-separated)")
        submitted = st.form_submit_button("Save fact", type="primary")
        if submitted:
            if not title.strip() or not content.strip():
                st.error("Title and fact content are required.")
            else:
                fact = Fact(
                    fact_type=fact_type, title=title.strip(), organization=organization.strip(),
                    content=content.strip(), skills=[x.strip() for x in skills.split(",") if x.strip()],
                    metrics=[x.strip() for x in metrics.split(",") if x.strip()],
                    confirmed=True,
                )
                db.save_fact(fact)
                st.success("Fact saved.")
                st.rerun()

    st.subheader("Fact list")
    facts = db.list_facts()
    if not facts:
        st.info("Add at least one fact to get started.")
    for fact in facts:
        with st.expander(f"#{fact.id} · {fact.title}"):
            st.write(fact.content)
            st.caption("Skills: " + (", ".join(fact.skills) or "—"))
            if st.button("Delete", key=f"delete_{fact.id}"):
                db.delete_fact(fact.id)
                st.rerun()

with analyze_tab:
    st.subheader("Analyze a target job")
    company = st.text_input("Company", key="company")
    role_title = st.text_input("Job title", key="role_title")
    url = st.text_input("Job URL (optional)", key="url")
    jd_text = st.text_area("Job Description", height=300, key="jd_text")
    if st.button("Parse & match", type="primary"):
        try:
            with st.status("Parsing JD and matching against your facts…", expanded=True) as status:
                jd = parse_jd(jd_text)
                st.write(f"Detected role: {jd.role_title} · {jd.role_category}")
                report = match(jd, db.list_facts(confirmed_only=True))
                job_id = db.save_job(
                    company.strip(), role_title.strip() or jd.role_title, url.strip(), jd_text,
                    jd.model_dump_json(), report.model_dump_json(),
                )
                st.session_state.update(jd=jd, report=report, job_id=job_id, company_active=company)
                status.update(label="Analysis complete", state="complete")
        except Exception as exc:
            st.error(str(exc))

    if "report" in st.session_state:
        jd: JDAnalysis = st.session_state.jd
        report: MatchReport = st.session_state.report
        st.metric("Overall match", f"{report.overall_score}%")
        for item in report.matches:
            req = next(r for r in jd.requirements if r.id == item.requirement_id)
            icon = {"strong": "✅", "partial": "🟡", "gap": "🔴"}[item.status]
            with st.expander(f"{icon} {req.id} · {req.text} · {item.score}%"):
                st.write(item.rationale)
                st.write("Suggestion: ", item.suggestion)
                st.caption("Evidence: " + (", ".join(f"#{x}" for x in item.fact_ids) or "none"))

        st.divider()
        st.subheader("Resume Coach")
        st.caption(
            "The coach interviews you about gaps and weak spots — often the experience exists, "
            "it just never made it into your facts. Honest answers only; blank or \"no\" is fine."
        )
        if st.button("Get coaching questions"):
            try:
                with st.spinner("Reviewing your match for things worth asking about…"):
                    st.session_state.coach = coach_questions(
                        jd, report, db.list_facts(confirmed_only=True)
                    )
            except Exception as exc:
                st.error(str(exc))

        if "coach" in st.session_state:
            requirements_by_id = {r.id: r for r in jd.requirements}
            for i, q in enumerate(st.session_state.coach.questions):
                st.markdown(f"**{i + 1}. {q.question}**")
                st.caption(f"Why it matters: {q.why}")
                st.text_area(
                    "Your answer (leave blank if it doesn't apply)",
                    key=f"coach_ans_{i}", height=80, label_visibility="collapsed",
                    placeholder="Leave blank if it doesn't apply — never invent anything.",
                )
            if st.button("Save answers & re-run match", type="primary"):
                answered = 0
                for i, q in enumerate(st.session_state.coach.questions):
                    answer = (st.session_state.get(f"coach_ans_{i}") or "").strip()
                    if not answer or answer.lower() in {"no", "n/a", "none"}:
                        continue
                    req = requirements_by_id[q.requirement_id]
                    db.save_fact(Fact(
                        fact_type=FactType.EXPERIENCE,
                        title=f"Coaching: {req.text[:60]}",
                        content=answer,
                        skills=req.skills,
                        confirmed=True,
                    ))
                    answered += 1
                if not answered:
                    st.warning("No answers to save.")
                else:
                    try:
                        with st.spinner(f"Saved {answered} new facts. Re-running match…"):
                            new_report = match(jd, db.list_facts(confirmed_only=True))
                            db.update_job_match(st.session_state.job_id, new_report.model_dump_json())
                            st.session_state.report = new_report
                            del st.session_state.coach
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

with materials_tab:
    st.subheader("Generate reviewable materials")
    if "report" not in st.session_state:
        st.info("Run a JD analysis and match first.")
    else:
        if st.button("Generate tailored resume", type="primary"):
            try:
                with st.spinner("Generating and validating fact citations…"):
                    draft = generate_resume(
                        st.session_state.jd, st.session_state.report,
                        db.list_facts(confirmed_only=True),
                    )
                    db.save_material(st.session_state.job_id, "resume", draft.model_dump_json())
                    st.session_state.resume_draft = draft
            except Exception as exc:
                st.error(str(exc))
        if "resume_draft" in st.session_state:
            draft = st.session_state.resume_draft
            st.markdown(f"### {profile.name or 'Your Name'}")
            if profile.contact_line():
                st.caption(profile.contact_line())
            st.write(draft.summary)
            st.write("**Skills:** " + ", ".join(draft.skills))
            for section in draft.sections:
                st.markdown(f"#### {section.heading}")
                for entry in section.entries:
                    header = f"**{entry.title}**"
                    if entry.organization:
                        header += f" — {entry.organization}"
                    if entry.date_range:
                        header += f" · {entry.date_range}"
                    st.markdown(header)
                    for bullet in entry.bullets:
                        st.write(f"• {bullet.text}")
                        st.caption("Evidence: " + ", ".join(f"fact #{x}" for x in bullet.fact_ids))
            st.download_button(
                "Download resume (Word)", resume_docx(draft, profile), "tailored_resume.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        if st.button("Generate cover letter"):
            try:
                with st.spinner("Generating and validating fact citations…"):
                    letter = generate_cover_letter(
                        st.session_state.get("company_active", ""),
                        st.session_state.jd, st.session_state.report,
                        db.list_facts(confirmed_only=True),
                    )
                    db.save_material(st.session_state.job_id, "cover_letter", letter.model_dump_json())
                    st.session_state.letter_draft = letter
            except Exception as exc:
                st.error(str(exc))
        if "letter_draft" in st.session_state:
            letter = st.session_state.letter_draft
            st.write(letter.salutation)
            for i, paragraph in enumerate(letter.paragraphs):
                st.write(paragraph)
                st.caption("Evidence: " + ", ".join(f"fact #{x}" for x in letter.paragraph_fact_ids[i]))
            st.write(letter.closing)
            st.download_button(
                "Download cover letter (Word)", cover_letter_docx(letter), "cover_letter.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

with tracker_tab:
    st.subheader("Application history")
    jobs = db.list_jobs()
    if not jobs:
        st.info("Analyze a job and it will show up here.")
    for job in jobs:
        with st.expander(f"#{job['id']} · {job['company']} · {job['title']} · {job['status']}"):
            status = st.selectbox(
                "Status", ["Interested", "Preparing", "Applied", "Interviewing", "Offer", "Rejected", "Withdrawn"],
                index=["Interested", "Preparing", "Applied", "Interviewing", "Offer", "Rejected", "Withdrawn"].index(job["status"]),
                key=f"status_{job['id']}",
            )
            notes = st.text_area("Notes", value=job["notes"], key=f"notes_{job['id']}")
            if st.button("Save", key=f"save_job_{job['id']}"):
                db.update_job_status(job["id"], status, notes)
                st.success("Saved.")

            materials = db.list_materials(job["id"])
            if materials:
                st.caption("Generated: " + ", ".join(
                    f"{m['kind']} v{m['version']}" for m in materials[:6]
                ))
            if job["jd_analysis_json"] and job["match_report_json"]:
                if st.button("Regenerate tailored resume", key=f"regen_{job['id']}"):
                    try:
                        with st.spinner("Regenerating from the stored JD analysis…"):
                            jd_stored = JDAnalysis.model_validate_json(job["jd_analysis_json"])
                            report_stored = MatchReport.model_validate_json(job["match_report_json"])
                            draft = generate_resume(
                                jd_stored, report_stored, db.list_facts(confirmed_only=True)
                            )
                            db.save_material(job["id"], "resume", draft.model_dump_json())
                            st.session_state[f"regen_draft_{job['id']}"] = draft
                    except Exception as exc:
                        st.error(str(exc))
                if f"regen_draft_{job['id']}" in st.session_state:
                    st.download_button(
                        "Download regenerated resume (Word)",
                        resume_docx(st.session_state[f"regen_draft_{job['id']}"], profile),
                        f"tailored_resume_job{job['id']}.docx",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"regen_dl_{job['id']}",
                    )
