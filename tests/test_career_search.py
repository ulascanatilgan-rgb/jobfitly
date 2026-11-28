"""Career-intent and geography regression tests, no network or API keys."""
import pytest
from career_search import role_groups, role_relevance, role_eligible, location_eligible, career_targets
from job_search import language_eligible

CV = ("Banking and payments operations, internal auditing and IT security risk "
      "governance. Managed financial controls, cross-functional change projects, "
      "stakeholders and process improvements at regulated institutions.")
PROFILE = {
    "cv_for_matching": CV,
    "keywords": "business operations, strategy, project manager",
    "country": "Belgium",
    "city": "Brussels",
    "language": "English",
    "swipes": {"role_type": ["Operations & strategy"], "sector": ["Finance"]},
}

@pytest.mark.parametrize("title", [
    "Business Operations Manager",
    "Strategy and Operations Lead",
    "Internal Audit Manager",
    "Risk & Compliance Manager",
    "Banking Operations Manager",
    "Project Manager - Financial Services",
    "Chief of Staff",
])
def test_professionally_related_titles_allowed(title):
    assert role_eligible({"title":title}, PROFILE), title

@pytest.mark.parametrize("title", [
    "Autonomous Car Driver",
    "Food Delivery Rider",
    "Warehouse Picker",
    "Bartender",
    "Registered Nurse",
    "Chef de Partie",
    "Software Engineer",
])
def test_unrelated_work_is_not_fill_for_five(title):
    assert not role_eligible({"title":title}, PROFILE), title

def test_user_search_direction_is_in_queries():
    targets="; ".join(career_targets(PROFILE)).lower()
    assert "business operations" in targets
    assert any(x in targets for x in ("risk", "audit", "banking", "operations"))

def test_geo_exact_city_and_remote():
    assert location_eligible({"city":"Brussels","country":"Belgium"},PROFILE)
    assert location_eligible({"city":"Ixelles","country":"Belgium"},PROFILE)
    assert location_eligible({"city":"Remote - Belgium","country":"Belgium"},PROFILE)
    assert not location_eligible({"city":"Ghent","country":"Belgium"},PROFILE)
    assert not location_eligible({"city":"New York","country":"United States"},PROFILE)

def test_multiple_city_selection():
    profile=dict(PROFILE,city="Brussels, Antwerp")
    assert location_eligible({"city":"Antwerp","country":"Belgium"},profile)
    assert not location_eligible({"city":"Ghent","country":"Belgium"},profile)

def test_language_is_hard_filter_before_role_fit():
    job={"title":"Banking Operations Manager - Dutch-speaking",
         "description":"Risk, finance and banking experience required.",
         "city":"Brussels","country":"Belgium"}
    assert role_eligible(job,PROFILE)
    assert not language_eligible(job,PROFILE["language"])
