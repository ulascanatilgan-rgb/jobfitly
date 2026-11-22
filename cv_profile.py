"""Conservative, CV-grounded personal identity extraction.

Locations and job titles are never accepted as names. Ambiguity requires the
candidate's explicit confirmation in their profile.
"""
import re
import unicodedata

EMAIL=re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",re.I)
PHONE=re.compile(r"(?<!\w)(?:\+?\d[\d ()/-]{7,}\d)(?!\w)")
URL=re.compile(r"(?:https?://)?(?:www\.)?[\w.-]+\.(?:com|be|eu|org|net|co\.uk)(?:/[\w./-]+)?",re.I)
HEADINGS={"PROFILE","SUMMARY","PROFESSIONAL EXPERIENCE","EXPERIENCE","WORK EXPERIENCE",
"EDUCATION","LANGUAGES","SKILLS","CERTIFICATIONS","PROJECTS","PROFESSIONAL SUMMARY",
"PERSONAL DETAILS","CONTACT","CORE COMPETENCIES","ABOUT ME","CURRICULUM VITAE",
"RESUME","CV","QUALIFICATIONS","TRAINING"}
LABELS={"name":"name","full name":"name","candidate name":"name","email":"email",
"e-mail":"email","phone":"phone","mobile":"phone","telephone":"phone",
"address":"location","location":"location","city":"location",
"linkedin":"linkedin","website":"website","nationality":"nationality",
"date of birth":"date_of_birth","languages":"languages"}
# Explicitly disqualify country/city words and career-title tokens from personal names.
GEO=set("""belgium belgian belgique belgie belgië kapellen antwerp antwerpen
brussels brussel bruxelles kalmthout brasschaat stabroek berchem gent ghent
leuven mechelen aalst bruges brugge liège liege namur netherlands dutch
holland france french paris germany german berlin turkey turkiye türkiye
turkish istanbul ankara london england ireland scotland uk united kingdom
states usa europe european luxembourg amsterdam rotterdam eindhoven""".split())
JOB=set("""manager management operations operational expert engineer auditor analyst
director executive officer assistant consultant coordinator lead leader head senior
junior specialist strategy banking finance financial business technology security
risk information digital professional project programme program administrator
governance communication marketing customer product international profile
resume curriculum vitae university institute college school ing linkedin""".split())
CONNECTORS={"van","von","de","der","den","da","di","del","al","bin","la","le","du"}
WORD_RE=re.compile(r"^[^\W\d_]+(?:[-'’][^\W\d_]+)*$",re.UNICODE)

def _norm(value):
    value=str(value or "").casefold().replace("ı","i").replace("æ","ae").replace("œ","oe")
    value="".join(ch for ch in unicodedata.normalize("NFKD",value)
                  if not unicodedata.combining(ch))
    return re.sub(r"[^a-z]","",value)

def is_plausible_person_name(value):
    """Reject place names, job titles, contact strings and generic CV headings."""
    value=re.sub(r"\s+"," ",str(value or "")).strip(" ,;:.•")
    words=value.split()
    if not (2<=len(words)<=5 and 5<=len(value)<=80):return False
    if any(not WORD_RE.fullmatch(w) for w in words):return False
    norm_words=[_norm(w) for w in words]
    if any(w in GEO or w in JOB for w in norm_words):return False
    if any(w in ("address","location","street","straat","road","avenue","laan")
           for w in norm_words):return False
    if sum(1 for w in words if w[0].isupper() or w.isupper())<2:return False
    if norm_words[0] in CONNECTORS or norm_words[-1] in CONNECTORS:return False
    return True

