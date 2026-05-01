"""
PDF + DOCX 모드 자체 검증 (Playwright)
"""
import sys, os, time, json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

LIVE_URL = "https://hyshin6664.github.io/hwpx-editor/"
PDF_FILE = Path(r"C:\Users\신현식\Desktop\예약이체 내역.pdf")
DOCX_FILE = Path(__file__).parent / "sample.docx"
OUT_DIR = Path(__file__).parent / "out"
OUT_DIR.mkdir(exist_ok=True)


def p(msg): print(msg, flush=True)


def test_one(file_path, mode_name, save_btn_id):
    if not file_path.exists():
        p(f"  파일 없음: {file_path}")
        return False
    p(f"\n=== {mode_name} 테스트: {file_path.name} ({file_path.stat().st_size:,} bytes) ===")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        page = ctx.new_page()

        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        console_msgs = []
        page.on("console", lambda m: console_msgs.append(f"[{m.type}] {m.text}"))

        try:
            page.goto(LIVE_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_function(
                "() => document.getElementById('picker') != null",
                timeout=30000,
            )
            # hwp 엔진은 PDF/DOCX 에는 안 필요. 바로 파일 선택.
            page.set_input_files("#picker", str(file_path))

            # mode 가 적용될 때까지 대기 (최대 60초)
            page.wait_for_function(
                f"() => window.currentMode === '{mode_name}' || document.getElementById('{save_btn_id}').offsetParent !== null && !document.getElementById('{save_btn_id}').disabled",
                timeout=60000,
            )

            # mode 확인
            state = page.evaluate(
                """(saveBtn) => ({
                  filename: document.getElementById('filenameLabel').textContent,
                  saveBtnVisible: document.getElementById(saveBtn).offsetParent !== null,
                  saveBtnDisabled: document.getElementById(saveBtn).disabled,
                  pdfHostExists: !!document.getElementById('pdfHost'),
                  docxHostExists: !!document.getElementById('docxHost'),
                  pdfCanvases: document.querySelectorAll('#pdfHost canvas').length,
                  docxParas: document.querySelectorAll('#docxHost [contenteditable]').length
                })""",
                save_btn_id,
            )
            p(f"  state: {state}")

            # 다운로드 클릭
            with page.expect_download(timeout=60000) as dl_info:
                page.click(f"#{save_btn_id}")
            dl = dl_info.value
            dl_path = OUT_DIR / f"downloaded_{mode_name}.{file_path.suffix.lstrip('.')}"
            dl.save_as(str(dl_path))
            sz = dl_path.stat().st_size if dl_path.exists() else 0
            p(f"  download: {sz} bytes ({dl.suggested_filename})")

            page.screenshot(path=str(OUT_DIR / f"{mode_name}_view.png"))
            ok = sz > 1000
            p(f"  → {'PASS' if ok else 'FAIL'}")
            return ok
        except Exception as e:
            p(f"  EXCEPTION: {e}")
            try:
                page.screenshot(path=str(OUT_DIR / f"{mode_name}_err.png"))
            except Exception: pass
            for line in console_msgs[-20:]: p(f"    {line}")
            for line in errors[-5:]: p(f"    [error] {line}")
            return False
        finally:
            browser.close()


def main():
    p("=== PDF + DOCX 자체 검증 ===")
    p(f"URL: {LIVE_URL}")
    pdf_ok = test_one(PDF_FILE, "pdf", "savePdfBtn")
    docx_ok = test_one(DOCX_FILE, "docx", "saveDocxBtn")
    p("")
    p("=== 종합 ===")
    p(f"  PDF: {'PASS' if pdf_ok else 'FAIL'}")
    p(f"  DOCX: {'PASS' if docx_ok else 'FAIL'}")
    sys.exit(0 if (pdf_ok and docx_ok) else 1)


if __name__ == "__main__":
    main()
