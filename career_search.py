"""Profession-independent CV-first role discovery and eligibility.

Broad occupational taxonomy gives explainable signals; the personalized list
of occupations comes from the user's own CV and evidence-validated profile.
Unknown job titles can still match strongly documented CV roles. Hard gates
never rely on user preferences as proof of a license or career experience.
"""
import re
from career_dna import career_dna
from matching import specialty_fit
from occupation_profile import cv_role_titles
from shared_inventory import _country_matches

ROLE_TYPES={
 "operations":r"operations?|operational|business manager|chief of staff|founder.s associate|office manager|service delivery|process (?:improvement|excellence)|business support|executive assistant",
 "project":r"project|programme|program|pmo|change manager|transformation|implementation|delivery manager|portfolio officer|portfolio manager",
 "risk":r"risk|audit|auditor|internal control|compliance|governance|fraud|financial crime|regulatory|aml|kyc|sox|quality assurance",
 "finance":r"bank|banking|finance|financial|investment|payments?|treasury|asset management|wealth|fund operations|reconciliation|capital markets|securities|insurance|insurtech|fintech",
 "strategy":r"strateg(y|ic)|corporate development|business analyst|business analysis|business planning|business performance|management consulting|operating model|value realization",
 "technology":r"it |information technology|cyber|security|iam|identity|access management|technology risk|tech risk|cloud|software|data|product owner|product manager|information systems|systems administrator",
 "sales":r"sales|business development|account manager|customer success|partnership|relationship manager|commercial|membership",
 "people":r"human resources|talent|recruit|people operations|learning and development|hr manager",
 "marketing":r"marketing|brand|graphic design|content creator|communication|creative|ux designer",
 "engineering":r"electrician|electrical|engineer|technician|mechanic|manufacturing|construction",
 "medical":r"physician|medical doctor|general practitioner|family doctor|doctor|surgeon|dentist|radiologist|anesthetist|anaesthetist|psychiatrist|pediatrician|paediatrician",
 "nursing":r"registered nurse|nurse|nursing|midwife|paramedic|physiotherapist|occupational therapist|radiographer|clinical therapist",
 "pharmacy":r"pharmacist|pharmaceutical|pharmacy technician",
 "legal":r"lawyer|attorney|solicitor|barrister|legal counsel|general counsel|legal associate|litigation|paralegal|notary|jurist|advocate|contract lawyer|legal officer",
 "safety":r"occupational safety|health and safety|safety manager|safety officer|safety inspector|hse|ehs|workplace safety|industrial hygiene|occupational health|prevention advisor|safety specialist",
 "education":r"teacher|educat|lectur|school principal|professor|tutor|training manager|curriculum specialist",
 "trades":r"plumber|carpenter|welder|hvac|machinist|electrician|mechanic|maintenance technician|fabricator|industrial maintenance",
 "transport":r"driver|driving|chauffeur|courier|delivery rider|vehicle operator|truck|warehouse picker|forklift|fleet driver|bus operator|pilot",
 "hospitality":r"chef|cook|waiter|bartender|kitchen|housekeeping|hotel receptionist|baker|barista|restaurant manager|hospitality",
 "science":r"research scientist|scientist|postdoctoral|postdoc|laboratory|research fellow|biologist|chemist|physicist|geologist|research associate|researcher|clinical research",
 "nonprofit":r"social worker|social services|ngo|nonprofit|fundraising|public affairs|civil servant|public policy|government relations|case manager",
 "arts":r"artist|journalist|photographer|illustrator|editor|film producer|musician|graphic artist|art director|videographer|curator",
 "environment":r"agronomist|agriculture|ecologist|environmental|forestry|sustainability|conservation|farmer|horticulturist",
}
FAMILY_MAP={
 "Operations & management":{"operations","strategy"},
 "Project & programme":{"project","operations"},
 "Risk & compliance":{"risk","finance"},
 "Finance & banking":{"finance","risk"},
 "Security & technology":{"technology","risk"},
 "Sales & partnerships":{"sales"},
 "Product & strategy":{"strategy","technology","project"},
 "People & talent":{"people"},
 "Design & marketing":{"marketing"},
 "Engineering & trades":{"engineering"},
 "Healthcare":{"medical"},
 "Education":{"education"},
 "Legal & justice":{"legal"},
 "Occupational safety":{"safety"},
 "Medical & clinical practice":{"medical"},
 "Nursing & allied care":{"nursing"},
 "Pharmacy & medicines":{"pharmacy"},
 "Skilled trades":{"trades","engineering"},
 "Transport & logistics":{"transport"},
 "Hospitality & culinary":{"hospitality"},
 "Scientific research":{"science"},
 "Public service & nonprofit":{"nonprofit"},
 "Arts & media":{"arts"},
 "Agriculture & environment":{"environment"},
}
ADJACENT={
 "operations":{"project","strategy","finance","risk"},
 "project":{"operations","strategy","technology","engineering","science"},
 "risk":{"operations","finance","project","technology","safety"},
 "finance":{"operations","risk","strategy"},
 "strategy":{"operations","project","finance"},
 "technology":{"risk","project","strategy","engineering"},
 "sales":{"operations","strategy"},
 "people":{"operations"},
 "marketing":{"sales","arts"},
 "engineering":{"project","trades","safety"},
 "medical":{"science","nursing"},
 "nursing":{"medical"},
 "pharmacy":{"science","medical"},
 "legal":{"nonprofit","risk"},
 "safety":{"engineering","risk","operations"},
 "education":{"science","nonprofit"},
 "trades":{"engineering","safety"},
 "transport":{"operations"},
 "hospitality":{"operations"},
 "science":{"medical","environment","education"},
 "nonprofit":{"education","legal"},
 "arts":{"marketing"},
 "environment":{"science","engineering"},
}
CITIES={
 "brussels":{"brussels","brussel","bruxelles","etterbeek","ixelles","elsene","auderghem","oudergem","woluwe","schaarbeek","schaerbeek","uccle","ukkel"},
 "antwerp":{"antwerp","antwerpen","anvers","berchem","deurne","merksem","wilrijk","kapellen","brasschaat","ekeren"},
 "ghent":{"ghent","gent","gand"},
 "liege":{"liège","liege","luik"},
 "leuven":{"leuven","louvain"},
}
CITY_ALIAS={a:key for key,aliases in CITIES.items() for a in aliases}
GENERIC_WORDS=set("senior junior head lead chief assistant associate manager management specialist officer role job position expert professional trainee graduate business service services team member staff and the of for in on at to".split())

