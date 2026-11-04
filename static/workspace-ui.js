/* Progressive workspace organization. Server roles and existing handlers stay authoritative. */
(() => {
  'use strict';
  const dashboard = document.getElementById('hod-dashboard');
  if (!dashboard) return;
  const app = document.getElementById('app');
  const assignment = document.getElementById('hod-section');
  const queue = document.getElementById('queue-title').closest('section');
  const activity = document.getElementById('notifications-box').parentElement;
  queue.classList.add('task-work-panel');
  const nav = document.createElement('div');
  nav.className = 'workspace-views'; nav.setAttribute('role','tablist'); nav.setAttribute('aria-label','Task workspace sections');
  const definitions = [['overview','Overview',[dashboard]],['assign','Assign work',[assignment]],['review','Review tasks',[queue]],['activity','Activity & insights',[activity]]];
  let current = '';
  function available() { return definitions.filter(([key]) => !['overview','assign'].includes(key) || !assignment.hidden); }
  function select(key, focus = false) {
    current = key;
    const active = definitions.find(item => item[0] === key);
    for (const section of [dashboard,assignment,queue,activity]) section.classList.toggle('view-hidden', !active[2].includes(section));
    nav.querySelectorAll('button').forEach(button => {
      const chosen = button.dataset.view === key;
      button.setAttribute('aria-selected',String(chosen)); button.tabIndex = chosen ? 0 : -1;
      if (focus && chosen) button.focus();
    });
    active[2].forEach(section => { section.classList.remove('workspace-view-enter'); requestAnimationFrame(() => section.classList.add('workspace-view-enter')); });
  }
  function setup() {
    if (app.hidden) return;
    const views = available();
    const signature = views.map(v=>v[0]).join(',');
    if (nav.dataset.views === signature) return;
    nav.dataset.views = signature;
    nav.replaceChildren(...views.map(([key,label]) => {
      const button = document.createElement('button'); button.type='button'; button.dataset.view=key; button.id='workspace-view-'+key;
      button.setAttribute('role','tab'); button.textContent=label;button.setAttribute('aria-controls',definitions.find(item=>item[0]===key)[2].map((section,index)=>{if(!section.id)section.id='workspace-panel-'+key+'-'+index;return section.id}).join(' '));
      button.addEventListener('click',()=>select(key));
      return button;
    }));
    app.prepend(nav);
    select(views.some(v=>v[0]===current) ? current : views[0][0]);
  }
  nav.addEventListener('keydown',event=>{
    const buttons=[...nav.querySelectorAll('button')], index=buttons.indexOf(document.activeElement);
    if(index<0)return;
    const next=event.key==='ArrowRight'?(index+1)%buttons.length:event.key==='ArrowLeft'?(index+buttons.length-1)%buttons.length:event.key==='Home'?0:event.key==='End'?buttons.length-1:-1;
    if(next<0)return;event.preventDefault();select(buttons[next].dataset.view,true);
  });
  new MutationObserver(setup).observe(app,{attributes:true,subtree:true,attributeFilter:['hidden']});
  setup();
})();
