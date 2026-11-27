"""Regression tests for strict user-selected job language eligibility."""
import pytest
from job_search import language_eligible, required_languages

@pytest.mark.parametrize("title,description", [
    ("Account Manager — Dutch Speaker", "Excellent opportunity."),
    ("Customer Success (Dutch-speaking)", "International team."),
    ("Nederlandstalige projectcoördinator", "Open role."),
    ("Consultant NL/FR", "Projects in Belgium."),
    ("Operations Manager", "Fluent Dutch is required."),
    ("Business Analyst", "You must speak French."),
    ("Risk Officer", "Excellent knowledge of Nederlands."),
    ("Support Agent", "Bilingual English and Dutch required."),
    ("Project Manager", "Vloeiend Nederlands vereist."),
])
def test_english_only_rejects_other_required_languages(title, description):
    assert not language_eligible({"title": title, "description": description}, "English")

@pytest.mark.parametrize("title,description", [
    ("Business Operations Manager", "Fluent English required."),
    ("Project Coordinator", "English mandatory. Dutch is a plus."),
    ("Risk Analyst", "Dutch is not required."),
    ("Business Analyst", "You will cover the Dutch market and French clients."),
])
def test_english_only_accepts_compatible_jobs(title, description):
    assert language_eligible({"title": title, "description": description}, "English")

def test_multi_language_selection():
    vacancy={"title": "Dutch-speaking Risk Analyst", "description": "English mandatory."}
    assert language_eligible(vacancy, "English, Dutch")
    assert not language_eligible(vacancy, "English")

def test_explicit_requirement_parsing():
    assert "dutch" in required_languages("Dutch speaker")
    assert "french" in required_languages("French-speaking project manager")
    assert "dutch" not in required_languages("Dutch is a plus.")
