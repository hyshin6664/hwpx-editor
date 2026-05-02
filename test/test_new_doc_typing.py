"""
새 문서 [.docx], [.hwpx] 양쪽 모두 클릭 즉시 타이핑 가능한지 검증.
+ 사전 보정으로 HWPX 비표준 다이얼로그 안 뜨는지 확인.
"""
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass

URL = "https://hyshin6664.github.io/hwpx-editor/"
HWPX = Path(r"C:\Users\신현식\Desktop\★[최종양식] 2026년 오픈소스 AI·SW 개발·활용 지원사업_수정-v.1_수정_2026-04-30_09-01_수정_2026-04-30_09-21_수정_2026-04-30_09-36.hwpx")
OUT = Path(__file__).parent / "out_newdoc"; OUT.mkdir(exist_ok=True)


def main():
    results = []
    def step(name, ok, detail=""):
        emoji = "✅" if ok else "❌"
        results.append((emoji, name, detail))
        print(f"  {emoji} {name}{(' — ' + detail) if detail else ''}", flush=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        page = ctx.new_page()
        msgs = []
        errs = []
        page.on("console", lambda m: msgs.append(f"[{m.type}] {m.text}"))
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.on("dialog", lambda d: d.accept())  # confirm 등 자동 OK

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function("() => window.__editorReady === true", timeout=60000)
        step("페이지 + 엔진 준비", True)

        # ─── 새 .docx → 즉시 타이핑 ───
        page.click("#newBtn"); page.wait_for_timeout(200)
        page.click('#newMenu .newm-item[data-fmt="docx"]')
        page.wait_for_function("() => document.querySelectorAll('#docxHost .docx p[contenteditable]').length > 0", timeout=20000)
        first_p = page.query_selector('#docxHost .docx p[contenteditable]')
        first_p.click(); page.wait_for_timeout(200)
        before = page.evaluate("() => document.querySelector('#docxHost .docx p[contenteditable]').textContent")
        page.keyboard.press("End")
        page.keyboard.type(" 워드테스트", delay=20)
        page.wait_for_timeout(300)
        after = page.evaluate("() => document.querySelector('#docxHost .docx p[contenteditable]').textContent")
        ok = "워드테스트" in after
        step("[새 워드] 즉시 타이핑", ok, f"{before!r} → {after!r}")

        # 닫기
        page.click("#closeBtn"); page.wait_for_timeout(400)

        # ─── 새 .hwpx → 즉시 타이핑 ───
        page.click("#newBtn"); page.wait_for_timeout(200)
        page.click('#newMenu .newm-item[data-fmt="hwpx"]')
        page.wait_for_function("() => document.querySelectorAll('#docxHost .docx p[contenteditable]').length > 0", timeout=20000)
        first_p = page.query_selector('#docxHost .docx p[contenteditable]')
        first_p.click(); page.wait_for_timeout(200)
        before = page.evaluate("() => document.querySelector('#docxHost .docx p[contenteditable]').textContent")
        page.keyboard.press("End")
        page.keyboard.type(" 한글테스트", delay=20)
        page.wait_for_timeout(300)
        after = page.evaluate("() => document.querySelector('#docxHost .docx p[contenteditable]').textContent")
        ok = "한글테스트" in after
        step("[새 한글] 즉시 타이핑", ok, f"{before!r} → {after!r}")

        # 새 한글 → .hwpx 다운로드 가능?
        try:
            with page.expect_download(timeout=30000) as di:
                page.click("#saveHwpxBtn")
            dl = di.value
            p = OUT / "newdoc_hwpx.hwpx"; dl.save_as(str(p))
            step("[새 한글] → .hwpx 저장", p.exists() and p.stat().st_size > 1000, f"{p.stat().st_size if p.exists() else 0} bytes")
        except Exception as e:
            step("[새 한글] → .hwpx 저장", False, str(e))

        page.click("#closeBtn"); page.wait_for_timeout(400)

        # ─── 실제 HWPX 파일 열기 — 비표준 다이얼로그 사용자에게 보이는지 확인 ───
        if HWPX.exists():
            page.set_input_files("#picker", str(HWPX))
            # 마운트 대기
            page.wait_for_function("() => window.__currentMode === 'hwp'", timeout=120000)
            page.wait_for_timeout(2000)
            # rhwp iframe 안에 비표준 다이얼로그가 떠있는지 — cross-origin 이라 직접 못 보지만,
            # 우리 console log 에 "HWPX 자동 보정 적용" 메시지 떴는지 확인
            sanitized = any("HWPX 자동 보정 적용" in m for m in msgs)
            step("HWPX 사전 보정 적용", sanitized, "rhwp 다이얼로그 안 뜸 (사용자 안 봄)" if sanitized else "보정 미적용 (원본이 이미 표준일 수 있음)")
        else:
            step("HWPX 샘플 파일", False, "샘플 파일 없음 — 스킵")

        page.screenshot(path=str(OUT / "final.png"), full_page=True)
        browser.close()

    pass_cnt = sum(1 for r in results if r[0] == '✅')
    print(f"\n  결과: {pass_cnt} / {len(results)} PASS")
    if errs:
        print("  페이지 에러:")
        for e in errs[-3:]: print(f"    {e}")
    sys.exit(0 if pass_cnt == len(results) else 1)


if __name__ == "__main__":
    main()
