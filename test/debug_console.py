import sys, time
from playwright.sync_api import sync_playwright
try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

URL = "http://127.0.0.1:8765/?cb=" + str(int(time.time()*1000))

with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()
    msgs = []
    page.on("console", lambda m: msgs.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: msgs.append(f"[ERR] {e}"))
    page.on("dialog", lambda d: d.accept())
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_function("() => window.__editorReady === true", timeout=60000)
    page.click("#newBtn"); page.wait_for_timeout(150)
    page.click('#newMenu .newm-item[data-fmt="docx"]')
    page.wait_for_function("() => document.querySelectorAll('#docxHost .docx p[contenteditable]').length>0", timeout=20000)
    page.wait_for_timeout(800)
    for m in msgs:
        if 'fix-width' in m or '렌더링' in m or 'ERR' in m or 'error' in m.lower():
            print(m)
    info = page.evaluate("""() => {
      const sec=document.querySelector('#docxHost section');
      const docx=document.querySelector('#docxHost .docx');
      const wrap=docx.parentElement;
      const cs = getComputedStyle(sec);
      return {
        secInline: sec.getAttribute('style'),
        secComputedW: cs.width,
        secComputedTransform: cs.transform,
        secOffsetW: sec.offsetWidth,
        docxClass: docx.className,
        docxInline: docx.getAttribute('style'),
        docxComputedTransform: getComputedStyle(docx).transform,
        docxOffsetW: docx.offsetWidth,
        wrapInline: wrap ? wrap.getAttribute('style') : null,
        wrapOffsetW: wrap ? wrap.offsetWidth : null,
        hostOffsetW: document.getElementById('docxHost').offsetWidth,
      };
    }""")
    print('INFO:')
    for k, v in info.items(): print(f"  {k} = {v!r}")
    b.close()
