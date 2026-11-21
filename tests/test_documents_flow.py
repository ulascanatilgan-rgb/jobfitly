"""Regression tests for reference-style PDF templates and six-step navigation."""
import io
from pathlib import Path

from pypdf import PdfReader
import pytest

from pdf_documents import motivation_pdf, _extract_motivation_sections
from pdf_cv_sidebar import tailored_cv_pdf


def _sample_motivation():
    intro = (
        "I bring hands-on experience in financial operations, risk controls, "
        "stakeholder communication and practical reporting. "
        "I would welcome the opportunity to apply this combination of "
        "skills to the organisation's operations."
    )
    points = [
        ("Financial operations", "Reviewed operational controls and banking transactions as documented in the candidate's experience."),
        ("Risk and governance", "Assessed business risks, validated evidence and presented practical findings to managers."),
        ("Project coordination", "Coordinated cross-functional reviews and kept workstreams aligned on key deliverables."),
        ("Stakeholder engagement", "Worked with internal teams, auditors and external consultants in regulated organisations."),
        ("Practical ownership", "Managed operational tasks and followed projects from planning through execution."),
        ("Technology and reporting", "Used systems and concise reporting to make operational processes clearer."),
        ("Contribution", "Can bring analytical discipline, clear follow-up and proven collaboration to the target function."),
    ]
    return intro + "\n\n" + "\n\n".join(
        f"{i}. {title}\n{body}" for i,(title,body) in enumerate(points,1))


def test_motivation_uses_single_page_reference_layout():
    pdf=motivation_pdf(
        "Alex Morgan","Operations & Finance Manager",
        "Example International Institute",_sample_motivation(),
        city="Brussels, Belgium",email="alex@example.org"
    )
    pages=PdfReader(io.BytesIO(pdf)).pages
    assert len(pages)==1
    text=pages[0].extract_text()
    assert "MOTIVATION" in text
    assert "Operations & Finance Manager" in text
    assert "Example International Institute" in text
    assert "Alex Morgan" in text
    assert "alex@example.org" in text
    assert "1." in text and "7." in text


def test_motivation_numbering_must_be_complete():
    incomplete="Intro.\n\n1. One\nEvidence.\n\n2. Two\nEvidence."
    with pytest.raises(ValueError,match="seven"):
        _extract_motivation_sections(incomplete)


def test_tailored_cv_has_professional_header_and_original_evidence():
    body=(
        "Alex Morgan\n"
        "PROFILE\nFinancial operations and stakeholder coordination professional.\n"
        "EXPERIENCE\nOperations Manager | Example Bank | 2021-2025\n"
        "- Directed operational processes and managed cross-team reporting.\n"
        "- Reviewed risk controls and improved governance documentation.\n"
        "EDUCATION\nBachelor in Business Administration, 2018\n"
        "SKILLS\n- Operations\n- Financial controls\n"
    )
    pdf=tailored_cv_pdf(
        "Alex Morgan","Operations Manager","Example Employer",body,
        city="Brussels, Belgium",email="alex@example.org"
    )
    pages=PdfReader(io.BytesIO(pdf)).pages
    assert len(pages)==1
    text="\n".join(page.extract_text() for page in pages)
    assert "Alex Morgan" in text
    assert "Operations Manager" in text
    assert "EXPERIENCE" in text
    assert "Example Bank" in text
    assert "Financial controls" in text


def test_six_step_page_and_original_portrait_file():
    base=Path(__file__).resolve().parents[1]
    html=(base/"templates"/"index.html").read_text()
    js=(base/"static"/"flow.js").read_text()
    assert 'flow-app-header' in html
    assert 'executive-office-original.png' in html
    assert (base/"static"/"executive-office-original.png").is_file()
    assert js.count('id:"')==6
    for title in (
        "Upload your CV","Tell about yourself","What you search",
        "Let's find","Watchlist","History"
    ):
        assert title in js
    assert 'Your profile' in html and 'Log out' in html
