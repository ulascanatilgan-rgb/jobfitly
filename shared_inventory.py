"""Zero-new-service shared job inventory: public employer ATS boards and optional licensed Adzuna.

All employers are fetched by company-specific public job-board slugs; no
applicant CV, name, email, answers or location are sent to these boards.
The inventory lives in the existing persistent SQLite database.
"""
import concurrent.futures
import datetime as dt
import json
import os
import re
import sqlite3
import time
from urllib.parse import urlparse

import requests
from job_feeds import _job, _text, _country_code
from career_dna import career_dna

BOARD_SEEDS={
 "greenhouse":[("gitlab","GitLab"),("mollie","Mollie"),("datadog","Datadog"),("pleo","Pleo")],
 "lever":[
  ("Qover","Qover"),("milltownpartners","Milltown Partners"),
  ("tsmg","TSMG"),("rws","RWS"),("valpeo.com","VALPEO"),
  ("kpler","Kpler"),("jobgether","Jobgether"),("vogo","Vogo")
 ],
 "ashby":[
  ("alan","Alan"),("payflip","Payflip"),("deliveroo","Deliveroo"),
  ("shield","Shield AI"),("trm-labs","TRM Labs"),
  ("granular-energy.com","Granular Energy"),
  # Public employer-hosted boards verified from real career vacancy pages.
  ("mollie","Mollie"),("warren","Warren"),("fyst","FYST"),
  ("airwallex","Airwallex"),("moss","Moss"),
  ("lendable","Lendable"),("candex","Candex"),("solidgate","Solidgate"),
  ("conveo","Conveo"),("Clera","Clera"),("horizon3ai","Horizon3")
 ],
}
TTL_SECONDS=3*3600
MAX_STALE_SECONDS=24*3600
LEASE_SECONDS=100
HTTP_TIMEOUT=(2.5,7)
HEADERS={"Accept":"application/json","User-Agent":"Waydefine public career listings (respectful 3h cache)"}

def _boards():
 boards={key:list(val) for key,val in BOARD_SEEDS.items()}
 raw=os.getenv("ATS_BOARDS","")
 if raw:
  try:
   custom=json.loads(raw)
   for provider in BOARD_SEEDS:
    for token in (custom.get(provider) or [])[:20]:
     if isinstance(token,str) and re.fullmatch(r"[A-Za-z0-9_.-]{2,65}",token):
      boards[provider].append((token,token.replace("-"," ").title()))
  except (ValueError,TypeError,AttributeError):
   pass
 return [(provider,slug,name) for provider,items in boards.items()
         for slug,name in dict(items).items()]

def _request(url,params=None):
 response=requests.get(url,params=params or {},timeout=HTTP_TIMEOUT,headers=HEADERS)
 response.raise_for_status()
 if len(response.content)>9_000_000:raise ValueError("Excessively large board response")
 return response.json()

def _loc(entry):
 if isinstance(entry,dict):
  return _text(entry.get("name") or entry.get("location") or "")
 return _text(entry)

def _greenhouse(slug,company):
 url=f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
 data=_request(url,{"content":"true"})
 result=[]
 for item in data.get("jobs",[])[:400]:
  if not isinstance(item,dict) or not item.get("id"):continue
  if item.get("internal_job_id") is None:continue
  loc=_loc(item.get("location"))
  if not loc:
   loc="; ".join(_loc(o) for o in (item.get("offices") or []) if _loc(o))
  result.append(_job(item.get("title"),company,item.get("content") or "",
                     item.get("absolute_url"),"", "Greenhouse",loc,"",loc))
 return [item for item in result if item]

def _lever(slug,company):
 # Lever global and EU instances can differ. Query the EU board for Belgian firms.
 hosts=["api.eu.lever.co","api.lever.co"] if slug in {"Qover","milltownpartners","valpeo.com"} else ["api.lever.co","api.eu.lever.co"]
 data=None
 for host in hosts:
  try:
   data=_request(f"https://{host}/v0/postings/{slug}",{"mode":"json","limit":400})
   if isinstance(data,list):break
  except (requests.RequestException,ValueError):continue
 if not isinstance(data,list):return []
 result=[]
 for item in data[:400]:
  if not isinstance(item,dict) or not item.get("id"):continue
  loc=_text((item.get("categories") or {}).get("location"))
  desc=item.get("descriptionPlain") or item.get("description") or item.get("openingPlain") or ""
  lists=item.get("lists") or []
  if isinstance(lists,list):
   desc+=" "+" ".join(_text(p.get("content")) for p in lists if isinstance(p,dict))
  country=_text(item.get("country") or "")
  result.append(_job(item.get("text"),company,desc,item.get("hostedUrl") or item.get("applyUrl"),
                     "", "Lever",loc,country,loc))
 return [item for item in result if item]

