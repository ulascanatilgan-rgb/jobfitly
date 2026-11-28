"""Deterministic, CV-evidence-based Career DNA. No AI calls or third-party PII sharing."""
import re
import unicodedata

FAMILIES={
 "Operations & management":("operations","operational","logistics","supply chain","process improvement","bedrijfsvoering","operasyon","service delivery","office manager"),
 "Project & programme":("project manager","project management","project coordination","program management","programme","pmo","projectleider","change management","project officer"),
 "Risk & compliance":("risk","audit","internal control","compliance","governance","fraud","aml","kyc","denetim","regulatory"),
 "Finance & banking":("banking","bank","payments","finance","financial","investment","treasury","accounting","boekhouding","finans"),
 "Security & technology":("cyber","security","iam","identity access","active directory","it infrastructure","information technology","software","developer","cloud","data engineering"),
 "Sales & partnerships":("sales","business development","account management","commercial","partnership","client acquisition","customer success","relationship manager"),
 "Product & strategy":("product owner","product manager","product operations","strategy","strategic planning","business analyst","consulting","portfolio management"),
 "People & talent":("human resources","recruitment","recruiter","talent","people operations","learning and development","hr manager"),
 "Design & marketing":("marketing","communications","branding","graphic design","creative","digital campaign","content"),
 "Engineering & trades":("engineer","electrical","electrician","technician","mechanic","construction","elektricien","technieker"),
 "Healthcare":("nurse","medical","clinical","healthcare","pharmacy","hospital","verpleegkundige"),
 "Education":("teacher","teaching","education","lecturer","training","curriculum"),
 "Legal & justice":("attorney","lawyer","solicitor","barrister","legal counsel","litigation","contract law","juris doctor","paralegal","legal practice","advocacy"),
 "Occupational safety":("occupational health and safety","safety officer","hse","ehs","safety inspector","nebosh","iosh","risk assessment","industrial hygiene","workplace safety","safety management"),
 "Medical & clinical practice":("physician","doctor of medicine","medical doctor","general practitioner","surgeon","dentist","clinical care","patient care","hospital physician","medical residency"),
 "Nursing & allied care":("registered nurse","nursing","physiotherapist","occupational therapist","radiographer","midwife","paramedic"),
 "Pharmacy & medicines":("licensed pharmacist","pharmacy degree","pharmd","pharmacist","pharmaceutical care","clinical pharmacist"),
 "Skilled trades":("plumber","carpenter","welder","electrician","machinist","fabricator","hvac technician","automotive technician"),
 "Transport & logistics":("truck driver","delivery driver","courier","fleet driver","pilot","forklift operator","transport manager","supply chain"),
 "Hospitality & culinary":("chef","cook","baker","barista","restaurant manager","hospitality","hotel manager","culinary"),
 "Scientific research":("scientist","researcher","laboratory","biomedical","research assistant","research fellow","phd","postdoctoral"),
 "Public service & nonprofit":("civil servant","policy officer","public affairs","ngo","nonprofit","social worker","case manager","public administration"),
 "Arts & media":("artist","illustrator","photographer","film production","musician","journalist","editor","art director"),
 "Agriculture & environment":("agronomist","agriculture","farm management","sustainability","environmental science","ecologist","forestry"),

}
SKILLS={
 "Stakeholder management":("stakeholder","client relations","relationship management","partner management"),
 "Process improvement":("process improvement","operational efficiency","process optimization","continuous improvement","lean"),
 "Project delivery":("project coordination","project management","project delivery","programme management","pmo"),
 "Financial analysis":("financial analysis","finance reporting","budget","financial modelling","forecasting"),
 "Risk controls":("risk","internal control","audit","compliance","regulatory"),
 "People leadership":("people management","team leadership","managed a team","team management","supervised"),
 "Customer relations":("customer experience","customer success","client service","customer support","account management"),
 "Business development":("business development","sales pipeline","commercial strategy","prospecting"),
 "Data & reporting":("dashboard","analytics","reporting","excel","power bi","data analysis"),
 "Technology":("software","cloud","security","api","python","sql","iam","devops"),
 "Communication":("communications","presentations","public speaking","stakeholder engagement"),
 "Operations coordination":("operations","coordination","logistics","scheduling","service delivery"),
 "Legal casework":("case law","legal drafting","litigation","legal counsel","client advocacy"),
 "Clinical care":("patient care","diagnosis","clinical assessment","medical practice"),
 "Workplace safety":("risk assessments","occupational safety","hse","safety inspections"),
 "Research methodology":("laboratory","research methodology","scientific analysis","clinical trials"),
 "Trade skills":("apprenticeship","maintenance","installation","welding","electrician"),

}
ALIASES={
 "Operations & management":("operations","operational","logistics","service delivery","office manager","process"),
 "Project & programme":("project","programme","program","pmo","implementation","delivery manager","change manager"),
 "Risk & compliance":("risk","audit","compliance","governance","fraud","regulatory","aml"),
 "Finance & banking":("banking","bank","payments","finance","treasury","investment","accounting"),
 "Security & technology":("cyber","security","iam","software","engineering","developer","it specialist"),
 "Sales & partnerships":("sales","commercial","business development","account manager","customer success","partnerships"),
 "Product & strategy":("product","strategy","consulting","business analyst","portfolio"),
 "People & talent":("human resources","talent","recruitment","hr","people operations"),
 "Design & marketing":("marketing","design","advertising","creative","communications"),
 "Engineering & trades":("electrician","technician","engineer","mechanic","construction"),
 "Healthcare":("clinical","healthcare","nurse","medical","pharmacist"),
 "Education":("teacher","lecturer","educator","education","trainer"),
 "Legal & justice":("legal","lawyer","solicitor","attorney","counsel","litigation","paralegal","law firm"),
 "Occupational safety":("occupational safety","health and safety","hse","ehs","safety officer","safety inspector","industrial hygiene"),
 "Medical & clinical practice":("doctor","physician","surgeon","gp","general practitioner","medical","dentist"),
 "Nursing & allied care":("nurse","midwife","physiotherapy","therapist","paramedic"),
 "Pharmacy & medicines":("pharmacist","clinical pharmacist","pharmacy","medicines"),
 "Skilled trades":("electrician","plumber","carpenter","welder","mechanic","hvac","technician"),
 "Transport & logistics":("driver","courier","fleet","transport","logistics","pilot"),
 "Hospitality & culinary":("chef","cook","baker","barista","hospitality","hotel","restaurant"),
 "Scientific research":("scientist","researcher","laboratory","research fellow","postdoctoral"),
 "Public service & nonprofit":("public policy","civil servant","nonprofit","ngo","social worker","public affairs"),
 "Arts & media":("artist","journalist","photographer","illustrator","creative director","film","music"),
 "Agriculture & environment":("agriculture","agronomy","environmental","ecologist","sustainability"),

}

