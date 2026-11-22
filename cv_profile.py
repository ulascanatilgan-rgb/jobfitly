"""Source-backed personal facts from an uploaded CV. Never fill missing details."""
import re

EMAIL=re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",re.I)
PHONE=re.compile(r"(?:\+?\d[\d ()/-]{7,}\d)")
URL=re.compile(r"(?:https?://)?(?:www\.)?[\w.-]+\.(?:com|be|eu|org|net|co\.uk)(?:/[\w./-]+)?",re.I)
HEADINGS={"PROFILE","SUMMARY","PROFESSIONAL EXPERIENCE","EXPERIENCE","WORK EXPERIENCE","EDUCATION",
"LANGUAGES","SKILLS","CERTIFICATIONS","PROJECTS","PROFESSIONAL SUMMARY","PERSONAL DETAILS",
"CONTACT","CORE COMPETENCIES","ABOUT ME","CURRICULUM VITAE","RESUME","CV"}
LABELS={"name":"name","full name":"name","email":"email","e-mail":"email",
"phone":"phone","mobile":"phone","telephone":"phone","address":"location",
"location":"location","city":"location","linkedin":"linkedin","website":"website",
"nationality":"nationality","date of birth":"date_of_birth","languages":"languages"}

def extract_cv_details(text):
    """Read actual CV text; missing fields remain empty rather than guessed."""
    lines=[re.sub(r"\s+"," ",x).strip(" \t•") for x in str(text or "").splitlines()]
    lines=[x for x in lines if x][:300]
    result={}
    for line in lines[:24]:
        m=re.match(r"^(?:full name|name)\s*[:\-]\s*(.+)$",line,re.I)
        if m and 2<=len(m.group(1).split())<=5:
            result["name"]=m.group(1).strip()[:100]
            break
    if "name" not in result:
        for line in lines[:15]:
            words=line.replace(",","").split()
            if line.upper().strip(" .:") in HEADINGS or re.search(r"\d|@|http|www|linkedin|[|•/]",line,re.I):continue
            if 2<=len(words)<=5 and 5<=len(line)<=64 and all(word[0].isupper() for word in words):
                result["name"]=line.strip()
                break
    for line in lines[:30]:
        match=re.match(r"^([A-Za-z][A-Za-z -]{2,25})\s*[:\-]\s*(.+)$",line)
        if match:
            key=LABELS.get(match.group(1).strip().lower())
            if key and key not in result:result[key]=match.group(2).strip()[:200]
    text_lines="\n".join(lines)
    match=EMAIL.search(text_lines)
    if match:result["email"]=match.group()
    for line in lines[:15]:
        match=PHONE.search(EMAIL.sub("",line))
        if match and len(re.sub(r"\D","",match.group()))>=9:
            result.setdefault("phone",match.group().strip())
            break
    for line in lines[:25]:
        low=line.lower()
        if "linkedin.com/" in low:
            match=re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/[\w./-]+",line,re.I)
            if match:result["linkedin"]=match.group().rstrip("/")
        for match in URL.finditer(line):
            url=match.group().rstrip(".,;")
            if "linkedin" not in url.lower() and not EMAIL.search(line[:match.end()]):
                result.setdefault("website",url)
        if re.search(r"\b(Belgium|Netherlands|France|Germany|Turkey|Türkiye|United Kingdom|United States)\b",line,re.I):
            if len(line)<105 and not any(x in low for x in ("experience","project","worked","company")):
                result.setdefault("location",next((part.strip() for part in line.split("|") if re.search(r"\b(Belgium|Netherlands|France|Germany|Turkey|Türkiye|United Kingdom|United States)\b",part,re.I)),line[:105])[:105])
    for i,line in enumerate(lines):
        if line.upper().rstrip(":") in ("LANGUAGES","LANGUAGE SKILLS"):
            values=[]
            for nxt in lines[i+1:i+5]:
                if nxt.upper().rstrip(":") in HEADINGS:break
                values.append(nxt)
            if values:result["languages"]="; ".join(values)[:350]
            break
    if result.get("name"):
        for line in lines[:8]:
            if line!=result["name"] and 8<len(line)<110 and "|" in line and not re.search(r"@|http|www|linkedin|\+\d",line,re.I):
                result.setdefault("headline",line)
                break
    return {key:value for key,value in result.items() if value}
