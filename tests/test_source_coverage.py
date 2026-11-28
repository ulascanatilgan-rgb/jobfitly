"""Regression checks: wider sources without invented or search-result jobs."""
from job_search import _canonical, _source_name
from search_quality import search_waves, preliminary_fit, qualified_pool_size
from preferences import preference_constraints_match, _mode_evidence

CV=("Banking Operations Manager\nExperience in banking operations, "
    "risk governance, internal audit, regulatory controls, payments, "
    "business process improvement and project management.")
PROFILE={
    "cv_for_matching":CV,
    "country":"Belgium","city":"","language":"English",
    "keywords":"business operations, banking operations, project manager",
}

def test_direct_posting_urls_are_indexable():
    assert _canonical("https://be.linkedin.com/jobs/view/operations-manager-at-test-4493754425")
    assert _canonical("https://emplois.be.indeed.com/viewjob?jk=0929e16c826dbd3d")
    assert _canonical("https://www.stepstone.be/jobs--Accountant-International-Consulting-Brussels-Sander-Brussels--2252234-inline.html")
    assert _canonical("https://www.yaymonday.be/jobs/senior-marketing-content-coordinator-fuse-brussels")

def test_duplicate_indeed_url_identity_uses_job_id():
    one=_canonical("https://be.indeed.com/viewjob?jk=aaaa1111")
    two=_canonical("https://be.indeed.com/viewjob?jk=bbbb2222")
    assert one!=two

def test_never_accept_job_search_result_page_as_a_vacancy():
    assert _canonical("https://be.linkedin.com/jobs/operations-jobs") is None
    assert _canonical("https://www.stepstone.be/jobs/business-operations") is None
    assert _canonical("https://be.indeed.com/q-operations-jobs.html") is None
    assert _canonical("https://www.yaymonday.be/find-a-job") is None

def test_search_waves_cover_major_board_indices_and_employer_ats():
    waves=search_waves(PROFILE)
    assert len(waves)==4
    assert "Employer" not in waves[0]["wave"]  # machine-readable key
    major=next(w for w in waves if w["wave"]=="major_boards")["source_focus"]
    assert "LinkedIn" in major
    assert "Indeed" in major
    assert "StepStone" in major
    assert "jobs/view/" in major
    assert "business operations" in waves[1]["search_focus"].lower()

def test_preliminary_quality_distinguishes_driver_from_banking():
    relevant={"title":"Banking Operations Manager",
              "description":"Banking payments risk internal audit and governance"}
    unrelated={"title":"Autonomous Car Driver",
               "description":"Vehicle transport and deliveries"}
    assert preliminary_fit(relevant,PROFILE)>preliminary_fit(unrelated,PROFILE)
    assert qualified_pool_size([unrelated,unrelated],PROFILE)==0

def test_hybrid_work_patterns_from_local_market():
    assert _mode_evidence({"description":"Hybrid workplace, 2 days of thuiswerk."})=="Hybrid"
    assert _mode_evidence({"description":"Partially remote, 2 days from home."})=="Hybrid"
    assert _mode_evidence({"description":"100% remote work."})=="Remote"
    assert _mode_evidence({"description":"Fully on-site at the company office."})=="On-site"
    assert preference_constraints_match(
        {"description":"Hybrid workplace."},{"mode":["Remote","Hybrid","On-site"]})