def _hits(text,pattern):
 return bool(re.search(r"(?<!\w)(?:"+pattern+r")(?!\w)",str(text or "").casefold()))

def role_groups(title):
 """Classify specific advertised role functions (not generic CV descriptions)."""
 return {group for group,pattern in ROLE_TYPES.items() if _hits(title,pattern)}

def _role_tokens(title):
 """Skip seniority/filler words, retaining specialty-bearing occupational terms."""
 return {token for token in re.findall(r"[a-zà-ÿ]{3,}",str(title or "").casefold())
         if token not in GENERIC_WORDS}

def _title_overlap(a,b):
 ta,tb=_role_tokens(a),_role_tokens(b)
 if not ta or not tb:return 0
 return len(ta&tb)/max(1,len(ta|tb))

def _support_groups(profile,dna):
 cv=str(profile.get("cv_for_matching") or profile.get("cv_text_preview") or "")
 support=set().union(*(FAMILY_MAP.get(row.get("name"),set())
                      for row in dna.get("role_families",[]) if isinstance(row,dict)))
 # Recognize explicit occupational CV language even if the older cached
 # career_dna was generated before a new profession was added.
 for group,pattern in ROLE_TYPES.items():
  if _hits(cv,pattern):support.add(group)
 return support

def _validated_roles(profile):
 # AI-generated roles are checked against literal CV evidence by occupation_profile.
 roles=(profile.get("occupation_profile") or {}).get("roles",[])
 if not isinstance(roles,list):roles=[]
 cv=str(profile.get("cv_for_matching") or profile.get("cv_text_preview") or "")
 return list(dict.fromkeys(
  [s for s in roles if isinstance(s,str) and 3<len(s)<=95]
  +cv_role_titles(cv)))[:17]

