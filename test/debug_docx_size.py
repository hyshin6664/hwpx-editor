"""docx-preview 가 렌더링한 실제 페이지 폭 측정."""
import sys
from playwright.sync_api import sync_playwright
try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

URL = "https://hyshin6664.github.io/hwpx-editor/"

with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1920, "height": 1080})
    page = ctx.new_page()
    page.on("dialog", lambda d: d.accept())
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_function("() => window.__editorReady === true", timeout=60000)
    page.click("#newBtn"); page.wait_for_timeout(200)
    page.click('#newMenu .newm-item[data-fmt="docx"]')
    page.wait_for_function("() => document.querySelectorAll('#docxHost .docx p[contenteditable]').length > 0", timeout=20000)
    info = page.evaluate("""() => {
      const host = document.getElementById('docxHost');
      const docxRoot = host.querySelector('.docx');
      const wrap = docxRoot ? docxRoot.parentElement : null;
      const section = host.querySelector('section');
      return {
        viewportW: window.innerWidth,
        hostW: host ? host.offsetWidth : -1,
        wrapW: wrap ? wrap.offsetWidth : -1,
        wrapMaxW: wrap ? getComputedStyle(wrap).maxWidth : '',
        docxRootW: docxRoot ? docxRoot.offsetWidth : -1,
        sectionW: section ? section.offsetWidth : -1,
        sectionH: section ? section.offsetHeight : -1,
        sectionStyle: section ? section.getAttribute('style') : '',
      };
    }""")
    print(info)
    b.close()
