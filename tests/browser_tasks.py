"""Real Chromium screens, mock API transport; separate backend integration tests assert RBAC."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_runtime import launch_chromium
BASE=Path(__file__).resolve().parents[1]/'static'

def test_browser():
  with sync_playwright() as pw:
    browser=launch_chromium(pw,headless=True)
    for role in ('hod','staff','principal','iqac','admin'):
      page=browser.new_page(viewport={'width':390 if role=='staff' else 1366,'height':840})
      errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
      html=(BASE/'tasks.html').read_text(encoding='utf-8').replace('<link rel="stylesheet" href="/static/tasks.css?v=20261021-per-file-checklists">','<style>'+ (BASE/'tasks.css').read_text(encoding='utf-8')+'</style>')
      html=html.replace('<script src="/static/tasks.js" defer></script>','')
      html=html.replace('<script src="/static/hod-dashboard.js?v=20261017f" defer></script>','')
      html=html.replace('<link rel="stylesheet" href="/static/hod-dashboard.css?v=20261017f">',
        '<style>'+ (BASE/'hod-dashboard.css').read_text(encoding='utf-8')+'</style>')
      page.set_content(html)
      page.evaluate("""(role)=>{window.fetch=async(url,opts)=>{
        const u=String(url);let data={};
        if(u.includes('/auth/me'))data={user:{id:1,name:'Faculty Example',role,department:'Computer Applications'},csrf:'demo-token'};
        else if(u.endsWith('/tasks')){const task=id=>({id,batch_id:1,file:id===1?'Academic_Audit.pdf':'Course_Outcomes.pdf',state:role==='hod'&&!window.__assigned?'unassigned':window.__taskState||'assigned',department:'Computer Applications',assigned_to:'Faculty Example',assigned_staff_id:5,deadline:window.__changedDeadline||window.__assigned?.deadline||null,overdue:false,score:null,report:{},notes:'Please follow requirements',rules:[]});data={items:window.__multi?[task(1),task(2)]:[task(1)]};}
        else if(u.includes('/tasks/dashboard')){
          const assigned=Boolean(window.__assigned);
          const eventTime='2026-10-17T10:00:00+00:00';
          const history=assigned?[{event:'assigned',at:eventTime,actor:'NCET hod',detail:'Assigned to Faculty Example',state:'assigned'}]:[];
          data={counts:{total:1,working:assigned?1:0,reviewing:0,approved:0,overdue:0,unassigned:assigned?0:1},
            as_of:eventTime,daily_approvals:[],task_list_truncated:false,task_list_offset:0,task_list_total:1,
            staff:assigned?[{id:5,name:'Faculty Example',total:1,working:1,reviewing:0,approved:0,overdue:0}]:[],
            activity:assigned?[{...history[0],task_id:1,file:'Academic_Audit.pdf',staff:'Faculty Example'}]:[],
            tasks:[{id:1,file:'Academic_Audit.pdf',staff:assigned?'Faculty Example':null,
              staff_id:assigned?5:null,state:assigned?'assigned':'unassigned',score:null,
              submitted_at:null,approved_at:null,deadline:window.__assigned?.deadline||null,
              updated_at:eventTime,overdue:false,history}]};
          const query=new URL(u,'https://ncet.test').searchParams;
          if(query.get('search') && !'academic_audit.pdf faculty example'.includes(query.get('search').toLowerCase())){data.tasks=[];data.task_list_total=0;}
          if(query.get('status')==='working'&&!assigned){data.tasks=[];data.task_list_total=0;}
        }
        else if(u.endsWith('/staff'))data={items:[{id:5,name:'Faculty Example',username:'faculty',department:'Computer Applications'}]};
        else if(u.includes('/notifications/inbox'))data={unread:1,items:[{id:10,text:'Academic audit assigned',at:'2026-10-16T10:00:00Z',seen:false}]};
        else if(u.includes('/insights/summary'))data={staff:[],total:1,states:{assigned:1}};
        else if(u.includes('/insights/discussions'))data={items:[]};
        else if(u.includes('/ai/status'))data={configured:false,model:null};
        else if(u.endsWith('/tasks/rules/drafts'))data={items:[{task_id:1,state:'ready',summary:'Rules extracted from the uploaded PDF',model:'deepseek-chat',rules:[{id:'reference_1',title:'Introduction',type:'required_heading',required:true,value:'Introduction',instructions:'Use the introduction heading'}]}]};
        else if(u.endsWith('/tasks/assign')){window.__assigned=JSON.parse(opts.body);data={assigned:window.__assigned.task_ids.length};}
        else if(u.includes('/deadline')){window.__changedDeadline=JSON.parse(opts.body).deadline;data={changed:true,deadline:window.__changedDeadline};}
        else if(u.includes('/tasks/1/decide')){window.__decision=JSON.parse(opts.body);data={state:window.__decision.decision==='approved'?'approved':'correction_required'};}
        else data={ok:true,assigned:1};
        return {ok:true,json:async()=>data,status:200};
      }}""",role)
      page.add_script_tag(content=(BASE/'hod-dashboard.js').read_text(encoding='utf-8'))
      page.add_script_tag(content=(BASE/'tasks.js').read_text(encoding='utf-8'))
      page.locator('#tasks strong[title="Academic_Audit.pdf"]').wait_for()
      assert page.get_by_text('Academic audit assigned').count()==1
      if role=='hod':
        assert page.locator('#hod-section').is_visible()
        assert page.locator('#hod-dashboard').is_visible()
        page.locator('#dashboard-metrics [data-dash-status="all"] strong').wait_for()
        assert page.locator('#dashboard-metrics [data-dash-status="all"] strong').inner_text()=='1'
        assert page.locator('#dashboard-metrics [data-dash-status="approved"] strong').inner_text()=='0'
        assert page.locator('#dash-stage-chart .stage-ring').is_visible()
        assert page.locator('#dash-trend-chart .daily-column').count()==14
        page.locator('[data-select="1"]').check()
        assert '1 unassigned PDFs selected' in page.locator('#selected-ids').inner_text()
        assert page.locator('#rules-mode').input_value()=='manual'
        assert page.locator('#manual-rules').is_visible()
        page.locator('.manual-rule input[type="text"]').first.fill('Include approval block')
        page.locator('.manual-rule input[type="text"]').nth(1).fill('Approved by department head')
        assert page.locator('#rules').count()==0, 'Legacy line-by-line rule parser must be removed'
        page.locator('#staff-id').select_option('5')
        page.locator('#notes').fill('Complete the academic document following the reference PDF.')
        assert page.locator('#assignment-deadline[type="datetime-local"]').is_visible()
        date_value=page.evaluate("""() => {
          const d=new Date(Date.now()+3*86400000);
          const pad=n=>String(n).padStart(2,'0');
          return d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate())+'T'+pad(d.getHours())+':'+pad(d.getMinutes());
        }""")
        page.locator('#assignment-deadline').fill(date_value)
        page.locator('#assign-form button[type=submit]').click()
        page.wait_for_function('window.__assigned && window.__assigned.use_generated_rules===false')
        data=page.evaluate('window.__assigned')
        assert data['confirmed_task_ids']==[]
        assert data['task_ids']==[1]
        expected_deadline=page.evaluate('(value)=>new Date(value).toISOString()',date_value)
        assert data['deadline']==expected_deadline
        assert data['rules'][0]['title']=='Include approval block'
        assert data['rules'][0]['value']=='Approved by department head'
        page.locator('button[data-op="deadline"]').wait_for(state='visible')
        page.locator('button[data-op="deadline"]').click()
        assert page.locator('#deadline-dialog').is_visible()
        page.locator('#edit-deadline').fill(date_value)
        page.locator('#deadline-form button[type=submit]').click()
        page.wait_for_function('window.__changedDeadline !== undefined')
        assert page.locator('#deadline-dialog').is_hidden()
        page.locator('#dashboard-metrics [data-dash-status="working"] strong').wait_for()
        page.locator('#dashboard-metrics [data-dash-status="working"]').click()
        assert page.locator('#dash-tasks .dashboard-task').count()==1
        page.locator('#dash-tasks .dashboard-task summary').click()
        assert page.locator('.dash-history').is_visible()
        assert 'NCET hod' in page.locator('.dash-history').inner_text()
        page.locator('#dash-search').fill('not-found-file')
        page.locator('#dash-tasks .dashboard-empty').wait_for()
        page.locator('#dash-search').fill('Academic_Audit')
        page.locator('.dashboard-task').first.wait_for()
        assert page.locator('#dash-deadline').is_visible()
        assert page.locator('#dash-sort').is_visible()
        page.locator('#dash-deadline').select_option('due_set')
        page.locator('#dash-sort').select_option('due_soon')
        page.locator('#dash-from').fill('2026-10-01')
        page.locator('#dash-reset').click()
        assert page.locator('#dash-deadline').input_value()=='all'
        assert page.locator('#dash-from').input_value()==''
        assert page.locator('#dash-search').input_value()==''
        assert page.locator('#dash-sort').input_value()=='updated'
        assert page.locator('.dashboard-task').count()==1
        # Responsive HOD dashboard checks: metric grid, charts and task drilldown.
        for width in (320,390,768,1024,1366):
          page.set_viewport_size({'width':width,'height':850})
          assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2'),(width,page.evaluate("[...document.querySelectorAll('body *')].map(e=>({tag:e.tagName,id:e.id,cls:String(e.className||''),right:Math.round(e.getBoundingClientRect().right),width:Math.round(e.getBoundingClientRect().width),display:getComputedStyle(e).display})).filter(x=>x.right>innerWidth+2&&x.display!=='none').slice(0,12)"))
          assert page.locator('#dashboard-metrics [data-dash-status="all"]').is_visible(),width
          assert page.locator('#dash-stage-chart').is_visible(),width
        page.set_viewport_size({'width':1366,'height':840})
        # Exercise the no-AI checklist path through the actual HOD form and request payload.
        page.evaluate('window.__assigned=null;window.__changedDeadline=null')
        page.locator('#refresh').click()
        page.locator('[data-select="1"]').wait_for()
        page.locator('[data-select="1"]').check()
        page.locator('#rules-mode').select_option('manual')
        page.locator('#staff-id').select_option('5')
        page.locator('#notes').fill('Complete the academic document following the reference PDF.')
        page.locator('#assign-form button[type=submit]').click()
        page.wait_for_function('window.__assigned && window.__assigned.use_generated_rules===false')
        manual=page.evaluate('window.__assigned')
        assert manual['rules'][0]['title']=='Include approval block'
        assert manual['rules'][0]['value']=='Approved by department head'
        assert manual['confirmed_task_ids']==[]
        page.evaluate('window.__multi=true;window.__assigned=null;window.__taskState=null')
        page.locator('#refresh').click()
        page.locator('[data-select="1"]').check()
        page.locator('[data-select="2"]').check()
        assert page.locator('#per-file-toggle-label').is_visible()
        page.locator('#per-file-toggle').check()
        cards=page.locator('.per-file-checklist')
        assert cards.count()==2
        cards.nth(0).locator('.manual-rule input[type="text"]').nth(0).fill('Department cover page')
        cards.nth(0).locator('.manual-rule input[type="text"]').nth(1).fill('Department Cover')
        cards.nth(1).locator('.manual-rule input[type="text"]').nth(0).fill('Course outcomes section')
        cards.nth(1).locator('.manual-rule input[type="text"]').nth(1).fill('Course Outcomes')
        page.locator('#staff-id').select_option('5')
        page.locator('#notes').fill('Complete the separate academic documents using their own checklists.')
        page.locator('#assign-form button[type=submit]').click()
        page.wait_for_function("window.__assigned && window.__assigned.rules_by_task['1'] && window.__assigned.rules_by_task['2']")
        per_file=page.evaluate('window.__assigned.rules_by_task')
        assert per_file['1'][0]['value']=='Department Cover'
        assert per_file['2'][0]['value']=='Course Outcomes'
        page.evaluate("window.__taskState='manual_review'")
        page.locator('#refresh').click()
        page.locator('button[data-op="decide"]').first.wait_for(state='visible')
        page.locator('button[data-op="decide"]').first.click()
        assert page.locator('#task-review-dialog').is_visible()
        assert page.locator('#task-review-title').inner_text()=='Request a correction'
        page.locator('#task-review-note').fill('Please add the missing department approval signature.')
        page.locator('#task-review-submit').click()
        page.wait_for_function('window.__decision !== undefined')
        decision=page.evaluate('window.__decision')
        assert decision['decision']=='needs_correction'
        assert len(decision['note'])>=10
        assert page.locator('#task-review-dialog').is_hidden()
        page.evaluate("window.__taskState='awaiting_hod'")
        page.locator('#refresh').click()
        page.locator('button[data-op="decide"]').first.wait_for(state='visible')
        page.locator('button[data-op="decide"]').first.click()
        assert page.locator('#task-review-title').inner_text()=='Approve submitted work'
        page.locator('#task-review-note').fill('Checked against the reference and approved for filing.')
        page.locator('#task-review-submit').click()
        page.wait_for_function("window.__decision && window.__decision.decision==='approved'")
        assert page.locator('#task-review-dialog').is_hidden()

      else:
        assert page.locator('#hod-section').is_hidden()
        assert page.locator('#hod-dashboard').is_hidden()
      if role=='staff':
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
        assert page.locator('.deadline-cell').count()==1
        assert page.locator('button[data-op="deadline"]').count()==0
      assert not errors,errors
      page.close()
    browser.close()
if __name__=='__main__':test_browser();print('TASK UI PASS: five roles and mobile')