def career_targets(profile):
 """Search titles derived from the person's CV and selected directions."""
 cv=str(profile.get("cv_for_matching") or profile.get("cv_text_preview") or "")
 dna=profile.get("career_dna") or career_dna(cv)
 support=_support_groups(profile,dna)
 allowed=set(support)
 for group in support:allowed.update(ADJACENT.get(group,set()))
 result=[]
 # Highest priority: user search interests which are supported by CV roles
 # or related specialties; preferences never manufacture credentials.
 for phrase in re.split(r"[,;\n]+",str(profile.get("keywords") or "")):
  phrase=phrase.strip()
  if not 3<len(phrase)<=70 or len(phrase.split())>8:continue
  if role_groups(phrase)&allowed or any(_title_overlap(phrase,r)>=.45 for r in _validated_roles(profile)):
   result.append(phrase)
 for p in profile.get("path_keywords") or []:
  if isinstance(p,str) and (role_groups(p)&allowed or any(_title_overlap(p,r)>=.45 for r in _validated_roles(profile))):
   result.append(p.strip())
 result.extend(_validated_roles(profile))
 # Universal fallback for all professions: generate specialty-based titles
 # from the actual user's CV, not from one banking/technology example.
 titles={
  "legal":["legal counsel","lawyer","solicitor"],
  "medical":["medical doctor","general practitioner","physician"],
  "nursing":["registered nurse","nursing specialist","clinical nurse"],
  "pharmacy":["pharmacist","clinical pharmacist"],
  "safety":["health and safety officer","HSE specialist","safety manager"],
  "trades":["electrician","maintenance technician","skilled tradesperson"],
  "transport":["professional driver","logistics coordinator"],
  "hospitality":["chef","restaurant manager","hospitality manager"],
  "science":["research scientist","research associate","laboratory specialist"],
  "arts":["creative designer","visual artist","art director"],
  "environment":["environmental specialist","sustainability manager"],
  "nonprofit":["policy officer","programme coordinator"],
  "operations":["business operations manager","operations manager"],
  "project":["project manager","programme manager"],
  "risk":["risk manager","internal audit manager"],
  "finance":["banking operations manager","finance manager"],
  "strategy":["strategy and operations","business manager"],
  "technology":["IT risk manager","technology specialist"],
  "sales":["account manager","business development manager"],
  "people":["HR manager","talent acquisition specialist"],
  "marketing":["marketing manager","marketing specialist"],
  "engineering":["project engineer","maintenance engineer"],
  "education":["teacher","education specialist"],
 }
 # Keep CV family rank order, then any remaining supported family.
 ordered=[]
 for row in dna.get("role_families",[]):
  if isinstance(row,dict):
   for group in sorted(FAMILY_MAP.get(row.get("name"),set())):
    if group in support and group not in ordered:ordered.append(group)
 ordered.extend(sorted(support- set(ordered)))
 for group in ordered:result.extend(titles.get(group,[])[:2])
 return list(dict.fromkeys(x for x in result if isinstance(x,str) and x.strip()))[:14]

def role_relevance(job,profile,dna=None):
 """Occupational match 0-100, CV dependent and profession independent."""
 title=str(job.get("title") or "")
 cv=str(profile.get("cv_for_matching") or profile.get("cv_text_preview") or "")
 if not specialty_fit(title,cv):return 0
 dna=dna or profile.get("career_dna") or career_dna(cv)
 support=_support_groups(profile,dna)
 job_groups=role_groups(title)
 role_titles=_validated_roles(profile)
 # Exact/similar documented CV occupation title is authoritative.
 # An unrelated generic role cannot pass solely via the user's wish list.
 best=max((_title_overlap(title,r) for r in role_titles),default=0)
 if best>=.78:return 97
 if best>=.55:return 90
 restricted={"people","medical","nursing","pharmacy","legal","safety",
             "education","transport","hospitality","trades","engineering",
             "science","arts","environment"}
 # Profession-specific tracks require the matching CV occupational evidence.
 if any(g in job_groups and g not in support for g in restricted):
  # Allow a closely substantiated nonidentical title but never a broad
  # transferable soft-skill / generic operations hit to override a license.
  return 82 if best>=.48 else 0
 if job_groups & support:return 92
 adjacent=set().union(*(ADJACENT.get(g,set()) for g in support))
 if job_groups & adjacent and job_groups & {g for q in career_targets(profile) for g in role_groups(q)}:
  return 79
 if job_groups & adjacent:return 68
 # Previously unseen specialty families can still enter an AI review when
 # the occupation title itself is evidenced in a real CV role line.
 return 75 if best>=.42 else 0

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
