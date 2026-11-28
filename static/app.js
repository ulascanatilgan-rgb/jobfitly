const $=id=>document.getElementById(id);
const state={config:null,me:null,jobs:[],watch:[],screen:'today',step:0,qIndex:0,sIndex:0,questions:{},swipes:{},kit:null,kitTab:'motivation',job:null,authMode:'register',editMode:false};
const JOB_LANGUAGES=['English','Dutch','French','German','Spanish','Italian','Portuguese','Turkish'];
function selectedLanguageList(value){
 const raw=Array.isArray(value)?value:String(value||'').split(/[,;|]/);
 return raw.map(v=>String(v).trim()).filter(v=>JOB_LANGUAGES.includes(v));
}
function languagePicker(id,value){
 const chosen=selectedLanguageList(value);
 return '<fieldset class="languages-field" id="'+id+'"><legend>Languages <small>(select all that apply)</small></legend><div class="language-choices">'
 +JOB_LANGUAGES.map(lang=>'<label class="language-chip"><input type="checkbox" value="'+lang+'" '+(chosen.includes(lang)?'checked':'')+'><span>'+lang+'</span></label>').join('')
 +'</div></fieldset>';
}
function chosenLanguages(id){
 return [...document.querySelectorAll('#'+id+' input[type="checkbox"]:checked')]
   .map(el=>el.value).join(', ');
}
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path,options={}){const r=await fetch(path,{...options,headers:{...(options.body instanceof FormData?{}:{'Content-Type':'application/json'}),...(state.config?.csrf?{'X-CSRF-Token':state.config.csrf}:{}),...(options.headers||{})}});const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.error||'Something went wrong');return d;}
function notify(msg,error=false){const e=$('toast');e.textContent=msg;e.className='toast show'+(error?' error':'');setTimeout(()=>e.className='toast',3400);}
function section(id){['landing','auth','app','onboarding'].forEach(i=>$(i).classList.toggle('hidden',i!==id));window.scrollTo(0,0);}
function showLanding(){section('landing');}
function showAuth(mode='register'){state.authMode=mode;section('auth');$('auth-title').textContent=mode==='register'?'Create your account.':'Welcome back.';$('auth-subtitle').textContent=mode==='register'?'Just the essentials. We’ll take it from there.':'Ready for your next five?';$('auth-submit').textContent=mode==='register'?'Create account →':'Log in →';$('auth-toggle').innerHTML=mode==='register'?'Already have an account? <button onclick="showAuth(\'login\')">Log in</button>':'New to Waydefine? <button onclick="showAuth(\'register\')">Get started</button>';}
$('auth-form').addEventListener('submit',async e=>{e.preventDefault();const submit=$('auth-submit');submit.disabled=true;try{const login=await api('/api/'+state.authMode,{method:'POST',body:JSON.stringify({email:$('auth-email').value,password:$('auth-password').value,remember:$('auth-remember').checked})});state.config.csrf=login.csrf;await boot(true);}catch(e){notify(e.message,true)}finally{submit.disabled=false}});
async function boot(){state.config=await api('/api/config');try{state.me=await api('/api/me')}catch{showLanding();return;}let p=state.me.profile;state.questions={...p.questions};state.swipes={...p.swipes};await loadContent();navigate('today')}
async function loadContent(){let [a,b]=await Promise.all([api('/api/jobs'),api('/api/watchlist')]);state.jobs=a.jobs;state.watch=b.jobs;state.has_run=a.has_run;state.date=a.date;updateCounts();}
function updateCounts(){$('watch-counter').textContent=state.watch.length;}
function startOnboarding(edit=false){state.editMode=edit;state.step=0;state.qIndex=0;state.sIndex=0;section('onboarding');drawStep();}
function stepBack(){if(state.step===1&&state.qIndex>0){state.qIndex--;drawStep();return;}if(state.step===2&&state.sIndex>0){state.sIndex--;drawStep();return;}if(state.step>0){state.step--;drawStep();return;}if(state.editMode){section('app');navigate('profile')}}
async function stepNext(){try{
 if(state.step===0){const name=$('p-name').value.trim(),city=$('p-city').value.trim(),country=$('p-country').value.trim(),keywords=$('p-keywords').value.trim(),language=chosenLanguages('onboard-languages');let data=await api('/api/profile',{method:'POST',body:JSON.stringify({name,city,country,language,keywords})});state.me.profile=data.profile;let file=$('cv-input').files[0];if(file){let fd=new FormData();fd.append('file',file);data=await api('/api/cv',{method:'POST',body:fd});state.me.profile=data.profile}if(!state.me.profile.has_cv){notify('Please upload your CV to build your profile.',true);return;}state.step=1;drawStep();return;}
 if(state.step===1){const q=state.config.questions[state.qIndex];state.questions[q.id]=Number($('question-slider').value);if(state.qIndex<state.config.questions.length-1){state.qIndex++;drawStep();return;}let data=await api('/api/profile',{method:'POST',body:JSON.stringify({questions:state.questions})});state.me.profile=data.profile;state.step=2;drawStep();return;}
 if(state.step===2){const s=state.config.swipes[state.sIndex];if(state.sIndex<state.config.swipes.length-1){state.sIndex++;drawStep();return;}let data=await api('/api/profile',{method:'POST',body:JSON.stringify({swipes:state.swipes})});state.me.profile=data.profile;await loadContent();section('app');navigate('today');notify('Your profile is ready. Press Run to find your jobs.');}
 }catch(e){notify(e.message,true)}}
