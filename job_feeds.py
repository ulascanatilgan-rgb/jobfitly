"""Source-backed job feeds independent of OpenAI search.

Uses public job-board feeds with provider attribution. Never creates job URLs
or fabricates employer information. Only CV-derived keywords are sent as queries;
the uploaded CV and personal details never leave the JobFitly backend.
"""
import concurrent.futures
import datetime
import html
import logging
import re
import threading
import time
from urllib.parse import urlparse

import requests

LOG=logging.getLogger(__name__)
_CACHE={}
_LOCK=threading.Lock()
_TTL=900
_HEADERS={"Accept":"application/json","User-Agent":"JobFitly job discovery/1.0"}
_COUNTRIES={
 "belgium":"BE","belgië":"BE","belgique":"BE","netherlands":"NL",
 "the netherlands":"NL","germany":"DE","france":"FR","united kingdom":"GB",
 "uk":"GB","ireland":"IE","luxembourg":"LU","switzerland":"CH",
 "austria":"AT","spain":"ES","portugal":"PT","italy":"IT",
 "poland":"PL","turkey":"TR","türkiye":"TR","united states":"US",
 "usa":"US","canada":"CA","australia":"AU"
}
_EU={"BE","NL","DE","FR","GB","IE","LU","CH","AT","ES","PT","IT","PL",
     "DK","SE","NO","FI","CZ","SK","HU","RO","BG","GR","HR","SI","EE","LV","LT","MT","CY"}
_FIELDS=(
 (("operations","operational","logistics","operationeel","bedrijfsvoering","logistiek","operasyon","betriebsführung"),"operations"),
 (("customer success","client","customer service","klantenservice","klantendienst","musteri iliskileri","service client"),"customer success"),
 (("project","pmo","program management","projectleider","projectcoördinator","projektmanagement","gestion de projet","proje yonetimi","proje yönetimi"),"project management"),
 (("finance","accounting","financial","boekhouding","comptable","finanzen","muhasebe","finans"),"finance"),
 (("risk","audit","governance","compliance","denetim","risico","risicobeheer","prüfung","contrôle"),"risk"),
 (("security","cyber","identity and access","beveiliging","toegangsbeheer","siber güvenlik","securite informatique"),"security"),
 (("software","developer","programming","engineer"),"software"),
 (("data","analytics","reporting","business intelligence"),"data"),
 (("sales","account manager","business development"),"sales"),
 (("marketing","brand","advertising"),"marketing"),
 (("human resources","recruit","talent acquisition"),"human resources"),
 (("designer","design","ux"),"design"),
 (("product manager","product owner"),"product"),
 (("electrician","electrical technician","elektricien","elektrotechniek","electricien","elektrik","elektrotechniker"),"electrician"),
 (("teacher","education","lecturer"),"education"),
 (("nurse","clinical","verpleegkundige","infirmier","hemşire"),"nurse"),
 (("mechanic","automotive"),"mechanic")
)

def _country_code(country):
    word=str(country or "").strip().casefold()
    return _COUNTRIES.get(word,word.upper() if len(word)==2 else "")

def _text(value):
    value=str(value or "")
    value=re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>"," ",value)
    value=re.sub(r"(?s)<[^>]*>"," ",value)
    return re.sub(r"\s+"," ",html.unescape(value)).strip()

def _date(value):
    if value is None or value=="":return ""
    try:
        if isinstance(value,(float,int)) or str(value).isdigit():
            return datetime.datetime.fromtimestamp(int(value),datetime.timezone.utc).date().isoformat()
        return datetime.datetime.fromisoformat(str(value).replace("Z","+00:00")).date().isoformat()
    except (OverflowError,ValueError,TypeError):return ""

def _fetch_json(url,params):
    key=(url,tuple(sorted((k,str(v)) for k,v in params.items())))
    with _LOCK:
        cached=_CACHE.get(key)
        if cached and time.monotonic()-cached[0]<_TTL:
            return cached[1]
    response=requests.get(url,params=params,headers=_HEADERS,timeout=(3,9))
    response.raise_for_status()
    result=response.json()
    if not isinstance(result,dict):raise ValueError("Unexpected job API response")
    with _LOCK:_CACHE[key]=(time.monotonic(),result)
    return result

def _valid_url(value):
    try:
        uri=urlparse(str(value or ""))
        return uri.scheme=="https" and bool(uri.hostname) and not uri.username
    except ValueError:return False

def _job(title,company,description,url,published,source,city="",country="",location=""):
    title=_text(title)[:240];company=_text(company)[:200]
    description=_text(description)[:9000];url=str(url or "").strip()
    if not (title and company and description and _valid_url(url)):
        return None
    return {
        "external_id":source.lower().replace(" ","-")+":"+url[:430],
        "title":title,"company":company,"city":_text(city)[:180],
        "country":_text(country)[:90],
        "description":description,"url":url,"published":_date(published),
        "source":source,"location_label":_text(location)[:180]
    }

def _role_queries(cv,keywords=""):
    cv=str(cv or "").casefold()
    queries=[]
    # Search keywords reflect the CV's *documented* experience, not merely wishes.
    for terms,query in _FIELDS:
        if any(re.search(r"\b"+re.escape(term)+r"\b",cv) for term in terms):
            queries.append(query)
    if not queries:
        lines=[x.strip() for x in str(cv or "").splitlines() if x.strip()]
        for line in lines[:32]:
            if re.search(r"\b(manager|specialist|coordinator|consultant|analyst|technician|engineer|officer)\b",line,re.I):
                query=re.sub(r"[^a-zA-Z\s]"," ",line.split("|")[0]).strip().lower()
                if 4<len(query)<45 and len(query.split())<=5:
                    queries.append(query)
    clean=[]
    for query in queries:
        if query not in clean:clean.append(query)
    if not clean and keywords:
        clean=[str(keywords).split(",")[0].strip()[:45]]
    return clean[:4]

