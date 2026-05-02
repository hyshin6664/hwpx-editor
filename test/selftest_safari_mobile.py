"""
WebKit (Safari) 엔진 + 아이폰 viewport 로 모바일 텍스트 입력 검증.
- 새 docx 만들고 첫 문단에 키보드로 입력 → 글자가 표시되는지
- font-size 16px+ 적용 (iOS auto-zoom 방지)
- contenteditable -webkit-user-select 검증
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass

URL = "https://hyshin6664.github.io/hwpx-editor/"
OUT_DIR = Path(__file__).parent / "out_safari"; OUT_DIR.mkdir(exist_ok=True)


def run(engine_name, launch_fn, viewport, ua=None):
    print(f"\n══════════════ {engine_name} ══════════════", flush=True)
    results = []
    def step(name, ok, detail=""):
        emoji = "✅" if ok else "❌"
        results.append((emoji, name, detail))
        print(f"  {emoji} {name}{(' — ' + detail) if detail else ''}", flush=True)

    with sync_playwright() as pw:
        browser = launch_fn(pw)
        ctx_args = {"viewport": viewport}
        if ua: ctx_args["user_agent"] = ua
        ctx = browser.new_context(**ctx_args, accept_downloads=True)
        page = ctx.new_page()
        msgs = []
        errs = []
        page.on("console", lambda m: msgs.append(f"[{m.type}] {m.text}"))
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.on("dialog", lambda d: d.accept())

        try:
            page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_function("() => document.getElementById('newBtn') != null", timeout=15000)
            step("페이지 로드", True)

            # 새 docx — 모바일이면 햄버거 통해, 데스크톱이면 직접
            is_mobile = viewport["width"] < 720
            if is_mobile:
                page.click("#hamburgerBtn"); page.wait_for_timeout(300)
                page.click('#hamDrawer .ham-item[data-act="new-docx"]')
            else:
                page.click("#newBtn"); page.wait_for_timeout(200)
                page.click('#newMenu .newm-item[data-fmt="docx"]')
            page.wait_for_function("() => document.querySelectorAll('#docxHost .docx p[contenteditable]').length > 0", timeout=20000)
            step("새 docx 마운트", True, "via 햄버거" if is_mobile else "via newBtn")

            # 첫 문단 클릭 + 키보드 입력
            first_p = page.query_selector('#docxHost .docx p[contenteditable]')
            first_p.scroll_into_view_if_needed()
            first_p.click()
            page.wait_for_timeout(300)

            # 포커스 확인
            focused = page.evaluate("() => document.activeElement && document.activeElement.tagName === 'P' && document.activeElement.contentEditable === 'true'")
            step("contenteditable 포커스", focused)

            # font-size 16px+ 검증
            font_size = page.evaluate("() => parseFloat(getComputedStyle(document.querySelector('#docxHost .docx p[contenteditable]')).fontSize)")
            step(f"폰트 16px+ (iOS auto-zoom 방지)", font_size >= 16, f"{font_size}px")

            # -webkit-user-select 검증
            user_sel = page.evaluate("() => getComputedStyle(document.querySelector('#docxHost .docx p[contenteditable]')).webkitUserSelect || getComputedStyle(document.querySelector('#docxHost .docx p[contenteditable]')).userSelect")
            step("-webkit-user-select: text", user_sel == 'text', f"{user_sel}")

            # 키보드 타이핑
            before = page.evaluate("() => document.querySelector('#docxHost .docx p[contenteditable]').textContent")
            page.keyboard.type("안녕하세요", delay=30)
            page.wait_for_timeout(500)
            after = page.evaluate("() => document.querySelector('#docxHost .docx p[contenteditable]').textContent")
            inserted = after != before and "안녕" in after
            step(f"한글 키보드 입력", inserted, f"전={before!r} → 후={after!r}")

            # ASCII 입력
            page.keyboard.type(" hello world", delay=20)
            page.wait_for_timeout(300)
            after2 = page.evaluate("() => document.querySelector('#docxHost .docx p[contenteditable]').textContent")
            step("ASCII 키보드 입력", "hello" in after2, after2[:60])

            # 저장 — 모바일은 하단 [💾 저장], 데스크톱은 #saveDocxBtn
            try:
                save_selector = '#mbSaveBtn' if is_mobile else '#saveDocxBtn'
                with page.expect_download(timeout=20000) as di:
                    if is_mobile:
                        page.click(save_selector)
                    else:
                        page.evaluate("document.getElementById('saveDocxBtn').click()")
                dl = di.value
                p = OUT_DIR / f"saved_{engine_name}.docx"; dl.save_as(str(p))
                step("저장 + 다운로드", p.exists() and p.stat().st_size > 1000, f"{p.stat().st_size if p.exists() else 0} bytes")
            except Exception as e:
                step("저장 + 다운로드", False, str(e))

            page.screenshot(path=str(OUT_DIR/f"{engine_name}_after.png"), full_page=True)
        except Exception as e:
            print(f"EXCEPTION: {e}")
            for m in msgs[-15:]: print(f"  {m}")
            for er in errs[-5:]: print(f"  ERR {er}")
        finally:
            browser.close()

    pass_count = sum(1 for r in results if r[0] == '✅')
    print(f"\n  결과: {pass_count} / {len(results)} PASS", flush=True)
    return pass_count == len(results)


def main():
    iphone_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
    iphone_vp = {"width": 390, "height": 844}
    desktop_vp = {"width": 1280, "height": 900}

    ok1 = run("WebKit/iPhone (Safari 엔진)",
              lambda pw: pw.webkit.launch(headless=True),
              iphone_vp, iphone_ua)
    ok2 = run("WebKit/맥 데스크톱 (Safari 엔진)",
              lambda pw: pw.webkit.launch(headless=True),
              desktop_vp, "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15")
    ok3 = run("Chromium 모바일",
              lambda pw: pw.chromium.launch(headless=True),
              iphone_vp, iphone_ua)

    print("\n═══════════════ 종합 ═══════════════")
    print(f"  iPhone Safari: {'PASS' if ok1 else 'FAIL'}")
    print(f"  Mac Safari   : {'PASS' if ok2 else 'FAIL'}")
    print(f"  Mobile Chrome: {'PASS' if ok3 else 'FAIL'}")
    sys.exit(0 if (ok1 and ok2 and ok3) else 1)


if __name__ == "__main__":
    main()
