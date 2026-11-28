"""Multi-select job preference evaluation. Lightweight and deterministic."""
import re

NEUTRAL={"Open to all","No preference","Flexible","Any",""}
CHOICES={
 "role_type":{
  "Operations & strategy":("operations","operational","strategy","strategic","project","program","programme","pmo","business manager","chief of staff","business operations"),
  "People & relationships":("client","customer","stakeholder","partnership","account manager","customer success","sales","relationship","membership","business development"),
  "Analytical":("analysis","analyst","data","audit","financial","risk","controls","research","intelligence"),
  "Creative & product":("product","design","creative","brand","marketing","innovation"),
  "Clinical & care":("physician","doctor","clinical","nursing","hospital","care","therapist","dentist"),
  "Legal & policy":("lawyer","attorney","legal","law firm","solicitor","counsel","litigation","policy"),
  "Technical & field":("electrician","engineer","technician","site","maintenance","hvac","plumber","mechanic","field operations"),
  "Safety & regulation":("hse","ehs","occupational safety","health and safety","safety officer","safety manager","regulatory","prevention"),
  "Teaching & research":("education","teacher","professor","lecturer","research","laboratory","curriculum")
 },
 "sector":{
  "Technology":("software","technology","tech","ai","engineering","cloud","saas","cyber"),
  "Finance":("bank","finance","financial","investment","fintech","insurance","payments","capital markets"),
  "Healthcare":("medical","health","pharma","clinical","patient","hospital"),
  "Creative":("design","art","marketing","creative","studio","museum"),
  "Legal & public service":("law firm","lawyer","legal","public policy","government","notary","justice","ngo","nonprofit"),
  "Safety & industry":("occupational safety","industrial","manufacturing","hse","ehs","workplace safety","construction"),
  "Engineering & trades":("engineering","electrician","technician","mechanic","hvac","construction","maintenance"),
  "Education & research":("school","university","education","research","academic","scientific","laboratory"),
  "Hospitality & services":("hotel","restaurant","hospitality","culinary","barista","bakery","catering","customer service")
 },
 "environment":{
  "Startup":("startup","start-up","early-stage","scale-up","scaleup","seed stage"),
  "Established company":("global","multinational","enterprise","established","corporation","leading provider","publicly listed")
 },
 "priority":{
  "Growth":("growth","scale","build","leadership","development","promotion","career progression"),
  "Security":("permanent","stable","long-term","full-time","full time"),
  "Balance":("flexible","hybrid","work-life","work life","part-time","wellbeing")
 },
 "mode":{
  "Remote":("fully remote","100% remote","remote-first","remote","work from home","home-based","home based","telework","teleworking","telecommute"),
  "Hybrid":("hybrid","hybrid work","partially remote","partly remote","partial remote","2 days from home","3 days from home","home office days","thuiswerk","télétravail","teletravail","part-time homeworking","flexible working"),
  "On-site":("on-site","onsite","on site","on location","office-based","office based","in-office","in person","on premises","at our office")
 },
 "seniority":{
  "Specialist":("specialist","advisor","analyst","associate","consultant","engineer","individual contributor"),
  "Manager":("manager","lead","head of","team leader","project manager","supervisor"),
  "Leadership":("director","head of","chief","vp ","vice president","executive","general manager","senior manager")
 }
}
WEIGHTS={"role_type":3,"sector":2,"mode":2,"seniority":2,"environment":1,"priority":1}

def preferences_list(value):
 """Accept older scalar preferences and new multi-valued lists."""
 if isinstance(value,str):raw=[value]
 elif isinstance(value,(list,tuple)):raw=value
 else:return []
 out=[]
 for item in raw:
  if not isinstance(item,str):continue
  item=item.strip()
  if item and item not in NEUTRAL and item not in out:
   out.append(item)
 return out[:8]