def _normalize(s):
 s=unicodedata.normalize("NFKD",str(s or "").casefold()).replace("ı","i")
 return "".join(c for c in s if not unicodedata.combining(c))

def _hit(text,term):
 return re.search(r"(?<!\w)"+re.escape(_normalize(term))+r"(?!\w)",text) is not None

def career_dna(cv,preferences=None):
 """Expose only demonstrable skill signals; never infer credentials or employers."""
 text=_normalize(cv)[:23000]
 ranked=[]
 for name,terms in FAMILIES.items():
  evidence=[term for term in terms if _hit(text,term)]
  if evidence:
   ranked.append((name,len(evidence),evidence[:3]))
 ranked.sort(key=lambda row:(row[1],len(row[2])),reverse=True)
 skills=[label for label,terms in SKILLS.items() if any(_hit(text,t) for t in terms)]
 roles=[{"name":name,"evidence":evidence} for name,_,evidence in ranked[:5]]
 # Do not mistake a self-described preference for actual professional experience.
 return {
  "role_families":roles,
  "transferable_skills":skills[:10],
  "headline":roles[0]["name"] if roles else "Experience-led career profile",
  "method":"Extracted from documented CV terminology; verify before applying.",
  "suggested_directions":[x["name"] for x in roles[:3]],
 }

def role_similarity(job,dna):
 """0-100 cross-title support. Other filters still verify real CV credentials."""
 title=_normalize(job.get("title"))
 desc=_normalize(job.get("description"))[:3500]
 evidence=[r.get("name") for r in dna.get("role_families",[]) if isinstance(r,dict)]
 score=0
 for rank,family in enumerate(evidence):
  terms=ALIASES.get(family,())
  if any(_hit(title,t) for t in terms):
   score=max(score,100-8*rank)
  elif any(_hit(desc,t) for t in terms):
   score=max(score,48-4*rank)
 skills=dna.get("transferable_skills") or []
 related=sum(1 for k in skills if any(_hit(desc,t) for t in SKILLS.get(k,())))
 return min(100,max(score, min(68,related*11)))
