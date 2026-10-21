"""Principal oversight summary UI across desktop and narrow viewports."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_runtime import launch_chromium

BASE=Path(__file__).resolve().parents[1]/'static'

SUMMARY={
    'view':'summary','cases_total':3,
    'cases_by_status':{'submitted':1,'in_review':1,'resolved':1,'closed':0},
    'projects_total':2,'projects_open':1,'projects_closed':1,
    'departments':[
        {'department':'Computer Science & Engineering','cases_total':2,
         'cases_by_status':{'submitted':1,'in_review':1},'projects_total':1,'projects_open':1},
        {'department':'Mechanical Engineering','cases_total':1,
         'cases_by_status':{'resolved':1},'projects_total':1,'projects_open':0},
    ],
}

def main():
    with sync_playwright() as playwright:
        browser=launch_chromium(playwright,headless=True)
        for width in (320,390,768,1366):
            page=browser.new_page(viewport={'width':width,'height':850})
            errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            html=(BASE/'bca-oversight.html').read_text(encoding='utf-8')
            for href,filename in (('/static/bca.css','bca.css'),('/static/oversight.css','oversight.css'),
                                  ('/static/notifications.css','notifications.css'),
                                  ('/static/ncet-brand-system.css?v=20261017','ncet-brand-system.css'),
                                  ('/static/institutional-ui.css?v=20261017d','institutional-ui.css')):
                html=html.replace(f'<link rel="stylesheet" href="{href}">',
                                  '<style>'+ (BASE/filename).read_text(encoding='utf-8')+'</style>')
            html=html.replace('<script src="/static/bca-oversight.js" defer></script>','')
            page.set_content(html)
            page.evaluate("""(summary)=>{
              window.fetch=async()=>new Response(JSON.stringify(summary),{status:200,
                headers:{'Content-Type':'application/json'}});
            }""",SUMMARY)
            page.add_script_tag(content=(BASE/'bca-oversight.js').read_text(encoding='utf-8'))
            page.locator('#department-rows tr').nth(1).wait_for()
            assert page.locator('#page-title').inner_text()=='Institutional oversight'
            assert page.locator('#cases-total').inner_text()=='3 requests in total'
            assert page.locator('#department-rows tr').count()==2
            assert 'Computer Science & Engineering' in page.locator('#department-rows').inner_text()
            assert page.locator('#hod-recent').is_hidden()
            assert page.locator('#department-summary').is_visible()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2'),width
            if width<620:
                assert page.locator('.table-wrap').evaluate('(el)=>el.scrollWidth>el.clientWidth')
            assert not errors,errors
            page.close()
        browser.close()
    print('INSTITUTIONAL OVERSIGHT UI PASS: aggregate view, branch table, 320–1366px')

if __name__=='__main__':
    main()
