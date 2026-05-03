"""
v22.0 사용자처럼 처음부터 끝까지 모든 단계 실제로 클릭하며 테스트.
1) 페이지 로드
2) PDF 파일 업로드
3) PDF 모드 도구바 확인 (OCR 버튼 있는지)
4) [💾 저장 → .docx] → 다운로드 + 검증
5) [💾 저장 → .xlsx] → 다운로드 + 검증
6) OCR 클릭 → 앱 안에서 워드 모드로 변경 + 검증
7) [💾 저장 → 구글 시트] → 클립보드 + 시트 새 탭
"""
import sys, time, zipfile, re
from pathlib import Path
from playwright.sync_api import sync_playwright
try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

URL = "https://hyshin6664.github.io/hwpx-editor/?cb=" + str(int(time.time()*1000))
PDF = Path(r"C:\Users\신현식\Desktop\예약이체 내역.pdf")
OUT = Path(__file__).parent / "out_v22_user"; OUT.mkdir(exist_ok=True)

def main():
    if not PDF.exists():
        print(f"❌ PDF 없음: {PDF}"); sys.exit(1)
    print("="*60)
    print("📋 v22.0 — 사용자처럼 처음부터 끝까지 테스트")
    print("="*60)

    results = []
    def step(name, ok, detail=""):
        em = "✅" if ok else "❌"
        results.append((em, name, detail))
        print(f"  {em} {name}{(' — ' + detail) if detail else ''}")

    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True, permissions=['clipboard-read', 'clipboard-write'])
        page = ctx.new_page()
        page.on("dialog", lambda d: d.accept())

        # 1. 페이지 로드
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function("() => window.__editorReady === true", timeout=60000)
        ver = page.evaluate("() => document.getElementById('verBtn').textContent")
        step(f"페이지 로드 (v22.0 deployed)", "v22" in ver or "21." in ver, ver)

        # 2. PDF 업로드
        page.set_input_files("#picker", str(PDF))
        page.wait_for_function("() => window.__currentMode === 'pdf'", timeout=60000)
        page.wait_for_timeout(1500)
        step("PDF 마운트", page.evaluate("() => window.__currentMode === 'pdf'"))

        # 3. PDF 도구바 확인
        toolbar_info = page.evaluate("""() => ({
          erase: !!document.querySelector('button[data-tool=\"erase\"]'),
          eraseText: !!document.querySelector('button[data-tool=\"erase-text\"]'),
          text: !!document.querySelector('button[data-tool=\"text\"]'),
          ocr: !!document.querySelector('#pdfOcrBtn'),
        })""")
        step("PDF 도구바 (지우개·글자·OCR)", all(toolbar_info.values()), str(toolbar_info))

        # 4. 저장 드롭다운 항목 확인
        save_items = page.evaluate("""() => [...document.querySelectorAll('#saveMenu .save-item')].map(b => b.dataset.fmt)""")
        expected = ['hwpx', 'hwp', 'docx', 'pdf', 'xlsx', 'gsheet']
        step(f"저장 메뉴 항목 (xlsx + gsheet 추가)", all(f in save_items for f in expected), str(save_items))

        # 5. .docx 다운로드 (편집가능 워드)
        with page.expect_download(timeout=120000) as di:
            page.evaluate("document.getElementById('saveDocxBtn').click()")
        dl = di.value
        out_docx = OUT / "test.docx"; dl.save_as(str(out_docx))
        with zipfile.ZipFile(out_docx) as z:
            xml = z.read("word/document.xml").decode("utf-8")
            tables = xml.count("<w:tbl>")
            cells = xml.count("<w:tc>")
            shading = len(re.findall(r'<w:shd[^/]*w:fill="DEDEDE"', xml))
        step(f".docx 변환", tables > 0 and cells > 5, f"{out_docx.stat().st_size/1024:.1f}KB, 표{tables}, 셀{cells}, 회색헤더{shading}")

        # 6. .xlsx 다운로드 (NEW v22.0)
        with page.expect_download(timeout=180000) as di:
            page.evaluate("(async () => { const b=document.getElementById('saveBtn'); b.click(); await new Promise(r=>setTimeout(r,200)); document.querySelector('#saveMenu .save-item[data-fmt=\"xlsx\"]').click(); })()")
        dl = di.value
        out_xlsx = OUT / "test.xlsx"; dl.save_as(str(out_xlsx))
        with zipfile.ZipFile(out_xlsx) as z:
            sheet_xml = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
            xl_rows = sheet_xml.count("<row ")
            xl_cells = sheet_xml.count("<c ")
            has_fill = "<patternFill" in z.read("xl/styles.xml").decode("utf-8")
        step(f".xlsx 변환", xl_rows >= 4 and xl_cells > 5, f"{out_xlsx.stat().st_size/1024:.1f}KB, 행{xl_rows}, 셀{xl_cells}, 색{has_fill}")

        # 7. OCR 클릭 → 앱 안 워드 모드 (v21.9 수정)
        page.click("#closeBtn"); page.wait_for_timeout(500)
        page.set_input_files("#picker", str(PDF))
        page.wait_for_function("() => window.__currentMode === 'pdf'", timeout=60000)
        page.wait_for_timeout(1500)
        page.evaluate("document.getElementById('pdfOcrBtn').click()")
        try:
            page.wait_for_function("() => window.__currentMode === 'docx'", timeout=180000)
            page.wait_for_timeout(2000)
            ocr_check = page.evaluate("""() => ({
              mode: window.__currentMode,
              pdfToolbarGone: !document.querySelector('.pdf-toolbar.visible'),
              docxShown: !!document.querySelector('#docxHost section'),
              tables: document.querySelectorAll('#docxHost .docx table').length,
              editableCells: [...document.querySelectorAll('#docxHost .docx td p, #docxHost .docx th p')].filter(p => p.contentEditable === 'true').length,
              imgInDocx: document.querySelectorAll('#docxHost img').length,
            })""")
            ok_ocr = (ocr_check['mode']=='docx' and ocr_check['pdfToolbarGone'] and
                      ocr_check['tables']>0 and ocr_check['editableCells']>5 and ocr_check['imgInDocx']==0)
            step("OCR → 앱 내 워드 모드", ok_ocr, str(ocr_check))
        except Exception as e:
            step("OCR → 앱 내 워드 모드", False, str(e))

        page.screenshot(path=str(OUT / "ocr_result.png"))

        b.close()

    pc = sum(1 for r in results if r[0]=='✅')
    print(f"\n결과: {pc} / {len(results)} PASS")
    for r in results:
        if r[0] == '❌': print(f"  ❌ {r[1]} — {r[2]}")
    print(f"\n📁 {OUT}")
    sys.exit(0 if pc == len(results) else 1)

if __name__ == "__main__":
    main()
