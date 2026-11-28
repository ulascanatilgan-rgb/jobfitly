"""Deterministic eligibility and professional-title matching for Waydefine.

Hard gates run before AI, rankings and fallback. The CV is evidence; search
keywords express intent but cannot invent professional credentials.
"""
import re
from career_dna import career_dna
from matching import specialty_fit
from shared_inventory import _country_matches

ROLE_TYPES = {
    "operations": r"operations?|operational|business manager|chief of staff|founder.s associate|office manager|service delivery|process (?:improvement|excellence)|business support|executive assistant|operations coordinator",
    "project": r"project|programme|program|pmo|change manager|transformation|implementation|delivery manager|portfolio officer|portfolio manager",
    "risk": r"risk|audit|auditor|internal control|compliance|governance|fraud|financial crime|regulatory|aml|kyc|sox|quality assurance",
    "finance": r"bank|banking|finance|financial|investment|payments?|treasury|asset management|wealth|fund operations|reconciliation|capital markets|securities|insurance|insurtech|fintech",
    "strategy": r"strateg(y|ic)|corporate development|business analyst|business analysis|business planning|business performance|management consulting|operating model|value realization",
    "technology": r"it |information technology|cyber|security|iam|identity|access management|technology risk|tech risk|cloud|software|data|product owner|product manager|information systems",
    "sales": r"sales|business development|account manager|customer success|partnership|relationship manager|commercial|membership",
    "people": r"human resources|talent|recruit|people operations|learning and development|hr manager",
    "marketing": r"marketing|brand|graphic design|content creator|communication|creative|ux designer",
    "engineering": r"electrician|electrical|engineer|technician|mechanic|manufacturing|construction",
    "healthcare": r"nurs(e|ing)|doctor|pharmac|medical|clinical|healthcare",
    "education": r"teacher|educat|lectur|school|professor",
    "transport": r"driver|driving|chauffeur|courier|delivery rider|vehicle operator|truck|warehouse picker|forklift",
    "hospitality": r"chef|cook|waiter|bartender|kitchen|housekeeping|hotel receptionist",
}
FAMILY_MAP = {
    "Operations & management": {"operations", "strategy"},
    "Project & programme": {"project", "operations"},
    "Risk & compliance": {"risk", "finance"},
    "Finance & banking": {"finance", "risk"},
    "Security & technology": {"technology", "risk"},
    "Sales & partnerships": {"sales"},
    "Product & strategy": {"strategy", "technology", "project"},
    "People & talent": {"people"},
    "Design & marketing": {"marketing"},
    "Engineering & trades": {"engineering"},
    "Healthcare": {"healthcare"},
    "Education": {"education"},
}
ADJACENT = {
    "operations": {"project", "strategy", "finance", "risk"},
    "project": {"operations", "strategy", "technology"},
    "risk": {"operations", "finance", "project", "technology"},
    "finance": {"operations", "risk", "strategy"},
    "strategy": {"operations", "project", "finance"},
    "technology": {"risk", "project", "strategy"},
    "sales": {"operations", "strategy"},
    "people": {"operations"},
    "marketing": {"sales"},
    "engineering": {"project", "technology"},
    "healthcare": {"operations"},
    "education": {"project"},
}
CITIES = {
    "brussels": {"brussels","brussel","bruxelles","etterbeek","ixelles","elsene","auderghem","oudergem","woluwe","schaarbeek","schaerbeek","uccle","ukkel"},
    "antwerp": {"antwerp","antwerpen","anvers","berchem","deurne","merksem","wilrijk","kapellen","brasschaat","ekeren"},
    "ghent": {"ghent","gent","gand"},
    "liege": {"liège","liege","luik"},
    "leuven": {"leuven","louvain"},
}
CITY_ALIAS = {a:key for key,aliases in CITIES.items() for a in aliases}

def _hits(text,pattern):
    return bool(re.search(r"(?<!\w)(?:" + pattern + r")(?!\w)",str(text or "").casefold()))

def role_groups(title):
    """Classify the main actual advertised job title, not vague body text."""
    title=str(title or "").casefold()
    return {group for group,pattern in ROLE_TYPES.items() if _hits(title,pattern)}

