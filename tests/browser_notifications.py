"""Browser test: BCA student skill list and signed-in notification panel."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_runtime import launch_chromium
from browser_bca import load_page

STATIC=Path(__file__).resolve().parents[1]/'static'

def main():
    with sync_playwright() as pw:
        browser=launch_chromium(pw,headless=True)
        page=browser.new_page(viewport={'width':390,'height':844})
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        load_page(page,'student-portal.html','student-portal.js',mock_denied=True)
        page.evaluate("""() => {
          const input=document.getElementById('showcase-skills');
          input.value=Array.from({length:50},(_,i)=>i===0?'C':'Skill '+i).join(', ');
          input.dispatchEvent(new Event('input',{bubbles:true}));
        }""")
        assert '50 / 100' in page.locator('#skill-count').inner_text()
        assert page.locator('#showcase-skills').evaluate('(e)=>e.tagName')=='TEXTAREA'
        assert page.locator('.social-link').count()>=9
        page.goto('about:blank')
        page.set_content('<main><h1>Logged-in NCET dashboard</h1></main>')
        page.evaluate("""() => {
          window.fetch=async url=>{
            if(String(url).includes('/api/auth/me'))
              return new Response(JSON.stringify({csrf:'mock-token',user:{role:'principal'}}),{status:200,headers:{'Content-Type':'application/json'}});
            if(String(url).includes('/api/alerts/inbox'))
              return new Response(JSON.stringify({unread:2,items:[
                {id:'a-1',text:'New BCA student request',category:'complaints',link:'/bca/oversight',seen:false,at:'2026-10-16T10:00:00+00:00'},
                {id:'t-1',text:'A task was assigned',category:'tasks',link:'/tasks',seen:false,at:'2026-10-16T11:00:00+00:00'}
              ]}),{status:200,headers:{'Content-Type':'application/json'}});
            return new Response('{}',{status:200});
          };
        }""")
        page.add_script_tag(content=(STATIC/'notifications.js').read_text(encoding='utf-8'))
        page.locator('#ncet-alerts').wait_for(state='visible')
        assert '2 new' in page.locator('#alert-count').inner_text()
        page.locator('#alert-toggle').click()
        assert page.locator('.alert-entry').count()==2
        assert page.locator('a[href="/bca/oversight"]').count()==1
        page.keyboard.press('Escape')
        assert page.locator('#alert-list').is_hidden()
        assert errors==[],errors
        browser.close()

if __name__=='__main__':
    main()
    print('Skill and notification Chromium smoke tests passed')
