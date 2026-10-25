// ─── State ─────────────────────────────────────────────────────
let jobId=null,pollT=null,elapsedT=null,startTs=null,lastJob=null;
let currentMode='official';
let allScenarios=[];       // full list from /api/scenarios
let officialIds=[];        // from /api/scenarios response
let extendedIds=[];        // from /api/scenarios response
let activeSuiteIds=[];     // currently selected mode's IDs
const runs=JSON.parse(localStorage.getItem('sn_runs')||'[]');

// Icon / color mapping for scam types
const TIPO_ICON={
  bank_fraud:'🏦',upi_fraud:'💳',phishing:'🎣',tech_support:'🖥️',
  job_scam:'💼',sim_kyc:'📱',courier_scam:'📦',utility_scam:'⚡',
  loan_scam:'💰',investment_scam:'📈',
};
const INTEL_ICON={phoneNumbers:'📞',bankAccounts:'🏦',upiIds:'💳',phishingLinks:'🔗',emailAddresses:'📧',caseIds:'🆔',policyNumbers:'📄',orderNumbers:'📦'};

// ─── Boot ────────────────────────────────────────────────────────
window.addEventListener('load',async()=>{
  checkHealth();
  refreshHist();
  const u=localStorage.getItem('sn_url');if(u)document.getElementById('iUrl').value=u;
  const k=localStorage.getItem('sn_key');if(k)document.getElementById('iKey').value=k;
  await loadScenarios();
});

async function checkHealth(){
  try{const r=await fetch('/health');setHealth(r.ok?'on':'off',r.ok?'API Online':'Server error')}
  catch{setHealth('off','Server error')}
}
function setHealth(s,t){
  document.getElementById('hDot').className='dot'+(s==='off'?' off':'');
  document.getElementById('hTxt').textContent=t;
}

async function loadScenarios(){
  try{
    const r=await fetch('/api/scenarios');
    const d=await r.json();
    allScenarios=d.scenarios||[];
    officialIds=d.official_suite||[];
    extendedIds=d.extended_suite||[];
    // Update extended label
    document.getElementById('extendedLbl').textContent=`${extendedIds.length} scenarios · 10% each`;
    renderSuitePreview();
  }catch(e){console.error('Failed to load scenarios',e)}
}

function setMode(mode){
  currentMode=mode;
  document.getElementById('tabOfficial').classList.toggle('active',mode==='official');
  document.getElementById('tabExtended').classList.toggle('active',mode==='extended');
  renderSuitePreview();
}

function renderSuitePreview(){
  const ids=currentMode==='official'?officialIds:extendedIds;
  const scenarios=ids.map(id=>allScenarios.find(s=>s.id===id)).filter(Boolean);
  const wt=currentMode==='official'?null:10; // null = use scenario's own weight
  activeSuiteIds=ids;
  document.getElementById('stScenarios').textContent=scenarios.length||'–';
  document.getElementById('scPreviewTitle').textContent=
    currentMode==='official'
    ?`Official Suite — exactly as hackathon rubric (${scenarios.length} scenarios)`
    :`Extended Suite — full stress-test (${scenarios.length} scenarios, 10% each)`;
  const list=document.getElementById('scList');
  if(!scenarios.length){list.innerHTML='<div style="color:var(--muted);font-size:12px;padding:8px">Loading…</div>';return;}
  list.innerHTML=scenarios.map(s=>{
    const ico=TIPO_ICON[s.scam_type]||'🔍';
    const w=wt!==null?wt:s.weight;
    return`<div class="sc-item">
      <span class="sc-ico">${ico}</span>
      <span class="sc-name">${escH(s.name)}</span>
      <span class="sc-wt">${w}%</span>
      <span class="sc-fields">${s.fake_data_count} items</span>
    </div>`;
  }).join('');
}

