"""Multi-select job preference evaluation. Lightweight and deterministic."""
import re

NEUTRAL={"Open to all","No preference","Flexible","Any",""}
CHOICES={
 "role_type":{
  "Operations & strategy":("operations","operational","strategy","strategic","project","program","programme","pmo","business manager","chief of staff","business operations"),
  "People & relationships":("client","customer","stakeholder","partnership","account manager","customer success","sales","relationship","membership","business development"),
  "Analytical":("analysis","analyst","data","audit","financial","risk","controls","research","intelligence"),
  "Creative & product":("product","design","creative","brand","marketing","innovation")
 },
 "sector":{
  "Technology":("software","technology","tech","ai","engineering","cloud","saas","cyber"),
  "Finance":("bank","finance","financial","investment","fintech","insurance","payments","capital markets"),
  "Healthcare":("medical","health","pharma","clinical","patient","hospital"),
  "Creative":("design","art","marketing","creative","studio","museum")
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
  "Remote":("remote","work from home","home-based","home based"),
  "Hybrid":("hybrid","flexible working","partial remote"),
  "On-site":("on-site","onsite","on site","office-based","office based","in-office")
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
