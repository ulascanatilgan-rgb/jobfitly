"""Adaptive discovery orchestration.

Search waves prioritize current employer vacancies and index-backed direct job
links (not scraping restricted job boards); stop based on CV-match quality,
not raw source count. All users get a bespoke set of career search terms.
"""
import re

from career_search import career_targets, role_relevance
from matching import _tokens, lexical_fit


def search_waves(profile):
    roles=career_targets(profile)
    if not roles:
        roles=(profile.get("occupation_profile") or {}).get("roles",[])[:8]
    roles=[str(x).strip() for x in roles if str(x).strip()]
    if not roles:
        roles=[str(profile.get("keywords") or "").strip()] if profile.get("keywords") else []
    if not roles:return []
    country=str(profile.get("country") or "").strip()
    belgium=country.casefold() in ("belgium","belgique","belgië","be")
    creative=bool(re.search(
        r"design|art|marketing|brand|music|film|media|culture|photograph|creative",
        " ".join(roles).lower()))
    groups=[
        ("employer",roles[:4],
         "Company career pages, SmartRecruiters, Greenhouse, Lever, Ashby, "
         "Workday, Teamtailor and employer-managed vacancy pages. Prefer direct "
         "employer application links and confirm location requirements."),
        ("major_boards",list(dict.fromkeys(roles[:2]+roles[4:7])),
         "Search indexed, individually clickable job listing URLs on LinkedIn "
         "(site:linkedin.com/jobs/view/), Indeed (site:indeed.com/viewjob or "
         "country-specific Indeed /viewjob?jk=...), StepStone "
         "(site:stepstone.be/jobs-- or /vacatures--), and employer careers. "
         "Do not return generic search or category listing pages."),
        ("adjacent_titles",list(dict.fromkeys(roles[:2]+roles[7:10])),
         "Look for CV-supported alternative job-title synonyms, role variants, "
         "and equivalent responsibilities on company careers pages and recognized "
         "local job boards; verify same occupational function and seniority."),
        ("last_mile",list(dict.fromkeys(roles[:2]+roles[10:14])),
         "Find additional high-quality employer-specific vacancies through "
         "indexed job postings, regional specialty boards, LinkedIn, Indeed, "
         "StepStone, Workday and ATS. No job-search result pages; actual job only."),
    ]
    if not belgium:
        # Other countries should not waste a paid web-search pass on Belgian
        # StepStone or be.indeed.com links.
        market={
            "netherlands":"stepstone.nl", "nederland":"stepstone.nl",
            "germany":"stepstone.de", "deutschland":"stepstone.de",
            "austria":"stepstone.at",
            "france":"fr.indeed.com", "united kingdom":"uk.indeed.com",
            "uk":"uk.indeed.com", "united states":"indeed.com",
            "usa":"indeed.com", "canada":"ca.indeed.com",
            "ireland":"ie.indeed.com", "luxembourg":"lu.indeed.com",
        }
        source=market.get(country.casefold())
        if source:
            groups=[(key,queries,notes.replace("site:stepstone.be/jobs-- or /vacatures--",
                                               "site:"+source+" individual vacancy pages"))
                    for key,queries,notes in groups]
        else:
            groups=[(key,queries,notes.replace("site:stepstone.be/jobs-- or /vacatures--",
                                               "local country job-board vacancy URLs"))
                    for key,queries,notes in groups]
    if belgium:
        extra=(" Also search Belgian jobs and employers using locally relevant "
               "location labels: Belgium, Bruxelles/Brussels, Antwerpen/Antwerp, "
               "Gent/Ghent, and other cities only where permitted by the "
               "user's city preferences.")
        groups=[(k,q,s+extra) for k,q,s in groups]
    if belgium and creative:
        k,q,s=groups[2]
        groups[2]=(k,q,s+" Search yaymonday.be/jobs/ individual creative vacancies.")
    output=[]
    for key,titles,sources in groups:
        if not titles:continue
        output.append({
            "wave":key,
            "search_focus":"; ".join(titles[:5]),
            "source_focus":sources,
        })
    return output


def preliminary_fit(job,profile):
    """Cheap 0..10 CV evidence proxy for deciding whether to broaden further.

    Deliberately not the final user-facing match score.
    """
    cv=str(profile.get("cv_for_matching") or profile.get("cv_text_preview") or "")
    title_strength=role_relevance(job,profile)
    if title_strength<65:return 0.0
    lex,_=lexical_fit(job,cv)
    cv_words=(profile.get("_match_cache") or {}).get("cv_words")
    if cv_words is None:cv_words=_tokens(cv)
    desc_words=_tokens(str(job.get("description") or "")[:7000])
    shared=len(cv_words & desc_words)
    context=min(100,shared*9)
    # Supported CV role titles can have different words than the advertisement.
    score=.52*title_strength+.28*lex+.20*context
    return round(min(10,score/10),2)


def qualified_pool_size(jobs,profile,limit=80):
    """Count distinctive, plausibly good roles, not generic remote feed volume."""
    seen=set();count=0
    for job in jobs:
        identity=(str(job.get("company") or "").casefold().strip(),
                  re.sub(r"\W+"," ",str(job.get("title") or "").casefold()).strip(),
                  str(job.get("city") or "").casefold().strip())
        if identity in seen:continue
        seen.add(identity)
        if preliminary_fit(job,profile)>=6.9:count+=1
        if count>=limit:break
    return count