def _eligible_geo(label,code):
    value=str(label or "").lower()
    if not code:return bool(re.search(r"\b(anywhere|worldwide|global|remote)\b",value))
    if any(word in value for word in ("anywhere","worldwide","global","world wide")):return True
    if code in _EU and any(word in value for word in ("europe","emea","eu only","european union","eu/")):return True
    if code=="US" and any(word in value for word in ("usa","united states","north america")):return True
    if code=="GB" and any(word in value for word in ("uk","united kingdom","england")):return True
    for name,country_code in _COUNTRIES.items():
        if country_code==code and name in value:return True
    return bool(re.search(r"\b"+re.escape(code.casefold())+r"\b",value))

def _arbeitnow(profile,code,page=1):
    if not code:return []
    # Arbeitnow is Germany-heavy; a physical vacancy is kept only if its
    # published location explicitly matches the requested country.
    data=_fetch_json("https://www.arbeitnow.com/api/job-board-api",{"page":page})
    out=[]
    for entry in data.get("data",[])[:320]:
        if not isinstance(entry,dict):continue
        location=_text(entry.get("location",""))
        if not _eligible_geo(location,code):continue
        country=next((name.title() for name,cc in _COUNTRIES.items()
                      if cc==code and name in location.casefold()),str(profile.get("country") or code))
        out.append(_job(entry.get("title"),entry.get("company_name"),entry.get("description"),
                        entry.get("url"),entry.get("created_at"),"Arbeitnow",
                        location, country,location))
    return [j for j in out if j]

def _jobicy(profile,code):
    geo="europe" if code in _EU else ("usa" if code=="US" else ("anywhere" if not code else ""))
    params={"count":200}
    if geo:params["geo"]=geo
    data=_fetch_json("https://jobicy.com/api/jobs",params)
    out=[]
    for entry in data.get("jobs",[])[:200]:
        if not isinstance(entry,dict):continue
        location=str(entry.get("jobGeo") or "")
        if not _eligible_geo(location,code):continue
        description=entry.get("jobDescription") or entry.get("jobExcerpt") or ""
        out.append(_job(entry.get("jobTitle"),entry.get("companyName"),description,
                        entry.get("url"),entry.get("pubDate"),"Jobicy",
                        "Remote",location or "Worldwide",location))
    return [j for j in out if j]

def _himalayas(profile,code,query=""):
    params={"sort":"recent"}
    if code:params["country"]=code
    if query:params["q"]=query[:45]
    data=_fetch_json("https://himalayas.app/jobs/api/search",params)
    out=[];now=datetime.datetime.now(datetime.timezone.utc).timestamp()
    for entry in data.get("jobs",[])[:50]:
        if not isinstance(entry,dict):continue
        expiry=entry.get("expiryDate")
        try:
            if expiry and float(expiry)<now:continue
        except (TypeError,ValueError):pass
        restrictions=entry.get("locationRestrictions") or []
        if restrictions and not any(_eligible_geo(location,code) for location in restrictions):
            continue
        if not code and restrictions:continue
        link=entry.get("applicationLink")
        # Himalayas terms require using applicationLink and giving source credit.
        out.append(_job(entry.get("title"),entry.get("companyName"),
                       entry.get("description") or entry.get("excerpt"),
                       link,entry.get("pubDate"),"Himalayas",
                       "Remote",str(profile.get("country") or "Worldwide"),
                       ", ".join(map(str,restrictions)) or "Worldwide"))
    return [j for j in out if j]

def discover_feed_jobs(profile):
    """Return normalized vacancies from independently maintained public APIs.

    A source outage is isolated to its own provider. Results have source links;
    an empty response is honest and never replaced with fictional vacancies.
    """
    code=_country_code(profile.get("country"))
    cv=str(profile.get("cv_for_matching") or profile.get("cv_text_preview") or "")
    queries=_role_queries(cv,profile.get("keywords"))
    from next_moves import valid_path_titles
    selected=valid_path_titles(profile.get("path_keywords"))
    # Preserve a CV-grounded broad query even when exploratory paths are chosen.
    focus=[*selected[:2],*(queries[:1] if queries else [])]
    if not focus:focus=queries[:2]
    focus=list(dict.fromkeys(focus))[:3]
    tasks=[("jobicy",lambda:_jobicy(profile,code))]
    for i,phrase in enumerate(focus):
        tasks.append(("himalayas"+str(i),lambda q=phrase:_himalayas(profile,code,q)))
    if not focus and code:
        tasks.append(("himalayas-default",lambda:_himalayas(profile,code))
    if code:tasks.extend([("arbeitnow1",lambda:_arbeitnow(profile,code,1)),
                          ("arbeitnow2",lambda:_arbeitnow(profile,code,2))])
    result=[];errors=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures={pool.submit(fn):name for name,fn in tasks}
        for future in concurrent.futures.as_completed(futures):
            try:result.extend(future.result())
            except (requests.RequestException,ValueError,KeyError,TypeError) as exc:
                errors.append(futures[future]+":"+type(exc).__name__)
    seen=set();unique=[]
    for job in result:
        url=job["url"].split("?")[0].rstrip("/").lower()
        if url in seen:continue
        seen.add(url)
        unique.append(job)
    LOG.info("Job sources: providers=%s candidates=%s errors=%s",
             len(tasks),len(unique),[x.split(":")[0] for x in errors])
    return unique,errors
