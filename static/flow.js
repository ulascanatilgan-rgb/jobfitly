/* JobFitly five-step interface; history lives under the personal profile. */
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
  window.renderFlowHome=function(){
    var p=state.me && state.me.profile || {};
    var html=steps.map(function(step){
      var status=indicator(step.id);
      var desc=(step.id==="cv" && p.has_cv) ? ("Uploaded: "+(p.cv_name||"CV")):step.desc;
      return '<button type="button" class="flow-step" onclick="navigate(&quot;'+step.id+'&quot;)">' +
        '<span class="flow-step-number">'+step.num+'</span>' +
        '<span class="flow-step-copy"><strong>'+esc(step.title)+'</strong><small>'+esc(desc)+'</small></span>' +
        (status?'<span class="flow-step-status">'+esc(status)+'</span>':'') +
        '<span class="flow-step-arrow" aria-hidden="true">↗</span></button>';
    }).join("");
    $("main-panel").innerHTML=
      '<div class="flow-home-intro"><div class="flow-home-overline">YOUR JOB SEARCH</div>' +
      '<h1>One step at a time<span>.</span></h1>' +
      '<p>Start with your CV. Move through each step when you are ready.</p></div>' +
      '<div class="flow-steps" aria-label="Five steps to finding a job">'+html+'</div>';
  };
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
      '<h1 class="page-heading">Let’s find<span class="accent">.</span></h1>' +
      '<p class="page-subheading">Your best available CV matches, highest fit first.</p>' +
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
    if(btn){btn.disabled=true;btn.setAttribute("aria-busy","true");btn.innerHTML='<span class="live-search-spinner" aria-hidden="true"></span> Searching live vacancies…';}
    try{
      var result=await api("/api/jobs/run",{method:"POST"});
      await loadContent();navigate("results");
      notify(result.count+" matching role"+(result.count===1?"":"s")+" found.");
    }catch(err){notify(err.message,true);renderFlowResults();crumb("results");}
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