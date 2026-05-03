"""
판교 PDF — OCR 변환 후 docx-preview 화면 시각 점검 + 모바일 핀치/줌 검사
"""
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright
try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

URL = "https://hyshin6664.github.io/hwpx-editor/?cb=" + str(int(time.time()*1000))
PDF = Path(r"C:\Users\신현식\Desktop\1.판교글로벌비즈센터 산업시설(B-301~303호) 처분 수의계약 공고문.pdf")
OUT = Path(__file__).parent / "out_pankyo_visual"; OUT.mkdir(exist_ok=True)

def desktop_test():
    print("=== 데스크톱 1280×900 ===")
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        page = ctx.new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function("() => window.__editorReady === true", timeout=60000)
        page.set_input_files("#picker", str(PDF))
        page.wait_for_function("() => window.__currentMode === 'pdf'", timeout=120000)
        page.wait_for_timeout(2000)
        # docx 변환 후 마운트 (사용자가 OCR 클릭 흐름 = 다운로드 + 다시 import)
        with page.expect_download(timeout=180000) as di:
            page.evaluate("document.getElementById('saveDocxBtn').click()")
        dl = di.value
        path = OUT / "pankyo.docx"; dl.save_as(str(path))
        # 닫고 다시 import
        page.evaluate("document.getElementById('closeBtn').click()"); page.wait_for_timeout(500)
        page.set_input_files("#picker", str(path))
        page.wait_for_function("() => window.__currentMode === 'docx'", timeout=30000)
        page.wait_for_timeout(2500)
        # 페이지 1 화면 캡처
        page.screenshot(path=str(OUT/"desktop_docx_view.png"))
        info = page.evaluate("""() => ({
          tables: document.querySelectorAll('#docxHost .docx table').length,
          editableCells: [...document.querySelectorAll('#docxHost .docx td p, #docxHost .docx th p')].filter(p => p.contentEditable === 'true').length,
          docxPagePxW: document.querySelector('#docxHost section')?.offsetWidth || 0,
          host: document.getElementById('docxHost').offsetWidth,
        })""")
        print(f"  docx 마운트: {info}")
        b.close()

def mobile_test():
    print("\n=== 모바일 375×812 ===")
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        # iPhone-like
        ctx = b.new_context(
            viewport={"width": 375, "height": 812},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            has_touch=True,
            is_mobile=True,
        )
        page = ctx.new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function("() => window.__editorReady === true", timeout=60000)
        page.set_input_files("#picker", str(PDF))
        page.wait_for_function("() => window.__currentMode === 'pdf'", timeout=120000)
        page.wait_for_timeout(3000)

        # 모바일 PDF 화면 + 측정
        m_info = page.evaluate("""() => {
          const c = document.querySelector('#pdfHost canvas');
          const r = c ? c.getBoundingClientRect() : null;
          return {
            innerW: innerWidth, innerH: innerHeight,
            canvasW: c ? c.width : 0,
            canvasNaturalH: c ? c.height : 0,
            canvasDispW: r ? Math.round(r.width) : 0,
            canvasDispH: r ? Math.round(r.height) : 0,
            scrollW: document.documentElement.scrollWidth,
          };
        }""")
        print(f"  PDF 모바일 표시: {m_info}")
        overflow = m_info['scrollW'] > m_info['innerW'] + 5
        print(f"  가로 스크롤 발생: {'❌ 있음' if overflow else '✅ 없음'}")
        page.screenshot(path=str(OUT/"mobile_pdf.png"))

        # 핀치 줌 시뮬 — touch 두 손가락 spread 시뮬레이션
        # Playwright 의 touchscreen 으로 dispatch
        try:
            await_eval = page.evaluate("""() => {
              // 핀치/줌 가능한지 — viewport meta 확인
              const meta = document.querySelector('meta[name=viewport]');
              return meta ? meta.content : 'no-viewport';
            }""")
            print(f"  viewport meta: {await_eval}")
        except: pass

        # docx 변환 후 모바일 표시
        with page.expect_download(timeout=180000) as di:
            page.evaluate("document.getElementById('saveDocxBtn').click()")
        dl = di.value
        out = OUT / "mobile_pankyo.docx"; dl.save_as(str(out))
        page.evaluate("document.getElementById('closeBtn').click()"); page.wait_for_timeout(500)
        page.set_input_files("#picker", str(out))
        page.wait_for_function("() => window.__currentMode === 'docx'", timeout=30000)
        page.wait_for_timeout(2500)

        m_docx_info = page.evaluate("""() => {
          const sec = document.querySelector('#docxHost section');
          return {
            scrollW: document.documentElement.scrollWidth,
            innerW: innerWidth,
            sectionW: sec ? sec.offsetWidth : 0,
            transform: sec ? getComputedStyle(sec).transform : '',
            host: document.getElementById('docxHost').offsetWidth,
            hostScrollW: document.getElementById('docxHost').scrollWidth,
          };
        }""")
        overflow_docx = m_docx_info['scrollW'] > m_docx_info['innerW'] + 5
        print(f"  docx 모바일: {m_docx_info}")
        print(f"  docx 가로 스크롤 발생: {'❌ 있음' if overflow_docx else '✅ 없음'}")
        page.screenshot(path=str(OUT/"mobile_docx.png"))
        b.close()

if __name__ == "__main__":
    desktop_test()
    mobile_test()
    print(f"\n📁 {OUT}")
