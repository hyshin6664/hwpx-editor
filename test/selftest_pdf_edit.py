"""
PDF 지우개 + 글씨 입력 자체 테스트
"""
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass

LIVE_URL = "https://hyshin6664.github.io/hwpx-editor/"
PDF_FILE = Path(r"C:\Users\신현식\Desktop\예약이체 내역.pdf")
OUT_DIR = Path(__file__).parent / "out"
OUT_DIR.mkdir(exist_ok=True)


def main():
    if not PDF_FILE.exists():
        print(f"PDF 파일 없음: {PDF_FILE}")
        sys.exit(2)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1400, "height": 900},
                                   accept_downloads=True)
        page = ctx.new_page()
        msgs = []
        errs = []
        page.on("console", lambda m: msgs.append(f"[{m.type}] {m.text}"))
        page.on("pageerror", lambda e: errs.append(str(e)))

        try:
            print("[1] 페이지 로드...")
            page.goto(LIVE_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_function("() => document.getElementById('picker') != null", timeout=30000)

            print("[2] PDF 업로드...")
            page.set_input_files("#picker", str(PDF_FILE))
            page.wait_for_function("() => document.querySelectorAll('#pdfHost canvas').length > 0", timeout=60000)
            print("    OK PDF 로드됨")
            page.wait_for_timeout(500)
            page.screenshot(path=str(OUT_DIR/"pdf_edit_01_loaded.png"))

            canvas = page.query_selector("#pdfHost canvas")
            canvas.scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            box = canvas.bounding_box()
            print(f"    canvas: {box}")

            print("[3] 지우개 모드로 드래그...")
            page.click('button[data-tool="erase"]')
            page.wait_for_timeout(200)
            # 툴바 sticky 회피 위해 위에서 충분히 떨어진 위치
            sx = box["x"] + 80
            sy = box["y"] + 200
            page.mouse.move(sx, sy)
            page.mouse.down()
            page.mouse.move(sx + 180, sy + 22, steps=10)
            page.mouse.up()
            page.wait_for_timeout(300)
            page.screenshot(path=str(OUT_DIR/"pdf_edit_02_erased.png"))

            edits = page.evaluate("() => window.pdfState && window.pdfState.pages[0].edits.length")
            # pdfState 가 window 에 노출 안 되어 있을 수 있어, 직접 카운트
            edits_check = page.evaluate("""() => {
              return Array.from(document.querySelectorAll('.erase-selection')).length;
            }""")
            print(f"    drag 후 selection 잔존: {edits_check}, edits: {edits}")

            print("[4] 글씨 모드로 클릭+입력...")
            page.click('button[data-tool="text"]')
            page.wait_for_timeout(200)
            tx = box["x"] + 100
            ty = box["y"] + 215
            page.mouse.click(tx, ty)
            page.wait_for_timeout(200)
            page.keyboard.type("TEST한글", delay=20)
            page.keyboard.press("Enter")
            page.wait_for_timeout(300)
            page.screenshot(path=str(OUT_DIR/"pdf_edit_03_typed.png"))

            print("[5] 저장 클릭 → PDF 다운로드...")
            with page.expect_download(timeout=120000) as di:
                page.click("#savePdfBtn")
            dl = di.value
            out = OUT_DIR / "pdf_edited.pdf"
            dl.save_as(str(out))
            sz = out.stat().st_size
            print(f"    download: {sz} bytes ({dl.suggested_filename})")

            # 최종 스크린샷
            page.screenshot(path=str(OUT_DIR/"pdf_edit_04_after_save.png"))

            ok = sz > 1000
            print(f"\n=== 결과: {'PASS' if ok else 'FAIL'} ===")
            if not ok:
                print("--- console (last 30) ---")
                for m in msgs[-30:]: print("  ", m)
                for e in errs[-5:]: print("  [ERR]", e)
            sys.exit(0 if ok else 1)
        except Exception as e:
            print("EXCEPTION:", e)
            try: page.screenshot(path=str(OUT_DIR/"pdf_edit_99_err.png"))
            except: pass
            print("--- console ---")
            for m in msgs[-30:]: print("  ", m)
            for er in errs[-5:]: print("  [ERR]", er)
            sys.exit(1)
        finally:
            browser.close()


if __name__ == "__main__":
    main()