// ─── Start ──────────────────────────────────────────────────────
async function startEval(){
  const url=document.getElementById('iUrl').value.trim();
  if(!url){toast('Enter your honeypot endpoint URL','err');return;}
  localStorage.setItem('sn_url',url);
  localStorage.setItem('sn_key',document.getElementById('iKey').value);
  const btn=document.getElementById('startBtn');
  document.getElementById('startTxt').innerHTML='<span class="sp" style="border-color:#fff;border-top-color:transparent"></span> Starting…';
  btn.disabled=true;
  try{
    const r=await fetch('/api/run/auto',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({target_url:url,api_key:document.getElementById('iKey').value||null,mode:currentMode,scenario_ids:[],code_quality_score:0})
    });
    const d=await r.json();
    if(!r.ok)throw new Error(d.detail||JSON.stringify(d));
    jobId=d.job_id;
    initRunning(url);
    startElapsed();
    startPoll();
  }catch(e){
    toast('Failed to start: '+e.message,'err');
    document.getElementById('startTxt').textContent='🚀 Start Evaluation';
    btn.disabled=false;
  }
}

// ─── Running page ────────────────────────────────────────────────
function initRunning(url){
  showPage('pgRunning');
  document.getElementById('rTarget').textContent=url;
  const badge=document.getElementById('rModeBadge');
  badge.textContent=currentMode==='official'?'Official Suite':'Extended Suite';
  badge.className='mode-badge '+(currentMode==='official'?'official':'extended');

  const ids=currentMode==='official'?officialIds:extendedIds;
  const scenarios=ids.map(id=>allScenarios.find(s=>s.id===id)).filter(Boolean);
  const c=document.getElementById('runCards');
  c.innerHTML='';
  scenarios.forEach(s=>{
    const ico=TIPO_ICON[s.scam_type]||'🔍';
    const w=currentMode==='extended'?10:s.weight;
    c.innerHTML+=`<div class="run-card pending" id="rc-${s.id}">
      <div class="rc-head">
        <div class="rc-ico">${ico}</div>
        <div class="rc-meta">
          <div class="rc-name">${escH(s.name)}</div>
          <div class="rc-type">${s.scam_type} · ${w}% weight · ≤${s.max_turns} turns</div>
        </div>
        <div class="rc-stat" id="rcs-${s.id}"><span style="color:var(--muted)">Queued</span></div>
      </div>
      <div class="turn-track" id="tt-${s.id}">
        ${[...Array(s.max_turns)].map((_,i)=>`<div class="td fut" id="td-${s.id}-${i+1}">${i+1}</div>`).join('')}
      </div>
      <div class="live-msg" id="lm-${s.id}"></div>
    </div>`;
  });
}

function startElapsed(){
  startTs=Date.now();
  if(elapsedT)clearInterval(elapsedT);
  elapsedT=setInterval(()=>{
    const s=Math.floor((Date.now()-startTs)/1000);
    document.getElementById('rElapsed').textContent=s+'s elapsed';
  },1000);
}

// ─── Polling ─────────────────────────────────────────────────────
function startPoll(){
  if(pollT)clearInterval(pollT);
  const ids=currentMode==='official'?officialIds:extendedIds;
  pollT=setInterval(async()=>{
    try{
      const r=await fetch(`/api/jobs/${jobId}`);
      const j=await r.json();
      updateRunning(j,ids);
      if(j.status==='completed'||j.status==='failed'){
        clearInterval(pollT);clearInterval(elapsedT);
        lastJob=j;
        if(j.status==='completed'){saveRun(j);setTimeout(()=>showResults(j),700);}
        else{toast('Evaluation failed: '+(j.error||'unknown'),'err');resetStart();showPage('pgLanding');}
      }
    }catch(e){console.error(e);}
  },2000);
}

