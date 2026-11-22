const $=id=>document.getElementById(id);
const state={config:null,me:null,jobs:[],watch:[],screen:'today',step:0,qIndex:0,sIndex:0,questions:{},swipes:{},kit:null,kitTab:'motivation',job:null,authMode:'register',editMode:false};
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path,options={}){const r=await fetch(path,{...options,headers:{...(options.body instanceof FormData?{}:{'Content-Type':'application/json'}),...(state.config?.csrf?{'X-CSRF-Token':state.config.csrf}:{}),...(options.headers||{})}});const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.error||'Something went wrong');return d;}
function notify(msg,error=false){const e=$('toast');e.textContent=msg;e.className='toast show'+(error?' error':'');setTimeout(()=>e.className='toast',3400);}
function section(id){['landing','auth','app','onboarding'].forEach(i=>$(i).classList.toggle('hidden',i!==id));window.scrollTo(0,0);}
function showLanding(){section('landing');}
function showAuth(mode='register'){state.authMode=mode;section('auth');$('auth-title').textContent=mode==='register'?'Create your account.':'Welcome back.';$('auth-subtitle').textContent=mode==='register'?'Just the essentials. We’ll take it from there.':'Ready for your next five?';$('auth-submit').textContent=mode==='register'?'Create account →':'Log in →';$('auth-toggle').innerHTML=mode==='register'?'Already have an account? <button onclick="showAuth(\'login\')">Log in</button>':'New to JobFitly? <button onclick="showAuth(\'register\')">Get started</button>';}
$('auth-form').addEventListener('submit',async e=>{e.preventDefault();const submit=$('auth-submit');submit.disabled=true;try{const login=await api('/api/'+state.authMode,{method:'POST',body:JSON.stringify({email:$('auth-email').value,password:$('auth-password').value,remember:$('auth-remember').checked})});state.config.csrf=login.csrf;await boot(true);}catch(e){notify(e.message,true)}finally{submit.disabled=false}});
async function boot(){state.config=await api('/api/config');try{state.me=await api('/api/me')}catch{showLanding();return;}let p=state.me.profile;state.questions={...p.questions};state.swipes={...p.swipes};await loadContent();navigate('today')}
async function loadContent(){let [a,b]=await Promise.all([api('/api/jobs'),api('/api/watchlist')]);state.jobs=a.jobs;state.watch=b.jobs;state.has_run=a.has_run;state.date=a.date;updateCounts();}
function updateCounts(){$('watch-counter').textContent=state.watch.length;}
function startOnboarding(edit=false){state.editMode=edit;state.step=0;state.qIndex=0;state.sIndex=0;section('onboarding');drawStep();}
function stepBack(){if(state.step===1&&state.qIndex>0){state.qIndex--;drawStep();return;}if(state.step===2&&state.sIndex>0){state.sIndex--;drawStep();return;}if(state.step>0){state.step--;drawStep();return;}if(state.editMode){section('app');navigate('profile')}}
async function stepNext(){try{
 if(state.step===0){const name=$('p-name').value.trim(),city=$('p-city').value.trim(),country=$('p-country').value.trim(),keywords=$('p-keywords').value.trim(),language=$('p-language').value;let data=await api('/api/profile',{method:'POST',body:JSON.stringify({name,city,country,language,keywords})});state.me.profile=data.profile;let file=$('cv-input').files[0];if(file){let fd=new FormData();fd.append('file',file);data=await api('/api/cv',{method:'POST',body:fd});state.me.profile=data.profile}if(!state.me.profile.has_cv){notify('Please upload your CV to build your profile.',true);return;}state.step=1;drawStep();return;}
 if(state.step===1){const q=state.config.questions[state.qIndex];state.questions[q.id]=Number($('question-slider').value);if(state.qIndex<state.config.questions.length-1){state.qIndex++;drawStep();return;}let data=await api('/api/profile',{method:'POST',body:JSON.stringify({questions:state.questions})});state.me.profile=data.profile;state.step=2;drawStep();return;}
 if(state.step===2){const s=state.config.swipes[state.sIndex];if(state.sIndex<state.config.swipes.length-1){state.sIndex++;drawStep();return;}let data=await api('/api/profile',{method:'POST',body:JSON.stringify({swipes:state.swipes})});state.me.profile=data.profile;await loadContent();section('app');navigate('today');notify('Your profile is ready. Press Run to find your jobs.');}
 }catch(e){notify(e.message,true)}}
