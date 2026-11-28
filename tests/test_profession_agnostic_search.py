"""Profession-neutral matching regression tests: five unrelated CV backgrounds."""
import pytest
from career_search import career_targets, role_eligible, role_relevance
from occupation_profile import cv_role_titles, occupation_profile

CASES=[
 (
  "Legal Counsel\n8 years legal practice, litigation and commercial contracts; qualified lawyer, legal drafting.",
  "Legal Counsel",["Legal Counsel","Attorney","Litigation Lawyer"],"Forklift Driver"
 ),
 (
  "Medical Doctor\nPhysician in general practice, patient diagnosis, clinical care, medical residency.",
  "General Practitioner",["Physician","Medical Doctor","General Practitioner"],"Marketing Manager"
 ),
 (
  "Occupational Health and Safety Officer\nHSE and EHS safety inspections, workplace safety, NEBOSH, risk assessment.",
  "HSE Specialist",["Health and Safety Officer","Safety Manager","HSE Specialist"],"Restaurant Chef"
 ),
 (
  "Qualified Electrician\nApprenticeship and installation, electrical maintenance, industrial wiring.",
  "Electrician",["Industrial Electrician","Maintenance Technician"],"Registered Nurse"
 ),
 (
  "Restaurant Chef\nWorked as head chef, pastry and baking, kitchen management, culinary experience.",
  "Head Chef",["Chef de Partie","Head Chef"],"Investment Analyst"
 ),
 (
  "Research Scientist\nPostdoctoral laboratory researcher, biomedical research methods and experiments.",
  "Research Scientist",["Research Associate","Research Scientist"],"Bus Driver"
 ),
]
@pytest.mark.parametrize("cv,expected,compatible,unrelated",CASES)
def test_each_users_occupation_drives_search(cv,expected,compatible,unrelated,monkeypatch):
 monkeypatch.delenv("OPENAI_API_KEY",raising=False)
 profile={"cv_for_matching":cv,"keywords":expected,"language":"English","country":"Belgium"}
 found=" ".join(career_targets(profile)).casefold()
 assert expected.casefold() in found,(expected,found)
 assert role_eligible({"title":expected},profile)
 assert any(role_eligible({"title":role},profile) for role in compatible)
 assert not role_eligible({"title":unrelated},profile)

def test_occupation_profile_offline_is_per_user(monkeypatch):
 monkeypatch.delenv("OPENAI_API_KEY",raising=False)
 legal=occupation_profile({"cv_for_matching":"Legal Counsel\nCommercial law and legal drafting"})
 clinical=occupation_profile({"cv_for_matching":"Medical Doctor\nGeneral practice and clinical care"})
 assert legal["roles"] != clinical["roles"]
 assert "Legal Counsel" in legal["roles"]
 assert "Medical Doctor" in clinical["roles"]

def test_unknown_profession_from_real_cv_not_blocked():
 profile={"cv_for_matching":"Hydrogeologist\nWorked on groundwater mapping and groundwater models."}
 assert "Hydrogeologist" in cv_role_titles(profile["cv_for_matching"])
 assert role_relevance({"title":"Hydrogeologist"},profile)>=65

def test_wished_but_unsupported_specialty_is_rejected():
 profile={"cv_for_matching":"Banking Operations Manager\nPayments, internal control, audit.",
          "keywords":"Surgeon, barrister, truck driver"}
 for title in ("Surgeon","Barrister","Truck Driver"):
  assert not role_eligible({"title":title},profile)

@pytest.mark.parametrize("cv,forbidden",[
 ("Medical Doctor\nPhysician managing general practice and diagnosis.","Registered Nurse"),
 ("Medical Doctor\nPhysician managing general practice and diagnosis.","Licensed Pharmacist"),
 ("Solicitor\nLegal counsel handling corporate contracts.","General Practitioner"),
 ("HSE Specialist\nOccupational health and safety inspections.","Legal Counsel"),
])
def test_professional_licenses_are_not_transferable(cv,forbidden):
 profile={"cv_for_matching":cv}
 assert not role_eligible({"title":forbidden},profile)