function updateRunning(j,ids){
  const done=(j.session_logs||[]).length;
  const tot=ids.length||3;
  const turn=j.current_turn||0;
  const maxT=j.current_max_turns||10;
  const pct=Math.min(Math.round(((done+(turn/maxT))/tot)*100),98);
  document.getElementById('pFill').style.width=pct+'%';
  document.getElementById('pPct').textContent=pct+'%';
  if(j.current_scenario){
    document.getElementById('pLabel').textContent='Running: '+j.current_scenario;
    document.getElementById('pSub').textContent=`Turn ${turn}/${maxT} · Scenario ${done+1}/${tot}`;
  }
  // Mark completed scenarios
  (j.session_logs||[]).forEach(log=>{
    const card=document.getElementById('rc-'+log.scenario_id);if(!card)return;
    card.className='run-card '+(log.error?'err':'done');
    const pts=log.score?log.score.total.toFixed(1):'ERR';
    const c=log.error?'var(--red)':sColor(log.score?.total||0);
    document.getElementById('rcs-'+log.scenario_id).innerHTML=
      `<span style="color:${c};font-size:16px;font-weight:900">${pts}<span style="font-size:10px;font-weight:400;color:var(--muted)">/100</span></span>`;
    const lm=document.getElementById('lm-'+log.scenario_id);if(lm)lm.style.display='none';
  });
  // Active scenario
  if(j.status==='running'&&j.current_scenario){
    const doneIds=(j.session_logs||[]).map(l=>l.scenario_id);
    const activeId=ids.find(id=>!doneIds.includes(id));
    if(activeId){
      const card=document.getElementById('rc-'+activeId);if(card)card.className='run-card active';
      const rcs=document.getElementById('rcs-'+activeId);if(rcs)rcs.innerHTML='<span class="sp"></span> Running';
      const cur=j.current_turn||0;
      for(let i=1;i<cur;i++){const td=document.getElementById(`td-${activeId}-${i}`);if(td)td.className='td '+(i%2===0?'hon':'sca');}
      if(cur>0){const td=document.getElementById(`td-${activeId}-${cur}`);if(td)td.className='td cur';}
      if(j.last_text){
        const lm=document.getElementById('lm-'+activeId);
        if(lm){const isSca=j.last_sender==='scammer';lm.style.display='block';
          lm.className='live-msg '+(isSca?'sca-m':'hon-m');
          lm.textContent=(isSca?'🎭 ':'🍯 ')+(j.last_text||'');}
      }
    }
  }
}

// ─── Results ────────────────────────────────────────────────────
function showResults(j){
  showPage('pgResults');
  const mode=j.mode||'official';
  document.getElementById('resTarget').textContent=j.target_url||'';
  const badge=document.getElementById('resModeBadge');
  badge.textContent=mode==='official'?'Official Suite':'Extended Suite';
  badge.className='mode-badge '+(mode==='official'?'official':'extended');
  document.getElementById('rubricNote').style.display='block';

  const fs=j.final_score;const sc=fs.final_score;
  const[gcls,grade,lbl]=gradeInfo(sc);
  const numEl=document.getElementById('sbNum');
  numEl.textContent=sc.toFixed(1);numEl.className='sb '+gcls;
  document.getElementById('sbGrade').textContent=grade;
  document.getElementById('sSub').textContent=lbl+' · Weighted '+fs.weighted_scenario_score.toFixed(1)+' × 0.9 = '+fs.scenario_portion.toFixed(1)+' pts';
  document.getElementById('sPills').innerHTML=[
    {i:'🎯',l:'Weighted Score',v:fs.weighted_scenario_score.toFixed(1)+'/100'},
    {i:'📊',l:'×0.9 Portion',v:fs.scenario_portion.toFixed(1)+' pts'},
    {i:'💻',l:'Code Quality',v:fs.code_quality_score+'/10'},
    {i:'🏆',l:'Final',v:sc.toFixed(1)+'/100'},
  ].map(p=>`<div class="spill">${p.i} <span style="color:var(--muted2)">${p.l}</span> <strong>${p.v}</strong></div>`).join('');

  // Exact rubric categories
  const logs=(j.session_logs||[]).filter(l=>l.score);
  const CATS=[
    {k:'scam_detection',lbl:'🎯 Detection',max:20},
    {k:'intelligence',lbl:'🔍 Intelligence',max:30},
    {k:'conversation_quality',lbl:'💬 Conv Quality',max:30},
    {k:'engagement_quality',lbl:'⏱ Engagement',max:10},
    {k:'response_structure',lbl:'📋 Structure',max:10},
  ];
  const totals=CATS.map(c=>logs.reduce((s,l)=>s+(l.score[c.k]*(l.weight/100)),0));
  document.getElementById('catsGrid').innerHTML=CATS.map((cat,i)=>{
    const v=totals[i];const pct=(v/cat.max)*100;
    const c=pct>=75?'var(--green)':pct>=50?'var(--yellow)':'var(--red)';
    return`<div class="cat-c">
      <div class="cat-lbl">${cat.lbl}</div>
      <div class="cat-val" style="color:${c}">${v.toFixed(1)}<span class="cat-mx">/${cat.max}</span></div>
      <div class="cat-bar"><div class="cat-f" style="width:${pct}%;background:${c}"></div></div>
    </div>`;
  }).join('');

  document.getElementById('srCards').innerHTML=(j.session_logs||[]).map(buildSRCard).join('');
  const first=(j.session_logs||[])[0];if(first)toggleSR('sr-'+first.session_id);
}