function drawStep(){let steps=['01 / ABOUT YOU','02 / YOUR WORK STYLE','03 / WHAT YOU WANT'];$('onboard-step-name').textContent=steps[state.step];$('onboard-step-count').textContent=(state.step+1)+' of 3';$('progress-bar').style.width=((state.step+1)/3*100)+'%';$('step-back').textContent=state.step===0?(state.editMode?'Cancel':'← Back'):'← Back';const next=$('step-next');next.textContent=state.step===2&&state.sIndex===state.config.swipes.length-1?'Find my 5 →':'Continue →';let p=state.me.profile;
 if(state.step===0){$('onboard-content').innerHTML=`<h1>Let's start with you.</h1><p class="intro">Your experience and your destination. Nothing more.</p><div class="two-fields"><label class="field">Your name<input id="p-name" placeholder="Your name" value="${esc(p.name)}"></label><label class="field">Preferred language<select id="p-language"><option ${p.language==='English'?'selected':''}>English</option><option ${p.language==='Dutch'?'selected':''}>Dutch</option><option ${p.language==='French'?'selected':''}>French</option><option ${p.language==='German'?'selected':''}>German</option></select></label><label class="field">Country<input id="p-country" placeholder="Belgium" value="${esc(p.country)}"></label><label class="field">City<input id="p-city" placeholder="Brussels" value="${esc(p.city)}"></label></div><label class="field">Roles or interests (a few words)<input id="p-keywords" placeholder="Operations, strategy, client relations" value="${esc(p.keywords)}"></label><label for="cv-input" class="file-drop"><span class="file-icon">⇧</span><strong id="file-label">${p.cv_name?esc(p.cv_name):'Upload your CV'}</strong><span>PDF, DOCX or TXT · Max 5 MB</span><input type="file" id="cv-input" accept=".pdf,.docx,.txt" onchange="$('file-label').textContent=this.files[0]?.name||'Upload your CV'"></label><p class="privacy-note">Your CV is private to your account. You can delete your account and data anytime.</p>`;}
 if(state.step===1){let q=state.config.questions[state.qIndex],value=state.questions[q.id]??5;$('onboard-content').innerHTML=`<h1>How do you work?</h1><p class="intro">20 quick questions. No right or wrong answers.</p><div class="question-progress">Question ${state.qIndex+1} of ${state.config.questions.length}</div><div class="question-panel"><h2>${esc(q.text)}</h2><div class="slider-row"><span>Not like me</span><span class="rating-output" id="slider-value">${value}/10</span></div><input id="question-slider" class="range" type="range" min="0" max="10" value="${value}" oninput="$('slider-value').textContent=this.value+'/10';state.questions['${q.id}']=Number(this.value)"><div class="scale-labels"><span>0 — Not at all</span><span>10 — Very much</span></div></div><div class="question-controls"><button class="subtle-button" onclick="stepBack()">← Previous</button><button class="subtle-button" onclick="state.questions['${q.id}']=5;$('question-slider').value=5;$('slider-value').textContent='5/10'">Reset to 5</button></div>`;}
 if(state.step===2){let s=state.config.swipes[state.sIndex];let chips=s.choices.map(ch=>`<button class="choice ${state.swipes[s.id]===ch?'selected':''}" onclick="pickChoice('${s.id}',decodeURIComponent('${encodeURIComponent(ch)}'))">${esc(ch)}</button>`).join('');$('onboard-content').innerHTML=`<h1>What feels right?</h1><p class="intro">Make a few quick choices. You can change them later.</p><div class="question-progress">Preference ${state.sIndex+1} of ${state.config.swipes.length}</div><div id="swipe-card" class="swipe-card"><div class="eyebrow" style="justify-content:center">YOUR IDEAL NEXT ROLE</div><h2>${esc(s.label)}</h2><div class="choice-row">${chips}</div></div><p class="swipe-hint">Choose a preference or swipe left/right to browse your options.</p>`;let e=$('swipe-card'),startX=0;e.addEventListener('touchstart',ev=>startX=ev.touches[0].clientX,{passive:true});e.addEventListener('touchend',ev=>{let dx=ev.changedTouches[0].clientX-startX;if(Math.abs(dx)>55){let old=s.choices.indexOf(state.swipes[s.id]);pickChoice(s.id,s.choices[(old+(dx>0?1:s.choices.length-1)+s.choices.length)%s.choices.length])}},{passive:true});}
}
function pickChoice(k,v){state.swipes[k]=v;drawStep()}
function navigate(screen){state.screen=screen;section('app');document.querySelectorAll('[data-screen]').forEach(b=>b.classList.toggle('active',b.dataset.screen===screen));if(screen==='today')renderToday();if(screen==='watch')renderWatch();if(screen==='profile')renderProfile();if(screen==='skills')renderSkills();if(screen==='search')renderSearch();if(screen==='cv')renderCV();if(screen==='history')renderHistory();window.scrollTo(0,0)}
function formatDate(s){try{return new Date(s+'T12:00:00Z').toLocaleDateString('en-GB',{month:'long',day:'numeric',year:'numeric'})}catch{return s}}
function renderToday(){let jobs=[...state.jobs].sort((a,b)=>Number(b.score||0)-Number(a.score||0)).map((j,i)=>jobCard(j,i)).join('');const p=state.me.profile;const ready=!!p.has_cv;const intro=state.has_run?`<div class="status-line"><span><i class="dot-live"></i>Run complete for today</span><span>Next Run tomorrow</span></div>`:`<div class="run-panel"><span class="date-caption">${esc(formatDate(state.date))}</span><h2>Five jobs. One click.</h2><p>Based on your CV, skills and preferences.</p><button class="btn btn-dark btn-xl" ${ready?'':'disabled'} onclick="reloadJobs()" id="run-button">Run →</button>${ready?'':'<p class="privacy-note">Upload a CV to start. Your preferences are optional.</p>'}</div>`;$('main-panel').innerHTML=`<div class="page-kicker">TODAY</div><h1 class="page-heading">Your five<span class="accent">.</span></h1>${intro}${state.has_run?'<div class="reset-actions"><button class="reset-matches" onclick="resetMyMatches()">Clear matches and search again ↺</button></div>':''}<div class="jobs-grid">${jobs}</div>${state.has_run?'<p class="privacy-note" style="margin-top:22px">Listings are sourced from web search. Some dates and links may be unverified; always check the employer’s original page before applying.</p>':''}${!state.has_run?'<div class="setup-row"><button onclick="navigate(&quot;cv&quot;)">01 CV</button><button onclick="navigate(&quot;skills&quot;)">02 Work Style</button><button onclick="navigate(&quot;search&quot;)">03 Purpose</button></div>':''}`;}
function jobCard(j,i=0){return `<article class="job-card"><div class="job-top"><div><div class="job-company">${esc(j.company)} ${j.source?.includes('DEMO')?'<span class="tag">Sample</span>':''}</div><h2 class="job-title">${esc(j.title)}</h2><div class="job-loc">${esc([j.city,j.country].filter(Boolean).filter((value,index,array)=>array.indexOf(value)===index).join(", "))}</div></div><div class="score-circle"><strong>${Number(j.score).toFixed(1)}</strong><small>FIT / 10</small></div></div><div class="job-bottom"><button class="text-action" onclick="showJob(${j.id})">Why this fit ↗</button><button class="save-button ${j.saved?'saved':''}" onclick="toggleSave(${j.id},${Boolean(j.saved)})">${j.saved?'♥ Saved':'+ MyJobs'}</button></div></article>`}
async function reloadJobs(){const btn=$('run-button');if(btn){btn.disabled=true;btn.textContent='Checking live jobs…'}try{let r=await api('/api/jobs/run',{method:'POST'});await loadContent();navigate('today');notify(r.count===5?'Your five matches are ready.':r.count+' verified jobs found today.')}catch(e){notify(e.message,true);renderToday()}}
function renderWatch(){const items=state.watch.map(j=>`<div class="saved-row"><div><div class="job-company">${esc(j.company)} <span class="accent">· ${j.score}/10 fit</span></div><h3>${esc(j.title)}</h3><p>${esc(j.city||j.country)}</p></div><div class="saved-actions"><button class="btn btn-light" onclick="removeSave(${j.id})">Remove</button><button class="btn btn-outline" onclick="openKit(${j.id},'motivation')">Generate motivations</button><button class="btn btn-dark" onclick="openKit(${j.id},'cv')">Update CV · PDF</button></div></div>`).join('');$('main-panel').innerHTML=`<div class="page-kicker">SAVED</div><h1 class="page-heading">My jobs<span class="accent">.</span></h1><div class="saved-list">${items||'<div class="empty-state"><h3>No saved jobs yet.</h3><button class="btn btn-dark" onclick="navigate(&quot;today&quot;)">Today’s 5</button></div>'}</div>`;}
async function toggleSave(id,saved){try{await api('/api/watchlist/'+id,{method:saved?'DELETE':'POST'});await loadContent();state.screen==='today'?renderToday():renderWatch();notify(saved?'Removed from MyJobs.':'Added to MyJobs.')}catch(e){notify(e.message,true)}}
function removeSave(id){toggleSave(id,true)}
function showJob(id){let j=[...state.jobs,...state.watch].find(x=>x.id===id);if(!j)return;const overlay=document.createElement('div');overlay.id='detail-modal';overlay.className='modal-back';overlay.onclick=e=>{if(e.target===overlay)overlay.remove()};overlay.innerHTML=`<div class="modal"><button class="close" aria-label="Close" onclick="$('detail-modal').remove()">×</button><div class="page-kicker">${esc(j.company)}</div><h2>${esc(j.title)}</h2><p>${esc(j.city)} · ${esc(j.country)} · ${j.score}/10 profile fit</p><div class="kit-banner"><strong>Why this matches</strong><p>${j.matched_terms?.length?'Your background and this listing share: '+j.matched_terms.map(esc).join(', ')+'.':'This posting has some relevance to your background and preferences; inspect the original listing before applying.'}</p></div><p style="max-height:220px;overflow:auto;white-space:pre-wrap">${esc(j.description||'No description available.')}</p><div class="kit-actions">${j.url?`<a class="btn btn-dark" href="${esc(j.url)}" target="_blank" rel="noopener noreferrer">View original listing ↗</a>`:'<span class="tag">Sample listing — no application link</span>'}<button class="btn btn-outline" onclick="$('detail-modal').remove();toggleSave(${j.id},${Boolean(j.saved)})">${j.saved?'Remove from saved':'+ MyJobs'}</button></div></div>`;document.body.appendChild(overlay)}
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
 +'<section class="profile-cv-facts"><h2>Work style</h2><p>'+esc(scores.filter(q=>q.score>=7).map(q=>q.label.replace(/^I /,'')).join(' · ')||'Add your work-style preferences.')+'</p></section>'
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
 +'<div class="kit-actions"><a class="btn btn-dark" href="/api/kit/'+j.id+'/download/'+state.kitTab+'" download>Download '+(state.kitTab==='cv'?'tailored CV':'motivation')+' (PDF) ↓</a>'
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
function downloadKit(){const link=document.createElement('a');link.href=`/api/kit/${state.job.id}/download/${state.kitTab}`;link.download='';document.body.appendChild(link);link.click();link.remove()}
async function copyKit(){try{await navigator.clipboard.writeText(state.kit[state.kitTab]);notify('Copied to clipboard.')}catch{notify('Copy not available in this browser.',true)}}
function renderCV(){const p=state.me.profile;$('main-panel').innerHTML=`<div class="page-kicker">YOUR EXPERIENCE</div><h1 class="page-heading">CV<span class="accent">.</span></h1><p class="page-subheading">${p.has_cv?esc(p.cv_name):'Upload your CV to start.'}</p><label for="cv-edit-file" class="file-drop"><span class="file-icon">⇧</span><strong id="cv-edit-label">${p.has_cv?'Replace CV':'Choose a CV'}</strong><span>PDF, DOCX or TXT · Max 5 MB</span><input id="cv-edit-file" type="file" accept=".pdf,.docx,.txt"></label><button class="btn btn-dark margin-top" onclick="saveCV()">Save CV →</button>`;const input=$('cv-edit-file');input.onchange=()=>{$('cv-edit-label').textContent=input.files[0]?.name||'Choose a CV';};}
async function saveCV(){const file=$('cv-edit-file').files[0];if(!file){notify('Select a file.',true);return}let fd=new FormData();fd.append('file',file);try{const r=await api('/api/cv',{method:'POST',body:fd});state.me.profile=r.profile;notify('CV saved. Personal details were extracted into Your profile.');renderCV()}catch(e){notify(e.message,true)}}
function renderSkills(){const p=state.me.profile;const qs=state.config.questions;$('main-panel').innerHTML=`<div class="page-kicker">WORK STYLE</div><h1 class="page-heading">Work Style<span class="accent">.</span></h1><p class="page-subheading">Rate yourself from 0 to 10.</p><div class="skills-grid">${qs.map((q,i)=>{const v=p.questions[q.id]??5;return `<label class="skill-item"><span>${String(i+1).padStart(2,'0')} · ${esc(q.text)}</span><strong id="v-${q.id}">${v}/10</strong><input data-skill="${q.id}" type="range" min="0" max="10" value="${v}" oninput="$('v-${q.id}').textContent=this.value+'/10'"></label>`}).join('')}</div><button class="btn btn-dark margin-top" onclick="saveSkills()">Save Work Style →</button>`;}
async function saveSkills(){const qs={};document.querySelectorAll('[data-skill]').forEach(x=>qs[x.dataset.skill]=Number(x.value));try{const r=await api('/api/profile',{method:'POST',body:JSON.stringify({questions:qs})});state.me.profile=r.profile;notify('Work Style saved.')}catch(e){notify(e.message,true)}}
function renderSearch(){
 const p=state.me.profile;
 const selects=state.config.swipes.map(s=>`<label class="field search-preference"><span>${esc(s.label)}</span><select data-preference="${esc(s.id)}" aria-label="${esc(s.label)}"><option value="" ${!p.swipes[s.id]?'selected':''}>Any</option>${s.choices.map(ch=>`<option value="${esc(ch)}" ${p.swipes[s.id]===ch?'selected':''}>${esc(ch)}</option>`).join('')}</select></label>`).join('');
 $('main-panel').innerHTML=`<div class="page-kicker">STEP 03 / YOUR SEARCH</div><h1 class="page-heading">What you search<span class="accent">.</span></h1><p class="page-subheading">Your next move, in one view.</p><div class="search-compact-panel"><div class="two-fields search-fields"><label class="field">Country<input id="search-country" autocomplete="country-name" value="${esc(p.country)}" placeholder="Belgium"></label><label class="field">City<input id="search-city" value="${esc(p.city)}" placeholder="Brussels"></label><label class="field">Language<select id="search-language">${['English','Dutch','French','German'].map(l=>`<option ${p.language===l?'selected':''}>${l}</option>`).join('')}</select></label><label class="field">Job keywords<input id="search-keywords" value="${esc(p.keywords)}" placeholder="Operations, client relations"></label></div><div class="search-section-label">YOUR PREFERENCES</div><div class="search-preferences-grid">${selects}</div><button class="btn btn-dark search-save-button" onclick="saveSearch()">Save preferences ↗</button></div>`;
}
function pickSearch(button){document.querySelectorAll('[data-choice="'+button.dataset.choice+'"]').forEach(b=>b.classList.toggle('selected',b===button));}
async function saveSearch(){
 const swipes={};
 document.querySelectorAll('[data-preference]').forEach(el=>{if(el.value)swipes[el.dataset.preference]=el.value;});
 const data={country:$('search-country').value.trim(),city:$('search-city').value.trim(),language:$('search-language').value,keywords:$('search-keywords').value.trim(),swipes};
 
 try{const r=await api('/api/profile',{method:'POST',body:JSON.stringify(data)});state.me.profile=r.profile;notify('Preferences saved.');}catch(e){notify(e.message,true);}
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
async function deleteAccount(){if(!confirm('Permanently delete your JobFitly account, CV, preferences and saved jobs? This cannot be undone.'))return;try{const r=await api('/api/account/delete',{method:'POST'});state.me=null;showLanding();notify('Account deleted.')}catch(e){notify(e.message,true)}}
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