def _ashby(slug,company):
 data=_request(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
 result=[]
 for item in data.get("jobs",[])[:400]:
  if not isinstance(item,dict) or item.get("isListed") is False:continue
  loc=_text(item.get("location"))
  for secondary in (item.get("secondaryLocations") or [])[:4]:
   if isinstance(secondary,dict):
    loc+="; "+_text(secondary.get("location"))
  desc=item.get("descriptionPlain") or item.get("descriptionHtml") or ""
  country=""
  address=item.get("address")
  if isinstance(address,dict):country=_text(address.get("addressCountry"))
  if item.get("isRemote") and "remote" not in loc.lower():loc+=" (Remote)"
  result.append(_job(item.get("title"),company,desc,item.get("jobUrl") or item.get("applyUrl"),
                     item.get("publishedAt") or "", "Ashby",loc,country,loc))
 return [item for item in result if item]

def _country_matches(job,country):
 code=_country_code(country)
 if not code:return True
 loc=_text(job.get("location_label") or job.get("city") or "")
 value=(loc+" "+str(job.get("country") or "")).casefold()
 aliases={
  "BE":("belgium","belgië","belgique","brussels","antwerp","antwerpen","ghent","gent","leuven","liège","liege"),
  "NL":("netherlands","nederland","amsterdam","rotterdam","utrecht"),
  "FR":("france","paris","lyon"),"DE":("germany","deutschland","berlin","munich"),
  "GB":("united kingdom","london","england","uk "),
  "US":("united states","usa","new york","san francisco"),
  "LU":("luxembourg",),"CH":("switzerland","zurich","zürich"),
  "IE":("ireland","dublin"),"TR":("turkey","türkiye","istanbul"),
  "ES":("spain","madrid"),"IT":("italy","milan"),"PT":("portugal","lisbon"),
  "PL":("poland","warsaw"),"CA":("canada","toronto"),
 }
 declared=_country_code(job.get("country"))
 if declared and declared==code:return True
 if declared and declared not in ("",code):return False
 if any(token in value for token in aliases.get(code,())):return True
 if re.search(r"\b"+re.escape(code.casefold())+r"\b",value):return True
 global_remote=("worldwide","anywhere","global remote","work from anywhere")
 if any(v in value for v in global_remote):return True
 eu={"BE","NL","FR","DE","LU","IE","CH","ES","IT","PT","PL","AT","DK","SE","FI"}
 if code in eu and any(x in value for x in ("remote europe","remote - europe","europe remote","eu remote","emea remote","remote emea")):return True
 # Do not guess that unspecified "Remote" means eligible for a country.
 return False

def prepare_inventory(c):
 c.executescript("""
 CREATE TABLE IF NOT EXISTS shared_jobs(
  url TEXT PRIMARY KEY,source TEXT NOT NULL,title TEXT NOT NULL,company TEXT NOT NULL,
  city TEXT,country TEXT,description TEXT,published TEXT,
  location_label TEXT,external_id TEXT,fetched_at INTEGER NOT NULL);
 CREATE INDEX IF NOT EXISTS ix_shared_jobs_fetched ON shared_jobs(fetched_at DESC);
 CREATE TABLE IF NOT EXISTS shared_refresh(
  source TEXT PRIMARY KEY,last_success INTEGER NOT NULL DEFAULT 0,
  lease_until INTEGER NOT NULL DEFAULT 0);
 """)

def shared_jobs(db,country="",max_rows=700):
 con=sqlite3.connect(str(db),timeout=15)
 con.row_factory=sqlite3.Row
 try:
  prepare_inventory(con)
  cutoff=int(time.time())-MAX_STALE_SECONDS
  # Filter by eligibility *before* applying the display cap; otherwise large
  # overseas boards can displace all local Belgian/other-country vacancies.
  rows=con.execute("""SELECT * FROM shared_jobs WHERE fetched_at>=?
   ORDER BY fetched_at DESC LIMIT 5000""",(cutoff,)).fetchall()
  jobs=[]
  for row in rows:
   job=dict(row)
   if not _country_matches(job,country):continue
   jobs.append(job)
   if len(jobs)>=max_rows:break
  return jobs
 finally:con.close()

def _licensed_adzuna():
 return all((os.getenv("ADZUNA_APP_ID"),os.getenv("ADZUNA_APP_KEY"),
             os.getenv("ADZUNA_COMMERCIAL_LICENSE_CONFIRMED")=="1"))

def _adzuna(profile):
 if not _licensed_adzuna():return []
 country=_country_code(profile.get("country")) or "BE"
 queries=career_dna(profile.get("cv_for_matching") or "").get("suggested_directions",[])
 what=(queries[0] if queries else str(profile.get("keywords") or "operations"))[:55]
 data=_request(f"https://api.adzuna.com/v1/api/jobs/{country.lower()}/search/1",{
  "app_id":os.environ["ADZUNA_APP_ID"],"app_key":os.environ["ADZUNA_APP_KEY"],
  "results_per_page":30,"what":what,"content-type":"application/json"})
 result=[]
 for item in data.get("results",[])[:30]:
  if not isinstance(item,dict):continue
  company=item.get("company") or {}
  name=company.get("display_name") if isinstance(company,dict) else ""
  place=item.get("location") or {}
  loc=place.get("display_name") if isinstance(place,dict) else ""
  result.append(_job(item.get("title"),name,item.get("description"),
                     item.get("redirect_url"),item.get("created"),"Adzuna",
                     loc,profile.get("country") or country,loc))
 return [j for j in result if j]

def _fetch_board(item):
 source,slug,company=item
 if source=="greenhouse":return _greenhouse(slug,company)
 if source=="lever":return _lever(slug,company)
 return _ashby(slug,company)

def refresh_shared(db,profile=None):
 """Single SQLite lease per environment; other workers reuse existing data.

    At most one refresh per 3 hours, no extra paid services or schedulers.
 """
 ts=int(time.time())
 con=sqlite3.connect(str(db),timeout=15)
 try:
  prepare_inventory(con)
  con.execute("BEGIN IMMEDIATE")
  row=con.execute("SELECT * FROM shared_refresh WHERE source='ats-v2'").fetchone()
  if row and (row[1]+TTL_SECONDS>ts or row[2]>ts):
   con.commit();return shared_jobs(db,(profile or {}).get("country"))
  con.execute("""INSERT INTO shared_refresh(source,last_success,lease_until)
    VALUES('ats-v2',0,?) ON CONFLICT(source) DO UPDATE SET lease_until=excluded.lease_until""",
    (ts+LEASE_SECONDS,))
  con.commit()
 finally:con.close()
 boards=_boards()
 gathered=[];success=0
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
  futures={pool.submit(_fetch_board,item):item for item in boards}
  for future in concurrent.futures.as_completed(futures):
   try:
    gathered.extend(future.result())
    success+=1
   except (requests.RequestException,ValueError,TypeError,KeyError):
    continue
 # Optional and explicitly licensed Adzuna is not part of the employer ATS refresh.
 if _licensed_adzuna() and profile:
  try:gathered.extend(_adzuna(profile))
  except (requests.RequestException,ValueError,KeyError,TypeError):pass
 con=sqlite3.connect(str(db),timeout=15)
 try:
  prepare_inventory(con)
  if gathered:
   con.executemany("""INSERT INTO shared_jobs(
       url,source,title,company,city,country,description,published,
       location_label,external_id,fetched_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,?)
      ON CONFLICT(url) DO UPDATE SET
        source=excluded.source,title=excluded.title,company=excluded.company,
        city=excluded.city,country=excluded.country,description=excluded.description,
        published=excluded.published,location_label=excluded.location_label,
        external_id=excluded.external_id,fetched_at=excluded.fetched_at""",
     [(j["url"][:1400],j["source"],j["title"],j["company"],j.get("city") or "",
       j.get("country") or "",j.get("description") or "",j.get("published") or "",
       j.get("location_label") or "",j.get("external_id") or "",ts) for j in gathered])
  # A failed provider wave backs off for 10 minutes instead of hammering
  # every public employer API on each new user's next search.
  if success:
   con.execute("UPDATE shared_refresh SET lease_until=0,last_success=? WHERE source='ats-v2'",(ts,))
  else:
   con.execute("UPDATE shared_refresh SET lease_until=? WHERE source='ats-v2'",(ts+600,))
  con.execute("DELETE FROM shared_jobs WHERE fetched_at<?",(ts-MAX_STALE_SECONDS,))
  con.commit()
 finally:con.close()
 return shared_jobs(db,(profile or {}).get("country"))
