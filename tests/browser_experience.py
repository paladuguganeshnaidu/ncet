"""Chromium interaction checks for the NCET public, faculty and responsive workflows.

The faculty data transport is explicitly mocked; backend roles and exports are
covered separately by integration tests. No production student data is used.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_runtime import launch_chromium
from browser_bca import load_page

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"


def main():
    with sync_playwright() as playwright:
        browser = launch_chromium(playwright,headless=True)
        errors=[]
        page=browser.new_page(viewport={"width":1440,"height":900},accept_downloads=True)
        page.on("pageerror",lambda error: errors.append(str(error)))
        page.set_default_timeout(12000)

        # Anonymous visitors see functional links, a keyboard-operable help
        # accordion and a direct profile-search form, not rotating ad graphics.
        load_page(page,"public-home.html","public-home.js")
        assert page.locator(".film-frames").count()==0
        assert page.locator('.identity-crest').evaluate('(img)=>img.complete && img.naturalWidth>0')
        assert page.locator('.topnav .brand img').evaluate('(img)=>img.complete && img.naturalWidth>0')
        assert page.locator('.topnav .brand-title').inner_text()=='NCET Student Portal'
        assert page.locator('.topnav .brand-subtitle').inner_text()=='VerifyFlow · Student and faculty collaboration'
        assert page.locator('.identity-crest').get_attribute('src').startswith('data:image/svg+xml;base64,')
        assert page.locator('body').inner_text().lower().find('student services')==-1
        assert page.locator('.identity-crest').evaluate(
            '(img)=>Math.abs(img.getBoundingClientRect().width / img.getBoundingClientRect().height - 455/225)<.15')
        assert page.locator('.identity-panel').evaluate(
            '(el)=>getComputedStyle(el).backgroundColor')=='rgb(255, 255, 255)'
        people=page.locator('.footer-credits a').all()
        assert [a.inner_text().split(' · ')[-1].replace(' ↗','') for a in people]==['Principal','HOD','Developer']
        assert [a.get_attribute('href') for a in people]==[
            'https://www.linkedin.com/in/dr-thippeswamy-gangappa-686b3822/',
            'https://www.linkedin.com/in/bhargava-r-a08b8182/',
            'https://www.linkedin.com/in/paladuguganeshnaidu/'
        ]
        assert page.locator("a.service-card").count()==3
        for card in page.locator("a.service-card").all():
            assert card.get_attribute("href") in ("/students/portal","/students/directory")
        page.locator(".guide-grid summary").first.focus()
        page.keyboard.press("Enter")
        assert page.locator(".guide-grid details").first.evaluate("(el) => el.open")
        page.locator("#homepage-search").fill("1NC24BCA901")
        assert page.locator('form[role="search"]').get_attribute("method")=="get"

        # Roster export and search should work for an authorized BCA faculty
        # session without exposing temporary passwords in downloaded CSV.
        load_page(page,"bca-management.html")
        page.evaluate("""() => {
          const oldCreate=URL.createObjectURL.bind(URL);
          window.__exportedCSV=null;
          URL.createObjectURL=(blob)=>{
            blob.text().then(text=>window.__exportedCSV=text);
            return oldCreate(blob);
          };
          window.fetch=async(url)=>{
            const data=String(url).endsWith('/api/auth/me')?
              {csrf:'mock-csrf',user:{role:'staff',name:'Demo BCA Faculty',department:'Computer Applications'}}:
              String(url).endsWith('/api/academic/departments')?
              {items:[{code:'Computer Applications',name:'Computer Applications',active:true}]}:
              String(url).endsWith('/api/bca/students')?
              {items:[
                {usn:'1NC24BCA901',name:'Student Alpha',semester:3,active:true},
                {usn:'1NC24BCA902',name:'Student Beta',semester:2,active:true}
              ]}:{items:[]};
            return new Response(JSON.stringify(data),{
              status:200,headers:{'Content-Type':'application/json'}});
          };
        }""")
        page.add_script_tag(content=(STATIC/"bca-management.js").read_text(encoding='utf-8'))
        page.locator("#desk").wait_for(state="visible")
        assert page.title()=="Department Student Desk | NCET VerifyFlow"
        assert page.locator(".brand small").inner_text()=="Computer Applications"
        assert page.locator("#roster .entry").count()==2
        page.locator("#roster-search").fill("bca901")
        assert page.locator("#roster .entry").count()==1
        assert "Student Alpha" in page.locator("#roster").inner_text()
        page.locator("#roster-search").fill("unknown")
        assert page.get_by_text("No students match your search.").is_visible()
        page.locator("#roster-search").fill("")
        with page.expect_download() as download_info:
            page.locator("#export-roster").click()
        download=download_info.value
        assert download.suggested_filename=="NCET_student_roster_without_passwords.csv"
        page.wait_for_function("window.__exportedCSV !== null")
        exported=page.evaluate("window.__exportedCSV")
        assert "1NC24BCA901" in exported and "1NC24BCA902" in exported
        assert "temporary_password" not in exported
        assert "email" not in exported and "mobile" not in exported

        # Super Admin manages all branches; keep its student desk labels and
        # export names department-neutral while retaining BCA labels for staff.
        load_page(page,"bca-management.html")
        page.evaluate("""() => {
          window.fetch=async(url)=>{
            const path=String(url);
            const data=path.endsWith('/api/auth/me')?
              {csrf:'mock-csrf',user:{role:'admin',name:'Demo Admin',department:'Computer Science & Engineering'}}:
              path.endsWith('/api/academic/departments')?
              {items:[{code:'Computer Science & Engineering',name:'Computer Science & Engineering',active:true}]}:
              path.endsWith('/api/bca/students')?
              {items:[{usn:'1NC24CS901',name:'Admin Student',branch:'Computer Science & Engineering',
                branch_name:'Computer Science & Engineering',semester:3,active:true}]}:
              {items:[]};
            return new Response(JSON.stringify(data),{
              status:200,headers:{'Content-Type':'application/json'}});
          };
        }""")
        page.add_script_tag(content=(STATIC/"bca-management.js").read_text(encoding="utf-8"))
        page.locator("#desk").wait_for(state="visible")
        assert page.title()=="Student Administration | NCET VerifyFlow"
        assert page.locator(".brand small").inner_text()=="All departments"
        assert "ALL DEPARTMENTS" in page.locator(".shell-head").inner_text()
        assert "Student administration" in page.locator("footer").inner_text()
        assert "BCA student portal" not in page.locator("footer").inner_text()
        with page.expect_download() as admin_download_info:
            page.locator("#export-roster").click()
        assert admin_download_info.value.suggested_filename=="NCET_student_roster_without_passwords.csv"

        # Responsive checks across public and protected pages; no persistent
        # motion when reduced-motion is requested.
        for width in (320,390,768,1024,1440):
            page.set_viewport_size({"width":width,"height":900})
            load_page(page,"public-home.html","public-home.js")
            overflow=page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
            assert not overflow, f"Horizontal overflow at {width}px"
            assert page.locator('.identity-crest').is_visible(),width
            # The complete NCET Student Portal label must be uniformly styled,
            # readable and contained at every mobile and desktop breakpoint.
            header=page.locator('.topnav .brand')
            typeface=header.evaluate("""(root) => {
              const title=root.querySelector('.brand-title');
              const subtitle=root.querySelector('.brand-subtitle');
              const t=title.getBoundingClientRect();
              const b=root.getBoundingClientRect();
              const styles=getComputedStyle(title),small=getComputedStyle(subtitle);
              return {title:title.textContent.trim(),titleSize:parseFloat(styles.fontSize),
                subtitleSize:parseFloat(small.fontSize),
                weight:parseInt(styles.fontWeight,10),titleRight:t.right,
                brandRight:b.right,subtitleVisible:small.display!=='none'};
            }""")
            assert typeface['title']=='NCET Student Portal',width
            assert 12.5<=typeface['titleSize']<=17,width
            assert typeface['subtitleSize']<typeface['titleSize'],width
            assert typeface['weight']>=700,width
            assert typeface['subtitleVisible'],width
            assert typeface['titleRight']<=typeface['brandRight']+2,(width,typeface)
            assert page.locator('.identity-crest').evaluate('(img)=>img.naturalWidth>0'),width
            assert page.locator('.footer-credits a').count()==3,width
            assert page.locator('.identity-panel').evaluate('(el)=>getComputedStyle(el).backgroundColor')=='rgb(255, 255, 255)'
        page.emulate_media(reduced_motion="reduce")
        load_page(page,"public-home.html","public-home.js")
        assert page.locator(".identity-crest").is_visible()
        duration=page.locator(".service-card").first.evaluate(
            "(el) => getComputedStyle(el).transitionDuration")
        assert duration in ("0s","1e-05s"), duration
        assert not errors, errors
        browser.close()


if __name__=="__main__":
    main()
    print("NCET experience checks passed: faculty roster, privacy-safe export, links, keyboard and responsive")