def normalize_preferences(raw,allowed=None):
 """Validate against defined choices when provided, treating neutral as empty."""
 if not isinstance(raw,dict):return {}
 result={}
 for key,values in raw.items():
  if allowed is not None and key not in allowed:continue
  picked=preferences_list(values)
  if allowed is not None:picked=[v for v in picked if v in allowed[key]]
  if picked:result[key]=picked
 return result

def _match(text,phrase):
 # Prevent false hits on small fragments like 'ai' in 'detail'.
 phrase=phrase.lower()
 return re.search(r'(?<!\w)'+re.escape(phrase)+r'(?!\w)',text) is not None

def preference_alignment(job,raw):
 """Return a 0..10 score where options inside each category have OR semantics.

    User-supplied categories with no preference have no effect; roles and actual
    CV matching still determine the majority of the final ranking.
 """
 preferences=normalize_preferences(raw)
 if not preferences:return None
 title=str(job.get("title") or "").lower()
 description=str(job.get("description") or "")[:4500].lower()
 place=(" ".join(str(job.get(k) or "") for k in ("city","country","location_label"))).lower()
 total=0.0
 weight_total=0.0
 for field,values in preferences.items():
  if field not in CHOICES:continue
  if not any(CHOICES[field].get(value) for value in values):continue
  weight=WEIGHTS.get(field,1)
  best=0.0
  for value in values:
   hints=CHOICES[field].get(value,())
   if not hints:continue
   hits_title=any(_match(title,phrase) for phrase in hints)
   hits_text=any(_match(description,phrase) for phrase in hints)
   hits_location=field=="mode" and any(_match(place,phrase) for phrase in hints)
   # A title match is strongest. Unstated constraints are not magically verified.
   strength=1.0 if hits_title else 0.78 if hits_location or hits_text else 0.15
   best=max(best,strength)
  total+=best*weight
  weight_total+=weight
 if not weight_total:return None
 return round(10*total/weight_total,2)

def _mode_evidence(job):
 """Identify stated employer work setting; ignore negated remote mentions."""
 title=str(job.get("title") or "").lower()
 description=str(job.get("description") or "")[:9000].lower()
 place=(" ".join(str(job.get(k) or "") for k in ("city","country","location_label"))).lower()
 text=" ".join((title,description,place))
 has_hybrid=any(_match(text,p) for p in CHOICES["mode"]["Hybrid"])
 has_remote=any(_match(text,p) for p in CHOICES["mode"]["Remote"])
 has_on_site=any(_match(text,p) for p in CHOICES["mode"]["On-site"])
 # A clear employer statement overrides incidental keywords elsewhere.
 if re.search(r"\b(?:no|not|without|geen|niet|pas de)\s+(?:full\s+)?remote\b",text):
  has_remote=False
 if re.search(r"\b(?:remote work|work from home|home office)\s+(?:is\s+)?(?:not\s+)?(?:available|permitted|possible)\b",text):
  if re.search(r"\b(?:not|no|never)\s+(?:available|permitted|possible)\b",text):
   has_remote=False
 if re.search(r"\b(?:fully|entirely|100%)\s+on[- ]site\b|\bmust\s+(?:be\s+)?(?:in|at)\s+(?:the\s+)?office\b",text):
  return "On-site"
 if has_hybrid:return "Hybrid"
 if has_remote:return "Remote"
 if has_on_site:return "On-site"
 return "Unknown"

def preference_constraints_match(job,raw):
 """Apply only genuinely hard preference constraints.

 Work setting is an explicit eligibility filter. Other preference groups remain
 ranking signals because sector/company-type/seniority text is often incomplete.
 """
 preferences=normalize_preferences(raw)
 modes=preferences.get("mode",[])
 if not modes:return True
 evidence=_mode_evidence(job)
 allowed=set(modes)
 if evidence!="Unknown":return evidence in allowed
 # An unknown setting can safely behave as ordinary location-based/on-site only
 # when On-site was selected. It must never satisfy Remote-only or Hybrid-only.
 return "On-site" in allowed