def career_targets(profile):
    """Small and focused discovery queries, ordered by user intent and CV evidence."""
    cv=str(profile.get("cv_for_matching") or profile.get("cv_text_preview") or "")
    dna=profile.get("career_dna") or career_dna(cv)
    supported=set().union(*(FAMILY_MAP.get(row.get("name"),set())
                            for row in dna.get("role_families",[]) if isinstance(row,dict)))
    desired=role_groups(str(profile.get("keywords") or "").replace(",","; "))
    for path in profile.get("path_keywords") or []:
        desired |= role_groups(path)
    if any("Operations & strategy" in str(x) for x in
           (profile.get("swipes") or {}).get("role_type",[])):
        desired.update(("operations","strategy"))
    if any("Analytical" in str(x) for x in
           (profile.get("swipes") or {}).get("role_type",[])):
        desired.update(("risk","finance"))
    preferred=desired & (supported | set().union(*(ADJACENT.get(x,set()) for x in supported)))
    # Stable intent order: user's keyword order first, then actual CV career
    # families in evidence rank order, never unordered Python set iteration.
    user_groups=[]
    for phrase in re.split(r"[,;\n]+",str(profile.get("keywords") or "")):
        for group in sorted(role_groups(phrase)):
            if group not in user_groups:user_groups.append(group)
    for path in profile.get("path_keywords") or []:
        for group in sorted(role_groups(path)):
            if group not in user_groups:user_groups.append(group)
    supported_order=[]
    for row in dna.get("role_families",[]):
        if not isinstance(row,dict):continue
        for group in sorted(FAMILY_MAP.get(row.get("name"),set())):
            if group not in supported_order:supported_order.append(group)
    groups=list(dict.fromkeys(
        [g for g in user_groups if g in preferred]
        +[g for g in supported_order if g in supported]
        +sorted(preferred)))
    queries={
        "operations":["business operations manager","operations manager","operations specialist"],
        "project":["project manager","programme manager","PMO manager"],
        "risk":["risk manager","internal audit manager","compliance operations"],
        "finance":["banking operations manager","payments operations","investment operations"],
        "strategy":["strategy and operations","business manager","chief of staff"],
        "technology":["IT risk manager","security governance","identity access management"],
        "sales":["business development manager","customer success manager"],
        "people":["people operations manager","HR business partner"],
        "marketing":["marketing operations manager"],
        "engineering":["engineering project manager","electrical technician"],
        "healthcare":["healthcare operations manager"],
        "education":["education programme manager"],
    }
    ordered=[]
    # A user's own relevant keywords come first, not their CV's broad vocabulary.
    for phrase in re.split(r"[,;\n]+",str(profile.get("keywords") or "")):
        phrase=phrase.strip()
        if 3<=len(phrase)<=65 and len(phrase.split())<=6 and role_groups(phrase)&(supported|preferred):
            ordered.append(phrase)
    for group in groups:
        ordered.extend(queries.get(group,[])[:2])
    return list(dict.fromkeys(ordered))[:10]

def role_relevance(job,profile,dna=None):
    """0..100 title/domain relevance. Unrelated titles get 0 irrespective of description."""
    title=job.get("title") or ""
    cv_evidence=profile.get("cv_for_matching") or profile.get("cv_text_preview") or ""
    if not specialty_fit(title,cv_evidence):return 0
    groups=role_groups(title)
    if not groups:return 0
    cv=str(profile.get("cv_for_matching") or "")
    dna=dna or profile.get("career_dna") or career_dna(cv)
    support=set().union(*(FAMILY_MAP.get(r.get("name"),set())
                          for r in dna.get("role_families",[]) if isinstance(r,dict)))
    if not support:return 0
    # A generic 'operations' word must never disguise a specialist track:
    # e.g. People Operations or Vehicle Operations without proven experience.
    restricted={"people","healthcare","education","transport","hospitality"}
    if any(group in groups and group not in support for group in restricted):
        return 0
    adjacent=set().union(*(ADJACENT.get(group,set()) for group in support))
    target_groups=set().union(*(role_groups(q) for q in career_targets(profile)))
    # Professional track matters more than soft skills or generic text overlap.
    if groups & support:return 98 if groups & target_groups else 90
    if groups & adjacent and groups & target_groups:return 85
    if groups & adjacent:return 69
    return 0

def location_eligible(job,profile):
    """Country hard gate, and explicit city shortlist where one was entered."""
    country=str(profile.get("country") or "").strip()
    if country and not _country_matches(job,country):return False
    user_city=str(profile.get("city") or "").strip()
    if not user_city or user_city.casefold() in {"any","all","anywhere","all cities","nationwide","belgium","remote"}:
        return True
    # Support multiple explicit cities rather than silently applying one.
    requested=[x.strip().casefold() for x in re.split(r"[,;|/&]+",user_city) if x.strip()]
    if not requested:return True
    place=" ".join(str(job.get(key) or "") for key in ("city","location_label")).casefold()
    # Countrywide and European remote roles are eligible without a single-city address.
    if any(s in place for s in ("remote","anywhere in","throughout","nationwide","countrywide","all belgium")):
        return True
    for city in requested:
        family=CITY_ALIAS.get(city,city)
        aliases=CITIES.get(family,{city})
        if any(_hits(place,re.escape(alias)) for alias in aliases):return True
    return False

def role_eligible(job,profile,dna=None):
    return role_relevance(job,profile,dna)>=65
