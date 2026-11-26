"""Explainable, zero-API-cost adjacent career paths based on CV evidence.

This is exploratory career guidance, not a live vacancy count or a hiring prediction.
Preferences affect ranking but never stand in for documented experience.
"""
from career_dna import _normalize, _hit

# Each pathway deliberately sits next to—not inside—a documented skill family.
# Hard professional licensing, regulated medical/legal practice and directorial
# claims requiring specific experience are outside the catalog.
CATALOG = [
 {"title":"Business Operations Manager","family":"Operations & management","families":("Finance & banking","Risk & compliance","Project & programme"),"skills":("Process improvement","Operations coordination","Stakeholder management","Risk controls","Data & reporting"),"style":("operations","coordination","ownership"),"gap":"business-wide delivery and budget ownership","focus":"cross-team operational improvements"},
 {"title":"Chief of Staff","family":"Product & strategy","families":("Operations & management","Project & programme","Finance & banking"),"skills":("Stakeholder management","Project delivery","Communication","Data & reporting","People leadership"),"style":("strategy","coordination","leadership"),"gap":"executive-level communication and decision support","focus":"executive priorities and cross-functional coordination"},
 {"title":"Business Transformation Manager","family":"Project & programme","families":("Risk & compliance","Operations & management","Security & technology","Finance & banking"),"skills":("Project delivery","Process improvement","Stakeholder management","Risk controls"),"style":("strategy","ownership","ambiguity"),"gap":"large-scale change delivery and measurable transformation results","focus":"change programmes and operational transformation"},
 {"title":"Product Operations Manager","family":"Product & strategy","families":("Security & technology","Operations & management","Project & programme"),"skills":("Process improvement","Project delivery","Data & reporting","Technology","Stakeholder management"),"style":("analytical","coordination","creative"),"gap":"direct product-team and customer lifecycle exposure","focus":"connecting product teams with business operations"},
 {"title":"Operational Resilience Coordinator","family":"Risk & compliance","families":("Finance & banking","Security & technology","Operations & management"),"skills":("Risk controls","Process improvement","Stakeholder management","Data & reporting"),"style":("detail","structure","coordination"),"gap":"business continuity or resilience framework experience","focus":"continuity planning and resilient business processes"},
 {"title":"Technology Governance Lead","family":"Security & technology","families":("Risk & compliance","Finance & banking","Project & programme"),"skills":("Risk controls","Technology","Stakeholder management","Data & reporting"),"style":("analytical","structure","leadership"),"gap":"technology governance ownership at the target organisation","focus":"bridging technology decisions and business controls"},
 {"title":"Portfolio Operations Specialist","family":"Finance & banking","families":("Operations & management","Project & programme","Product & strategy"),"skills":("Financial analysis","Data & reporting","Stakeholder management","Process improvement"),"style":("analytical","detail","operations"),"gap":"portfolio-specific reporting and investment operations knowledge","focus":"investment portfolio processes and reporting"},
 {"title":"Partnerships Manager","family":"Sales & partnerships","families":("Finance & banking","Operations & management","Product & strategy","People & talent"),"skills":("Stakeholder management","Customer relations","Business development","Communication","Project delivery"),"style":("people","client_energy","communication"),"gap":"direct partnership ownership and commercial targets","focus":"external relationships and business partnerships"},
 {"title":"Customer Success Manager","family":"Sales & partnerships","families":("Security & technology","Project & programme","Operations & management","Education"),"skills":("Customer relations","Stakeholder management","Project delivery","Communication","Operations coordination"),"style":("people","client_energy","communication"),"gap":"customer retention or account ownership experience","focus":"helping clients adopt services successfully"},
 {"title":"Implementation Manager","family":"Project & programme","families":("Security & technology","Finance & banking","Sales & partnerships","Operations & management"),"skills":("Project delivery","Stakeholder management","Technology","Operations coordination","Process improvement"),"style":("coordination","ownership","operations"),"gap":"end-to-end customer implementation accountability","focus":"bringing client-facing projects into production"},
 {"title":"Service Delivery Manager","family":"Operations & management","families":("Engineering & trades","Security & technology","Sales & partnerships","Healthcare"),"skills":("Operations coordination","Customer relations","Process improvement","Stakeholder management","Project delivery"),"style":("operations","coordination","people"),"gap":"service-level agreement and delivery performance ownership","focus":"reliable customer-facing service operations"},
 {"title":"Commercial Operations Manager","family":"Sales & partnerships","families":("Finance & banking","Product & strategy","Operations & management","Design & marketing"),"skills":("Data & reporting","Process improvement","Business development","Stakeholder management"),"style":("analytical","strategy","people"),"gap":"commercial forecasting and revenue pipeline ownership","focus":"sales operations and commercial execution"},
 {"title":"Business Intelligence Coordinator","family":"Product & strategy","families":("Finance & banking","Risk & compliance","Operations & management","Design & marketing"),"skills":("Data & reporting","Financial analysis","Process improvement","Stakeholder management"),"style":("analytical","detail","strategy"),"gap":"hands-on analytics tooling and BI reporting depth","focus":"turning operational data into business decisions"},
 {"title":"Client Onboarding Manager","family":"Sales & partnerships","families":("Finance & banking","Risk & compliance","Security & technology","Operations & management"),"skills":("Customer relations","Stakeholder management","Risk controls","Project delivery","Operations coordination"),"style":("people","client_energy","coordination"),"gap":"client lifecycle and onboarding metrics ownership","focus":"guiding clients through complex onboarding processes"},
 {"title":"Programme Operations Coordinator","family":"Project & programme","families":("Education","Healthcare","People & talent","Operations & management","Design & marketing"),"skills":("Project delivery","Operations coordination","Communication","Stakeholder management"),"style":("coordination","people","structure"),"gap":"programme scheduling and multi-stakeholder delivery","focus":"running multi-team programmes and events"},
 {"title":"Learning Operations Manager","family":"Education","families":("People & talent","Project & programme","Operations & management","Sales & partnerships"),"skills":("Communication","Project delivery","Stakeholder management","Operations coordination"),"style":("people","coordination","creative"),"gap":"learning platform and training delivery experience","focus":"designing scalable learning operations"},
 {"title":"Community & Membership Manager","family":"Sales & partnerships","families":("People & talent","Design & marketing","Education","Operations & management"),"skills":("Customer relations","Communication","Stakeholder management","Operations coordination"),"style":("people","client_energy","creative"),"gap":"membership retention and event community outcomes","focus":"building professional communities and member relationships"},
 {"title":"Growth Operations Manager","family":"Product & strategy","families":("Design & marketing","Sales & partnerships","Operations & management"),"skills":("Data & reporting","Business development","Process improvement","Stakeholder management"),"style":("analytical","creative","strategy"),"gap":"experimentation and growth measurement experience","focus":"improving customer acquisition and growth processes"},
 {"title":"Technical Project Coordinator","family":"Project & programme","families":("Engineering & trades","Security & technology","Operations & management"),"skills":("Technology","Project delivery","Operations coordination","Stakeholder management"),"style":("detail","coordination","operations"),"gap":"hands-on scheduling and technical project delivery","focus":"coordinating technical teams and project work"},
 {"title":"Facilities Operations Manager","family":"Operations & management","families":("Engineering & trades","Healthcare","Operations & management"),"skills":("Operations coordination","Process improvement","Stakeholder management","Project delivery"),"style":("operations","structure","coordination"),"gap":"facilities compliance and contractor oversight","focus":"running sites, vendors and operational processes"},
 {"title":"Healthcare Operations Coordinator","family":"Operations & management","families":("Healthcare","Project & programme","Risk & compliance"),"skills":("Operations coordination","Process improvement","Risk controls","Stakeholder management"),"style":("people","operations","detail"),"gap":"healthcare setting and clinical workflow knowledge","focus":"supporting healthcare delivery without clinical practice"},
 {"title":"Employer Brand Coordinator","family":"Design & marketing","families":("People & talent","Design & marketing","Education"),"skills":("Communication","Customer relations","Project delivery","Stakeholder management"),"style":("creative","people","communication"),"gap":"recruitment marketing and employer brand campaigns","focus":"communicating a company’s culture to prospective talent"},
 {"title":"Customer Education Manager","family":"Education","families":("Security & technology","Sales & partnerships","Education","People & talent"),"skills":("Communication","Technology","Customer relations","Project delivery"),"style":("people","creative","communication"),"gap":"training curriculum and learning effectiveness measurement","focus":"turning product expertise into useful client education"},
]

