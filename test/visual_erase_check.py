"""
지우개 결과를 실제로 캡처해서 사용자가 본 화면 그대로 검사.
- 예약이체 PDF 열기
- 텍스트 박스 5개 정도 골라서 erase-text 실행
- 캡처 → before/after 비교
- 각 erase 영역의 픽셀을 분석: 배경과 얼마나 일치하는지
"""
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

URL = "http://127.0.0.1:8765/?cb=" + str(int(time.time()*1000))
PDF = Path(r"C:\Users\신현식\Desktop\예약이체 내역.pdf")
OUT = Path(__file__).parent / "out_visual"; OUT.mkdir(exist_ok=True)

def main():
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1400, "height": 1000})
        page = ctx.new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function("() => window.__editorReady === true", timeout=60000)
        page.set_input_files("#picker", str(PDF))
        page.wait_for_function("() => window.__currentMode === 'pdf'", timeout=60000)
        page.wait_for_timeout(1000)

        # before 스크린샷
        page.screenshot(path=str(OUT / "1_before.png"))

        # erase-text 도구
        page.click('button[data-tool="erase-text"]')
        page.wait_for_timeout(200)

        # 첫 5개 textBox 골라서 각각 erase (전체)
        result = page.evaluate("""() => {
          const pg = window.__pdfState.pages[0];
          // 표 안의 텍스트 — 페이지 중앙 근처 + 다양한 길이
          const all = pg.textBoxes.filter(tb => tb.str && tb.str.trim().length > 0);
          // y 좌표가 페이지 중간(canvas height 의 30~70%) + str 이 숫자/한글 포함
          const ch = pg.canvas.height;
          const tbs = all.filter(tb => tb.y > 150 && tb.y < 350 && tb.w > 5).slice(0, 5);
          if (tbs.length === 0) tbs.push(...all.slice(0, 5));
          // 각 textBox 픽셀 영역 캡처 (before)
          const ctx = pg.canvas.getContext('2d');
          const beforeSamples = tbs.map(tb => {
            // bbox 중앙 픽셀 (글자 위치)
            const cx = Math.floor(tb.x + tb.w/2);
            const cy = Math.floor(tb.y + tb.h/2);
            const d = ctx.getImageData(cx, cy, 1, 1).data;
            // 외곽 1px 픽셀 (배경)
            const bg = ctx.getImageData(Math.max(0,Math.floor(tb.x-3)), Math.floor(tb.y), 1, 1).data;
            return { str: tb.str, bbox: tb, centerColor: [d[0],d[1],d[2]], bgColor: [bg[0],bg[1],bg[2]] };
          });
          return { tbs, beforeSamples };
        }""")

        print("Before erase, 첫 5개 textBox:")
        for s in result['beforeSamples']:
            print(f"  '{s['str']}' bbox={s['bbox']['x']:.0f},{s['bbox']['y']:.0f} {s['bbox']['w']:.0f}x{s['bbox']['h']:.0f} center={s['centerColor']} bg={s['bgColor']}")

        # 각 textBox 를 정확히 dragging — drag 영역과 textBox 가 정확히 일치하게
        for i, tb in enumerate(result['tbs']):
            # canvas 좌표 → screen 좌표
            page.evaluate(f"""() => {{
              const ov = document.querySelectorAll('#pdfHost .pdf-overlay')[0];
              const c = document.querySelector('#pdfHost canvas');
              const r = c.getBoundingClientRect();
              const sx = r.left + ({tb['x']} / c.width) * r.width;
              const sy = r.top + ({tb['y']} / c.height) * r.height;
              const ex = r.left + (({tb['x']} + {tb['w']}) / c.width) * r.width;
              const ey = r.top + (({tb['y']} + {tb['h']}) / c.height) * r.height;
              const fire = (type, x, y) => ov.dispatchEvent(new MouseEvent(type, {{bubbles:true,clientX:x,clientY:y,button:0,view:window}}));
              fire('mousedown', sx, sy);
              fire('mousemove', (sx+ex)/2, (sy+ey)/2);
              fire('mousemove', ex, ey);
              fire('mouseup', ex, ey);
            }}""")
            page.wait_for_timeout(150)

        # after 스크린샷 + 픽셀 분석
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "2_after.png"))

        analysis = page.evaluate("""() => {
          const pg = window.__pdfState.pages[0];
          const all = pg.textBoxes.filter(tb => tb.str && tb.str.trim().length > 0);
          const ch = pg.canvas.height;
          const tbs = all.filter(tb => tb.y > 150 && tb.y < 350 && tb.w > 5).slice(0, 5);
          if (tbs.length === 0) tbs.push(...all.slice(0, 5));
          const ctx = pg.canvas.getContext('2d');
          return tbs.map(tb => {
            // bbox 안 9개 sample 픽셀 vs 외곽 배경
            const samples = [];
            for (let dx = 0; dx < 3; dx++) {
              for (let dy = 0; dy < 3; dy++) {
                const px = Math.floor(tb.x + tb.w * (0.2 + dx*0.3));
                const py = Math.floor(tb.y + tb.h * (0.2 + dy*0.3));
                const d = ctx.getImageData(px, py, 1, 1).data;
                samples.push([d[0],d[1],d[2]]);
              }
            }
            const bg = ctx.getImageData(Math.max(0,Math.floor(tb.x-3)), Math.floor(tb.y), 1, 1).data;
            const bgColor = [bg[0],bg[1],bg[2]];
            // 각 sample 의 배경과의 차이
            const diffs = samples.map(s => Math.max(Math.abs(s[0]-bgColor[0]), Math.abs(s[1]-bgColor[1]), Math.abs(s[2]-bgColor[2])));
            return { str: tb.str, samples, bgColor, maxDiff: Math.max(...diffs), avgDiff: diffs.reduce((a,b)=>a+b,0)/diffs.length };
          });
        }""")

        print("\nAfter erase 분석 (배경과 차이가 크면 흔적이 보이는 것):")
        for a in analysis:
            verdict = "✅ 깨끗" if a['maxDiff'] < 10 else ("⚠️ 약간 흔적" if a['maxDiff'] < 30 else "❌ 명확한 흔적")
            print(f"  {verdict} '{a['str']}' maxDiff={a['maxDiff']} avgDiff={a['avgDiff']:.1f} bg={a['bgColor']}")

        b.close()
        print(f"\n📷 스크린샷 저장됨:\n  {OUT}/1_before.png\n  {OUT}/2_after.png")

if __name__ == "__main__":
    main()
