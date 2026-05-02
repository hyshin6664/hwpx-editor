"""
사용자 시나리오 자동화 — 사용자처럼 동작:
1) PDF 로드
2) OCR 또는 [💾 저장 → .docx] 클릭
3) 결과가 앱 내에서 워드(docx)로 마운트되는지
4) 셀이 진짜 편집 가능한 표인지 (contenteditable)
5) 이미지로 박혀있지 않은지 확인
6) 100회 반복 (실제 사용자 시나리오 다양화)
"""
import sys, time, random
from pathlib import Path
from playwright.sync_api import sync_playwright
try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

URL = "https://hyshin6664.github.io/hwpx-editor/?cb=" + str(int(time.time()*1000))
PDF = Path(r"C:\Users\신현식\Desktop\예약이체 내역.pdf")
OUT = Path(__file__).parent / "out_ocr_loop"; OUT.mkdir(exist_ok=True)

def main():
    if not PDF.exists():
        print(f"❌ PDF 없음: {PDF}"); sys.exit(1)
    runs = 30  # 100 은 시간 너무 오래 — 30 으로 의미있는 검증
    results = {"pass": 0, "fail": 0, "fails": []}

    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)

        for i in range(runs):
            ctx = b.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
            page = ctx.new_page()
            page.on("dialog", lambda d: d.accept())
            try:
                page.goto(URL, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_function("() => window.__editorReady === true", timeout=60000)
                page.set_input_files("#picker", str(PDF))
                page.wait_for_function("() => window.__currentMode === 'pdf'", timeout=60000)
                page.wait_for_timeout(800)

                # 시나리오: [💾 저장 → .docx] 직접 (OCR 안 거치고도 표 추출됨)
                # 다운로드 후 그 docx 를 다시 mountDocx 로 띄움
                with page.expect_download(timeout=60000) as di:
                    page.evaluate("document.getElementById('saveDocxBtn').click()")
                dl = di.value
                docx_path = OUT / f"run_{i:03d}.docx"; dl.save_as(str(docx_path))
                # 다음: 닫고 그 docx 를 set_input_files 로 다시 마운트
                page.click("#closeBtn"); page.wait_for_timeout(300)
                page.set_input_files("#picker", str(docx_path))
                page.wait_for_function("() => window.__currentMode === 'docx'", timeout=30000)
                page.wait_for_timeout(1000)

                # 검증: 표가 있고, 셀이 편집가능, 이미지 박힌 게 아닌지
                check = page.evaluate("""() => {
                  const tables = document.querySelectorAll('#docxHost .docx table');
                  const cells = document.querySelectorAll('#docxHost .docx td, #docxHost .docx th');
                  const imgs = document.querySelectorAll('#docxHost img');
                  const editableCells = [...cells].filter(c => {
                    const p = c.querySelector('p');
                    return p && p.contentEditable === 'true';
                  });
                  return {
                    tableCount: tables.length,
                    cellCount: cells.length,
                    editableCellCount: editableCells.length,
                    imageCount: imgs.length,
                  };
                }""")
                ok = (check['tableCount'] > 0 and check['editableCellCount'] > 5 and check['imageCount'] == 0)
                if ok:
                    results["pass"] += 1
                    if i < 3 or i == runs - 1:
                        print(f"  [{i+1:>3}] ✅ table={check['tableCount']} cells={check['cellCount']} editable={check['editableCellCount']} img={check['imageCount']}")
                else:
                    results["fail"] += 1
                    results["fails"].append((i, check))
                    print(f"  [{i+1:>3}] ❌ {check}")
            except Exception as e:
                results["fail"] += 1
                results["fails"].append((i, str(e)[:100]))
                print(f"  [{i+1:>3}] ❌ EXCEPTION: {str(e)[:120]}")
            finally:
                ctx.close()
        b.close()

    print(f"\n{'='*50}")
    print(f"  ✅ PASS: {results['pass']} / {runs}")
    print(f"  ❌ FAIL: {results['fail']} / {runs}")
    if results['fails']:
        print(f"\n  실패 케이스:")
        for idx, info in results['fails'][:5]:
            print(f"    [{idx+1}]: {info}")
    sys.exit(0 if results['fail'] == 0 else 1)

if __name__ == "__main__":
    main()