function drawStep(){let steps=['01 / ABOUT YOU','02 / YOUR WORK STYLE','03 / WHAT YOU WANT'];$('onboard-step-name').textContent=steps[state.step];$('onboard-step-count').textContent=(state.step+1)+' of 3';$('progress-bar').style.width=((state.step+1)/3*100)+'%';$('step-back').textContent=state.step===0?(state.editMode?'Cancel':'← Back'):'← Back';const next=$('step-next');next.textContent=state.step===2&&state.sIndex===state.config.swipes.length-1?'Find my 5 →':'Continue →';let p=state.me.profile;
 if(state.step===0){$('onboard-content').innerHTML=`<h1>Let's start with you.</h1><p class="intro">Your experience and your destination. Nothing more.</p><div class="two-fields"><label class="field">Your name<input id="p-name" placeholder="Your name" value="${esc(p.name)}"></label>${languagePicker('onboard-languages',p.language)}<label class="field">Country<input id="p-country" placeholder="Belgium" value="${esc(p.country)}"></label><label class="field">City (optional)<input id="p-city" placeholder="Blank = nationwide" value="${esc(p.city)}"></label></div><label class="field">Roles or interests (a few words)<input id="p-keywords" placeholder="Operations, strategy, client relations" value="${esc(p.keywords)}"></label><label for="cv-input" class="file-drop"><span class="file-icon">⇧</span><strong id="file-label">${p.cv_name?esc(p.cv_name):'Upload your CV'}</strong><span>PDF, DOCX or TXT · Max 5 MB</span><input type="file" id="cv-input" accept=".pdf,.docx,.txt" onchange="$('file-label').textContent=this.files[0]?.name||'Upload your CV'"></label><p class="privacy-note">Your CV is private to your account. You can delete your account and data anytime.</p>`;}
 if(state.step===1){let q=state.config.questions[state.qIndex],value=state.questions[q.id]??5;$('onboard-content').innerHTML=`<h1>How do you work?</h1><p class="intro">20 quick questions. No right or wrong answers.</p><div class="question-progress">Question ${state.qIndex+1} of ${state.config.questions.length}</div><div class="question-panel"><h2>${esc(q.text)}</h2><div class="slider-row"><span>Not like me</span><span class="rating-output" id="slider-value">${value}/10</span></div><input id="question-slider" class="range" type="range" min="0" max="10" value="${value}" oninput="$('slider-value').textContent=this.value+'/10';state.questions['${q.id}']=Number(this.value)"><div class="scale-labels"><span>0 — Not at all</span><span>10 — Very much</span></div></div><div class="question-controls"><button class="subtle-button" onclick="stepBack()">← Previous</button><button class="subtle-button" onclick="state.questions['${q.id}']=5;$('question-slider').value=5;$('slider-value').textContent='5/10'">Reset to 5</button></div>`;}
 if(state.step===2){let s=state.config.swipes[state.sIndex];let chips=s.choices.map(ch=>`<button class="choice ${(selectedPreferenceValues(state.swipes[s.id]).includes(ch)||(isNeutralPreference(ch)&&!selectedPreferenceValues(state.swipes[s.id]).length))?'selected':''}" onclick="pickChoice('${s.id}',decodeURIComponent('${encodeURIComponent(ch)}'))">${esc(ch)}</button>`).join('');$('onboard-content').innerHTML=`<h1>What feels right?</h1><p class="intro">Make a few quick choices. You can change them later.</p><div class="question-progress">Preference ${state.sIndex+1} of ${state.config.swipes.length}</div><div id="swipe-card" class="swipe-card"><div class="eyebrow" style="justify-content:center">YOUR IDEAL NEXT ROLE</div><h2>${esc(s.label)}</h2><div class="choice-row">${chips}</div></div><p class="swipe-hint">Choose one or more options. Leave empty for no preference.</p>`;}
}
function pickChoice(k,v){
 const current=selectedPreferenceValues(state.swipes[k]);
 if(isNeutralPreference(v))state.swipes[k]=[];
 else state.swipes[k]=current.includes(v)?current.filter(item=>item!==v):[...current,v];
 drawStep();
}
function navigate(screen){state.screen=screen;section('app');document.querySelectorAll('[data-screen]').forEach(b=>b.classList.toggle('active',b.dataset.screen===screen));if(screen==='today')renderToday();if(screen==='watch')renderWatch();if(screen==='profile')renderProfile();if(screen==='skills')renderSkills();if(screen==='search')renderSearch();if(screen==='cv')renderCV();if(screen==='history')renderHistory();window.scrollTo(0,0)}
function formatDate(s){try{return new Date(s+'T12:00:00Z').toLocaleDateString('en-GB',{month:'long',day:'numeric',year:'numeric'})}catch{return s}}
function renderToday(){let jobs=[...state.jobs].sort((a,b)=>Number(b.score||0)-Number(a.score||0)).map((j,i)=>jobCard(j,i)).join('');const p=state.me.profile;const ready=!!p.has_cv;const intro=state.has_run?`<div class="status-line"><span><i class="dot-live"></i>Run complete for today</span><span>Next Run tomorrow</span></div>`:`<div class="run-panel"><span class="date-caption">${esc(formatDate(state.date))}</span><h2>Five jobs. One click.</h2><p>Based on your CV, skills and preferences.</p><button class="btn btn-dark btn-xl" ${ready?'':'disabled'} onclick="reloadJobs()" id="run-button">Run →</button>${ready?'':'<p class="privacy-note">Upload a CV to start. Your preferences are optional.</p>'}</div>`;$('main-panel').innerHTML=`<div class="page-kicker">TODAY</div><h1 class="page-heading">Your five<span class="accent">.</span></h1>${intro}${state.has_run?'<div class="reset-actions"><button class="reset-matches" onclick="resetMyMatches()">Clear matches and search again ↺</button></div>':''}<div class="jobs-grid">${jobs}</div>${state.has_run?'<p class="privacy-note" style="margin-top:22px">Listings are sourced from web search. Some dates and links may be unverified; always check the employer’s original page before applying.</p>':''}${!state.has_run?'<div class="setup-row"><button onclick="navigate(&quot;cv&quot;)">01 CV</button><button onclick="navigate(&quot;skills&quot;)">02 Work Style</button><button onclick="navigate(&quot;search&quot;)">03 Purpose</button></div>':''}`;}
function jobCard(j,i=0){return `<article class="job-card"><div class="job-top"><div><div class="job-company">${esc(j.company)} ${j.source?.includes('DEMO')?'<span class="tag">Sample</span>':''}</div><h2 class="job-title">${esc(j.title)}</h2><div class="job-loc">${esc([j.city,j.country].filter(Boolean).filter((value,index,array)=>array.indexOf(value)===index).join(", "))}</div></div><div class="score-circle"><strong>${Number(j.score).toFixed(1)}</strong><small>FIT / 10</small></div></div><div class="job-bottom"><button class="text-action" onclick="showJob(${j.id})">Why this fit ↗</button><div class="job-feedback-actions"><button class="not-for-me" onclick="rejectJob(${j.id})" title="Help Waydefine learn what to avoid">Not for me</button><button class="save-button ${j.saved?'saved':''}" onclick="toggleSave(${j.id},${Boolean(j.saved)})">${j.saved?'♥ Saved':'+ MyJobs'}</button></div></div></article>`}
async function rejectJob(id){
 try{
  await api('/api/jobs/'+id+'/not-for-me',{method:'POST'});
  await loadContent();
  navigate(state.screen==='watch'?'watch':'results');
  notify('Noted. Waydefine learns from your feedback and will prioritize different roles.');
 }catch(e){notify(e.message,true)}
}
async function reloadJobs(){const btn=$('run-button');if(btn){btn.disabled=true;btn.textContent='Checking live jobs…'}try{let r=await api('/api/jobs/run',{method:'POST'});await loadContent();navigate('today');notify(r.count===5?'Your five matches are ready.':r.count+' verified jobs found today.')}catch(e){notify(e.message,true);renderToday()}}
function renderWatch(){const items=state.watch.map(j=>`<div class="saved-row"><div><div class="job-company">${esc(j.company)} <span class="accent">· ${j.score}/10 fit</span></div><h3>${esc(j.title)}</h3><p>${esc(j.city||j.country)}</p></div><div class="saved-actions"><button class="not-for-me" onclick="rejectJob(${j.id})">Not for me</button><button class="btn btn-light" onclick="removeSave(${j.id})">Remove</button><button class="btn btn-outline" onclick="openKit(${j.id},'motivation')">Generate motivations</button><button class="btn btn-dark" onclick="openKit(${j.id},'cv')">Update CV · PDF</button></div></div>`).join('');$('main-panel').innerHTML=`<div class="page-kicker">SAVED</div><h1 class="page-heading">My jobs<span class="accent">.</span></h1><div class="saved-list">${items||'<div class="empty-state"><h3>No saved jobs yet.</h3><button class="btn btn-dark" onclick="navigate(&quot;today&quot;)">Today’s 5</button></div>'}</div>`;}
async function toggleSave(id,saved){try{await api('/api/watchlist/'+id,{method:saved?'DELETE':'POST'});await loadContent();state.screen==='today'?renderToday():renderWatch();notify(saved?'Removed from MyJobs.':'Added to MyJobs.')}catch(e){notify(e.message,true)}}
function removeSave(id){toggleSave(id,true)}
function showJob(id){let j=[...state.jobs,...state.watch].find(x=>x.id===id);if(!j)return;const overlay=document.createElement('div');overlay.id='detail-modal';overlay.className='modal-back';overlay.onclick=e=>{if(e.target===overlay)overlay.remove()};overlay.innerHTML=`<div class="modal"><button class="close" aria-label="Close" onclick="$('detail-modal').remove()">×</button><div class="page-kicker">${esc(j.company)}</div><h2>${esc(j.title)}</h2><p>${esc(j.city)} · ${esc(j.country)} · ${j.score}/10 profile fit</p><div class="kit-banner"><strong>Why this matches</strong><p>${j.matched_terms?.length?'Your background and this listing share: '+j.matched_terms.map(esc).join(', ')+'.':'This posting has some relevance to your background and preferences; inspect the original listing before applying.'}</p></div><p style="max-height:220px;overflow:auto;white-space:pre-wrap">${esc(j.description||'No description available.')}</p>${['Himalayas','Jobicy','Arbeitnow','Greenhouse','Lever','Ashby','Adzuna'].includes(j.source)?`<p class="job-source-credit">Listing supplied by ${esc(j.source)}. <a href="${esc(j.url)}" target="_blank" rel="noopener noreferrer">View source ↗</a></p>`:''}<div class="kit-actions">${j.url?`<a class="btn btn-dark" href="${esc(j.url)}" target="_blank" rel="noopener noreferrer">View original listing ↗</a>`:'<span class="tag">Sample listing — no application link</span>'}<button class="btn btn-outline" onclick="$('detail-modal').remove();toggleSave(${j.id},${Boolean(j.saved)})">${j.saved?'Remove from saved':'+ MyJobs'}</button></div></div>`;document.body.appendChild(overlay)}
function renderWorkStyleRadar(answers={}){
 const dimensions=[
  {label:'Analysis',items:['analytical','detail']},
  {label:'Creativity',items:['creative','ambiguity']},
  {label:'Strategy',items:['strategy','ownership']},
  {label:'Leadership',items:['leadership','coordination']},
  {label:'Teamwork',items:['collaboration','people']},
  {label:'Client focus',items:['client_energy','communication']},
  {label:'Independence',items:['autonomy','structure']},
  {label:'Execution',items:['operations','pace']}
 ];
 const values=dimensions.map(dim=>{
   const entries=dim.items.filter(key=>Number.isFinite(Number(answers[key]))&&answers[key]!=null);
   return entries.length?entries.reduce((sum,key)=>sum+Number(answers[key]),0)/entries.length:5;
 });
 const answered=Object.keys(answers||{}).length;
 const cx=200,cy=163,radius=108;
 const location=(index,magnitude)=>{const theta=-Math.PI/2+index*Math.PI/4;return [cx+radius*magnitude*Math.cos(theta),cy+radius*magnitude*Math.sin(theta)]};
 const coords=pts=>pts.map(([x,y])=>x.toFixed(1)+','+y.toFixed(1)).join(' ');
 const grid=[.25,.5,.75,1].map(level=>'<polygon class="radar-grid-ring" points="'+coords(dimensions.map((_,i)=>location(i,level)))+'"/>').join('');
 const axes=dimensions.map((_,i)=>{const [x,y]=location(i,1);return '<line class="radar-axis" x1="'+cx+'" y1="'+cy+'" x2="'+x+'" y2="'+y+'"/>'}).join('');
 const labels=dimensions.map((dim,i)=>{
   const [px,y]=location(i,1.12);
   const x=i===6?Math.max(90,px):px;
   const anchor=x<cx-14?'end':x>cx+14?'start':'middle';
   return '<text class="radar-label" x="'+x.toFixed(1)+'" y="'+(y+3).toFixed(1)+'" text-anchor="'+anchor+'">'+esc(dim.label)+'</text>';
 }).join('');
 const filled=coords(dimensions.map((_,i)=>location(i,values[i]/10)));
 const vertices=dimensions.map((_,i)=>{
   const [x,y]=location(i,values[i]/10);
   return '<circle class="radar-vertex" cx="'+x.toFixed(1)+'" cy="'+y.toFixed(1)+'" r="3.1"/>';
 }).join('');
 const summary=dimensions.map((dim,i)=>dim.label+': '+values[i].toFixed(1)+'/10').join(', ');
 return '<div class="radar-wrap">'
  +'<div class="radar-intro"><span>YOUR WORK STYLE</span><strong>'+answered+' / 20 responses</strong></div>'
  +'<svg class="work-radar" viewBox="0 0 400 338" role="img" aria-label="'+esc(summary)+'">'
  +'<g>'+grid+axes+'</g>'+labels
  +(answered?'<polygon class="radar-surface" points="'+filled+'"/>'+vertices:'')
  +'<circle class="radar-center" cx="'+cx+'" cy="'+cy+'" r="2.5"/>'
  +'</svg>'
  +'<p class="radar-caption">'+(answered?'An illustrative view of how you prefer to work.':'Complete Tell about yourself to draw your work-style profile.')+' It does not change your job matching.</p>'
  +'</div>';
}
function jobPossibilityScore(profile){
 const p=profile||{},cv=String(p.cv_text_preview||'').trim();
 const cvPoints=p.has_cv?5+Math.min(4,Math.floor(cv.length/650)):0;
 const answered=Object.values(p.questions||{}).filter(v=>v!==null&&v!==''&&Number.isFinite(Number(v))).length;
 const stylePoints=Math.round(4*Math.min(20,answered)/20);
 const prefs=[p.city,p.country,p.language,p.keywords,...Object.values(p.swipes||{})].filter(v=>v!=null&&String(v).trim()).length;
 const preferencePoints=Math.min(4,prefs);
 const observed=(state.jobs||[]).map(j=>Number(j.score)).filter(n=>Number.isFinite(n)&&n>0);
 const marketPoints=observed.length?Math.min(3,Math.round(Math.max(...observed)*.3)):0;
 return Math.max(80,Math.min(100,80+cvPoints+stylePoints+preferencePoints+marketPoints));
}
function renderPossibilityScore(profile){
 const value=jobPossibilityScore(profile);
 const caption=(state.jobs||[]).length
   ?'Illustrative profile readiness based on your CV, preferences and available job matches. Not a hiring probability.'
   :'Illustrative profile readiness based on your CV and preferences. Market matches are included after a search; not a hiring probability.';
 return '<div class="possibility-wrap"><div class="possibility-pills" aria-label="Job Possibility Score '+value+' out of 100">'
   +'<span class="possibility-label">Job Possibility Score</span>'
   +'<strong class="possibility-number">'+value+'/100</strong></div>'
   +'<p class="possibility-note">'+esc(caption)+'</p></div>';
}
function renderCareerDNA(dna={},feedbackCount=0){
 const families=(dna.role_families||[]).filter(x=>x&&x.name).slice(0,5);
 const skills=(dna.transferable_skills||[]).slice(0,9);
 const roles=families.map(x=>'<span class="dna-role" title="'+esc((x.evidence||[]).join(', '))+'">'+esc(x.name)+'</span>').join('');
 const badges=skills.map(x=>'<span class="dna-skill">'+esc(x)+'</span>').join('');
 return '<section class="profile-cv-facts career-dna"><div class="dna-heading"><h2>Career DNA</h2><span>CV based · no extra AI cost</span></div>'
  +'<p class="dna-intro">Documented strengths and related career directions identified from your CV.</p>'
  +'<h3>Career directions</h3><div class="dna-tags">'+(roles||'<span class="flow-muted">Upload a detailed CV to identify role families.</span>')+'</div>'
  +'<h3>Transferable skills</h3><div class="dna-tags">'+(badges||'<span class="flow-muted">No clear skill evidence identified yet.</span>')+'</div>'
  +'<p class="dna-footnote">Evidence-based suggestions, not verified qualifications or guaranteed job matches.</p>'
  +(feedbackCount?'<p class="dna-learning-note">Waydefine Learns · '+feedbackCount+' rejected role'+(feedbackCount===1?'':'s')+' remembered.</p>':'')
  +'</section>';
}
function renderAlternativeNextMoves(moves=[],selected=[]){
 if(!Array.isArray(moves)||!moves.length)return '<section class="profile-cv-facts next-moves">'
  +'<div class="next-moves-head"><div><span class="next-moves-eyebrow">DISCOVER WHAT ELSE YOU COULD DO</span><h2>Alternative Next Move<span class="accent">.</span></h2></div></div>'
  +'<p class="next-moves-intro">Upload a detailed CV to uncover career directions beyond your current job title.</p></section>';
 return '<section class="profile-cv-facts next-moves">'
  +'<div class="next-moves-head"><div><span class="next-moves-eyebrow">YOUR CAREER, REIMAGINED</span><h2>Alternative Next Move<span class="accent">.</span></h2></div>'
  +'<span class="next-moves-count">03 NEW PATHS</span></div>'
  +'<p class="next-moves-intro">Three adjacent career directions you might not have considered, based on your CV, skills and work style. Explore them without limiting your regular job search.</p>'
  +'<div class="next-moves-cards">'+moves.slice(0,3).map((move,i)=>{
     const has=selected.includes(move.title);
     const cv=Math.min(100,Math.max(0,Number(move.evidence_score)||0));
     const style=move.style_score==null?null:Math.min(100,Math.max(0,Number(move.style_score)||0));
     return '<article class="next-move-card">'
      +'<div class="next-move-card-top"><span class="next-move-ordinal">0'+(i+1)+'</span><span class="next-move-family">'+esc(move.family)+'</span></div>'
      +'<h3>'+esc(move.title)+'</h3>'
      +'<p class="next-move-copy">'+esc(move.description)+'</p>'
      +'<div class="next-move-signals">'
      +'<div class="next-move-signal"><div class="next-move-signal-title"><span>CV strength overlap</span><strong>'+cv+'/100</strong></div><div class="next-move-track"><span class="next-move-fill" style="width:'+cv+'%"></span></div></div>'
      +'<div class="next-move-signal"><div class="next-move-signal-title"><span>Work-style alignment</span><strong>'+(style===null?'Not set':style+'/100')+'</strong></div>'
      +'<div class="next-move-track"><span class="next-move-fill secondary" style="width:'+(style===null?0:style)+'%"></span></div></div></div>'
      +'<div class="next-move-tags">'+(move.cv_evidence||[]).slice(0,3).map(t=>'<span>'+esc(t)+'</span>').join('')+'</div>'
      +'<button class="next-move-add'+(has?' is-added':'')+'" data-path="'+esc(move.title)+'" onclick="addAlternativePath(this.dataset.path)">'
      +(has?'Added to search ✓':'Add to search +')+'</button>'
      +'</article>';
   }).join('')+'</div>'
  +'<p class="next-moves-footnote">Exploratory suggestions, not advertised vacancies or hiring probabilities. The bars represent indicative evidence signals, not your chance of being hired.</p>'
  +'</section>';
}
async function addAlternativePath(title){
 const selected=Array.isArray(state.me?.profile?.path_keywords)?state.me.profile.path_keywords:[];
 if(selected.includes(title)){navigate('search');return;}
 if(selected.length>=3){notify('Choose up to three alternative paths. Remove one in What you search first.',true);return;}
 try{
  const result=await api('/api/profile',{method:'POST',body:JSON.stringify({path_keywords:[...selected,title]})});
  state.me.profile=result.profile;
  navigate('search');
  notify('Added '+title+' to your search focus. CV-based matches remain included.');
 }catch(error){notify(error.message,true)}
}
async function removeAlternativePath(title){
 const selected=Array.isArray(state.me?.profile?.path_keywords)?state.me.profile.path_keywords:[];
 try{
  const result=await api('/api/profile',{method:'POST',body:JSON.stringify({path_keywords:selected.filter(value=>value!==title)})});
  state.me.profile=result.profile;
  const target=document.querySelector('[data-selected-path="'+CSS.escape(title)+'"]');
  if(target)target.remove();
  const list=$('selected-path-list');
  if(list&&!list.querySelector('.selected-path-chip'))list.innerHTML='<span class="selected-path-empty">No alternative paths selected yet. Explore Your profile to add one.</span>';
  notify('Removed from your search focus.');
 }catch(error){notify(error.message,true)}
}
function renderSelectedPathKeywords(paths=[]){
 return '<div class="selected-paths"><div class="selected-paths-title">SELECTED CAREER DIRECTIONS <span>Optional search focus</span></div>'
  +'<div id="selected-path-list" class="selected-path-list">'
  +(paths.length?paths.map(path=>'<span class="selected-path-chip" data-selected-path="'+esc(path)+'">'
   +'<span>'+esc(path)+'</span><button type="button" data-path="'+esc(path)+'" aria-label="Remove '+esc(path)+'" onclick="removeAlternativePath(this.dataset.path)">×</button></span>').join('')
   :'<span class="selected-path-empty">No alternative paths selected yet. Explore Your profile to add one.</span>')
  +'</div><p class="selected-path-hint">We prioritize these directions while continuing to look for other jobs that match your CV.</p></div>';
}
function renderProfile(){
 const p=state.me.profile||{},d=p.cv_details||{};
 const label={name:'Name',email:'Email',phone:'Phone',location:'Location',linkedin:'LinkedIn',website:'Website',languages:'Languages',headline:'Professional headline',nationality:'Nationality',date_of_birth:'Date of birth'};
 const rows=Object.entries(d).filter(([k,v])=>v&&k!=='name_confirmed').map(([k,v])=>'<div class="cv-fact"><span>'+esc(label[k]||k.replaceAll('_',' '))+'</span><strong>'+esc(String(v))+'</strong></div>').join('');
 const scores=(state.config.questions||[]).map(q=>({label:q.text,score:(p.questions||{})[q.id]??5})).sort((a,b)=>b.score-a.score).slice(0,4);
 const preferences=Object.values(p.swipes||{}).filter(Boolean);
 const nameNotice=p.name_needs_confirmation?'<p class="profile-name-warning">We could not confidently identify your name from the uploaded CV. Please enter your real full name below before generating documents.</p>':'<p class="profile-name-caption">Please verify the name extracted from your CV. Correct it here if necessary.</p>';
 const confirmName='<form class="profile-name-form" onsubmit="saveConfirmedName();return false;"><label for="confirmed-name">Full name</label><div class="profile-name-row"><input id="confirmed-name" autocomplete="name" maxlength="80" placeholder="First and last name" value="'+esc(d.name||'')+'"><button class="btn btn-outline" type="submit">Confirm name</button></div></form>';
 $('main-panel').innerHTML='<div class="page-kicker">PERSONAL PROFILE</div><h1 class="page-heading">Your profile<span class="accent">.</span></h1>'
 +'<p class="page-subheading">Personal details from your CV. The name is validated separately so a location cannot become your identity.</p>'
 +'<section class="profile-cv-facts"><h2>'+esc(d.name||'Name confirmation needed')+'</h2>'+nameNotice+confirmName
 +(rows||'<p class="flow-muted">Upload a readable CV to extract your details.</p>')+'</section>'
 +'<section class="profile-cv-facts"><h2>What you are looking for</h2><p>'+esc([p.city,p.country,p.language,...preferences].filter(Boolean).join(' · ')||'Set your job preferences.')+'</p></section>'
 +renderCareerDNA(p.career_dna||{},p.feedback_count||0)
 +renderAlternativeNextMoves(p.next_moves||[],p.path_keywords||[])
 +'<section class="profile-cv-facts profile-work-style"><h2>Work style</h2>'+renderWorkStyleRadar(p.questions||{})+renderPossibilityScore(p)+'</section>'
 +'<p class="profile-small-note">Your CV remains the source of truth. Confirmed names are used consistently in both PDF documents.</p>'
 +'<button class="subtle-button" style="color:var(--plum)" onclick="deleteAccount()">Delete my account and data ↗</button>';
}
async function saveConfirmedName(){
 const input=$('confirmed-name'),name=input&&input.value.trim();
 if(!name){notify('Enter your first and last name.',true);return}
 try{
  const response=await api('/api/profile/name',{method:'POST',body:JSON.stringify({name})});
  state.me.profile=response.profile;renderProfile();notify('Your name is confirmed for future CVs and motivation letters.');
 }catch(error){notify(error.message,true)}
}
async function openKit(id,tab='motivation'){
 const job=state.watch.find(x=>x.id===id);if(!job)return;
 state.job=job;state.kit=null;state.kitTab=tab;state.kitBusy=true;
 renderKit();await generateKit();
}
function kitBusyMarkup(){
 return '<div class="kit-preparing" role="status" aria-live="polite">'
 +'<svg class="kit-hourglass" viewBox="0 0 80 90" aria-hidden="true" focusable="false">'
 +'<path class="kit-hourglass-frame" d="M18 7 H62 M18 83 H62 M23 8 V19 Q23 33 40 45 Q57 57 57 71 V82 M57 8 V19 Q57 33 40 45 Q23 57 23 71 V82" />'
 +'<path class="kit-hourglass-sand-top" d="M28 19 H52 Q52 29 40 40 Q28 29 28 19 Z"/>'
 +'<path class="kit-hourglass-sand-bottom" d="M40 51 Q28 65 28 76 H52 Q52 65 40 51 Z"/>'
 +'<path class="kit-hourglass-stream" d="M40 43 V52" />'
 +'</svg>'
 +'<strong>Preparing your application</strong>'
 +'<span>Matching your experience to the vacancy and refining the document.</span>'
 +'</div>';
}
function renderKit(){
 const j=state.job,kit=state.kit;
 const content=state.kitBusy?kitBusyMarkup():kit?
 '<div class="kit-tabs"><button class="'+(state.kitTab==='motivation'?'active':'')+'" onclick="switchKit(\'motivation\')">Motivation statement</button><button class="'+(state.kitTab==='cv'?'active':'')+'" onclick="switchKit(\'cv\')">Tailored CV</button></div>'
 +'<div class="kit-text">'+esc(kit[state.kitTab])+'</div>'
 +'<div class="kit-actions"><button class="btn btn-dark" onclick="previewKitPdf()">Preview & download PDF ↗</button>'
 +'<button class="btn btn-outline" onclick="copyKit()">Copy text</button><button class="btn btn-outline" onclick="generateKit()">Regenerate ↻</button></div>'
 :'<div class="kit-banner"><strong>One role. Two thoughtful drafts.</strong><p>We tailor your CV and motivation from the uploaded CV and this vacancy.</p></div><button class="btn btn-dark" onclick="generateKit()">Generate application kit ↗</button>';
 $('main-panel').innerHTML='<button class="subtle-button kit-back" onclick="navigate(\'watch\')">← Back to My jobs</button>'
 +'<div class="page-kicker">APPLICATION KIT</div><h1 class="page-heading">Ready to apply<span class="accent">.</span></h1>'
 +'<p class="page-subheading">'+esc(j.title)+' · '+esc(j.company)+'</p>'
 +(j.url?'<a class="text-action" href="'+esc(j.url)+'" target="_blank" rel="noopener noreferrer">Open original listing ↗</a>':'')
 +'<div id="kit-body">'+content+'</div>'
 +'<p class="privacy-note" style="margin-top:25px">Review the generated draft. Document generation sends CV text and vacancy details to OpenAI when AI is enabled.</p>';
}
async function generateKit(){
 if(state.kitBusyRequest)return;
 state.kitBusy=true;state.kitBusyRequest=true;renderKit();
 try{
  const kit=await api('/api/kit/'+state.job.id,{method:'POST'});
  state.kit=kit;state.kitBusy=false;renderKit();
  notify(kit.engine==='AI'?'Your tailored documents are ready.':'Your draft is ready.');
 }catch(error){
  state.kitBusy=false;renderKit();notify(error.message,true);
 }finally{state.kitBusyRequest=false}
}
function switchKit(t){state.kitTab=t;renderKit()}
function closePdfPreview(){
 const screen=$('pdf-preview');
 if(screen)screen.remove();
 document.body.classList.remove('pdf-open');
}
function previewKitPdf(){
 if(!state.job||!state.kit){notify('Generate a document before opening the PDF.',true);return;}
 closePdfPreview();
 const kind=state.kitTab,job=state.job;
 const label=kind==='cv'?'Tailored CV':'Motivation statement';
 const preview=document.createElement('div');
 preview.className='pdf-preview-screen';preview.id='pdf-preview';
 preview.innerHTML='<header class="pdf-preview-header">'
 +'<button class="pdf-back" type="button" onclick="closePdfPreview()">← Back to Waydefine</button>'
 +'<strong>'+label+'</strong>'
 +'<button class="pdf-save btn btn-dark" type="button" onclick="savePdfFromApp()">Save PDF ↓</button>'
 +'</header>'
 +'<iframe class="pdf-preview-frame" title="'+label+' PDF preview" src="/api/kit/'+job.id+'/download/'+kind+'?view=1"></iframe>'
 +'<p class="pdf-preview-tip">The preview stays inside Waydefine. Use Back to return to your application.</p>';
 document.body.appendChild(preview);
 document.body.classList.add('pdf-open');
}
async function savePdfFromApp(){
 if(!state.job||!state.kit)return;
 const kind=state.kitTab,job=state.job;
 const endpoint='/api/kit/'+job.id+'/download/'+kind;
 try{
  const response=await fetch(endpoint,{credentials:'same-origin'});
  if(!response.ok){
   const data=await response.json().catch(()=>({}));
   throw new Error(data.error||'PDF could not be prepared.');
  }
  const blob=await response.blob();
  if(blob.type!=='application/pdf')throw new Error('Unexpected file format.');
  const link=URL.createObjectURL(blob),anchor=document.createElement('a');
  const company=String(job.company||'Application').replace(/[^a-z0-9_-]/gi,'_').slice(0,40);
  anchor.href=link;anchor.download='Waydefine_'+kind+'_'+company+'.pdf';
  document.body.appendChild(anchor);anchor.click();anchor.remove();
  setTimeout(()=>URL.revokeObjectURL(link),25000);
  notify('PDF ready. Use Back to Waydefine when finished.');
 }catch(error){notify(error.message,true)}
}
function downloadKit(){previewKitPdf()}
async function copyKit(){try{await navigator.clipboard.writeText(state.kit[state.kitTab]);notify('Copied to clipboard.')}catch{notify('Copy not available in this browser.',true)}}
function renderCV(){const p=state.me.profile;$('main-panel').innerHTML=`<div class="page-kicker">YOUR EXPERIENCE</div><h1 class="page-heading">CV<span class="accent">.</span></h1><p class="page-subheading">${p.has_cv?esc(p.cv_name):'Upload your CV to start.'}</p><label for="cv-edit-file" class="file-drop"><span class="file-icon">⇧</span><strong id="cv-edit-label">${p.has_cv?'Replace CV':'Choose a CV'}</strong><span>PDF, DOCX or TXT · Max 5 MB</span><input id="cv-edit-file" type="file" accept=".pdf,.docx,.txt"></label><button class="btn btn-dark margin-top" onclick="saveCV()">Save CV →</button>`;const input=$('cv-edit-file');input.onchange=()=>{$('cv-edit-label').textContent=input.files[0]?.name||'Choose a CV';};}
async function saveCV(){const file=$('cv-edit-file').files[0];if(!file){notify('Select a file.',true);return}let fd=new FormData();fd.append('file',file);try{const r=await api('/api/cv',{method:'POST',body:fd});state.me.profile=r.profile;notify('CV saved. Personal details were extracted into Your profile.');renderCV()}catch(e){notify(e.message,true)}}
function renderSkills(){const p=state.me.profile;const qs=state.config.questions;$('main-panel').innerHTML=`<div class="page-kicker">WORK STYLE</div><h1 class="page-heading">Work Style<span class="accent">.</span></h1><p class="page-subheading">Rate yourself from 0 to 10.</p><div class="skills-grid">${qs.map((q,i)=>{const v=p.questions[q.id]??5;return `<label class="skill-item"><span>${String(i+1).padStart(2,'0')} · ${esc(q.text)}</span><strong id="v-${q.id}">${v}/10</strong><input data-skill="${q.id}" type="range" min="0" max="10" value="${v}" oninput="$('v-${q.id}').textContent=this.value+'/10'"></label>`}).join('')}</div><button class="btn btn-dark margin-top" onclick="saveSkills()">Save Work Style →</button>`;}
async function saveSkills(){const qs={};document.querySelectorAll('[data-skill]').forEach(x=>qs[x.dataset.skill]=Number(x.value));try{const r=await api('/api/profile',{method:'POST',body:JSON.stringify({questions:qs})});state.me.profile=r.profile;notify('Work Style saved.')}catch(e){notify(e.message,true)}}
function isNeutralPreference(v){
 return ['Open to all','No preference','Flexible','Any',''].includes(String(v||''));
}
function selectedPreferenceValues(value){
 const array=Array.isArray(value)?value:typeof value==='string'?[value]:[];
 return [...new Set(array.filter(v=>typeof v==='string'&&v.trim()&&!isNeutralPreference(v)))];
}
function searchKeywordValues(value){
 return [...new Set(String(value||'').split(/[,;\n]+/).map(v=>v.trim()).filter(Boolean))].slice(0,12);
}
function renderSearchKeywordChips(value){
 const items=searchKeywordValues(value);
 return '<div id="search-keyword-list" class="selected-path-list search-keyword-list">'
  +(items.length?items.map(word=>'<span class="selected-path-chip search-keyword-chip" data-search-keyword="'+esc(word)+'"><span>'+esc(word)+'</span><button type="button" data-keyword="'+esc(word)+'" aria-label="Remove '+esc(word)+'" onclick="removeSearchKeyword(this.dataset.keyword)">×</button></span>').join('')
  :'<span class="selected-path-empty" id="search-keyword-empty">Add one or more job keywords.</span>')
  +'</div>';
}
function addSearchKeyword(){
 const input=$('search-keywords');
 if(!input)return;
 const additions=searchKeywordValues(input.value);
 if(!additions.length)return;
 const list=$('search-keyword-list');
 const existing=[...list.querySelectorAll('[data-search-keyword]')].map(el=>el.dataset.searchKeyword);
 const merged=[...new Set([...existing,...additions])].slice(0,12);
 list.innerHTML=merged.map(word=>'<span class="selected-path-chip search-keyword-chip" data-search-keyword="'+esc(word)+'"><span>'+esc(word)+'</span><button type="button" data-keyword="'+esc(word)+'" aria-label="Remove '+esc(word)+'" onclick="removeSearchKeyword(this.dataset.keyword)">×</button></span>').join('');
 input.value='';
 input.focus();
}
function removeSearchKeyword(word){
 const chip=[...document.querySelectorAll('[data-search-keyword]')].find(el=>el.dataset.searchKeyword===word);
 if(chip)chip.remove();
 const list=$('search-keyword-list');
 if(list&&!list.querySelector('[data-search-keyword]'))list.innerHTML='<span class="selected-path-empty" id="search-keyword-empty">Add one or more job keywords.</span>';
}
function collectSearchKeywords(){
 const saved=[...document.querySelectorAll('[data-search-keyword]')].map(el=>el.dataset.searchKeyword);
 const pending=searchKeywordValues($('search-keywords')?.value||'');
 return [...new Set([...saved,...pending])].slice(0,12).join(', ');
}
function renderPreferenceMenu(group,oldValue){
 const selected=selectedPreferenceValues(oldValue);
 const options=group.choices.filter(ch=>!isNeutralPreference(ch));
 const labels=selected.length?selected.length===1?selected[0]:selected.length+' selected':'Any';
 return '<details class="multi-pref" data-preference-field="'+esc(group.id)+'">'
 +'<summary><span class="multi-pref-title">'+esc(group.label)+'</span>'
 +'<span class="multi-pref-summary" data-pref-summary>'+esc(labels)+'</span>'
 +'<span class="multi-pref-chevron" aria-hidden="true">⌄</span></summary>'
 +'<div class="multi-pref-options" role="group" aria-label="'+esc(group.label)+'">'
 +options.map(ch=>'<label class="multi-pref-item"><input type="checkbox" value="'+esc(ch)+'" '
 +(selected.includes(ch)?'checked ':'')+'onchange="refreshPreferenceMenu(this)">'
 +'<span>'+esc(ch)+'</span></label>').join('')
 +'</div></details>';
}
function refreshPreferenceMenu(checkbox){
 const container=checkbox.closest('[data-preference-field]');
 if(!container)return;
 const values=[...container.querySelectorAll('input[type="checkbox"]:checked')].map(el=>el.value);
 const label=container.querySelector('[data-pref-summary]');
 label.textContent=values.length?values.length===1?values[0]:values.length+' selected':'Any';
}
document.addEventListener('click',event=>{
 document.querySelectorAll('details.multi-pref[open]').forEach(menu=>{
  if(!menu.contains(event.target))menu.removeAttribute('open');
 });
});
function renderSearch(){
 const p=state.me.profile;
 const selects=state.config.swipes.map(group=>renderPreferenceMenu(group,p.swipes[group.id])).join('');
 $('main-panel').innerHTML=`<div class="page-kicker">STEP 03 / YOUR SEARCH</div><h1 class="page-heading">What you search<span class="accent">.</span></h1><p class="page-subheading">Language and location are strict requirements. Leave city blank to search the entire selected country.</p><div class="search-compact-panel"><div class="two-fields search-fields"><label class="field">Country<input id="search-country" autocomplete="country-name" value="${esc(p.country)}" placeholder="Belgium"></label><label class="field">City / cities (optional)<input id="search-city" value="${esc(p.city)}" placeholder="e.g. Brussels, Antwerp (blank = nationwide)"></label>${languagePicker('search-languages',p.language)}<label class="field search-keyword-field">Job keywords<div class="search-keyword-entry"><input id="search-keywords" value="" placeholder="Operations, client relations" onkeydown="if(event.key==='Enter'){event.preventDefault();addSearchKeyword()}"><button type="button" class="search-keyword-add" onclick="addSearchKeyword()">Add</button></div>${renderSearchKeywordChips(p.keywords)}</label></div>${renderSelectedPathKeywords(p.path_keywords||[])}<div class="search-section-label">YOUR PREFERENCES</div><div class="search-preferences-grid">${selects}</div><button class="btn btn-dark search-save-button" onclick="saveSearch()">Save preferences ↗</button></div>`;
}
function pickSearch(button){document.querySelectorAll('[data-choice="'+button.dataset.choice+'"]').forEach(b=>b.classList.toggle('selected',b===button));}
async function saveSearch(){
 const swipes={};
 document.querySelectorAll('[data-preference-field]').forEach(group=>{
  const chosen=[...group.querySelectorAll('input[type="checkbox"]:checked')].map(el=>el.value);
  if(chosen.length)swipes[group.dataset.preferenceField]=chosen;
 });
 const data={country:$('search-country').value.trim(),city:$('search-city').value.trim(),language:chosenLanguages('search-languages'),keywords:collectSearchKeywords(),swipes};
 
 try{const r=await api('/api/profile',{method:'POST',body:JSON.stringify(data)});state.me.profile=r.profile;state.swipes={...r.profile.swipes};notify('Preferences saved. Your next search will use these choices.');}catch(e){notify(e.message,true);}
}
async function renderHistory(){
 const el=$('main-panel');
 el.innerHTML=`<div class="page-kicker">PREVIOUS RUNS</div><h1 class="page-heading">History<span class="accent">.</span></h1><p class="page-subheading">Open any job to see its original listing.</p><div class="reset-actions"><button class="reset-matches" onclick="resetMyMatches()">Clear my previous matches ↺</button></div><div id="history-list"></div>`;
 try{
  const data=await api('/api/history');
  $('history-list').innerHTML=data.runs.length?data.runs.map(run=>`<section class="history-group"><h3>${esc(formatDate(run.date))}</h3>${run.jobs.map(j=>`<div class="history-row"><div class="history-role"><a class="history-link" href="${esc(j.url||'#')}" target="_blank" rel="noopener noreferrer"><strong>${esc(j.title)} ↗</strong><span>${esc(j.company)} · ${Number(j.score).toFixed(1)}/10</span></a></div><button class="save-button ${j.saved?'saved':''}" onclick="toggleHistorySave(${j.id},${Boolean(j.saved)})">${j.saved?'In MyJobs':'+ MyJobs'}</button></div>`).join('')}</section>`).join(''):'<p>No previous matches yet.</p>';
 }catch(e){notify(e.message,true)}
}
async function toggleHistorySave(id,saved){try{await api('/api/watchlist/'+id,{method:saved?'DELETE':'POST'});await loadContent();renderHistory();notify(saved?'Removed.':'Saved.')}catch(e){notify(e.message,true)}}
async function deleteAccount(){if(!confirm('Permanently delete your Waydefine account, CV, preferences and saved jobs? This cannot be undone.'))return;try{const r=await api('/api/account/delete',{method:'POST'});state.me=null;showLanding();notify('Account deleted.')}catch(e){notify(e.message,true)}}
async function resetMyMatches(){
 if(!confirm('Clear your previous matches and History? Jobs saved in MyJobs will stay.'))return;
 try{await api('/api/jobs/reset',{method:'POST'});await loadContent();navigate('today');notify('Previous matches cleared. Your MyJobs are safe. Run again.');}
 catch(e){notify(e.message,true)}
}
document.addEventListener('visibilitychange',async()=>{
 if(document.visibilityState!=='visible'||!state.me)return;
 try{await loadContent();if(state.screen==='today')renderToday();if(state.screen==='watch')renderWatch();if(state.screen==='history')renderHistory()}catch(_){}
});
async function logout(){const r=await api('/api/logout',{method:'POST'}).catch(()=>null);if(r?.csrf&&state.config)state.config.csrf=r.csrf;state.me=null;state.jobs=[];state.watch=[];showLanding()}
boot().catch(()=>showLanding());
function buildHeroWordReveal(){
 const line=document.getElementById('hero-wordline');if(!line)return;
 const sentence=line.textContent.trim();line.setAttribute('aria-label',sentence);line.textContent='';
 const wrap=document.createElement('span');wrap.className='hero-word-wrap';wrap.setAttribute('aria-hidden','true');
 sentence.split(/\s+/).forEach((word,i)=>{const span=document.createElement('span');span.className='hero-word';span.style.setProperty('--word-index',i);span.textContent=word;wrap.appendChild(span);if(i<sentence.split(/\s+/).length-1)wrap.appendChild(document.createTextNode(' '));});
 line.appendChild(wrap);
}
buildHeroWordReveal();