def _get_name(lines,email):
    """Compare plausible CV header names with contact/email evidence."""
    candidates=[]
    email_local=_norm(email.split("@")[0]) if email else ""
    for i,line in enumerate(lines[:45]):
        line=line.strip(" •,")
        if not line or line.upper().strip(". :") in HEADINGS:continue
        m=re.match(r"^(?:name|full name|candidate name)\s*[:\-]\s*(.+)$",line,re.I)
        explicit=bool(m)
        value=m.group(1).strip() if m else line
        if not is_plausible_person_name(value):continue
        words=value.split()
        score=10-i*.4 if i<24 else 2
        if explicit:score+=30
        if i<5:score+=2
        if value.isupper():score+=2
        if email_local:
            parts=[_norm(w) for w in words if _norm(w) not in CONNECTORS]
            if len(parts)>=2 and parts[0] in email_local and parts[-1] in email_local:
                score+=14
            elif any(len(w)>3 and w in email_local for w in parts):
                score+=3
        if i>0 and lines[i-1].strip().upper() in ("NAME","FULL NAME"):score+=20
        candidates.append((score,value))
    if not candidates:return ""
    candidates.sort(reverse=True,key=lambda x:x[0])
    score,name=candidates[0]
    if score<7:return ""
    # Two equally plausible names without independent corroboration are ambiguous.
    if len(candidates)>1 and candidates[1][0]>=score-1.5 and score<20:
        return ""
    return name

def extract_cv_details(text):
    lines=[re.sub(r"\s+"," ",x).strip(" \t•") for x in str(text or "").splitlines()]
    lines=[x for x in lines if x][:300]
    result={}
    email=EMAIL.search("\n".join(lines))
    if email:result["email"]=email.group()
    name=_get_name(lines,result.get("email",""))
    if name:result["name"]=name
    for line in lines[:35]:
        m=re.match(r"^([A-Za-z][A-Za-z -]{2,25})\s*[:\-]\s*(.+)$",line)
        if m:
            key=LABELS.get(m.group(1).strip().lower())
            value=m.group(2).strip()
            if key and key!="name" and value:
                result.setdefault(key,value[:180])
    for line in lines[:22]:
        without_email=EMAIL.sub("",line)
        for chunk in without_email.split("|"):
            match=PHONE.search(chunk)
            if match and len(re.sub(r"\D","",match.group()))>=9:
                result.setdefault("phone",match.group().strip())
                break
        if "phone" in result:break
    for line in lines[:30]:
        low=line.lower()
        if "linkedin.com/" in low:
            m=re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/[\w./-]+",line,re.I)
            if m:result.setdefault("linkedin",m.group().rstrip("/"))
        for m in URL.finditer(line):
            url=m.group().rstrip(".,;")
            if "linkedin" not in url.lower() and not EMAIL.search(line[:m.end()]):
                result.setdefault("website",url)
        if re.search(r"\b(Belgium|Netherlands|France|Germany|Turkey|Türkiye|United Kingdom|United States)\b",line,re.I):
            for part in line.split("|"):
                if len(part)<100 and re.search(r"\b(Belgium|Netherlands|France|Germany|Turkey|Türkiye|United Kingdom|United States)\b",part,re.I):
                    if not any(x in part.lower() for x in ("experience","project","worked","company")):
                        result.setdefault("location",part.strip()[:100])
                        break
    if "location" in result:
        result["location"]=re.sub(r"\s+"," ",result["location"]).strip()
    for i,line in enumerate(lines):
        if line.upper().rstrip(":") in ("LANGUAGES","LANGUAGE SKILLS"):
            values=[]
            for nxt in lines[i+1:i+5]:
                if nxt.upper().rstrip(":") in HEADINGS:break
                values.append(nxt)
            if values:result["languages"]="; ".join(values)[:350]
            break
    if name:
        for line in lines[:8]:
            if line!=name and 8<len(line)<110 and "|" in line and not re.search(r"@|http|www|linkedin|\+\d",line,re.I):
                if not any(x in line.casefold() for x in ("belgium","belgië","netherlands")):
                    result.setdefault("headline",line)
                    break
    return {key:value for key,value in result.items() if value}
