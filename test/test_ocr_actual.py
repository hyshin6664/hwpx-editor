"""
실제 OCR 클릭 흐름 검증 (사용자 시나리오 그대로):
1) PDF 로드
2) OCR 버튼 클릭
3) confirm dialog 자동 OK
4) Tesseract OCR 처리 대기 (~30~60초)
5) 자동 변환 후 검증:
   - currentMode === 'docx'
   - PDF toolbar 사라짐
   - docxHost 에 표 셀 contenteditable
   - 이미지 박힌 거 0개
"""
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright
try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

URL = "https://hyshin6664.github.io/hwpx-editor/?cb=" + str(int(time.time()*1000))
PDF = Path(r"C:\Users\신현식\Desktop\예약이체 내역.pdf")
OUT = Path(__file__).parent / "out_ocr_actual"; OUT.mkdir(exist_ok=True)

def main():
    if not PDF.exists():
        print(f"❌ PDF 없음: {PDF}"); sys.exit(1)
    print("📋 OCR 실제 클릭 흐름 검증\n")

    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        page = b.new_context(viewport={"width": 1280, "height": 900}).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function("() => window.__editorReady === true", timeout=60000)
        print("✅ 페이지 로드")
        page.set_input_files("#picker", str(PDF))
        page.wait_for_function("() => window.__currentMode === 'pdf'", timeout=60000)
        page.wait_for_timeout(1500)
        print("✅ PDF 로드")

        # 1. PDF 마운트 후 — pdf-toolbar 보임 확인
        info_pdf = page.evaluate("""() => ({
          mode: window.__currentMode,
          pdfToolbar: !!document.querySelector('.pdf-toolbar.visible'),
          pdfHostVisible: document.getElementById('pdfHost').style.display !== 'none',
          docxHostVisible: !!document.querySelector('#docxHost section'),
        })""")
        print(f"  PDF 모드: {info_pdf}")

        # 2. OCR 버튼 클릭 (PDF 모드 toolbar 의 pdfOcrBtn, 또는 hidden ocrBtn)
        # 텍스트 PDF 면 첫 confirm "그래도 OCR 진행?" 떠야 함
        print("\n📷 OCR 버튼 클릭...")
        page.evaluate("document.getElementById('pdfOcrBtn').click()")

        # OCR 처리 대기 (텍스트 PDF는 빠르고 라이브러리 처음 받으면 느림)
        # currentMode 가 'docx' 로 바뀌면 완료
        try:
            page.wait_for_function("() => window.__currentMode === 'docx'", timeout=180000)
            print("✅ OCR 변환 완료 (currentMode → docx)")
        except Exception as e:
            print(f"❌ OCR timeout: {e}")
            page.screenshot(path=str(OUT/"timeout.png"))
            b.close()
            sys.exit(1)
        page.wait_for_timeout(2000)

        # 3. 결과 검증
        result = page.evaluate("""() => ({
          mode: window.__currentMode,
          pdfToolbarStillVisible: !!document.querySelector('.pdf-toolbar.visible'),
          pdfHostHidden: document.getElementById('pdfHost').style.display === 'none',
          docxHostShown: !!document.querySelector('#docxHost section'),
          tableCount: document.querySelectorAll('#docxHost .docx table').length,
          editableCells: [...document.querySelectorAll('#docxHost .docx td p, #docxHost .docx th p')]
                         .filter(p => p.contentEditable === 'true').length,
          allCells: document.querySelectorAll('#docxHost .docx td, #docxHost .docx th').length,
          imgInDocxHost: document.querySelectorAll('#docxHost img').length,
        })""")
        print(f"\n📊 OCR 후 검증:")
        for k, v in result.items():
            print(f"  {k}: {v}")

        # 화면 캡처
        page.screenshot(path=str(OUT / "after_ocr.png"), full_page=False)
        print(f"\n📷 화면 캡처: {OUT}/after_ocr.png")

        # 합격 기준
        ok = (result['mode'] == 'docx' and
              not result['pdfToolbarStillVisible'] and
              result['pdfHostHidden'] and
              result['docxHostShown'] and
              result['tableCount'] > 0 and
              result['editableCells'] > 5 and
              result['imgInDocxHost'] == 0)
        b.close()
        print(f"\n{'✅ PASS — OCR 흐름 정상' if ok else '❌ FAIL — 문제 있음'}")
        sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
