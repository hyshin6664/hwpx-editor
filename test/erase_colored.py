"""
색깔 텍스트(빨강/파랑/초록) — 사용자가 [✏️ 글씨] 로 추가한 텍스트도 지워지는지.
"""
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright
try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

URL = "http://127.0.0.1:8765/?cb=" + str(int(time.time()*1000))
PDF = Path(r"C:\Users\신현식\Desktop\예약이체 내역.pdf")
OUT = Path(__file__).parent / "out_erase_colored"; OUT.mkdir(exist_ok=True)

def main():
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        page = b.new_context(viewport={"width": 1400, "height": 1100}).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function("() => window.__editorReady === true", timeout=60000)
        page.set_input_files("#picker", str(PDF))
        page.wait_for_function("() => window.__currentMode === 'pdf'", timeout=60000)
        page.wait_for_timeout(1000)

        # 빈 곳에 빨강·파랑·초록 텍스트 3개 추가
        colors = [('#ff0000', 'RED 빨강'), ('#0000ff', 'BLUE 파랑'), ('#008000', 'GREEN 초록')]
        for i, (color, text) in enumerate(colors):
            # 글씨 도구 + 색상 변경
            page.evaluate(f"""() => {{
              document.querySelector('button[data-tool=\\"text\\"]').click();
              const c = document.getElementById('pdfTextColor');
              c.value = '{color}';
              c.dispatchEvent(new Event('change'));
            }}""")
            page.wait_for_timeout(150)
            # canvas 의 빈 영역 (페이지 중간 하단) 클릭
            page.evaluate(f"""() => {{
              const ov = document.querySelectorAll('#pdfHost .pdf-overlay')[0];
              const c = document.querySelector('#pdfHost canvas');
              const r = c.getBoundingClientRect();
              // 빈 영역 좌표 (canvas 350x{300+30*0+i*40} 근처)
              const cx = r.left + 0.3 * r.width;
              const cy = r.top + (0.45 + {i}*0.04) * r.height;
              ov.dispatchEvent(new MouseEvent('click', {{bubbles:true, clientX:cx, clientY:cy, button:0, view:window}}));
            }}""")
            page.wait_for_timeout(300)
            page.keyboard.type(text, delay=20)
            page.keyboard.press("Enter")
            page.wait_for_timeout(300)

        # 추가된 text edit 수
        edits_n = page.evaluate("() => window.__pdfState.pages[0].edits.filter(e => e.type==='text').length")
        print(f"색깔 텍스트 추가됨: {edits_n}개")
        if edits_n != 3:
            print("⚠️ 추가 실패 — 글씨 도구 동작 확인 필요")

        page.screenshot(path=str(OUT / "1_after_add.png"))

        # erase-text 도구 → 추가된 텍스트 영역 드래그
        page.click('button[data-tool="erase-text"]')
        page.wait_for_timeout(200)

        # 각 색깔 텍스트 위치 영역 드래그
        edits_info = page.evaluate("""() => {
          return window.__pdfState.pages[0].edits.filter(e => e.type==='text').map(e => ({
            x: e.x, y: e.y, fontSize: e.fontSize || 12, text: e.text, color: e.color,
            pageH: window.__pdfState.pages[0].pdfPageHeight,
            scale: window.__pdfState.pages[0].scale,
          }));
        }""")
        print(f"\n사용자 추가 색깔 텍스트:")
        for e in edits_info:
            print(f"  {e['color']} '{e['text']}' (PDF x={e['x']:.0f},y={e['y']:.0f}, fs={e['fontSize']})")

        # 각 색깔 텍스트 영역 위에서 드래그 (PDF 좌표 → screen 좌표)
        for e in edits_info:
            page.evaluate(f"""() => {{
              const ov = document.querySelectorAll('#pdfHost .pdf-overlay')[0];
              const c = document.querySelector('#pdfHost canvas');
              const r = c.getBoundingClientRect();
              // PDF x → canvas x = x * scale
              const pageH = {e['pageH']}, scale = {e['scale']};
              const cw = c.width, ch = c.height;
              const cx0 = {e['x']} * scale;
              const cw0 = ({len(e['text'])} * {e['fontSize']} * 0.7) * scale;
              const ch0 = {e['fontSize']} * 1.4 * scale;
              const cy0 = (pageH - {e['y']} - {e['fontSize']}) * scale - ch0 * 0.2;
              const sx = r.left + (cx0 / cw) * r.width;
              const sy = r.top + (cy0 / ch) * r.height;
              const ex = r.left + ((cx0 + cw0) / cw) * r.width;
              const ey = r.top + ((cy0 + ch0) / ch) * r.height;
              const fire = (t,x,y) => ov.dispatchEvent(new MouseEvent(t, {{bubbles:true,clientX:x,clientY:y,button:0,view:window}}));
              fire('mousedown', sx, sy);
              fire('mousemove', (sx+ex)/2, (sy+ey)/2);
              fire('mousemove', ex, ey);
              fire('mouseup', ex, ey);
            }}""")
            page.wait_for_timeout(300)

        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "2_after_erase.png"))

        # 분석 — 색깔 텍스트 영역의 픽셀이 배경(흰색)으로 돌아왔는지
        analysis = page.evaluate("""() => {
          const pg = window.__pdfState.pages[0];
          const ctx = pg.canvas.getContext('2d');
          const edits = pg.edits.filter(e => e.type==='text');
          return edits.map(e => {
            const cx = e.x * pg.scale + (e.text.length * (e.fontSize || 12) * 0.35) * pg.scale;
            const cy = (pg.pdfPageHeight - e.y - (e.fontSize || 12)/2) * pg.scale;
            const px = Math.floor(cx), py = Math.floor(cy);
            if (px < 0 || py < 0 || px >= ctx.canvas.width || py >= ctx.canvas.height)
              return { text: e.text, color: e.color, status: 'out_of_canvas' };
            const d = ctx.getImageData(px, py, 1, 1).data;
            const bg = ctx.getImageData(Math.max(0, px - 30), py, 1, 1).data;
            const diff = Math.max(Math.abs(d[0]-bg[0]), Math.abs(d[1]-bg[1]), Math.abs(d[2]-bg[2]));
            return { text: e.text, color: e.color, pixel: [d[0],d[1],d[2]], bg: [bg[0],bg[1],bg[2]], diff };
          });
        }""")
        print("\n결과:")
        all_ok = True
        for a in analysis:
            ok = a.get('diff', 999) < 8
            mark = "✅" if ok else "❌"
            if not ok: all_ok = False
            print(f"  {mark} {a.get('color', '?')} '{a.get('text', '?')}' diff={a.get('diff', '?')} pixel={a.get('pixel', '?')} bg={a.get('bg', '?')}")
        b.close()
        print(f"\n📷 {OUT}/")
        sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()
