'use strict';
const el=id=>document.getElementById(id);
const ui={mode:'email',result:null,step:0,timer:null,sample:0,request:null};
const exampleValues={email:['student@example.com','a.b+tag@university.edu','user@@example.com','bad..dots@gmail.com','hello@sub.domain.org','user@example.c'],url:['https://example.com/path?q=1','http://localhost:3000','https://sub.example.co.in','www.google.com','https://example.com:99999','https://example.com/%GG']};
function toast(s){const t=el('toast');t.textContent=s;t.classList.add('show');clearTimeout(toast.timeout);toast.timeout=setTimeout(()=>t.classList.remove('show'),2300);}
function setMode(mode){cancelValidation();ui.mode=mode;ui.result=null;ui.step=0;stopPlay();el('modeEmail').classList.toggle('active',mode==='email');el('modeEmail').setAttribute('aria-selected',mode==='email');el('modeUrl').classList.toggle('active',mode==='url');el('modeUrl').setAttribute('aria-selected',mode==='url');el('inputString').value=mode==='email'?'student@example.com':'https://example.com/path?q=1';refreshInput();clearResult();}
function refreshInput(){el('inputCount').textContent=el('inputString').value.length+' / 2048';}
function clearResult(){el('resultBig').className='result-big';el('resultBig').innerHTML='READY<span class="result-asterisk">✳</span>';el('resultMessage').textContent='Enter an address and run the machine.';el('resultParts').replaceChildren();el('traceVisual').innerHTML='<div class="trace-empty">q0 <span>→</span> q1 <span>→</span> qA</div>';el('stepMeta').textContent='NO RUN YET';['prevStep','playStep','nextStep','resetStep','copyResult','saveResult'].forEach(i=>el(i).disabled=true);['currentState','currentSymbol','currentTransition'].forEach(i=>el(i).textContent='—');}
function newNode(tag,cls,content){const e=document.createElement(tag);if(cls)e.className=cls;if(content!==undefined)e.textContent=content;return e;}
function drawTrace(){const r=ui.result;if(!r)return;const step=r.trace[ui.step],last=ui.step===r.trace.length-1;el('stepMeta').textContent=`STEP ${String(ui.step+1).padStart(2,'0')} / ${String(r.trace.length).padStart(2,'0')}`;el('currentState').textContent=`${step.to} / ${r.states[step.to]||'State'}`;el('currentSymbol').textContent=step.char==='∎'?'END':step.char===' '?'SPACE':step.char;el('currentTransition').textContent=`${step.from} → ${step.to}`;let viewport=el('traceVisual');viewport.replaceChildren();const first=Math.max(0,ui.step-2),end=Math.min(r.trace.length,first+6);for(let i=first;i<end;i++){const t=r.trace[i];if(i>first)viewport.appendChild(newNode('span','trace-arrow','→'));const node=newNode('div',`trace-node ${i===ui.step?'active':''} ${t.to==='qA'?'accept':''} ${t.to==='qX'?'dead':''}`,t.to);node.title=`${t.char} : ${t.from} → ${t.to}`;viewport.appendChild(node);}el('prevStep').disabled=ui.step===0;el('nextStep').disabled=last;}
function stopPlay(){if(ui.timer){clearInterval(ui.timer);ui.timer=null;}el('playStep').textContent='▶ PLAY';el('playStep').setAttribute('aria-pressed','false');}
function cancelValidation(){
 if(ui.request){ui.request.abort();ui.request=null;}
 const button=el('validateBtn');button.disabled=false;button.firstChild.textContent='RUN VALIDATION ';
}
async function validate(){
 cancelValidation();stopPlay();ui.result=null;ui.step=0;clearResult();
 const controller=new AbortController();ui.request=controller;
 const mode=ui.mode,input=el('inputString').value,button=el('validateBtn');
 button.disabled=true;button.firstChild.textContent='RUNNING... ';
 try{
  const response=await fetch('/api/validate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode,input}),signal:controller.signal});
  const data=await response.json();if(ui.request!==controller)return;
  if(!response.ok)throw Error(data.error||'Validation error');
  ui.result=data;ui.step=0;
  el('resultBig').className=`result-big ${data.valid?'accepted':'rejected'}`;
  el('resultBig').textContent=data.valid?'ACCEPTED.':'REJECTED.';
  el('resultMessage').textContent=data.message;
  const parts=el('resultParts');parts.replaceChildren();
  (data.parts||[]).forEach(p=>{const pill=newNode('span','part-pill');pill.append(newNode('b','',p.label),newNode('span','',p.value));parts.appendChild(pill);});
  if(!data.valid)parts.appendChild(newNode('span','part-pill',`RULE: ${data.rule} · POSITION: ${data.index+1}`));
  ['playStep','resetStep','copyResult','saveResult'].forEach(i=>el(i).disabled=false);
  drawTrace();
 }catch(e){if(e.name!=='AbortError'&&ui.request===controller){el('resultMessage').textContent='Validation unavailable: '+e.message;toast('Could not validate: '+e.message);}}
 finally{if(ui.request===controller)cancelValidation();}
}
function play(){if(!ui.result)return;if(ui.timer){stopPlay();return;}if(ui.step===ui.result.trace.length-1)ui.step=0;el('playStep').textContent='Ⅱ PAUSE';el('playStep').setAttribute('aria-pressed','true');ui.timer=setInterval(()=>{if(ui.step>=ui.result.trace.length-1){stopPlay();return;}ui.step++;drawTrace();},220);drawTrace();}
function save(){if(!ui.result)return;const r=ui.result;const entry={timestamp:new Date().toISOString(),mode:r.mode,input:r.input,valid:r.valid,rule:r.rule,steps:r.steps};try{const stored=JSON.parse(localStorage.getItem('syntaxlab-history')||'[]');stored.unshift(entry);localStorage.setItem('syntaxlab-history',JSON.stringify(stored.slice(0,50)));toast('Saved locally on this browser.');}catch{toast('Local storage not available.');}}
async function copy(){if(!ui.result)return;const r=ui.result;const text=`SYNTAXLAB VALIDATION\nMode: ${r.mode}\nInput: ${r.input}\nStatus: ${r.status}\nRule: ${r.rule}\nMessage: ${r.message}\nSteps: ${r.steps}`;try{await navigator.clipboard.writeText(text);toast('Validation result copied.');}catch{toast('Clipboard unavailable in this browser.');}}
async function runTests(){const button=el('runTests');button.disabled=true;button.innerHTML='EXECUTING…';try{const r=await fetch('/api/cases');if(!r.ok)throw Error('Network failure');const data=await r.json(),rows=data.cases,passed=rows.filter(x=>x.passed).length;el('totalCases').textContent=rows.length;el('passedCases').textContent=passed;el('passRate').textContent=`${Math.round(passed/rows.length*100)}%`;el('testBarFill').style.width=`${100*passed/rows.length}%`;const region=el('testRows');region.replaceChildren();for(const t of rows){const row=newNode('div',`test-row ${t.passed?'pass':'fail'}`);row.append(newNode('span','mono muted',String(t.id).padStart(2,'0')),newNode('span','case-input',t.input),newNode('span','',t.mode.toUpperCase()),newNode('span','case-status',t.passed?'✓ PASS':'✕ FAIL'));row.title=t.detail;region.appendChild(row);}toast(`Executed ${rows.length} real test cases. ${passed} passed.`);}catch(e){toast('Tests unavailable: '+e.message);}finally{button.disabled=false;button.innerHTML='RUN FULL TEST SUITE <span>↗</span>';}}
function closeMenu(){
 const nav=el('nav'),button=el('menuToggle');nav.classList.remove('open');
 button.setAttribute('aria-expanded','false');button.setAttribute('aria-label','Open navigation menu');
}
function setup(){
 el('modeEmail').addEventListener('click',()=>setMode('email'));
 el('modeUrl').addEventListener('click',()=>setMode('url'));
 el('inputString').addEventListener('input',()=>{cancelValidation();refreshInput();stopPlay();ui.result=null;clearResult();});
 el('inputString').addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){e.preventDefault();validate();}});
 el('validateBtn').addEventListener('click',validate);
 el('sampleBtn').addEventListener('click',()=>{
  cancelValidation();stopPlay();ui.result=null;ui.step=0;
  const values=exampleValues[ui.mode];ui.sample=(ui.sample+1)%values.length;
  el('inputString').value=values[ui.sample];refreshInput();clearResult();el('inputString').focus();
  toast('Example loaded. Run validation.');
 });
 el('clearInput').addEventListener('click',()=>{
  cancelValidation();stopPlay();ui.result=null;ui.step=0;
  el('inputString').value='';refreshInput();clearResult();el('inputString').focus();
 });
 el('prevStep').addEventListener('click',()=>{stopPlay();ui.step=Math.max(0,ui.step-1);drawTrace();});
 el('nextStep').addEventListener('click',()=>{stopPlay();ui.step=Math.min(ui.result.trace.length-1,ui.step+1);drawTrace();});
 el('resetStep').addEventListener('click',()=>{stopPlay();ui.step=0;drawTrace();});
 el('playStep').addEventListener('click',play);
 el('copyResult').addEventListener('click',copy);
 el('saveResult').addEventListener('click',save);
 el('runTests').addEventListener('click',runTests);
 el('menuToggle').addEventListener('click',()=>{
  const open=el('nav').classList.toggle('open');
  el('menuToggle').setAttribute('aria-expanded',String(open));
  el('menuToggle').setAttribute('aria-label',open?'Close navigation menu':'Open navigation menu');
 });
 document.querySelectorAll('.nav a,.mobile-dock a,.brand,.hero-shortcuts a,.header-cta').forEach(a=>a.addEventListener('click',closeMenu));
 document.querySelectorAll('[data-mode]').forEach(a=>a.addEventListener('click',()=>setMode(a.dataset.mode)));
 document.addEventListener('keydown',e=>{if(e.key==='Escape')closeMenu();});
 document.addEventListener('click',e=>{if(!el('nav').contains(e.target)&&!el('menuToggle').contains(e.target))closeMenu();});
 if('IntersectionObserver' in window){
  const ob=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting){e.target.classList.add('visible');ob.unobserve(e.target);}}),{threshold:.08});
  document.querySelectorAll('.reveal').forEach(e=>ob.observe(e));
  const sections=[...document.querySelectorAll('section[id],footer[id]')];
  const navObserver=new IntersectionObserver(entries=>{
   for(const entry of entries){if(!entry.isIntersecting)continue;
    document.querySelectorAll('.nav a,.mobile-dock a').forEach(a=>{
     if(a.getAttribute('href')==='#'+entry.target.id)a.setAttribute('aria-current','location');
     else a.removeAttribute('aria-current');
    });
   }
  },{rootMargin:'-15% 0px -65% 0px',threshold:0});
  sections.forEach(section=>navObserver.observe(section));
 }else{document.querySelectorAll('.reveal').forEach(e=>e.classList.add('visible'));}
 refreshInput();orb();
}
function orb(){
 const canvas=el('heroCanvas');if(!canvas)return;
 const ctx=canvas.getContext('2d');if(!ctx)return;
 const n=canvas.width,small=window.matchMedia('(max-width:760px)').matches;
 const points=[],count=small?160:300;
 for(let i=0;i<count;i++){const u=(i+.5)/count,v=i*2.399963229728653,phi=Math.acos(1-2*u);points.push([Math.sin(phi)*Math.cos(v),Math.cos(phi),Math.sin(phi)*Math.sin(v)]);}
 let angle=0,frameId=0,last=0,visible=true;
 const reduced=window.matchMedia('(prefers-reduced-motion:reduce)').matches;
 function draw(){
  ctx.clearRect(0,0,n,n);
  const a=angle,b=.35,c=Math.cos(a),s=Math.sin(a),cb=Math.cos(b),sb=Math.sin(b),q=[];
  for(const p of points){const xx=p[0]*c-p[2]*s,zz=p[0]*s+p[2]*c,yy=p[1]*cb-zz*sb,depth=p[1]*sb+zz*cb,scale=1.12/(2.4-depth);q.push({x:n/2+xx*n*.58*scale,y:n/2+yy*n*.58*scale,depth});}
  q.sort((a,b)=>a.depth-b.depth);
  for(const p of q){ctx.beginPath();const r=(p.depth+1.8)*2.1;ctx.arc(p.x,p.y,Math.max(.8,r),0,Math.PI*2);ctx.fillStyle=p.depth>.15?'#00C5EC':'#181818';ctx.globalAlpha=.22+(p.depth+1)/2*.66;ctx.fill();}
  ctx.globalAlpha=1;ctx.save();ctx.translate(n/2,n/2);ctx.rotate(a*.75);ctx.strokeStyle='#141414';ctx.lineWidth=2;ctx.beginPath();ctx.ellipse(0,0,n*.38,n*.145,-.3,0,Math.PI*2);ctx.stroke();ctx.setLineDash([11,10]);ctx.strokeStyle='#008faa';ctx.lineWidth=2;ctx.beginPath();ctx.ellipse(0,0,n*.27,n*.34,.63,0,Math.PI*2);ctx.stroke();ctx.restore();
 }
 function nextFrame(now){frameId=0;if(!visible||document.hidden||reduced)return;if(!last||now-last>=33){draw();angle+=.008;last=now;}schedule();}
 function schedule(){if(!frameId&&visible&&!document.hidden&&!reduced)frameId=requestAnimationFrame(nextFrame);}
 function visibilityUpdate(){if(!visible||document.hidden){if(frameId)cancelAnimationFrame(frameId);frameId=0;}else schedule();}
 if('IntersectionObserver' in window)new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;visibilityUpdate();},{threshold:0}).observe(canvas);
 document.addEventListener('visibilitychange',visibilityUpdate);
 draw();schedule();
}
setup();