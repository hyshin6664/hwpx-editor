"""
실제 PDF 다양한 위치(회색헤더/흰배경/굵은글씨/숫자/한글)에서 지우개 완벽 검증.
배포(github.io) 에서.
"""
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright
try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

URL = "https://hyshin6664.github.io/hwpx-editor/?cb=" + str(int(time.time()*1000))
PDF = Path(r"C:\Users\신현식\Desktop\예약이체 내역.pdf")
OUT = Path(__file__).parent / "out_erase_perfect"; OUT.mkdir(exist_ok=True)

def main():
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        page = b.new_context(viewport={"width": 1400, "height": 1100}).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function("() => window.__editorReady === true", timeout=60000)
        page.set_input_files("#picker", str(PDF))
        page.wait_for_function("() => window.__currentMode === 'pdf'", timeout=60000)
        page.wait_for_timeout(1500)

        # 다양한 위치/길이의 textBox 20개 무작위 골라 지우기
        targets = page.evaluate("""() => {
          const all = window.__pdfState.pages[0].textBoxes.filter(tb => tb.str && tb.str.trim());
          // 헤더(회색) y=180-200, 데이터(흰) y=200-260, 합계 y=270 근처
          const header = all.filter(tb => tb.y >= 180 && tb.y < 200).slice(0, 8);
          const data   = all.filter(tb => tb.y >= 200 && tb.y < 260).slice(0, 8);
          const total  = all.filter(tb => tb.y >= 265 && tb.y < 290).slice(0, 4);
          return [...header, ...data, ...total];
        }""")
        print(f"검증 대상: {len(targets)}개 textBox")

        # 도구 활성
        page.click('button[data-tool="erase-text"]')
        page.wait_for_timeout(200)

        # 각 textBox 정확히 그 영역만 지움
        for tb in targets:
            page.evaluate(f"""() => {{
              const ov = document.querySelectorAll('#pdfHost .pdf-overlay')[0];
              const c = document.querySelector('#pdfHost canvas');
              const r = c.getBoundingClientRect();
              const sx = r.left + ({tb['x']} / c.width) * r.width;
              const sy = r.top + ({tb['y']} / c.height) * r.height;
              const ex = r.left + (({tb['x']} + {tb['w']}) / c.width) * r.width;
              const ey = r.top + (({tb['y']} + {tb['h']}) / c.height) * r.height;
              const fire = (t, x, y) => ov.dispatchEvent(new MouseEvent(t, {{bubbles:true,clientX:x,clientY:y,button:0,view:window}}));
              fire('mousedown', sx, sy);
              fire('mousemove', (sx+ex)/2, (sy+ey)/2);
              fire('mousemove', ex, ey);
              fire('mouseup', ex, ey);
            }}""")
            page.wait_for_timeout(80)

        page.wait_for_timeout(500)
        # 분석 — 각 영역 안 픽셀 vs 외곽 배경
        analysis = page.evaluate("""() => {
          const targets = arguments[0];
          const ctx = window.__pdfState.pages[0].canvas.getContext('2d');
          return targets.map(tb => {
            // bbox 안 9개 sample
            const samples = [];
            for (let dx = 0; dx < 3; dx++) {
              for (let dy = 0; dy < 3; dy++) {
                const px = Math.floor(tb.x + tb.w*(0.15 + dx*0.35));
                const py = Math.floor(tb.y + tb.h*(0.15 + dy*0.35));
                const d = ctx.getImageData(px, py, 1, 1).data;
                samples.push([d[0],d[1],d[2]]);
              }
            }
            // 외곽 배경 (5px 외곽)
            const bgX = Math.max(0, Math.floor(tb.x - 5));
            const bgY = Math.floor(tb.y);
            const bg = ctx.getImageData(bgX, bgY, 1, 1).data;
            const bgC = [bg[0],bg[1],bg[2]];
            const diffs = samples.map(s => Math.max(Math.abs(s[0]-bgC[0]),Math.abs(s[1]-bgC[1]),Math.abs(s[2]-bgC[2])));
            return { str: tb.str, maxDiff: Math.max(...diffs), bgColor: bgC };
          });
        }""", targets)

        clean = [a for a in analysis if a['maxDiff'] < 5]
        slight = [a for a in analysis if 5 <= a['maxDiff'] < 15]
        bad = [a for a in analysis if a['maxDiff'] >= 15]
        print(f"\n결과:")
        print(f"  ✅ 완벽 (diff<5):   {len(clean)}/{len(analysis)}")
        print(f"  ⚠️  미세 (diff<15): {len(slight)}/{len(analysis)}")
        print(f"  ❌ 흔적 (diff>=15): {len(bad)}/{len(analysis)}")
        if bad:
            print("\n흔적 남은 textBoxes:")
            for a in bad:
                print(f"   '{a['str']}' diff={a['maxDiff']} bg={a['bgColor']}")

        page.screenshot(path=str(OUT / "after_all_erase.png"))
        b.close()
        print(f"\n📷 {OUT}/after_all_erase.png")

if __name__ == "__main__":
    main()
