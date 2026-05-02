"""
원본 PDF 와 변환된 DOCX 시각 비교
1) PDF 모드로 원본 열기 → 스크린샷
2) PDF → 편집가능 DOCX 변환 → 다운로드
3) 새 페이지에 다운된 docx 열기 → 스크린샷
4) 두 화면 사이드 바이 사이드 PNG 출력
"""
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright
try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

URL = "http://127.0.0.1:8765/?cb=" + str(int(time.time()*1000))
PDF = Path(r"C:\Users\신현식\Desktop\예약이체 내역.pdf")
OUT = Path(__file__).parent / "out_compare"; OUT.mkdir(exist_ok=True)

def main():
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1280, "height": 1100}, accept_downloads=True)
        page = ctx.new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function("() => window.__editorReady === true", timeout=60000)

        # 1) PDF 원본 열기 + 스크린샷
        page.set_input_files("#picker", str(PDF))
        page.wait_for_function("() => window.__currentMode === 'pdf'", timeout=60000)
        page.wait_for_timeout(1000)
        # PDF host 영역만 캡쳐
        page.locator("#pdfHost canvas").first.screenshot(path=str(OUT / "1_pdf_original.png"))
        print(f"✅ 원본 PDF 캡처: {OUT}/1_pdf_original.png")

        # 2) DOCX 변환
        with page.expect_download(timeout=120000) as di:
            page.evaluate("document.getElementById('saveDocxBtn').click()")
        dl = di.value
        out = OUT / "예약이체_편집가능.docx"; dl.save_as(str(out))
        print(f"✅ DOCX 다운: {out} ({out.stat().st_size} bytes)")

        # 3) 닫고 변환된 DOCX 열기
        page.click("#closeBtn"); page.wait_for_timeout(500)
        page.set_input_files("#picker", str(out))
        page.wait_for_function("() => window.__currentMode === 'docx'", timeout=30000)
        page.wait_for_timeout(1500)
        page.locator("#docxHost").first.screenshot(path=str(OUT / "2_docx_converted.png"))
        print(f"✅ 변환된 DOCX 캡처: {OUT}/2_docx_converted.png")

        # 4) 표 셀 텍스트 추출
        cells_text = page.evaluate("""() => {
          const cells = [...document.querySelectorAll('#docxHost .docx td, #docxHost .docx th')];
          return cells.map(c => c.textContent.trim()).filter(t => t);
        }""")
        print(f"\n✅ 변환된 워드 셀 텍스트 ({len(cells_text)}개):")
        for i, t in enumerate(cells_text[:30]):
            print(f"  [{i}] {t!r}")
        b.close()

if __name__ == "__main__":
    main()