CATALOG_BY_TITLE={item["title"]:item for item in CATALOG}
PATH_LIMIT=3

def valid_path_titles(values):
 """Keep only known unique pathways; reject arbitrary user-injected search claims."""
 if not isinstance(values,list):return []
 seen=set();out=[]
 for value in values[:12]:
  if not isinstance(value,str) or value not in CATALOG_BY_TITLE or value in seen:continue
  seen.add(value);out.append(value)
  if len(out)==PATH_LIMIT:break
 return out

def path_title_match(job,selected):
 """Title-only match avoids unrelated descriptions with aspirational job mentions."""
 title=_normalize(job.get("title") or "").replace("programme","program").replace("programs","program")
 for phrase in valid_path_titles(selected):
  target=_normalize(phrase).replace("programme","program")
  if _hit(title,target):return 1.0
  left={part for part in title.split() if len(part)>3}
  right={part for part in target.split() if len(part)>3}
  if len(right)>1 and len(left&right)/len(right)>=.75:return .72
 return 0.0

def alternative_next_moves(cv,dna=None,questions=None,swipes=None,keywords=""):
 """Three adjacent pathways when CV evidence is sufficient.

 Evidence is drawn from the uploaded CV only. Optional work-style responses
 influence ordering, never become qualifications. No job availability claims.
 """
 cv=str(cv or "")[:23000]
 if len(cv.split())<9:return []
 from career_dna import career_dna
 dna=dna or career_dna(cv)
 families={entry.get("name") for entry in dna.get("role_families",[]) if isinstance(entry,dict)}
 documented=set(dna.get("transferable_skills",[]))
 if not families or len(documented)<1:return []
 questions=questions if isinstance(questions,dict) else {}
 swipes=swipes if isinstance(swipes,dict) else {}
 excluded_text=_normalize(cv+"\n"+str(keywords or ""))
 ranked=[]
 for item in CATALOG:
  title=item["title"]
  # Explicitly avoid current roles, and the user's already-searching-for titles.
  if _hit(excluded_text,title):continue
  evidence=[skill for skill in item["skills"] if skill in documented]
  related=families.intersection(item["families"])
  if not related or not evidence:continue
  style_values=[min(10,max(0,float(questions[k]))) for k in item["style"]
                if k in questions and isinstance(questions[k],(int,float))]
  style_score=round(sum(style_values)/len(style_values)*10) if style_values else None
  cv_score=min(92,43+11*len(evidence)+8*min(2,len(related)))
  preferences=swipes.get("role_type") or []
  if isinstance(preferences,str):preferences=[preferences]
  mode=swipes.get("mode") or []
  if isinstance(mode,str):mode=[mode]
  sector=swipes.get("sector") or []
  if isinstance(sector,str):sector=[sector]
  preference_text=_normalize(" ".join(preferences+mode+sector))
  preference_hint=any(_hit(preference_text,term) for term in
                        ("people","strategy","analytical","creative","operations","client","technology","finance"))
  # Small preference/style influence; demonstrated CV evidence dominates.
  ranking=2.5*len(evidence)+2.3*len(related)+(style_score or 50)*.023+(0.4 if preference_hint else 0)
  ranked.append((ranking,item,evidence,related,cv_score,style_score))
 ranked.sort(key=lambda row:(row[0],row[4]),reverse=True)
 chosen=[];used_families=set()
 for row in ranked:
  if len(chosen)==PATH_LIMIT:break
  if row[1]["family"] in used_families:continue
  chosen.append(row);used_families.add(row[1]["family"])
 for row in ranked:
  if len(chosen)==PATH_LIMIT:break
  if row in chosen:continue
  chosen.append(row)
 out=[]
 for _,item,evidence,related,cv_score,style_score in chosen:
  strength=", ".join(evidence[:2])
  another=evidence[2] if len(evidence)>2 else evidence[0]
  # Exactly four compact complete sentences; claims stay tied to source evidence.
  lines=[
   f"Your CV documents {strength.lower()}, which could transfer into this role.",
   f"This path focuses on {item['focus']} and draws on your {another.lower()} experience.",
   ("Your work-style answers suggest a useful alignment with this direction."
      if style_score is not None and style_score>=60 else
    "It offers a different way to use your existing professional strengths."),
   f"Before applying, check the employer's expectations for {item['gap']}."
  ]
  out.append({
   "id":item["title"].lower().replace(" ","-").replace("&","and"),
   "title":item["title"],"family":item["family"],
   "description":" ".join(lines),
   "cv_evidence":evidence[:3],
   "evidence_score":cv_score,
   "style_score":style_score,
   "note":"Exploratory, CV-grounded direction — not a job offer or hiring prediction."
  })
 return out
