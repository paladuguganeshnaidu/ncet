/* NCET VerifyFlow · staff and HOD document workflow. */
(() => {
  'use strict';
  const ROLES = {
    admin: { title:'Super Administrator', short:'Super Admin', name:'System Administrator', subtitle:'Security & access control', icon:'shield' },
    staff: { title: 'Faculty & Staff', short: 'Staff', name: 'Faculty Member', subtitle: 'Department contributor', icon: 'users' },
    hod: { title: 'Head of Department', short: 'HOD', name: 'Department HOD', subtitle: 'Department reviewer', icon: 'briefcase' },
    principal: { title: 'Principal', short: 'Principal', name: 'Office of the Principal', subtitle: 'Institutional oversight', icon: 'landmark' },
    iqac: { title: 'IQAC', short: 'IQAC', name: 'IQAC Coordinator', subtitle: 'Quality assurance', icon: 'award' },
  };
  const icons = {
    home: '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V10Z"/><path d="M9 21v-8h6v8"/>',
    file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6M8 13h8M8 17h8"/>',
    folder: '<path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>',
    upload: '<path d="M12 16V3m-5 5 5-5 5 5"/><path d="M4 16v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    checkCircle: '<circle cx="12" cy="12" r="9"/><path d="m8 12 2.5 2.5L16 9"/>',
    close: '<path d="M18 6 6 18M6 6l12 12"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l4 2"/>',
    search: '<circle cx="10.7" cy="10.7" r="7.7"/><path d="m16.5 16.5 5 5"/>',
    chevron: '<path d="m9 18 6-6-6-6"/>',
    down: '<path d="m6 9 6 6 6-6"/>',
    arrow: '<path d="M5 12h14m-6-6 6 6-6 6"/>',
    bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 8-3 9h18c0-1-3-2-3-9M10 21h4"/>',
    shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
    lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
    users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
    eye: '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
    eyeOff: '<path d="M3 3 21 21M10.6 5.1C11.1 5 11.5 5 12 5c6.4 0 10 7 10 7a17 17 0 0 1-3.5 4.2M6 6.5C3.4 8.3 2 12 2 12s3.6 7 10 7c1.6 0 3-.4 4.3-1"/><path d="M10 10a3 3 0 0 0 4 4"/>',
    briefcase: '<rect x="3" y="7" width="18" height="14" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12a20 20 0 0 0 18 0"/>',
    landmark: '<path d="m3 10 9-7 9 7M4 10h16M6 10v9m4-9v9m4-9v9m4-9v9M3 21h18"/>',
    award: '<circle cx="12" cy="8" r="5"/><path d="m8 12-2 10 6-3 6 3-2-10"/>',
    logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4m7 14 5-5-5-5m5 5H9"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
    info: '<circle cx="12" cy="12" r="10"/><path d="M12 11v6M12 7h.01"/>',
    calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 10h18"/>',
    download: '<path d="M12 3v13m-5-5 5 5 5-5M4 17v4h16v-4"/>',
    chart: '<path d="M4 20V4M4 20h17M9 16v-5m5 5V7m5 9V3"/>',
    filter: '<path d="M4 7h16M7 12h10m-7 5h4"/>',
    rotate: '<path d="M3 11a9 9 0 0 1 15-6l3 3V3m0 5h-5M21 13a9 9 0 0 1-15 6l-3-3v5m0-5h5"/>',
    sparkle: '<path d="m12 3 1.9 6.1L20 11l-6.1 1.9L12 19l-1.9-6.1L4 11l6.1-1.9L12 3ZM19 17v5m-2.5-2.5h5"/>',
    paperclip: '<path d="m20 11.5-7.5 7.5a5 5 0 0 1-7-7l8.5-8.5a3 3 0 0 1 4.2 4.2L9.7 16a1 1 0 0 1-1.4-1.4l7-7"/>',
    trash: '<path d="M4 7h16M10 11v7m4-7v7M6 7l1 14h10l1-14M9 7V4h6v3"/>',
    copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
  };
  const icon = (name, size = '') => `<svg aria-hidden="true" class="icon ${size}" viewBox="0 0 24 24">${icons[name] || icons.file}</svg>`;
  const esc = (x = '') => String(x).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const daysAgo = (n) => new Date(Date.now() - n * 864e5).toISOString();
  const prettyDate = (date, long = false) => new Date(date).toLocaleDateString('en-IN', long ? { day: 'numeric', month: 'long', year: 'numeric' } : { day: '2-digit', month: 'short', year: 'numeric' });
  const prettyTime = date => new Date(date).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' });
  const uid = () => (globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`);
  const currentAY = () => { const d = new Date(); const year = d.getMonth() >= 5 ? d.getFullYear() : d.getFullYear()-1; return `${year}-${String(year + 1).slice(2)}`; };
  let docs = [];
  let role = null;
  let user = null;
  let csrf = '';
  let selectedRole = 'staff';
  let page = 'overview';
  let filter = 'all';
  let query = '';
  let authError = '';
  let showPassword = false;
  let modal = null;
  let mobileOpen = false;
  let pickedFile = null;
  let toastTimer = null;
  let accounts = [];
  let academicDepartments = [];
  let auditEntries = [];
  let cleanupActions = [];
  let aiOverview = {};
  let rulebook={version:0,rules:[],history:[]};
  let integrations={configured:false,deepseek_configured:false,openrouter_configured:false,provider:null,model:null};
  let verifyReport=null;
  const app = document.getElementById('app');
  const currentRole = () => ({...ROLES[role || 'staff'], name: user?.name || ROLES[role || 'staff'].name, subtitle: user?.department || ROLES[role || 'staff'].subtitle});
  const canSee = d => role === 'principal' || role === 'iqac' ? d.status === 'approved' : (role === 'hod' ? d.department === user?.department : true);
  const available = () => docs.filter(canSee).slice().sort((a,b) => new Date(b.submitted) - new Date(a.submitted));
  async function api(path, options={}) {
    const headers = {'Accept':'application/json', ...(options.headers || {})};
    if (csrf && options.method && options.method.toUpperCase() !== 'GET') headers['X-CSRF-Token'] = csrf;
    const res = await fetch(path, {...options, credentials:'same-origin',headers});
    if (!res.ok) {
      let detail = 'The server could not complete this action.';
      try {const x=await res.json();detail=typeof x.detail==='string'?x.detail:detail;}catch(_){}
      if(res.status===401 && role) {role=null;user=null;csrf='';render();}
      throw new Error(detail);
    }
    return res.json();
  }
  async function refreshDocs() {
    if(role==='admin'){docs=[];render();return;}
    let all=[],offset=0,total=1;
    while(offset<total && offset<10000){
      const result=await api(`/api/documents?offset=${offset}&limit=200`);
      all=all.concat(result.items);total=result.total;offset+=result.items.length;
      if(!result.items.length) break;
    }
    docs=all;render();
  }
  async function start() {
    try {const auth=await api('/api/auth/me');user=auth.user;role=user.role;selectedRole=role;csrf=auth.csrf;await refreshDocs();}
    catch(_){role=null;user=null;csrf='';render();}
  }
  const updateDocs = fn => { docs = fn(docs);render(); };
  const statusHTML = status => `<span class="status ${esc(status)}"><span class="s-dot"></span>${{verifying:'Verification in progress',pending:'Pending HOD',manual_review:'Manual review',needs_correction:'Needs correction',approved:'Approved',rejected:'Rejected'}[status] || esc(status)}</span>`;
  const fmtSize = bytes => !bytes ? '—' : bytes > 1048576 ? `${(bytes / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
  const initials = str => String(str).split(/\s+/).slice(0,2).map(x=>x[0]).join('').toUpperCase();
  const titleFor = p => ({ overview:'Dashboard',documents:role === 'hod' ? 'Review submissions' : role === 'staff' ? 'My documents' : 'Approved documents',upload:'Submit a document',activity:'Activity & history',insights:'Reports & insights',guide:'How it works',rules:'Verification rules',integrations:'AI configuration',cleanup:'Database cleanup',users:role==='hod'?'Department staff':'User management',audit:'Security audit',account:'My account' })[p] || 'Dashboard';
  const crest = `<div class="crest ncms-crest"><img src="/static/ncet-brand.svg" alt="NCET tree and open-book emblem" /></div>`;
  const campus = `<svg viewBox="0 0 560 195" xmlns="http://www.w3.org/2000/svg" fill="none"><path d="M70 165h426" stroke="#D6BE91" stroke-opacity=".42" stroke-width="1.5"/><path d="M124 161V87L280 30l156 57v74" stroke="#E3CEA6" stroke-width="1.7" fill="#D9BB8B" fill-opacity=".045"/><path d="m115 90 165-68 165 68" stroke="#F5D5A1" stroke-width="2.5"/><path d="M154 161V95h252v66M177 95V72m206 23V72" stroke="#E3CEA6" stroke-opacity=".7" stroke-width="1.5"/><path d="M256 161v-44h48v44" stroke="#E3CEA6" stroke-width="2"/><path d="M268 161v-33h24v33M149 115h82m98 0h82M149 133h82m98 0h82" stroke="#C7D8CF" stroke-opacity=".38"/><path d="M205 95v66m150-66v66" stroke="#E3CEA6" stroke-opacity=".6"/><circle cx="280" cy="82" r="14" stroke="#F0D6A8"/><path d="M280 75v14m-7-7h14" stroke="#F0D6A8"/><path d="M92 164V99m0 7c-36-10-31-45-3-55 31-9 53 29 22 52M468 164V99m0 7c-36-10-31-45-3-55 31-9 53 29 22 52" stroke="#7EADA3" stroke-opacity=".6" stroke-width="1.5"/><path d="M46 174h468" stroke="#A9CEBB" stroke-opacity=".33" stroke-width="1"/></svg>`;
  const txt = str => esc(str || '');

  function loginHTML() {
    return `<div class="login-page">
      <section class="login-art"><div class="brandline">${crest}<div><div class="brand-name">NCET VerifyFlow</div><div class="brand-sub">Institutional workspace</div></div></div>
        <div class="hero-copy"><div class="eyebrow">INSTITUTIONAL DOCUMENT REVIEW</div><h1>Document review,<br><em>made straightforward.</em></h1><p>A clear, secure way to submit documents, review department requirements and track approvals at Nagarjuna College of Engineering and Technology.</p></div>
        
        <div class="art-bottom"><span><span class="beacon"></span> Institutional document review</span><span>NCET DOCUMENT WORKSPACE</span></div>
      </section>
      <section class="login-right"><div class="login-panel"><div class="auth-topline">${icon('shield', 'sm')} DOCUMENT VERIFICATION PORTAL <span class="demo-flag" style="margin-left:auto">Secure workspace</span></div>
        <h2>Welcome to NCET VerifyFlow</h2><p class="intro">Sign in with your institution-issued username and password. Your permissions are assigned by the college.</p>
        
        ${authError ? `<div class="error-message" role="alert">${icon('info','sm')}${esc(authError)}</div>` : ''}
        <form id="login-form" autocomplete="off"><div class="field"><label for="login-user" class="form-label">User ID</label><div class="input-wrap">${icon('user','leading')}<input class="with-icon" id="login-user" name="username" placeholder="Enter your user ID" aria-required="true" required autocapitalize="none" spellcheck="false" maxlength="40" /></div></div>
        <div class="field"><label for="login-pass" class="form-label">Password</label><div class="input-wrap">${icon('lock','leading')}<input id="login-pass" name="password" type="${showPassword ? 'text' : 'password'}" placeholder="Enter your password" aria-required="true" required maxlength="80" /><button class="trail" aria-label="Toggle password visibility" data-action="toggle-password" type="button">${icon(showPassword ? 'eyeOff':'eye','sm')}</button></div></div>
        <button type="submit" class="btn btn-primary btn-lg btn-full">Sign in to workspace ${icon('arrow','sm')}</button></form>
        <div class="demo-hint"><strong>Institutional account</strong><br>Access is provided by your department HOD or the institution administrator. Contact them if you need an account.</div>
        <p class="login-foot">Passwords are protected by server-side verification.<br>Authorized college personnel only. Sign out on shared devices.</p>
      </div></section>
    </div>`;
  }
  const isBcaDepartment = value => ['bca','computer applications','bachelor of computer applications']
    .includes(String(value||'').trim().toLowerCase());
  function sidebarHTML() {
    const count = role === 'hod' ? docs.filter(d=>['pending','manual_review'].includes(d.status)).length : 0;
    const nav = role==='admin' ? [['overview','home','Overview'],['users','users','User management'],['integrations','sparkle','AI configuration'],['cleanup','trash','Database cleanup'],['audit','shield','Security audit'],['account','user','My account']] : [['overview','home','Overview'],['documents',role==='hod'?'checkCircle':'folder',role==='hod'?'Review queue':role==='staff'?'My documents':'Approved records'],...(role==='staff'?[['upload','upload','Submit document']]:[]),...(role==='hod'?[['rules','shield','Verification rules'],['users','users','Department staff']]:[]),['activity','clock','Activity log'],...(role==='principal'||role==='iqac'?[['insights','chart','Reports & insights']]:[]),['account','user','My account'],['guide','info','Help & process']];
    return `<aside class="sidebar ${mobileOpen?'open':''}" id="sidebar"><div class="sidebar-brand">${crest}<div><div class="brand-name">NCET VerifyFlow</div><div class="brand-sub">Institutional workspace</div></div></div>
      <div class="nav-group"><div class="nav-heading">Workspace</div>${nav.map(([k,i,t])=>`<button class="nav-item ${page===k?'active':''}" data-page="${k}" aria-current="${page===k?'page':'false'}">${icon(i)}${t}${k==='documents'&&count ? `<span class="count">${count}</span>`:''}</button>`).join('')}</div>
      ${(role==='admin'||(['hod','staff'].includes(role) && String(user?.department||'').trim())) ? `<div class="nav-group"><div class="nav-heading">BRANCH SERVICES</div><a class="nav-item" href="/bca/manage" style="text-decoration:none">${icon('users')} Student enrollment</a>${role==='admin'||role==='hod'||isBcaDepartment(user?.department) ? `<a class="nav-item" href="/community" style="text-decoration:none">${icon('folder')} Projects & contributions</a>` : ''}</div>` : ''}
      ${(['hod','principal'].includes(role)) ? `<div class="nav-group"><div class="nav-heading">Student support</div>${role==='principal' ? `<a class="nav-item" href="/community" style="text-decoration:none">${icon('folder')} Project contributions</a>` : ''}<a class="nav-item" href="${role==='principal'?'/bca/oversight':'/complaints'}" style="text-decoration:none">${icon('shield')} ${role==='principal'?'Institution-wide oversight':'Complaint management'}</a></div>` : ''}
      <div class="nav-group"><div class="nav-heading">Department work</div><a class="nav-item" href="/tasks" style="text-decoration:none">${icon('file')} ${role==='hod'?'HOD task dashboard':'Tasks &amp; reports'}</a></div>
      <div class="sidebar-spacer"></div><div class="help-box">${icon('shield','sm')}<div class="h-title">A clear approval pathway</div><p>Faculty submission → HOD review → Principal and IQAC visibility.</p><button class="text-btn" data-page="guide">View workflow ${icon('arrow','sm')}</button></div>
      <div class="side-user"><span class="avatar">${initials(currentRole().name)}</span><div class="who"><strong>${txt(currentRole().name)}</strong><span>${txt(currentRole().subtitle)}</span></div><button type="button" class="icon-button" data-action="logout" aria-label="Sign out" title="Sign out">${icon('logout')}</button></div>
    </aside>`;
  }
  function headerHTML() {
    return `<header class="topbar"><div class="inline-center"><button type="button" class="icon-button mobile-toggle" aria-label="Open navigation" data-action="menu">${icon('menu')}</button><div class="breadcrumb">Workspace ${icon('chevron','sm')} <strong>${txt(titleFor(page))}</strong></div></div><div class="top-right"><span class="pill"><span class="dot"></span> Secure connection</span><button class="icon-button" aria-label="Recent activity" data-page="activity" title="View activity">${icon('bell')}</button><div class="avatar" title="${txt(currentRole().name)}">${initials(currentRole().name)}</div></div></header>`;
  }
  const pageHeader = (eyebrow, title, desc, extra='') => `<div class="page-header"><div><div class="overline">${eyebrow}</div><h1>${title}</h1><p>${desc}</p></div>${extra}</div>`;
  const kpi = (label, value, caption, glyph, theme) => `<div class="metric"><div class="metric-top"><div class="metric-label">${label}</div><div class="metric-icon ${theme}">${icon(glyph)}</div></div><div class="metric-num mono">${value}</div><div class="metric-caption">${caption}</div></div>`;
  function greeting() { const h = new Date().getHours(); return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening'; }
  function bannerHTML() {
    let headline, sub, btn = '';
    if (role==='staff') { headline = 'Faculty submissions'; sub = 'Submit documents, follow HOD decisions, and keep an organised record of your work.'; btn = `<button class="btn btn-primary" data-page="upload">${icon('upload','sm')} New submission</button>`; }
    else if (role==='hod') { headline = 'Department review queue'; sub = 'Review departmental submissions and make decisions that move records forward.'; btn = `<button class="btn btn-primary" data-page="documents">${icon('checkCircle','sm')} Open review queue</button>`; }
    else { headline = 'Institutional review overview'; sub = role==='principal' ? 'A consolidated view of HOD-approved records for institutional oversight.' : 'All department-approved documents, organised for quality assurance and accreditation readiness.'; btn = `<button class="btn btn-primary" data-page="documents">${icon('folder','sm')} Browse records</button>`; }
    return `<section class="banner"><div class="bn-copy"><div class="bn-eyebrow">NCET · DOCUMENT MANAGEMENT</div><h2>${headline}</h2><p>${sub}</p></div>${btn}</section>`;
  }
  const rowHTML = d => `<button class="doc-row" data-open="${esc(d.id)}" aria-label="View ${txt(d.title)}"><span class="file-glyph">${icon('file')}</span><span class="doc-meta"><span class="doc-title">${txt(d.title)}</span><span class="t-sub">${txt(d.category)} · ${prettyDate(d.submitted)}</span></span>${statusHTML(d.status)}</button>`;
  function emptyHTML(title='No documents found', desc='Try a different search or filter to see more records.') { return `<div class="empty-state"><div class="empty-icon">${icon('folder','lg')}</div><h3>${title}</h3><p>${desc}</p></div>`; }
  function activityEntries() {
    return available().flatMap(d=> (d.history || []).map(h=>({...h, doc:d}))).sort((a,b)=>new Date(b.at)-new Date(a.at));
  }
  function activityList(max=5) {
    const items=activityEntries().slice(0,max);
    return items.length ? `<div class="activity-list">${items.map(x=>`<div class="activity-item"><span class="activity-mark ${x.kind==='approved'?'done':x.kind==='rejected'?'red':'amber'}">${icon(x.kind==='approved'?'check':x.kind==='rejected'?'close':'upload','sm')}</span><div class="activity-copy"><strong>${x.kind==='submitted'?'Document submitted':x.kind==='approved'?'Document approved':x.kind==='rejected'?'Revision requested':'Document resubmitted'}</strong><p>${txt(x.doc.title)}</p><span class="activity-when">${prettyTime(x.at)} · ${txt(x.by)}</span></div></div>`).join('')}</div>` : emptyHTML('Nothing here yet','Your activity history will appear here.');
  }
  function overviewHTML() {
    if(role==='admin') return `${pageHeader('SUPER ADMINISTRATION','Institutional control centre','Manage staff access, secure integration credentials, and audit records.')}<div class="quick-actions"><button data-page="users" class="quick-card">${icon('users')} <div><span>Accounts and passwords</span><small>Provision and manage institutional users</small></div>${icon('arrow')}</button><button data-page="integrations" class="quick-card">${icon('sparkle')} <div><span>AI document review</span><small>Manage document review settings</small></div>${icon('arrow')}</button><button data-page="audit" class="quick-card">${icon('shield')} <div><span>Security audit</span><small>Inspect administrative events</small></div>${icon('arrow')}</button></div>`;
    const all = available(), pending=all.filter(d=>['pending','manual_review'].includes(d.status)).length, approved=all.filter(d=>d.status==='approved').length, rejected=all.filter(d=>['rejected','needs_correction'].includes(d.status)).length;
    return `${pageHeader('YOUR WORKSPACE',`${greeting()}, ${role==='staff'?'Faculty Member':role==='hod'?'HOD':role==='principal'?'Principal':'IQAC Team'}.`,'A quick snapshot of the records and decisions that matter to you.',`<span class="date-chip">${icon('calendar','sm')} ${prettyDate(new Date().toISOString(),true)}</span>`)}
      ${bannerHTML()}
      <div class="metrics">${kpi('Total documents',all.length,'Records in your workspace','folder','blue')}${kpi(role==='staff'||role==='hod'?'Awaiting decision':'Recently approved',role==='staff'||role==='hod'?pending:approved,role==='staff'||role==='hod'?'Pending HOD review':'Available for your review','clock','amber')}${kpi('Approved',approved,'Cleared by the HOD','checkCircle','green')}${kpi(role==='principal'||role==='iqac'?'Quality records':'Needs revision',role==='principal'||role==='iqac'?approved:rejected,role==='principal'||role==='iqac'?'Institutional archive':'Returned by HOD','file','red')}</div>
      ${role==='staff' ? `<div class="quick-actions"><button data-page="upload" class="quick-card"><span class="round-icon">${icon('upload')}</span><div><span>Submit a new document</span><small>Send to your Head of Department</small></div>${icon('arrow','sm')}</button><button data-page="documents" class="quick-card"><span class="round-icon">${icon('clock')}</span><div><span>Track submissions</span><small>Check status and HOD feedback</small></div>${icon('arrow','sm')}</button><button data-page="guide" class="quick-card"><span class="round-icon">${icon('info')}</span><div><span>How approvals work</span><small>Understand the complete process</small></div>${icon('arrow','sm')}</button></div>`:''}
      <div class="dashboard-grid"><div class="panel"><div class="panel-header"><div><h3 class="panel-title">${role==='hod'?'Pending department review':'Recent documents'}</h3><div class="panel-subtitle">${role==='hod'?'Submissions awaiting your decision':'Latest records in your workspace'}</div></div><button class="text-btn" data-page="documents">View all ${icon('arrow','sm')}</button></div>${(role==='hod'?all.filter(d=>['pending','manual_review'].includes(d.status)):all).slice(0,5).map(rowHTML).join('') || emptyHTML('You are all caught up','There are no items requiring attention right now.')}</div>
      <div class="panel"><div class="panel-header"><div><h3 class="panel-title">Document journey</h3><div class="panel-subtitle">A transparent, traceable process</div></div></div><div class="workflow">${[['upload','Submit document','Staff upload a record for departmental review.'],['clock','Review at department','The HOD approves verified or manually flagged documents.'],['checkCircle','Institutional visibility','Approved records reach Principal & IQAC.']].map((a,i)=>`<div class="flow-step"><span class="flow-symbol">${icon(a[0])}</span><div><b>${a[1]}</b><p>${a[2]}</p></div></div>`).join('')}</div><div class="panel-header" style="border-top:1px solid #eef1f2"><div><h3 class="panel-title">Recent activity</h3><div class="panel-subtitle">Latest changes to records</div></div><button data-page="activity" class="text-btn">See all ${icon('arrow','sm')}</button></div><div style="padding:0 22px">${activityList(3)}</div></div></div>`;
  }
  function documentsHTML() {
    const items=available();
    const allCount=items.length;
    const counts=Object.fromEntries(['all','verifying','pending','manual_review','needs_correction','approved','rejected'].map(x=>[x,x==='all'?allCount:items.filter(d=>d.status===x).length]));
    return `${pageHeader('DOCUMENT LIBRARY', titleFor('documents'), role==='staff'?'Track every submission, review feedback, and document status.':role==='hod'?'Review submissions and record clear, traceable decisions.':'Explore HOD-approved documents prepared for institutional review.',role==='staff'?`<button data-page="upload" class="btn btn-primary">${icon('upload','sm')} New submission</button>`:'')}
      <div class="panel"><div class="panel-header"><div><h3 class="panel-title">Document registry</h3><div class="panel-subtitle">${allCount} ${allCount===1?'document':'documents'} available to your role</div></div><button class="btn btn-sm" data-action="export">${icon('download','sm')} Export CSV</button></div>
      <div class="toolbar"><div class="segmented" role="group" aria-label="Filter documents">${[['all','All'],['verifying','Verifying'],['pending','HOD queue'],['manual_review','Manual review'],['needs_correction','Needs correction'],['approved','Approved'],['rejected','Rejected']].filter(x=>(role==='staff'||role==='hod'||x[0]==='all'||x[0]==='approved')).map(([id,label])=>`<button data-filter="${id}" class="${filter===id?'active':''}">${label} <span class="small">${counts[id]}</span></button>`).join('')}</div><label class="search-wrap">${icon('search','sm')}<input aria-label="Search documents" id="search-docs" placeholder="Search documents..." value="${esc(query)}" /></label></div>
      <div id="docs-results">${tableHTML()}</div></div>`;
  }
  function tableHTML() {
    const matching=available().filter(d=>(filter==='all'||d.status===filter)&&`${d.title} ${d.category} ${d.id} ${d.department} ${d.year}`.toLowerCase().includes(query.toLowerCase()));
    if(!matching.length) return emptyHTML('No matching documents','Try adjusting your search or choose a different status.');
    return `<div class="table-wrap"><table class="data-table"><thead><tr><th>DOCUMENT</th><th>CATEGORY</th><th>SUBMITTED</th><th>STATUS</th><th>ACTION</th></tr></thead><tbody>${matching.map(d=>`<tr><td><div class="t-name">${txt(d.title)}</div><div class="t-sub">${txt(d.id)} · ${txt(d.year)}</div></td><td>${txt(d.category)}</td><td>${prettyDate(d.submitted)}</td><td>${statusHTML(d.status)}</td><td><button class="table-action" data-open="${esc(d.id)}">${role==='hod'&&['pending','manual_review'].includes(d.status)?'Review':'View details'} ${icon('arrow','sm')}</button></td></tr>`).join('')}</tbody></table></div><div class="record-count">Showing ${matching.length} of ${available().length} documents</div>`;
  }
  function uploadHTML() {
    if (role !== 'staff') return overviewHTML();
    return `${pageHeader('NEW SUBMISSION','Submit a document','Documents are checked against current HOD rules, then routed for approval or corrections.')}
      <div class="split-grid"><div class="panel form-panel"><div class="form-header"><div class="overline">DOCUMENT DETAILS</div><h3>Submission information</h3><p>Complete the required fields to start a new review.</p></div>
      <form id="submit-document" novalidate><div class="field"><label class="field-label" for="doc-title">Document title <span style="color:#bf534b">*</span></label><input class="form-control" id="doc-title" name="title" maxlength="140" minlength="5" required placeholder="e.g. Academic audit report — Semester I" /></div>
      <div class="form-grid"><div class="field"><label class="field-label" for="doc-category">Document category *</label><select class="form-control" id="doc-category" name="category" required><option value="">Select category</option>${['Academic Audit','NAAC / Accreditation','Faculty Development','Event / Workshop','Examination / Assessment','Student Support','Infrastructure / Resources','Department Activities','Other'].map(x=>`<option>${x}</option>`).join('')}</select></div><div class="field"><label class="field-label" for="doc-year">Academic year *</label><select class="form-control" id="doc-year" name="year">${[currentAY(),...Array.from({length:4},(_,i)=>{const y=new Date().getFullYear()-1-i;return `${y}–${String(y+1).slice(-2)}`;})].filter((x,i,a)=>a.indexOf(x)===i).map(x=>`<option>${esc(x)}</option>`).join('')}</select></div></div>
      <div class="field"><label class="field-label" for="doc-department">Department *</label><input class="form-control" id="doc-department" name="department" value="${txt(user?.department)}" readonly /></div>
      <div class="field"><label class="field-label" for="doc-desc">Description / purpose *</label><textarea class="form-control textarea" id="doc-desc" name="description" minlength="10" maxlength="2000" placeholder="Explain what is included and why it is being submitted..." required></textarea></div>
      <div class="field"><label class="field-label">Supporting document *</label><div class="upload-zone" id="upload-zone" role="button" tabindex="0" aria-label="Choose or drop a document"> <div class="upload-icon">${icon('upload','lg')}</div><strong><em>Click to browse</em> or drag and drop a file</strong><p>PDF, DOCX, TXT, PNG, JPG · Maximum 10 MB</p>${pickedFile?`<div class="upload-file">${icon('file','sm')} <span>${txt(pickedFile.name)} · ${fmtSize(pickedFile.size)}</span> <button type="button" data-action="remove-file" class="icon-button" aria-label="Remove file">${icon('close','sm')}</button></div>`:''}</div><input id="file-input" name="file" type="file" accept=".pdf,.docx,.txt,.png,.jpg,.jpeg" hidden /></div>
      <div class="notice"><strong>${icon('info','sm')} Before you submit</strong> Your document will be analyzed against HOD rules. For document verification, content may be processed by an approved external AI service. Upload only documents authorized for that processing.</div>
      <div class="submit-actions"><button type="reset" class="btn" data-action="clear-form">Clear form</button><button type="submit" id="submit-btn" class="btn btn-primary">${icon('upload','sm')} Verify and submit ${icon('arrow','sm')}</button></div></form></div>
      <aside class="panel info-panel"><h3>Where does your document go?</h3><p>Every record follows a clear departmental review journey. You can track the outcome from your dashboard.</p><div class="info-list">${[['upload','01 · Submission','Provide details and attach your document.'],['clock','02 · HOD review','The Head of Department reviews the submission.'],['checkCircle','03 · Final visibility','Approved files appear in Principal and IQAC dashboards.'],['rotate','If revision is requested','See the reason and submit an updated record.']].map(a=>`<div class="info-row"><span class="info-mark">${icon(a[0],'sm')}</span><div><b>${a[1]}</b><p>${a[2]}</p></div></div>`).join('')}</div></aside></div>`;
  }
  function activityHTML() {
    const list=activityEntries();
    return `${pageHeader('FULL HISTORY','Activity & decisions','A chronological view of submissions, approvals, and revision requests.')}
      <div class="panel"><div class="panel-header"><div><h3 class="panel-title">Activity timeline</h3><p class="panel-subtitle">${list.length} recorded events</p></div><button class="btn btn-sm" data-action="export">${icon('download','sm')} Export records</button></div><div style="padding:5px 27px 20px">${list.map(a=>`<div class="activity-item"><span class="activity-mark ${a.kind==='approved'?'done':a.kind==='rejected'?'red':'amber'}">${icon(a.kind==='approved'?'check':a.kind==='rejected'?'close':'clock','sm')}</span><div class="activity-copy"><strong>${a.kind==='submitted'?'Submitted for department review':a.kind==='approved'?'Approved by HOD':a.kind==='rejected'?'Returned for revision':'Resubmitted for review'}</strong><p><button class="text-btn" data-open="${esc(a.doc.id)}">${txt(a.doc.title)}</button></p><p>${txt(a.note)}</p><span class="activity-when">${prettyTime(a.at)} · ${txt(a.by)}</span></div></div>`).join('') || emptyHTML()}</div></div>`;
  }
  function insightsHTML() {
    const visible=available(), approved=visible.filter(d=>d.status==='approved');
    const categories=approved.reduce((m,d)=>(m[d.category]=(m[d.category]||0)+1,m),{});
    const distribution=Object.entries(categories).sort((a,b)=>b[1]-a[1]);
    return `${pageHeader('INSTITUTIONAL REPORTING','Reports & insights','High-level insights from documents approved by the Head of Department.')}
      <div class="metrics">${kpi('Approved records',approved.length,'Available for institutional use','checkCircle','green')}${kpi('Document types',distribution.length,'Categories represented','folder','blue')}${kpi('Departments',new Set(approved.map(d=>d.department)).size,'Departments represented','landmark','amber')}${kpi('Latest approvals',approved.filter(d=>(Date.now()-new Date(d.history.at(-1)?.at).getTime())<30*864e5).length,'Approved in last 30 days','calendar','green')}</div>
      <div class="dashboard-grid"><section class="panel"><div class="panel-header"><div><h3 class="panel-title">Documentation by category</h3><p class="panel-subtitle">Composition of approved evidence</p></div></div><div style="padding:24px">${distribution.map(([cat,count])=>`<div style="margin-bottom:20px"><div style="display:flex;justify-content:space-between;gap:12px;font-size:12px;margin-bottom:9px"><strong>${txt(cat)}</strong><span class="muted">${count} ${count===1?'document':'documents'}</span></div><div style="height:8px;background:#edf3f2;border-radius:10px;overflow:hidden"><div style="width:${count/approved.length*100}%;height:100%;background:linear-gradient(90deg,#137466,#65b9a6);border-radius:10px"></div></div></div>`).join('') || emptyHTML()}</div></section>
      <section class="panel"><div class="panel-header"><div><h3 class="panel-title">Institutional archive</h3><p class="panel-subtitle">Approved and available records</p></div></div>${approved.slice(0,6).map(rowHTML).join('')}</section></div><button class="btn btn-primary" data-action="export">${icon('download','sm')} Export approved-records register</button>`;
  }
  function guideHTML() {
    return `${pageHeader('SUPPORT & GUIDANCE','How document review works','An easy-to-follow approval journey built around the responsibilities of each institutional role.')}
      <div class="panel" style="padding:26px"><div class="overline">THE PROCESS</div><div class="quick-actions" style="grid-template-columns:repeat(auto-fit,minmax(230px,1fr));margin-top:19px">${[['01','Staff submits','Upload the document and required details for review.'],['02','Verification + HOD','A review report highlights concerns for department review.'],['03','Principal + IQAC','Approved records become available for institutional reference.']].map(([n,t,d])=>`<div style="background:#f7faf9;border:1px solid #e7efec;border-radius:12px;padding:21px"><div class="overline">STEP ${n}</div><h3 style="font-size:16px;margin:11px 0">${t}</h3><p class="muted" style="font-size:12px;line-height:1.7">${d}</p></div>`).join('')}</div></div>
      <div class="split-grid" style="margin-top:22px"><section class="panel info-panel"><h3>Your permissions</h3><p>${role==='staff'?'You can submit, track and revise your own documents.':role==='hod'?'You can review submissions within your department.':role==='principal'?'You can inspect HOD-approved institutional documents.':'You can inspect and export HOD-approved institutional records.'}</p></section>
      <section class="panel info-panel"><h3>Document confidentiality</h3><p>Only authorized members can view documents. Sign out on shared computers and keep your password private.</p><button class="btn btn-secondary btn-sm" data-page="account">${icon('lock','sm')} Manage password</button></section></div>`;
  }
  function detailHTML(d) {
    const approvable=role==='hod'&&['pending','manual_review'].includes(d.status);
    const rejected=role==='staff'&&['rejected','needs_correction'].includes(d.status);
    return `<div class="modal-layer" data-action="close-modal-bg"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-heading" tabindex="-1"><div class="modal-top"><div><h2 id="modal-heading">Document details</h2><p>Record ID: ${txt(d.id)}</p></div><button type="button" class="icon-button" aria-label="Close dialog" data-action="close-modal">${icon('close')}</button></div><div class="modal-body">
      <div class="detail-title">${txt(d.title)}</div>${statusHTML(d.status)}${d.status==='verifying'&&role==='staff'?`<div class="staff-status-line">${icon('clock','sm')} Running document checks <span class="rotator">${icon('rotate','sm')}</span></div><div class="progress-track"><div class="progress-fill"></div></div>`:''}
      <div class="detail-grid">${[['Submitted by',d.author],['Category',d.category],['Department',d.department],['Academic year',d.year],['Submitted on',prettyDate(d.submitted,true)],['Current status',d.status==='pending'?'Awaiting department review':d.status==='approved'?'Approved by HOD':d.status==='verifying'?'Automated verification in progress':d.status==='manual_review'?'HOD must verify manually':d.status==='needs_correction'?'Corrections needed':'Returned for revision']].map(([k,v])=>`<div><div class="detail-label">${k}</div><div class="detail-value">${txt(v)}</div></div>`).join('')}</div>
      <div class="modal-section-title">About this document</div><p class="detail-text">${txt(d.description)}</p>
      <div class="modal-section-title">Attachment</div><div class="file-attachment">${icon('file','lg')}<div style="min-width:0;flex:1"><b>${txt(d.fileName)}</b><span>${fmtSize(d.fileSize)} · ${d.hasLocalFile ? 'Available to authorized reviewers' : 'Unavailable'}</span></div>${d.hasLocalFile ? `<button class="btn btn-sm" data-action="download" data-id="${esc(d.id)}">${icon('download','sm')} Download</button>` : `<span class="small muted">Unavailable</span>`}</div>
      <div class="modal-section-title">Verification report</div><button class="btn btn-secondary btn-sm" data-action="verification" data-id="${esc(d.id)}">${icon('sparkle','sm')} View detailed verification</button><div class="modal-section-title">Approval timeline</div><div class="timeline">${(d.history||[]).map(h=>`<div class="timeline-entry"><b>${h.kind==='approved'?'Approved by HOD':h.kind==='rejected'?'Returned for revision':h.kind==='resubmitted'?'Resubmitted':'Submitted for review'}</b><p>${txt(h.by)} · ${prettyTime(h.at)}</p>${h.note?`<p class="history-note">${txt(h.note)}</p>`:''}</div>`).join('')}</div></div>
      <div class="modal-actions">${approvable?`<button class="btn btn-danger" data-action="review" data-id="${esc(d.id)}" data-decision="rejected">${icon('close','sm')} Request changes</button><button class="btn btn-primary" data-action="review" data-id="${esc(d.id)}" data-decision="approved">${icon('check','sm')} Approve document</button>`:''}${rejected?`<button class="btn btn-primary" data-action="resubmit" data-id="${esc(d.id)}">${icon('rotate','sm')} Resubmit for review</button>`:''}<button class="btn" data-action="close-modal">Close</button></div></section></div>`;
  }
  function reviewHTML(id, decision) {
    const d=docs.find(d=>d.id===id);if(!d)return '';
    return `<div class="modal-layer" data-action="close-modal-bg"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-heading"><div class="modal-top"><div><h2 id="modal-heading">${decision==='approved'?'Approve document':'Request revisions'}</h2><p>Your decision will update the department workflow.</p></div><button class="icon-button" data-action="close-modal" aria-label="Close dialog">${icon('close')}</button></div><form id="review-form" data-id="${esc(id)}" data-decision="${esc(decision)}"><div class="modal-body"><div class="review-header">${icon('file','lg')}<div><strong>${txt(d.title)}</strong><small>${txt(d.id)} · ${txt(d.category)}</small></div></div><p class="small muted">${decision==='approved'?'Approved records are available in Principal and IQAC dashboards across authorized devices.':'The staff dashboard will display your feedback and allow resubmission.'}</p><label for="review-note" class="form-label" style="margin-top:21px">${decision==='rejected'?'Reason for revision (required)':'Reviewer note (optional)'}</label><textarea id="review-note" class="review-textarea" minlength="${decision==='rejected'?'10':'0'}" maxlength="1500" ${decision==='rejected'?'required':''} placeholder="${decision==='approved'?'e.g. Verified and approved for institutional records.':'Clearly explain what needs to be corrected or attached.'}"></textarea></div><div class="modal-actions"><button type="button" class="btn" data-action="close-modal">Cancel</button><button type="submit" class="btn ${decision==='approved'?'btn-primary':'btn-danger'}">${icon(decision==='approved'?'check':'close','sm')} ${decision==='approved'?'Confirm approval':'Send revision request'}</button></div></form></section></div>`;
  }
  function revisionHTML(d) {return `<div class="modal-layer" data-action="close-modal-bg"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-heading"><div class="modal-top"><div><h2 id="modal-heading">Submit a corrected version</h2><p>${txt(d.id)} · Revision requested by HOD</p></div><button class="icon-button" data-action="close-modal" aria-label="Close dialog">${icon('close')}</button></div><form id="revision-form" data-id="${esc(d.id)}"><div class="modal-body"><div class="review-header">${icon('file','lg')}<div><strong>${txt(d.title)}</strong><small>${txt(d.fileName)}</small></div></div><div class="notice" style="margin:0 0 21px"><strong>HOD feedback</strong>${txt(d.history?.at(-1)?.note||'Please review the document before resubmitting.')}</div><div class="field"><label class="form-label" for="revision-note">Summary of corrections *</label><textarea id="revision-note" required minlength="10" maxlength="900" class="review-textarea" placeholder="Describe the changes you made in the updated document..."></textarea></div><div class="field"><label class="form-label" for="revision-file">Revised attachment *</label><input id="revision-file" class="form-control" required type="file" accept=".pdf,.docx,.txt,.png,.jpg,.jpeg" aria-describedby="revision-hint"><p id="revision-hint" class="small muted" style="margin-top:9px">PDF, Word, JPG or PNG · Maximum 10 MB</p></div></div><div class="modal-actions"><button type="button" class="btn" data-action="close-modal">Cancel</button><button type="submit" class="btn btn-primary">${icon('upload','sm')} Resubmit to HOD</button></div></form></section></div>`;}

  function syncRuleForm() {
    const rows=[...document.querySelectorAll('#rule-form .rule-entry')];
    if(!rows.length)return;
    rulebook.rules=rows.map(row=>({id:row.querySelector('[name=rule_id]').value.trim(),title:row.querySelector('[name=title]').value.trim(),
      type:row.querySelector('[name=type]').value,required:row.querySelector('[name=required]').checked,
      value:row.querySelector('[name=value]').value.trim(),instructions:row.querySelector('[name=instructions]').value.trim()}));
  }
  function rulesHTML() {
    if(role!=='hod')return overviewHTML();
    const options=[['required_heading','Required heading'],['required_phrase','Required text'],['max_pages','Maximum pages'],['min_pages','Minimum pages'],['date_present','Date present'],['signature','Signature'],['formatting','Formatting'],['grammar','Grammar'],['semantic','Content relevance'],['other','College guideline']];
    return `${pageHeader('RULE GOVERNANCE','Department verification rules','Build your document checklist. Each save creates an immutable version, and each upload uses the active version.')}
    <div class="rules-layout"><section class="panel form-panel"><div class="rule-intro"><span class="version-chip">${icon('shield','sm')} Version ${rulebook.version||'—'}</span><span>${rulebook.rules.length} active requirements</span></div>
    <form id="rule-form">${rulebook.rules.map((r,i)=>`<div class="rule-entry" data-index="${i}"><div class="rule-title-row"><span class="rule-n">Rule ${i+1}</span><button type="button" class="btn btn-sm" data-action="remove-rule" data-index="${i}" aria-label="Remove rule ${i+1}">${icon('trash','sm')} Remove</button></div>
    <div class="field"><label class="field-label">Rule title *</label><input name="title" class="form-control" minlength="3" maxlength="110" value="${esc(r.title)}" placeholder="e.g. Signature of Department HOD" required /></div>
    <div class="form-grid"><div class="field"><label class="field-label">Validation type</label><select name="type" class="form-control">${options.map(([k,label])=>`<option value="${k}" ${r.type===k?'selected':''}>${label}</option>`).join('')}</select></div><div class="field"><label class="field-label">Expected value</label><input name="value" maxlength="400" class="form-control" placeholder="Heading, phrase or number" value="${esc(r.value||'')}"/></div></div>
    <div class="field"><label class="field-label">Guidelines for review</label><textarea name="instructions" class="form-control textarea" maxlength="1300" placeholder="Explain the college standard or what evidence is expected">${txt(r.instructions||'')}</textarea></div>
    <label class="rule-required"><input name="required" type="checkbox" ${r.required?'checked':''}/> Mandatory requirement</label><input type="hidden" name="rule_id" value="${esc(r.id)}" /></div>`).join('')||'<div class="empty-rules">No rules yet. Add your first rule to begin.</div>'}
    <div class="rule-form-actions"><button type="button" class="btn" data-action="add-rule">${icon('checkCircle','sm')} Add requirement</button><button type="submit" class="btn btn-primary">${icon('shield','sm')} Save new rule version</button></div></form></section>
    <aside class="panel info-panel"><h3>How verification works</h3><p>Measurable rules are checked deterministically. The configured AI provider reviews language, context and college guidelines, then suggests evidence-based corrections.</p>
    <div class="notice"><strong>${icon('info','sm')} Confidence first</strong> Uncertain findings are marked for manual HOD review instead of automatically rejecting faculty uploads.</div>
    <h3 style="margin-top:28px">Rule history</h3><div class="rule-history">${(rulebook.history||[]).map(h=>`<span>v${h.version} · ${prettyDate(h.created)}</span>`).join('')||'<span>Rule versions will appear after you save.</span>'}</div>
    <p class="small muted" style="margin-top:20px">Rule changes apply to future submissions; historical verification reports remain tied to their original version.</p></aside></div>`;
  }
  function integrationsHTML() {
    if(role!=='admin')return overviewHTML();
    const provider=integrations.provider || 'Not configured';
    const ready=Boolean(integrations.configured);
    const dedicated=Boolean(integrations.deepseek_configured);
    const fallback=Boolean(integrations.openrouter_configured);
    return `${pageHeader('SUPER ADMIN / INTEGRATIONS','DeepSeek AI settings','Connect DeepSeek to document review and task verification.')}
    <div class="manage-grid"><section class="panel form-panel">
    <div class="model-name">${icon('sparkle','lg')} <div><strong>DeepSeek AI document review</strong><span>Preferred provider · Direct DeepSeek</span></div></div>
    <div class="notice" role="status"><strong>${ready ? (dedicated?'DeepSeek configured':'Fallback provider configured') : 'AI provider not configured'}</strong>
      <p>Active provider: <b>${txt(provider)}</b>${integrations.model ? ' · '+txt(integrations.model) : ''}.
      ${ready?'Document verification will use the available provider.':'Without an available key, submissions require manual review.'}</p></div>
    <form id="integration-form" autocomplete="off">
      <div class="field"><label class="field-label" for="deepseek-key">DeepSeek API key</label>
      <input id="deepseek-key" type="password" name="api_key" class="form-control" minlength="15" maxlength="300" required autocomplete="new-password" placeholder="Paste your DeepSeek API key" /></div>
      <button class="btn btn-primary" type="submit">${icon('lock','sm')} Save DeepSeek key securely</button>
    </form>
    <p class="small muted" style="margin-top:15px">Saved keys are encrypted on the server. A configured key does not guarantee provider connectivity or available usage balance.</p>
    <details style="margin-top:20px"><summary class="field-label">Optional: OpenRouter fallback</summary>
      <p class="small muted">Used only when a dedicated DeepSeek key is unavailable. Existing OpenRouter configuration is retained.</p>
      <p class="small muted">Fallback: ${fallback?'Configured':'Not configured'}</p>
      <form id="fallback-form" autocomplete="off"><div class="field"><label class="field-label" for="fallback-key">OpenRouter fallback API key</label>
      <input id="fallback-key" type="password" name="api_key" class="form-control" minlength="15" maxlength="300" required autocomplete="new-password" placeholder="OpenRouter API key" /></div>
      <button class="btn btn-secondary" type="submit">Save fallback key</button></form>
    </details></section>
    <section class="panel info-panel"><h3>Privacy & verification</h3>
      <p>Document text and HOD rules are sent to the selected external AI provider only when configured. Obtain institutional authorization before processing sensitive records.</p>
      <div class="info-list"><div class="info-row"><span class="info-mark">${icon('shield')}</span><div><b>Server-side credentials</b><p>Only administrators can change integration credentials.</p></div></div>
      <div class="info-row"><span class="info-mark">${icon('file')}</span><div><b>Structured review</b><p>AI findings are validated. Failed or uncertain evaluations require human review.</p></div></div>
      <div class="info-row"><span class="info-mark">${icon('lock')}</span><div><b>Protected records</b><p>Private documents remain behind authenticated endpoints.</p></div></div></div>
    </section></div>`;
  }
  function reportHTML(){
    const v=verifyReport||{},r=v.report||{},rows=r.findings||[];
    return `<div class="modal-layer" data-action="close-modal-bg"><section class="modal verification-modal" role="dialog" aria-modal="true" aria-label="Document verification report" tabindex="-1">
      <div class="modal-top"><div><h2>Verification report</h2><p>${txt(v.document_id)} · Revision ${v.revision||1} · Rules v${v.policy_version||'—'}</p></div><button class="icon-button" data-action="close-modal" aria-label="Close report">${icon('close')}</button></div>
      <div class="modal-body"><div class="report-status">${statusHTML(r.status||v.status||'verifying')} <span class="small muted">${r.rule_count||0} rules · ${r.page_count||0} pages · ${r.ai_used?'AI analysis completed':'No AI response used'}</span></div>
      <p class="detail-text">${txt(r.summary||'The verification worker is still processing this file.')}</p>
      ${(r.notes||[]).length?`<div class="notice"><strong>Reviewer notes</strong>${r.notes.map(txt).join('; ')}</div>`:''}
      ${rows.map(item=>`<div class="finding"><div class="finding-top"><strong>${txt(item.title)}</strong><span class="finding-result ${item.result==='issue'?'issue':item.result==='pass'?'passed':'uncertain'}">${txt(item.result)}</span></div>
      <p class="small muted">${txt(item.location||'Location unspecified')} · ${txt(item.source)} · ${Math.round((item.confidence||0)*100)}% confidence</p>
      ${item.issue?`<p><strong>Issue:</strong> ${txt(item.issue)}</p>`:''}${item.evidence?`<p><strong>Evidence:</strong> ${txt(item.evidence)}</p>`:''}${item.correction?`<p class="correction"><strong>Suggested fix:</strong> ${txt(item.correction)}</p>`:''}</div>`).join('')||'<div class="empty-rules">Findings will appear here after verification finishes.</div>'}</div>
      <div class="modal-actions"><button class="btn btn-primary" data-action="close-modal">Close report</button></div></section></div>`;
  }

function cleanupHTML() {
  if(role!=='admin')return overviewHTML();
  const provider=aiOverview.provider || 'Not configured';
  const docCounts=aiOverview.document_statuses || {};
  const states=aiOverview.verification_states || {};
  return `${pageHeader('SUPER ADMINISTRATION','Database cleanup & AI overview','Preview the impact before changing data. Existing audit history is preserved.')}
    <section class="panel" aria-labelledby="ai-usage-heading">
      <div class="panel-header"><div><h3 class="panel-title" id="ai-usage-heading">AI verification operations</h3><p class="panel-subtitle">Live database counts · no document content exposed</p></div></div>
      <div class="metrics">${kpi('Active provider',aiOverview.provider_configured?'Connected':'Not configured',txt(provider),'sparkle','blue')}
      ${kpi('In verification',docCounts.verifying||0,'Queued or processing','clock','blue')}
      ${kpi('Manual review',docCounts.manual_review||0,'Needs human decision','shield','orange')}</div>
      <p class="small muted">Model: ${txt(aiOverview.model||'No active model')}. Verification jobs: ${Object.entries(states).map(([k,v])=>txt(k)+': '+v).join(', ')||'No jobs'}. AI never grants final approval.</p>
    </section>
    <div class="notice" role="note"><strong>Before changing production data:</strong> Check that you have a restorable database backup. Removing approved PDF records also removes their review revisions. Disabling users does not delete historical academic records.</div>
    <div class="cleanup-grid">${cleanupActions.map(action=>`
      <section class="cleanup-card"><h3>${txt(action.label)}</h3>
      <p>${txt(action.description)}</p>
      ${action.requires_backup?'<span class="cleanup-risk">Irreversible document deletion</span>':''}
      <div class="cleanup-footer"><span class="cleanup-count">${Number(action.count)||0} <small class="muted">affected</small></span>
      <button class="btn ${action.requires_backup?'btn-danger':'btn-secondary'}" data-action="cleanup-confirm" data-cleanup="${esc(action.id)}" ${!action.count?'disabled':''}>${icon(action.requires_backup?'trash':'shield','sm')} Review action</button></div></section>`).join('')||'<p>No cleanup actions are available.</p>'}</div>
    <p class="small muted">Public search results may retain cached student profiles after unpublishing. Request removal through Search Console when necessary.</p>`;
}
  function cleanupConfirmHTML() {
  const action=cleanupActions.find(x=>x.id===modal.action);
  if(!action)return '';
  return `<div class="modal-layer" data-action="close-modal-bg">
    <section class="modal cleanup-dialog" role="dialog" aria-modal="true" aria-labelledby="cleanup-dialog-heading" tabindex="-1">
    <div class="modal-top"><div><h2 id="cleanup-dialog-heading">Confirm database change</h2><p>${txt(action.label)}</p></div>
    <button type="button" class="icon-button" data-action="close-modal" aria-label="Close dialog">${icon('close')}</button></div>
    <form id="cleanup-confirm-form" data-cleanup="${esc(action.id)}">
      <div class="modal-body"><p>${txt(action.description)}</p>
      <p><strong>Preview: ${Number(action.count)||0} records will be affected.</strong></p>
      <p>Type the exact confirmation phrase:</p>
      <div class="cleanup-confirm-phrase">${txt(action.confirmation)}</div>
      <div class="field"><label class="field-label" for="cleanup-phrase">Confirmation phrase *</label>
      <input class="form-control" id="cleanup-phrase" name="confirmation" required autocomplete="off" spellcheck="false" /></div>
      ${action.requires_backup?`<label class="rule-required"><input type="checkbox" name="backup_confirmed" required /> I verified a recent recoverable offline backup of these records.</label>
      <div class="field"><label class="field-label" for="cleanup-admin-password">Current administrator password *</label>
      <input id="cleanup-admin-password" class="form-control" type="password" name="admin_password" autocomplete="current-password" required /></div>`:''}
      </div>
      <div class="modal-actions"><button type="button" class="btn" data-action="close-modal">Cancel</button>
      <button type="submit" class="btn ${action.requires_backup?'btn-danger':'btn-primary'}">Confirm ${Number(action.count)||0} affected records</button></div>
    </form></section></div>`;
}
  function usersHTML() {
    if(role!=='admin'&&role!=='hod') return overviewHTML();
    return `${pageHeader('ACCESS MANAGEMENT',role==='hod'?'Department staff':'Institutional accounts',role==='hod'?'Add faculty and manage access for your department.':'Manage institutional account access.')}
      <div class="manage-grid"><section class="panel form-panel"><h3 style="margin-bottom:20px">Create a new account</h3>
      <form id="create-user" autocomplete="off">
      <div class="field"><label class="field-label" for="acc-username">Username *</label><input class="form-control" id="acc-username" name="username" minlength="3" maxlength="80" required pattern="[a-zA-Z0-9._-]+" autocomplete="off" /></div>
      <div class="field"><label class="field-label" for="acc-name">Display name *</label><input class="form-control" id="acc-name" name="display_name" minlength="3" required/></div>
      <div class="field"><label class="field-label" for="acc-role">Assigned role *</label>${role==='hod'?`<input type="hidden" name="role" value="staff"/><input class="form-control" id="acc-role" value="Faculty & Staff" readonly aria-label="Assigned role"/>`:`<select class="form-control" id="acc-role" name="role">${Object.entries(ROLES).map(([k,v])=>`<option value="${k}">${txt(v.title)}</option>`).join('')}</select>`}</div>
      <div class="field"><label class="field-label" for="acc-dept">Department *</label>${role==='hod'?`<input type="hidden" name="department" value="${txt(user?.department)}"/><input class="form-control" id="acc-dept" value="${txt(user?.department)}" readonly aria-label="Department"/>`:`<select class="form-control" id="acc-dept" name="department" required><option value="">Choose an active department</option>${departments().map(d=>`<option value="${txt(d.name)}">${txt(d.name)}</option>`).join('')}</select>${departments().length?'':'<p class="small muted">No active departments are configured. Add one in Academic Departments before creating accounts.</p>'}`}</div>
      <div class="field"><label class="field-label" for="acc-password">Temporary password *</label><input class="form-control" id="acc-password" name="password" type="password" minlength="12" maxlength="128" required autocomplete="new-password" placeholder="At least 12 characters"/></div>
      <button type="submit" class="btn btn-primary">${icon('users','sm')} Create account</button></form></section>
      <section class="panel"><div class="panel-header"><div><h3 class="panel-title">Provisioned accounts</h3><p class="panel-subtitle">Enable, disable and manage user access</p></div></div>
      ${accounts.map(u=>`<div class="user-item"><span class="avatar">${initials(u.name)}</span><div class="user-details"><strong>${txt(u.name)}</strong><small>${txt(u.username)} · ${txt(u.role.toUpperCase())} · ${txt(u.department)} · ${u.active?'Active':'Disabled'}</small></div>
      ${u.id!==user?.id?`<div class="user-actions"><button class="btn btn-sm" data-action="reset-password" data-id="${u.id}">${icon('lock','sm')} Reset password</button><button class="btn btn-sm" data-action="toggle-user" data-id="${u.id}" data-active="${u.active}">${u.active?'Disable':'Enable'}</button></div>`:''}</div>`).join('')||emptyHTML('No accounts','Create the first institution account.')}
      </section></div>`;
  }
  const departments=()=>academicDepartments.filter(d=>d.active);
  function accountHTML() {return `${pageHeader('PERSONAL SECURITY','My account','Review your role and update your sign-in password.')}
      <div class="manage-grid"><section class="panel form-panel"><h3 style="margin-bottom:19px">Account information</h3><div class="detail-grid">
      ${[['Name',user?.name],['Username',user?.username],['Role',user?.role?.toUpperCase()],['Department',user?.department]].map(([k,v])=>`<div><div class="detail-label">${k}</div><div class="detail-value">${txt(v)}</div></div>`).join('')}</div></section>
      <section class="panel form-panel"><h3 style="margin-bottom:20px">Change password</h3><form id="password-form">
      <div class="field"><label class="field-label" for="old-pass">Current password</label><input class="form-control" id="old-pass" type="password" required name="old_password" autocomplete="current-password"/></div>
      <div class="field"><label class="field-label" for="new-pass">New password (12+ characters)</label><input class="form-control" id="new-pass" type="password" minlength="12" maxlength="128" required name="new_password" autocomplete="new-password"/></div>
      <button class="btn btn-primary" type="submit">${icon('lock','sm')} Update password</button></form></section></div>`;}
  function auditHTML(){if(role!=='admin') return overviewHTML();return `${pageHeader('ACCESS & COMPLIANCE','Security audit','Recent account activity and permissioned document events.')}
    <div class="panel">${auditEntries.length?auditEntries.map(a=>`<div class="user-item"><span class="info-mark">${icon('shield','sm')}</span><div class="user-details"><strong>${txt(a.event)}</strong><small>${txt(a.actor)} · ${txt(a.detail)} · ${prettyTime(a.at)}</small></div></div>`).join(''):emptyHTML('No audit events','Account and document activity will appear here.')}</div>`;}
  function resetPasswordHTML(id) {
    const target=accounts.find(a=>a.id===Number(id));if(!target)return '';
    return `<div class="modal-layer" data-action="close-modal-bg"><section class="modal" role="dialog" aria-modal="true"><div class="modal-top"><div><h2>Reset account password</h2><p>${txt(target.name)} · ${txt(target.username)}</p></div><button class="icon-button" data-action="close-modal" aria-label="Close">${icon('close')}</button></div>
      <form id="reset-user-password" data-id="${target.id}"><div class="modal-body"><div class="notice"><strong>${icon('shield','sm')} Account security</strong> Setting a new password immediately signs out the user's other sessions. Give the new credential to the user through an approved private channel.</div>
      <div class="field" style="margin-top:20px"><label class="form-label" for="new-user-password">New password (12+ characters) *</label><input id="new-user-password" class="form-control" type="password" required minlength="12" maxlength="128" autocomplete="new-password"/></div></div>
      <div class="modal-actions"><button type="button" class="btn" data-action="close-modal">Cancel</button><button class="btn btn-primary" type="submit">${icon('lock','sm')} Save new password</button></div></form></section></div>`;
  }
  function render() {
    const focus=document.activeElement;
    const inSearch=focus?.id==='search-docs';const pos=inSearch?focus.selectionStart:null;
    if(!role){app.innerHTML=loginHTML();return;}
    const body={overview:overviewHTML,documents:documentsHTML,upload:uploadHTML,activity:activityHTML,insights:insightsHTML,guide:guideHTML,users:usersHTML,cleanup:cleanupHTML,audit:auditHTML,account:accountHTML,rules:rulesHTML,integrations:integrationsHTML};
    app.innerHTML=`<div class="app-shell">${sidebarHTML()}<div class="mobile-scrim ${mobileOpen?'open':''}" data-action="close-menu"></div><main class="main">${headerHTML()}<div class="content">${(body[page]||overviewHTML)()}<footer class="footer"><span><img src="/static/ngi-brand.svg" alt="Nagarjuna Group" class="footer-ngi"/> © ${new Date().getFullYear()} Nagarjuna College of Engineering and Technology</span><span><a href="https://ncet.co.in/" target="_blank" rel="noopener noreferrer">College website</a> · Authorized access only · <a href="/students">Students</a> · <a href="/community">Project community</a> · <a href="https://www.linkedin.com/in/bhargava-r-a08b8182/" target="_blank" rel="noopener noreferrer">HOD Bhargava</a> · <a href="https://www.linkedin.com/in/dr-thippeswamy-gangappa-686b3822/" target="_blank" rel="noopener noreferrer">Principal</a> · <a href="https://www.linkedin.com/in/paladuguganeshnaidu/" target="_blank" rel="noopener noreferrer">Developer</a></span></footer></div></main></div>${modal ? (modal.type==='report'?reportHTML():modal.type==='detail'?detailHTML(docs.find(d=>d.id===modal.id)||{}):modal.type==='review'?reviewHTML(modal.id,modal.decision):modal.type==='resubmit'?revisionHTML(docs.find(d=>d.id===modal.id)||{}):modal.type==='resetpwd'?resetPasswordHTML(modal.id):modal.type==='cleanup'?cleanupConfirmHTML():''):''}`;
    if(inSearch){const el=document.getElementById('search-docs');if(el){el.focus();if(pos!==null) el.setSelectionRange(pos,pos);}}
    if(modal) app.querySelector('.modal')?.focus?.();
  }
  function notify(message,type='success') {
    let host=document.querySelector('.toast-container');if(!host){host=document.createElement('div');host.className='toast-container';document.body.appendChild(host);}
    host.innerHTML=`<div class="toast ${type==='error'?'error':''}" role="status">${icon(type==='error'?'info':'checkCircle')} ${txt(message)}</div>`;
    clearTimeout(toastTimer);toastTimer=setTimeout(()=>host.remove(),4300);
  }
  function celebrate(title, subtitle, status='approved') {
    const node=document.createElement('div');node.className='success-screen';node.innerHTML=`<div class="success-content"><span class="circle" style="${status==='rejected'?'background:#fef0e7;color:#b96843':''}">${icon(status==='rejected'?'rotate':'check','xl')}</span><strong>${txt(title)}</strong><span>${txt(subtitle)}</span></div>`;document.body.append(node);setTimeout(()=>node.remove(),1600);
  }
  function renderWithDraft(){const values=[...document.querySelectorAll('#submit-document [name]')].filter(x=>x.name!=='file').map(x=>[x.name,x.value]);render();for(const [name,value] of values){const el=document.querySelector(`#submit-document [name="${name}"]`);if(el)el.value=value;}}
  function chooseFile(file){if(!file)return;const valid=/\.(pdf|docx|txt|jpe?g|png)$/i.test(file.name);if(!valid)return notify('Unsupported file type. Select PDF, DOCX, TXT, JPG or PNG.','error');if(file.size>10*1024*1024)return notify('File is larger than the 10 MB limit.','error');if(!file.size)return notify('The selected file is empty.','error');pickedFile=file;renderWithDraft();}
  async function downloadDoc(id) {
    try {
      const item=docs.find(x=>x.id===id);
      if(!item||!item.hasLocalFile) throw Error('Attachment not available.');
      const response=await fetch(`/api/documents/${encodeURIComponent(id)}/file`,{credentials:'same-origin'});
      if(!response.ok) throw Error('The server denied this download.');
      const blob=await response.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');
      a.href=url;a.download=item.fileName;a.click();setTimeout(()=>URL.revokeObjectURL(url),15000);
    }catch(e){notify(e.message||'Document unavailable.','error');}
  }
  function exportCsv() {const records=available();const headings=['ID','Title','Category','Department','Academic Year','Status','Submitted Date','Submitted By','Last Reviewer Note'];const wrap=v=>`"${String(v??'').replace(/^[=+\-@\t\r]/,'\u0027$&').replace(/"/g,'""')}"`;const rows=records.map(d=>[d.id,d.title,d.category,d.department,d.year,d.status,prettyDate(d.submitted),d.author,d.history?.at(-1)?.note||'']);const csv='\uFEFF'+[headings,...rows].map(r=>r.map(wrap).join(',')).join('\r\n');const obj=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=obj;a.download=`ncms-verifyflow-${role}-${new Date().toISOString().slice(0,10)}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(obj),1000);notify('CSV report exported.');}
  document.addEventListener('click',async e=>{
    const t=e.target.closest('[data-action],[data-page],[data-open],[data-filter]');if(!t)return;
    if(t.hasAttribute('data-page')){page=t.dataset.page;filter='all';query='';mobileOpen=false;modal=null;try{if(page==='users'&&(role==='admin'||role==='hod')){accounts=(await api('/api/users')).items;if(role==='admin')academicDepartments=(await api('/api/academic/departments')).items;}if(page==='audit'&&role==='admin')auditEntries=(await api('/api/audit')).items;if(page==='rules'&&role==='hod')rulebook=await api('/api/rules');if(page==='integrations'&&role==='admin')integrations=await api('/api/admin/integrations');if(page==='cleanup'&&role==='admin'){const values=await Promise.all([api('/api/admin/cleanup/preview'),api('/api/admin/ai/overview')]);cleanupActions=values[0].actions;aiOverview=values[1];}}catch(err){notify(err.message,'error');}render();window.scrollTo(0,0);return;}
    if(t.hasAttribute('data-open')){const d=docs.find(x=>x.id===t.dataset.open);if(d&&canSee(d)){modal={type:'detail',id:d.id};render();}return;}
    if(t.hasAttribute('data-filter')){filter=t.dataset.filter;document.querySelectorAll('[data-filter]').forEach(x=>x.classList.toggle('active',x.dataset.filter===filter));const pane=document.getElementById('docs-results');if(pane)pane.innerHTML=tableHTML();return;}
    const a=t.dataset.action;
    if(a==='cleanup-confirm'&&role==='admin'){const item=cleanupActions.find(x=>x.id===t.dataset.cleanup);if(!item)return;modal={type:'cleanup',action:item.id};render();return;}
    if(a==='pick-role'){selectedRole=t.dataset.role;authError='';render();return;}
    if(a==='toggle-password'){const user=document.getElementById('login-user')?.value;const pass=document.getElementById('login-pass')?.value;showPassword=!showPassword;render();document.getElementById('login-user').value=user||'';document.getElementById('login-pass').value=pass||'';return;}
    if(a==='logout'){try{await api('/api/auth/logout',{method:'POST'});}catch(_){}role=null;user=null;csrf='';docs=[];page='overview';modal=null;pickedFile=null;render();return;}
    if(a==='menu'||a==='close-menu'){mobileOpen=(a==='menu');render();return;}
    if(a==='close-modal'){modal=null;render();return;}
    if(a==='close-modal-bg'&&e.target===t){modal=null;render();return;}
    if(a==='review'){if(role!=='hod'||!docs.some(x=>x.id===t.dataset.id&&['pending','manual_review'].includes(x.status)))return;modal={type:'review',id:t.dataset.id,decision:t.dataset.decision};render();return;}
    if(a==='resubmit'){if(role!=='staff')return;const item=docs.find(d=>d.id===t.dataset.id);if(!item||!['rejected','needs_correction'].includes(item.status))return;modal={type:'resubmit',id:item.id};render();return;}
    if(a==='remove-file'){e.stopPropagation();pickedFile=null;renderWithDraft();return;}
    if(a==='export'){exportCsv();return;}
    if(a==='reset-password'&&(role==='admin'||role==='hod')){modal={type:'resetpwd',id:Number(t.dataset.id)};render();return;}
    if(a==='toggle-user'){
      if(role!=='admin'&&role!=='hod')return;
      const desired=t.dataset.active!=='true';
      if(!confirm(`${desired?'Enable':'Disable'} this account?`)) return;
      try{await api(`/api/users/${Number(t.dataset.id)}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({active:desired})});
        accounts=(await api('/api/users')).items;render();notify('Account access updated.');}
      catch(err){notify(err.message,'error');}
      return;
    }
    if(a==='download'){await downloadDoc(t.dataset.id);return;}
    if(a==='verification'){try{verifyReport=await api(`/api/documents/${encodeURIComponent(t.dataset.id)}/verification`);modal={type:'report'};render();}catch(err){notify(err.message,'error');}return;}
    if(a==='add-rule'&&role==='hod'){syncRuleForm();rulebook.rules.push({id:'rule_'+Date.now().toString(36),title:'',type:'required_heading',required:true,value:'',instructions:''});render();return;}
    if(a==='remove-rule'&&role==='hod'){syncRuleForm();rulebook.rules.splice(Number(t.dataset.index),1);render();return;}
    if(a==='clear-form'){pickedFile=null;setTimeout(render,0);return;}
  });
  document.addEventListener('submit',async e=>{
    if(e.target.id==='cleanup-confirm-form'){
      e.preventDefault();if(role!=='admin')return;
      const item=cleanupActions.find(x=>x.id===e.target.dataset.cleanup);
      if(!item)return notify('Refresh the cleanup preview first.','error');
      const fields=new FormData(e.target);
      const button=e.target.querySelector('[type=submit]');
      button.disabled=true;button.setAttribute('aria-busy','true');
      try{
        const result=await api('/api/admin/cleanup/execute',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
          action:item.id,confirmation:String(fields.get('confirmation')||''),
          expected_count:item.count,backup_confirmed:fields.get('backup_confirmed')==='on',admin_password:String(fields.get('admin_password')||'')
        })});
        const values=await Promise.all([api('/api/admin/cleanup/preview'),api('/api/admin/ai/overview')]);
        cleanupActions=values[0].actions;aiOverview=values[1];modal=null;render();
        notify('Action completed. '+result.affected+' records affected.'+(result.storage_cleanup_failures?' Some files need storage cleanup.':''));
      }catch(err){button.disabled=false;button.removeAttribute('aria-busy');notify(err.message,'error');}
      return;
    }
    if(e.target.id==='rule-form'){e.preventDefault();if(role!=='hod')return;syncRuleForm();try{const result=await api('/api/rules',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({rules:rulebook.rules})});rulebook=await api('/api/rules');render();notify(`Rules saved as version ${result.version}.`);}catch(err){notify(err.message,'error');}return;}
    if(e.target.id==='integration-form'||e.target.id==='fallback-form'){e.preventDefault();if(role!=='admin')return;const fallback=e.target.id==='fallback-form';const val=e.target.querySelector('[name=api_key]').value.trim();try{await api(fallback?'/api/admin/integrations/openrouter':'/api/tasks/ai/key',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_key:val})});integrations=await api('/api/admin/integrations');render();notify(fallback?'Fallback key encrypted and saved.':'DeepSeek key encrypted and saved. Provider connectivity must be tested with a document review.');}catch(err){notify(err.message,'error');}return;}
    if(e.target.id==='login-form'){
      e.preventDefault();const data=new FormData(e.target);
      try{const auth=await api('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:String(data.get('username')||'').trim().toLowerCase(),password:String(data.get('password')||''),role:null})});
        user=auth.user;role=user.role;csrf=auth.csrf;authError='';page='overview';await refreshDocs();notify(`Welcome, ${currentRole().name}.`);}
      catch(err){authError=err.message;const attempted=String(data.get('username')||'').trim();render();const usernameField=document.getElementById('login-user');if(usernameField){usernameField.value=attempted;document.getElementById('login-pass')?.focus();}}return;
    }
    if(e.target.id==='submit-document'){
      e.preventDefault();if(role!=='staff')return;
      const form=e.target, title=String(form.elements.namedItem('title')?.value||'').trim(),
            description=String(form.elements.namedItem('description')?.value||'').trim(),
            category=String(form.elements.namedItem('category')?.value||'').trim(),
            year=String(form.elements.namedItem('year')?.value||'').trim();
      const fail=(field,message)=>{
        form.querySelectorAll('.field-error').forEach(el=>el.remove());
        form.querySelectorAll('[aria-invalid]').forEach(el=>el.removeAttribute('aria-invalid'));
        const input=field?form.elements.namedItem(field):null;
        if(input){input.setAttribute('aria-invalid','true');input.closest('.field')?.insertAdjacentHTML('beforeend','<p class="field-error" role="alert">'+txt(message)+'</p>');input.focus();}
        else document.getElementById('upload-zone')?.focus();
        notify(message,'error');
      };
      if(title.length<5)return fail('title','Document title must contain at least 5 characters.');
      if(title.length>140)return fail('title','Document title cannot exceed 140 characters.');
      if(!category||category.length<3||category.length>100)return fail('category','Select a document category.');
      if(!/^20\d{2}[-–]\d{2,4}$/.test(year))return fail('year','Select a valid academic year.');
      if(description.length<10)return fail('description','Description must contain at least 10 characters.');
      if(description.length>2000)return fail('description','Description cannot exceed 2,000 characters.');
      if(!pickedFile)return fail(null,'Attach a document before submitting.');
      const button=form.querySelector('button[type=submit]');button.disabled=true;button.setAttribute('aria-busy','true');
      const data=new FormData(form);data.set('file',pickedFile);
      try{await api('/api/documents',{method:'POST',body:data});pickedFile=null;page='documents';filter='verifying';modal=null;
        await refreshDocs();celebrate('Document received','Your document has been queued for verification.');notify('Verification queued. See status in My documents.');}
      catch(err){notify(err.message,'error');button.disabled=false;button.removeAttribute('aria-busy');}return;
    }
    if(e.target.id==='revision-form'){
      e.preventDefault();if(role!=='staff')return;
      const form=e.target,id=form.dataset.id,file=form.querySelector('#revision-file').files[0],note=form.querySelector('#revision-note').value.trim();
      if(!file||!note)return notify('A corrected file and note are required.','error');
      const data=new FormData();data.set('file',file);data.set('note',note);
      try{await api(`/api/documents/${encodeURIComponent(id)}/resubmit`,{method:'POST',body:data});modal=null;await refreshDocs();
        celebrate('Revision received','The corrected file is being verified again.');notify('Updated attachment queued for re-verification.');}
      catch(err){notify(err.message,'error');}return;
    }
    if(e.target.id==='review-form'){
      e.preventDefault();if(role!=='hod')return;
      const form=e.target,id=form.dataset.id,decision=form.dataset.decision,note=form.querySelector('#review-note').value.trim();
      try{await api(`/api/documents/${encodeURIComponent(id)}/review`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({decision,note})});
        modal=null;await refreshDocs();celebrate(decision==='approved'?'Document approved':'Revision requested',decision==='approved'?'Now visible to Principal and IQAC.':'The staff member can review your feedback.',decision);
        notify(decision==='approved'?'Document approved.':'Document returned with feedback.');}
      catch(err){notify(err.message,'error');}return;
    }
    if(e.target.id==='create-user'){
      e.preventDefault();if(role!=='admin'&&role!=='hod')return;
      const data=Object.fromEntries(new FormData(e.target).entries());
      try{await api('/api/users',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
        accounts=(await api('/api/users')).items;render();notify('Institutional user created.');}
      catch(err){notify(err.message,'error');}return;
    }
    if(e.target.id==='reset-user-password'){
      e.preventDefault();if(role!=='admin'&&role!=='hod')return;
      const id=Number(e.target.dataset.id),password=e.target.querySelector('#new-user-password').value;
      try{await api(`/api/users/${id}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({password})});
        modal=null;render();notify('Password reset. Previous sessions have been revoked.');}
      catch(err){notify(err.message,'error');}
      return;
    }
    if(e.target.id==='password-form'){
      e.preventDefault();const data=Object.fromEntries(new FormData(e.target).entries());
      try{await api('/api/auth/change-password',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
        e.target.reset();notify('Password changed. Other active sessions are revoked.');}
      catch(err){notify(err.message,'error');}return;
    }
  });
  document.addEventListener('input',e=>{if(e.target.id==='search-docs'){query=e.target.value;const results=document.getElementById('docs-results');if(results) results.innerHTML=tableHTML();}});
  document.addEventListener('change',e=>{if(e.target.id==='file-input')chooseFile(e.target.files?.[0]);});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&modal){modal=null;render();return;}if((e.key==='Enter'||e.key===' ')&&e.target.id==='upload-zone'){e.preventDefault();document.getElementById('file-input')?.click();}});
  document.addEventListener('click',e=>{if(e.target.closest('#upload-zone')&&!e.target.closest('[data-action]'))document.getElementById('file-input')?.click();});
  document.addEventListener('dragover',e=>{if(e.target.closest('#upload-zone')){e.preventDefault();document.getElementById('upload-zone')?.classList.add('dragging');}});
  document.addEventListener('dragleave',e=>{if(e.target.closest('#upload-zone'))document.getElementById('upload-zone')?.classList.remove('dragging');});
  document.addEventListener('drop',e=>{if(e.target.closest('#upload-zone')){e.preventDefault();document.getElementById('upload-zone')?.classList.remove('dragging');chooseFile(e.dataTransfer.files[0]);}});
  let lastPoll=0;setInterval(async()=>{if(document.hidden||!role||role==='admin'||!docs.some(d=>d.status==='verifying')||Date.now()-lastPoll<7000)return;lastPoll=Date.now();try{await refreshDocs();}catch(_){ }},8000);
  document.addEventListener('visibilitychange',async()=>{if(!document.hidden && role){try{await refreshDocs();}catch(_){/* keep current read-only screen until next action */}}});
  start();
})();
