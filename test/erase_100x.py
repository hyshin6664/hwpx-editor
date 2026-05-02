"""
실제 PDF textBoxes 100+ 개 모두 지우고 각각 픽셀-레벨 검증.
maxDiff < 3 → 완벽 (사람 눈으로 분간 불가)
"""
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright
try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

URL = "https://hyshin6664.github.io/hwpx-editor/?cb=" + str(int(time.time()*1000))
PDF = Path(r"C:\Users\신현식\Desktop\예약이체 내역.pdf")
OUT = Path(__file__).parent / "out_erase_100x"; OUT.mkdir(exist_ok=True)

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

        # 원본 캡처
        page.locator("#pdfHost canvas").first.screenshot(path=str(OUT / "0_before.png"))

        # 모든 textBoxes 가져오기
        N = page.evaluate("() => window.__pdfState.pages[0].textBoxes.length")
        print(f"총 textBoxes: {N}개")

        # 도구 활성
        page.click('button[data-tool="erase-text"]')
        page.wait_for_timeout(200)

        # 100+ 개 무작위 (또는 처음 100개) 지우기
        count = min(150, N)
        print(f"\n{count}개 지우개 시작...")

        # JS 측에서 한 번에 처리 (각각 dispatch 하면 너무 느림)
        result = page.evaluate(f"""async () => {{
          const pg = window.__pdfState.pages[0];
          const boxes = pg.textBoxes.slice(0, {count}).filter(tb => tb.str && tb.str.trim());
          const ov = document.querySelectorAll('#pdfHost .pdf-overlay')[0];
          const c = document.querySelector('#pdfHost canvas');
          const r = c.getBoundingClientRect();
          let processed = 0;
          for (const tb of boxes) {{
            const sx = r.left + (tb.x / c.width) * r.width;
            const sy = r.top + (tb.y / c.height) * r.height;
            const ex = r.left + ((tb.x + tb.w) / c.width) * r.width;
            const ey = r.top + ((tb.y + tb.h) / c.height) * r.height;
            const fire = (t, x, y) => ov.dispatchEvent(new MouseEvent(t, {{bubbles:true,clientX:x,clientY:y,button:0,view:window}}));
            fire('mousedown', sx, sy);
            fire('mousemove', (sx+ex)/2, (sy+ey)/2);
            fire('mousemove', ex, ey);
            fire('mouseup', ex, ey);
            processed++;
            await new Promise(r => setTimeout(r, 5));
          }}
          return processed;
        }}""")
        print(f"실행: {result}개")

        page.wait_for_timeout(1000)
        page.locator("#pdfHost canvas").first.screenshot(path=str(OUT / "1_after.png"))

        # 픽셀 분석 — 각 textBox 영역의 최대 차이 측정
        analysis = page.evaluate(f"""() => {{
          const pg = window.__pdfState.pages[0];
          const ctx = pg.canvas.getContext('2d');
          const boxes = pg.textBoxes.slice(0, {count}).filter(tb => tb.str && tb.str.trim());
          return boxes.map(tb => {{
            // bbox 안 9개 sample
            const samples = [];
            for (let dx = 0; dx < 3; dx++) for (let dy = 0; dy < 3; dy++) {{
              const px = Math.floor(tb.x + tb.w*(0.15 + dx*0.35));
              const py = Math.floor(tb.y + tb.h*(0.15 + dy*0.35));
              if (px < 0 || py < 0 || px >= ctx.canvas.width || py >= ctx.canvas.height) continue;
              const d = ctx.getImageData(px, py, 1, 1).data;
              samples.push([d[0],d[1],d[2]]);
            }}
            // 외곽 배경 (좌측 5px)
            const bgX = Math.max(0, Math.floor(tb.x - 5));
            const bgY = Math.floor(tb.y + tb.h/2);
            const bg = ctx.getImageData(bgX, bgY, 1, 1).data;
            const bgC = [bg[0],bg[1],bg[2]];
            const diffs = samples.map(s => Math.max(Math.abs(s[0]-bgC[0]),Math.abs(s[1]-bgC[1]),Math.abs(s[2]-bgC[2])));
            return {{ str: tb.str, maxDiff: diffs.length ? Math.max(...diffs) : 0, bg: bgC }};
          }});
        }}""")

        perfect = [a for a in analysis if a['maxDiff'] < 3]
        good    = [a for a in analysis if 3 <= a['maxDiff'] < 8]
        slight  = [a for a in analysis if 8 <= a['maxDiff'] < 20]
        bad     = [a for a in analysis if a['maxDiff'] >= 20]

        print(f"\n{'='*50}")
        print(f"📊 결과 ({len(analysis)}개)")
        print(f"{'='*50}")
        print(f"  ✅ 완벽 (diff<3) :  {len(perfect):>3} / {len(analysis)} ({len(perfect)*100/len(analysis):.1f}%)")
        print(f"  🆗 양호 (3~7)   :  {len(good):>3} / {len(analysis)}")
        print(f"  ⚠️  미세 (8~19)  :  {len(slight):>3} / {len(analysis)}")
        print(f"  ❌ 흔적 (>=20) :  {len(bad):>3} / {len(analysis)}")

        if bad:
            print("\n흔적 남은 textBoxes (상위 20개):")
            for a in sorted(bad, key=lambda x: -x['maxDiff'])[:20]:
                print(f"   '{a['str']}' diff={a['maxDiff']} bg={a['bg']}")
        if slight:
            print("\n미세 흔적 (상위 10개):")
            for a in sorted(slight, key=lambda x: -x['maxDiff'])[:10]:
                print(f"   '{a['str']}' diff={a['maxDiff']}")

        b.close()
        print(f"\n📷 {OUT}/")
        return len(perfect) + len(good) >= len(analysis) * 0.95

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