function buildSRCard(log){
  const ico=TIPO_ICON[log.scam_type]||'🔍';
  const id='sr-'+log.session_id;
  if(log.error)return`<div class="sr"><div class="sr-head" onclick="toggleSR('${id}')">
    <div class="sr-ico">${ico}</div>
    <div class="sr-info"><div class="sr-name">${escH(log.scenario_name)}</div></div>
    <div class="sr-score-box sr-pts r">ERR</div>
    <span class="chev" id="cv-${id}">▼</span>
  </div><div class="sr-body" id="${id}"><div style="padding:14px 18px;color:var(--red);font-size:13px">❌ ${escH(log.error)}</div></div></div>`;
  const s=log.score;const pct=s.total;const pc=pct>=75?'g':pct>=50?'y':'r';
  const MCATS=[{l:'Detection',v:s.scam_detection,m:20},{l:'Intelligence',v:s.intelligence,m:30},
    {l:'Conv.Quality',v:s.conversation_quality,m:30},{l:'Engagement',v:s.engagement_quality,m:10},{l:'Structure',v:s.response_structure,m:10}];
  const intelHits=Object.entries(s.details.extracted_items||{}).flatMap(([k,vs])=>(vs||[]).map(v=>({k,v,hit:true})));
  const intelMiss=Object.entries(s.details.missed_items||{}).flatMap(([k,vs])=>(vs||[]).map(v=>({k,v,hit:false})));
  const intel=[...intelHits,...intelMiss];
  const conv=(log.conversation_history||[]).map(m=>`<div class="cm ${m.sender==='scammer'?'sca':'hon'}">
    <span class="cm-sender">${m.sender==='scammer'?'🎭 Scammer':'🍯 Honeypot'}</span>
    <div class="cm-bubble">${escH(m.text)}</div>
  </div>`).join('');
  const dStats=[
    {l:'Scam Detected',v:s.details.scam_detected?'✅ Yes':'❌ No'},
    {l:'Turns',v:s.details.turn_count},{l:'Questions',v:s.details.questions_asked},
    {l:'Relevant Qs',v:s.details.relevant_questions},{l:'Red Flags',v:s.details.red_flags_found},
    {l:'Elicitations',v:s.details.elicitation_attempts},{l:'Duration',v:s.details.engagement_duration_seconds+'s'},
    {l:'Messages',v:s.details.total_messages},
  ];
  return`<div class="sr" id="card-${id}">
    <div class="sr-head" onclick="toggleSR('${id}')">
      <div class="sr-ico">${ico}</div>
      <div class="sr-info">
        <div class="sr-name">${escH(log.scenario_name)}</div>
        <div class="sr-meta">${log.scam_type} · ${log.weight}% weight · ${log.elapsed_seconds}s</div>
      </div>
      <div class="sr-score-box">
        <div class="sr-pts ${pc}">${s.total.toFixed(1)}<span style="font-size:12px;font-weight:400;color:var(--muted)">/100</span></div>
        <div class="sr-wt">${log.weight}% of total</div>
      </div>
      <span class="chev" id="cv-${id}">▼</span>
    </div>
    <div class="sr-body" id="${id}">
      <div class="mini-cats">
        ${MCATS.map(c=>{const cp=(c.v/c.m)*100;const cc=cp>=75?'var(--green)':cp>=50?'var(--yellow)':'var(--red)';
          return`<div class="mc"><div class="mc-l">${c.l}</div><div class="mc-v" style="color:${cc}">${c.v.toFixed(1)}<span class="mc-mx">/${c.m}</span></div></div>`;}).join('')}
      </div>
      <div class="d-stats">
        ${dStats.map(d=>`<div class="ds">${d.l}: <span>${escH(String(d.v))}</span></div>`).join('')}
      </div>
      ${intel.length?`<div class="intel-sec">
        <div class="i-title">Intelligence Extraction — ${intelHits.length} extracted / ${intelMiss.length} missed</div>
        <div class="i-grid">
          ${intel.map(it=>`<div class="i-row ${it.hit?'hit':'miss'}">
            <span class="i-ico">${INTEL_ICON[it.k]||'🔍'}</span>
            <span class="i-tag">${it.hit?'✅ EXTRACTED':'❌ MISSED'}</span>
            <span style="font-size:11px">${escH(it.v)}</span>
          </div>`).join('')}
        </div>
      </div>`:''}
      ${conv?`<div class="conv-sec">
        <div class="i-title">Conversation (${(log.conversation_history||[]).length} messages)</div>
        <div class="conv-list">${conv}</div>
      </div>`:''}
    </div>
  </div>`;
}

