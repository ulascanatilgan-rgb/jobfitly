/* Waydefine five-step interface; history lives under the personal profile. */
(function () {
  var steps = [
    {id:"cv",num:"1",title:"Upload your CV",desc:"Your career experience comes first."},
    {id:"skills",num:"2",title:"Tell about yourself",desc:"20 short work-style questions."},
    {id:"search",num:"3",title:"What you search",desc:"Location, sector and job direction."},
    {id:"results",num:"4",title:"Let's find",desc:"Up to five roles that fit your CV."},
    {id:"watch",num:"5",title:"My jobs",desc:"Selected jobs, motivation and tailored CV."}
  ];
  function indicator(id) {
    var p=state.me && state.me.profile || {};
    if(id==="cv" && p.has_cv)return "Ready";
    if(id==="skills" && Object.keys(p.questions||{}).length>=20)return "Ready";
    if(id==="search")return "Ready";
    if(id==="results" && state.has_run)return (state.jobs.length+" matches");
    if(id==="watch" && state.watch.length)return (state.watch.length+" saved");
    return "";
  }
  function compactHomeRadar(profile){
    var answers=profile.questions||{};
    if(Object.keys(answers).length<20)return '';
    var original=renderWorkStyleRadar(answers);
    var graphic=original.match(/<svg\b[^>]*>[\s\S]*?<\/svg>/);
    if(!graphic)return '';
    var displayName=String(profile.name||(profile.cv_details||{}).name||'').trim();
    var label=displayName||'Your profile';
    return '<aside class="flow-home-mini" aria-label="Work style profile for '+esc(label)+'">'
      +graphic[0]
      +'<div class="flow-home-person">'+esc(label)+'</div></aside>';
  }
  window.renderFlowHome=function(){
    var p=state.me && state.me.profile || {};
    var html=steps.map(function(step){
      var status=indicator(step.id);
      var desc=(step.id==="cv" && p.has_cv) ? ("Uploaded: "+(p.cv_name||"CV")):step.desc;
      return '<button type="button" class="flow-step" onclick="navigate(&quot;'+step.id+'&quot;)">'
        +'<span class="flow-step-number">'+step.num+'</span>'
        +'<span class="flow-step-copy"><strong>'+esc(step.title)+'</strong><small>'+esc(desc)+'</small></span>'
        +(status?'<span class="flow-step-status">'+esc(status)+'</span>':'')
        +'<span class="flow-step-arrow" aria-hidden="true">↗</span></button>';
    }).join("");
    var mini=compactHomeRadar(p);
    $("main-panel").innerHTML=
      '<div class="flow-home-top'+(mini?' has-radar':'')+'">'
      +'<div class="flow-home-intro"><div class="flow-home-overline">YOUR JOB SEARCH</div>'
      +'<h1>Time to boost<br>your career<span>.</span></h1>'
      +'<p>Start with your CV. Move through each step when you are ready.</p></div>'
      +mini+'</div>'
      +'<div class="flow-steps" aria-label="Five steps to finding a job">'+html+'</div>';
  };
  function renderMatchInsight(jobs){
    var scores=jobs.filter(function(j){return j.score!==null && j.score!==undefined && j.score!=="" && Number.isFinite(Number(j.score)) && !String(j.source||"").toUpperCase().includes("DEMO")}).map(function(j){return Number(j.score)});
    var strong=scores.filter(function(n){return n>=8}).length;
    var best=scores.length?Math.max.apply(null,scores):0;
    var title,copy;
    if(!scores.length){title="Keep exploring";copy="No scored opportunities are available in this search yet. Check back in the coming days as new vacancies appear.";}
    else if(strong>=2){title="Time to take action";copy="Several strong matches align with your profile, giving you promising opportunities to stand out. Prioritise these roles, tailor your CV and motivation, and consider contacting the hiring managers directly.";}
    else if(strong===1){title="One opportunity stands out";copy="One role is a strong match for your profile. Review it closely, tailor your CV and motivation, and reach out to the hiring manager if appropriate.";}
    else if(best>=7){title="Promising possibilities";copy="Some roles show promising alignment with your profile, although there is room for a stronger match. Review the best options carefully and keep searching for opportunities that fit your ambitions even better.";}
    else if(best>=5){title="Let’s keep looking";copy="A few roles could be suitable, but none is a strong match for your profile yet. Keep exploring in the coming days as new vacancies appear. Let’s keep looking for your best match.";}
    else{title="Better matches are worth waiting for";copy="The available roles have limited alignment with your profile. Avoid rushing into applications and keep searching as new opportunities appear.";}
    return '<aside aria-label="Search insight" style="box-sizing:border-box;flex:1 1 300px;max-width:440px;padding:16px 20px;border:1px solid rgba(110,30,48,.18);border-left:3px solid #78283d;border-radius:10px;background:rgba(120,40,61,.035);margin:0 0 20px"><small style="font-size:10px;font-weight:700;letter-spacing:.12em;color:#78283d">MATCH INSIGHT</small><div style="font-weight:700;font-size:15px;margin:5px 0">'+esc(title)+'</div><p style="font-size:13px;line-height:1.6;margin:0">'+esc(copy)+'</p></aside>';
  }
  window.renderFlowResults=function(){
    var p=state.me && state.me.profile || {};
    var ready=!!p.has_cv;
    var status=state.has_run
      ?'<div class="flow-result-status"><span>'+state.jobs.length+' roles from your search</span>' +
       '<button type="button" onclick="resetMyMatches()">Clear and search again ↺</button></div>'
      :'<div class="flow-result-start"><p>Your CV leads the matching. Preferences refine the selection.</p>' +
       '<button class="btn btn-dark flow-run" id="run-button" onclick="reloadJobs()" ' +
       (ready?'':'disabled')+'>Let’s find ↗</button>' +
       (ready?'':'<p class="flow-muted">Upload a CV to begin. Your preferences are optional.</p>')+'</div>';
    var jobs=state.jobs.length
       ?'<div class="jobs-grid flow-results-grid">'+state.jobs.slice().sort(function(a,b){return Number(b.score||0)-Number(a.score||0)}).map(function(j,i){return jobCard(j,i)}).join("")+'</div>'
       :(state.has_run?'<p class="flow-muted">No sourced vacancies available for this search.</p>':'');
    $("main-panel").innerHTML='<div class="page-kicker">STEP 04</div>' +
      '<div style="display:flex;flex-wrap:wrap;align-items:flex-start;justify-content:space-between;gap:16px"><div style="flex:1 1 240px">' +
      '<h1 class="page-heading">Let’s find<span class="accent">.</span></h1>' +
      '<p class="page-subheading">Your best available CV matches, highest fit first.</p></div>' +
      (state.has_run?renderMatchInsight(state.jobs):'')+'</div>' +
      status+jobs+'<p class="flow-verification">Confirm each vacancy on the employer’s website before applying.</p>';
  };
  var oldCV=renderCV,oldSkills=renderSkills,oldSearch=renderSearch,
      oldWatch=renderWatch,oldHistory=renderHistory,oldProfile=renderProfile;
  function watchTitle(){
    var heading=$("main-panel")&&$("main-panel").querySelector(".page-heading");
    if(heading)heading.innerHTML='My jobs<span class="accent">.</span>';
  }
  function crumb(screen){
    var names={cv:"1 / UPLOAD YOUR CV",skills:"2 / ABOUT YOU",search:"3 / YOUR SEARCH",
      results:"4 / LET’S FIND",watch:"5 / MY JOBS",history:"HISTORY",profile:"YOUR PROFILE"};
    if(!names[screen])return;
    var el=document.createElement("div");
    el.className="flow-detail-topline";
    el.innerHTML='<button type="button" onclick="navigate(&quot;home&quot;)">← All steps</button>' +
      '<span>'+names[screen]+'</span>';
    $("main-panel").prepend(el);
  }
  navigate=function(screen){
    if(screen==="today")screen="home";
    state.screen=screen;
    section("app");
    if(screen==="home")renderFlowHome();
    else if(screen==="results")renderFlowResults();
    else if(screen==="cv")oldCV();
    else if(screen==="skills")oldSkills();
    else if(screen==="search")oldSearch();
    else if(screen==="watch"){oldWatch();watchTitle()}
    else if(screen==="history")oldHistory();
    else if(screen==="profile")oldProfile();
    else renderFlowHome();
    if(screen!=="home")crumb(screen);
    window.scrollTo(0,0);
  };
  reloadJobs=async function(){
    var btn=$("run-button");
    if(!btn||btn.disabled)return;
    btn.disabled=true;btn.setAttribute("aria-busy","true");
    btn.innerHTML='<span class="find-hourglass-inline" aria-hidden="true">⌛</span> Searching…';
    var loader=document.createElement("div");
    loader.id="find-progress";loader.className="find-progress";
    loader.setAttribute("role","status");loader.setAttribute("aria-live","polite");
    loader.innerHTML='<svg class="find-hourglass-svg" viewBox="0 0 42 50" aria-hidden="true" focusable="false">'
      +'<path class="find-hg-frame" d="M9 5H33M9 45H33M12 7V14C12 21 17 22 21 25C25 28 30 29 30 36V43M30 7V14C30 21 25 22 21 25C17 28 12 29 12 36V43"/>'
      +'<path class="find-hg-sand-top" d="M15 14H27Q26 18 21 22Q16 18 15 14Z"/>'
      +'<path class="find-hg-sand-bottom" d="M21 30Q16 35 15 39H27Q26 35 21 30Z"/>'
      +'<path class="find-hg-stream" d="M21 25V31"/></svg>'
      +'<div class="find-progress-copy"><strong>Finding the right opportunities</strong>'
      +'<span>Matching current vacancies to your CV and preferences…</span></div>';
    btn.insertAdjacentElement("afterend",loader);
    var previewPanel=document.createElement("div");
    previewPanel.id="find-preview";previewPanel.className="find-preview";
    loader.insertAdjacentElement("afterend",previewPanel);
    var lastPreview="",finished=false;
    async function showEarlyMatches(){
      if(finished||!document.getElementById("find-preview"))return;
      try{
        var data=await api("/api/jobs/preview");
        if(finished||!document.getElementById("find-preview"))return;
        var jobs=(data.jobs||[]).slice(0,5);
        var signature=jobs.map(function(j){return j.url}).join("|");
        if(!jobs.length||signature===lastPreview)return;
        lastPreview=signature;
        previewPanel.innerHTML='<p class="preview-label">Early matches · final ranking in progress</p>'
          +jobs.map(function(j){
            return '<div class="preview-job"><div><strong>'+esc(j.title)+'</strong>'
              +'<small>'+esc(j.company)+' · '+esc(j.city||j.country||'Location to verify')+'</small></div>'
              +'<a href="'+esc(j.url)+'" target="_blank" rel="noopener noreferrer">View ↗</a></div>';
          }).join('');
      }catch(err){/* The full search continues even if preview fails. */}
    }
    var previewPoll=setInterval(showEarlyMatches,3200);
    showEarlyMatches();
    try{
      var result=await api("/api/jobs/run",{method:"POST"});
      finished=true;clearInterval(previewPoll);
      await loadContent();navigate("results");
      notify(result.count+" matching role"+(result.count===1?"":"s")+" found.");
    }catch(err){
      finished=true;clearInterval(previewPoll);
      notify(err.message,true);renderFlowResults();crumb("results");
    }
  };
  document.addEventListener("visibilitychange",async function(){
    if(document.visibilityState!=="visible"||!state.me)return;
    try{
      await loadContent();
      if(state.screen==="home")renderFlowHome();
      else if(state.screen==="results")renderFlowResults();
      else if(state.screen==="watch"){oldWatch();watchTitle()}
    }catch(_){}
  });
})();