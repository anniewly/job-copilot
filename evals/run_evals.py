"""Eval harness for the Job Copilot AI pipeline.

Run:  python -m evals.run_evals            (full: parser + matcher + resume faithfulness)
      python -m evals.run_evals --fast     (skip resume generation + LLM judge)

Checks each pipeline stage against golden JDs and a fixture fact library, plus an
LLM-as-judge faithfulness metric: does any resume bullet claim more than its cited
facts support? Results are printed and written to evals/results/<timestamp>.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv()

from ai_client import structured_response  # noqa: E402
from evals.golden import FIXTURE_FACTS, GOLDEN_JDS  # noqa: E402
from jd_parser import parse_jd  # noqa: E402
from matcher import match  # noqa: E402
from models import Fact, JDAnalysis, MatchReport  # noqa: E402
from resume_generator import MAX_BULLETS_PER_ENTRY, generate_resume  # noqa: E402


class BulletVerdict(BaseModel):
    verdict: Literal["supported", "exaggerated", "unsupported"]
    reason: str


JUDGE_SYSTEM = """You are a strict resume-faithfulness judge. You receive one resume bullet and the
verified facts it cites. Verdicts:
- supported: every claim in the bullet, including numbers and scope, is backed by the cited facts.
- exaggerated: the substance is real but the bullet inflates scope, numbers, seniority, or impact.
- unsupported: the bullet contains a claim with no basis in the cited facts.
Rewording and reordering are fine; only judge substance. Be strict about numbers."""


def judge_bullet(bullet_text: str, cited_facts: list[Fact]) -> BulletVerdict:
    payload = {
        "bullet": bullet_text,
        "cited_facts": [f.model_dump(mode="json") for f in cited_facts],
    }
    return structured_response(JUDGE_SYSTEM, json.dumps(payload, ensure_ascii=False),
                               BulletVerdict, name="judge_bullet_faithfulness")


def check(results: list[dict], name: str, passed: bool, detail: str = "") -> None:
    results.append({"check": name, "passed": bool(passed), "detail": detail})
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))


def requirements_mentioning(jd: JDAnalysis, term: str) -> list[str]:
    term = term.lower()
    return [r.id for r in jd.requirements
            if term in r.text.lower() or any(term in s.lower() for s in r.skills)]


def eval_parser(golden: dict, results: list[dict]) -> JDAnalysis:
    jd = parse_jd(golden["text"])
    check(results, f"{golden['name']}: role category",
          jd.role_category == golden["expected_category"],
          f"got {jd.role_category}")
    check(results, f"{golden['name']}: >= {golden['min_requirements']} requirements",
          len(jd.requirements) >= golden["min_requirements"], f"got {len(jd.requirements)}")
    ids = [r.id for r in jd.requirements]
    check(results, f"{golden['name']}: requirement ids unique", len(ids) == len(set(ids)))
    check(results, f"{golden['name']}: has required-kind items",
          any(r.kind == "required" for r in jd.requirements))
    check(results, f"{golden['name']}: gap term extracted",
          bool(requirements_mentioning(jd, golden["gap_term"])),
          f"looking for {golden['gap_term']!r}")
    return jd


def eval_matcher(golden: dict, jd: JDAnalysis, results: list[dict]) -> MatchReport:
    # match() itself enforces coverage and citation validity by raising.
    try:
        report = match(jd, FIXTURE_FACTS)
    except ValueError as exc:
        check(results, f"{golden['name']}: match structural validity", False, str(exc))
        raise
    check(results, f"{golden['name']}: match structural validity", True)

    gap_ids = requirements_mentioning(jd, golden["gap_term"])
    gap_ok = all(m.status != "strong" for m in report.matches if m.requirement_id in gap_ids)
    check(results, f"{golden['name']}: no fabricated strength for {golden['gap_term']!r}",
          gap_ok, f"requirements {gap_ids}")

    # Conservative grading (partial instead of strong) is fine; what matters is that
    # the right evidence is linked and the requirement is not written off as a gap.
    strong_ids = requirements_mentioning(jd, golden["strong_term"])
    strong_ok = any(golden["expected_fact_id"] in m.fact_ids and m.status != "gap"
                    for m in report.matches if m.requirement_id in strong_ids)
    check(results, f"{golden['name']}: evidence linked for {golden['strong_term']!r}",
          strong_ok, f"requirements {strong_ids}, expect fact #{golden['expected_fact_id']}")
    return report


def eval_resume(golden: dict, jd: JDAnalysis, report: MatchReport, results: list[dict]) -> dict:
    draft = generate_resume(jd, report, FIXTURE_FACTS)
    facts_by_id = {f.id: f for f in FIXTURE_FACTS}

    bullet_cap_ok = all(len(e.bullets) <= MAX_BULLETS_PER_ENTRY
                        for s in draft.sections for e in s.entries)
    check(results, f"{golden['name']}: <= {MAX_BULLETS_PER_ENTRY} bullets per entry", bullet_cap_ok)

    verdicts = []
    for section in draft.sections:
        for entry in section.entries:
            for bullet in entry.bullets:
                cited = [facts_by_id[i] for i in bullet.fact_ids]
                verdict = judge_bullet(bullet.text, cited)
                verdicts.append({"bullet": bullet.text, "verdict": verdict.verdict,
                                 "reason": verdict.reason})
    supported = sum(1 for v in verdicts if v["verdict"] == "supported")
    rate = supported / len(verdicts) if verdicts else 0.0
    check(results, f"{golden['name']}: bullet faithfulness >= 90%", rate >= 0.9,
          f"{supported}/{len(verdicts)} supported ({rate:.0%})")
    for v in verdicts:
        if v["verdict"] != "supported":
            print(f"        {v['verdict'].upper()}: {v['bullet']!r} — {v['reason']}")
    return {"faithfulness_rate": rate, "verdicts": verdicts}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true",
                        help="skip resume generation and the LLM judge")
    args = parser.parse_args()

    results: list[dict] = []
    metrics: dict = {}
    for golden in GOLDEN_JDS:
        print(f"\n=== {golden['name']} ===")
        jd = eval_parser(golden, results)
        report = eval_matcher(golden, jd, results)
        metrics[f"{golden['name']}_overall_score"] = report.overall_score
        if not args.fast:
            metrics[f"{golden['name']}_resume"] = eval_resume(golden, jd, report, results)

    passed = sum(1 for r in results if r["passed"])
    print(f"\n{'=' * 40}\n{passed}/{len(results)} checks passed")

    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out_path.write_text(json.dumps(
        {"timestamp": datetime.now(timezone.utc).isoformat(),
         "passed": passed, "total": len(results),
         "checks": results, "metrics": metrics}, indent=2, ensure_ascii=False))
    print(f"Report written to {out_path}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