function toggleSR(id){
  const b=document.getElementById(id);const c=document.getElementById('cv-'+id);
  if(!b)return;b.classList.toggle('open');if(c)c.classList.toggle('open');
}

// ─── History ─────────────────────────────────────────────────────
function saveRun(j){
  runs.unshift({score:j.final_score?.final_score||0,target:j.target_url,mode:j.mode||'official',ts:new Date().toISOString(),job:j});
  if(runs.length>15)runs.length=15;
  try{localStorage.setItem('sn_runs',JSON.stringify(runs));}catch{}
  refreshHist();
}
function refreshHist(){
  document.getElementById('histCount').textContent=runs.length;
  document.getElementById('histBtn').style.display=runs.length?'block':'none';
}
function openHist(){
  const el=document.getElementById('histList');
  el.innerHTML=runs.length?runs.map((h,i)=>{
    const[,grade,lbl]=gradeInfo(h.score);
    const c=h.score>=75?'var(--green)':h.score>=50?'var(--yellow)':'var(--red)';
    const mb=`<span class="mode-badge ${h.mode||'official'}" style="font-size:9px">${h.mode==='extended'?'Extended':'Official'}</span>`;
    return`<div class="h-row" onclick="loadHist(${i})">
      <div style="font-size:20px;font-weight:900;min-width:50px;color:${c}">${h.score.toFixed(1)}</div>
      <div style="flex:1">
        <div style="font-size:13px;font-weight:600;color:var(--text)">${escH(h.target)}</div>
        <div style="font-size:11px;color:var(--muted2);margin-top:2px">${new Date(h.ts).toLocaleString()} · ${lbl} ${mb}</div>
      </div>
      <span style="color:var(--muted);font-size:12px">→</span>
    </div>`;
  }).join(''):'<div style="color:var(--muted);text-align:center;padding:32px">No runs yet.</div>';
  document.getElementById('histModal').classList.add('open');
}
function closeHist(){document.getElementById('histModal').classList.remove('open');}
function loadHist(i){closeHist();const h=runs[i];if(!h)return;lastJob=h.job;currentMode=h.mode||'official';showResults(h.job);}

// ─── Misc ─────────────────────────────────────────────────────────
function showPage(id){document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));document.getElementById(id).classList.add('active');}
function goHome(){if(pollT)clearInterval(pollT);if(elapsedT)clearInterval(elapsedT);resetStart();showPage('pgLanding');}
function resetStart(){document.getElementById('startTxt').textContent='🚀 Start Evaluation';document.getElementById('startBtn').disabled=false;}
function gradeInfo(s){
  if(s>=90)return['A','A+','Excellent'];if(s>=80)return['A','A','Great'];
  if(s>=70)return['B','B','Good'];if(s>=60)return['C','C','Average'];
  if(s>=40)return['D','D','Below Average'];return['F','F','Needs Work'];
}
function sColor(v){return v>=75?'var(--green)':v>=50?'var(--yellow)':'var(--red)';}
function escH(s){return(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function toast(msg,type='ok'){
  const el=document.createElement('div');el.className='toast '+type;el.textContent=msg;
  document.getElementById('toasts').appendChild(el);setTimeout(()=>el.remove(),4000);
}
async function copyJSON(){
  if(!lastJob)return;
  try{await navigator.clipboard.writeText(JSON.stringify(lastJob,null,2));toast('JSON copied!');}
  catch{toast('Copy failed — see console','err');console.log(JSON.stringify(lastJob,null,2));}
}
