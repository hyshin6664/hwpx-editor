"""
실제 PDF 로 ✂️ 글자만 지우기 검증
- 사용자 PDF 열고 → erase-text 도구 → 텍스트 영역 일부 드래그 → edits 확인
- 저장된 PDF 가 실제로 다운로드 되는지
"""
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

URL = "https://hyshin6664.github.io/hwpx-editor/?cb=" + str(int(time.time()*1000))
PDF = Path(r"C:\Users\신현식\Desktop\예약이체 내역.pdf")
OUT = Path(__file__).parent / "out_erase_text"; OUT.mkdir(exist_ok=True)

def main():
    print("=" * 60)
    print(" ✂️ 글자만 지우기 실제 PDF 테스트")
    print("=" * 60)
    if not PDF.exists():
        print(f"❌ PDF 파일 없음: {PDF}")
        return

    results = []
    def step(name, ok, detail=""):
        emoji = "✅" if ok else "❌"
        results.append((emoji, name, detail))
        print(f"  {emoji} {name}{(' — ' + detail) if detail else ''}", flush=True)

    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        page = ctx.new_page()
        msgs = []
        page.on("console", lambda m: msgs.append(f"[{m.type}] {m.text}"))
        page.on("pageerror", lambda e: msgs.append(f"[ERR] {e}"))
        page.on("dialog", lambda d: d.accept())

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function("() => window.__editorReady === true", timeout=60000)
        step("페이지 로드", True)

        page.set_input_files("#picker", str(PDF))
        page.wait_for_function("() => window.__currentMode === 'pdf'", timeout=60000)
        page.wait_for_timeout(800)
        step("PDF 로드", True)

        # textBoxes 수집됐는지
        n = page.evaluate("() => window.__pdfState.pages[0].textBoxes ? window.__pdfState.pages[0].textBoxes.length : -1")
        step("textBoxes 추출", n > 0, f"{n}개")

        # 첫 textBox 정보 확인
        first = page.evaluate("""() => { const tb = window.__pdfState.pages[0].textBoxes[0];
          return tb ? { str:tb.str, x:Math.round(tb.x), y:Math.round(tb.y), w:Math.round(tb.w), h:Math.round(tb.h) } : null; }""")
        step("첫 텍스트박스 좌표", bool(first), str(first))

        # erase-text 도구 활성
        page.click('button[data-tool="erase-text"]')
        page.wait_for_timeout(200)
        tool = page.evaluate("() => window.__pdfState.tool")
        step("도구 erase-text 활성", tool == 'erase-text', tool)

        # canvas 위에서 첫 텍스트박스의 절반만 드래그 — 교집합 처리 검증
        canvas = page.query_selector("#pdfHost canvas")
        canvas.scroll_into_view_if_needed()
        page.wait_for_timeout(200)
        cb = canvas.bounding_box()
        # textBox 좌표(canvas 픽셀 기준) 그대로 활용
        # canvas 의 화면 좌표로 변환: cb.x + (tb.x / canvas.width) * cb.width
        canvas_w = page.evaluate("() => document.querySelector('#pdfHost canvas').width")
        canvas_h = page.evaluate("() => document.querySelector('#pdfHost canvas').height")
        scale_x = cb['width'] / canvas_w
        scale_y = cb['height'] / canvas_h
        # 첫 textBox 의 좌측 절반 드래그
        if first:
            sx = cb['x'] + first['x'] * scale_x
            sy = cb['y'] + first['y'] * scale_y
            ex = cb['x'] + (first['x'] + first['w']/2) * scale_x  # 절반만
            ey = cb['y'] + (first['y'] + first['h']) * scale_y
            page.mouse.move(sx, sy)
            page.mouse.down()
            page.mouse.move(ex, ey, steps=10)
            page.mouse.up()
            page.wait_for_timeout(500)

        edits = page.evaluate("() => window.__pdfState.pages[0].edits.length")
        step("erase-text edit 추가", edits > 0, f"{edits}개 edit")

        edit_info = page.evaluate("""() => { const e = window.__pdfState.pages[0].edits.find(e => e.type==='erase-text');
          return e ? { boxes: e.boxes.length, hits: e._displayPx.hits.length } : null; }""")
        step("edit 구조", edit_info and edit_info.get('boxes', 0) > 0, str(edit_info))

        # 저장
        try:
            with page.expect_download(timeout=30000) as di:
                page.evaluate("document.getElementById('savePdfBtn').click()")
            dl = di.value
            p = OUT / "erase_text_result.pdf"; dl.save_as(str(p))
            sz = p.stat().st_size
            step("PDF 저장", sz > 1000, f"{sz} bytes → {p}")
        except Exception as e:
            step("PDF 저장", False, str(e))

        page.screenshot(path=str(OUT / "after.png"), full_page=True)
        b.close()

    print(f"\n결과: {sum(1 for r in results if r[0]=='✅')} / {len(results)} PASS")
    for r in results:
        if r[0] == '❌': print(f"  ❌ {r[1]} — {r[2]}")
    sys.exit(0 if all(r[0]=='✅' for r in results) else 1)

if __name__ == "__main__":
    main()
