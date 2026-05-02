"""
PDF→Word 변환 결과의 셀 색·텍스트 색 검증
"""
import sys, time, zipfile, re
from pathlib import Path
from playwright.sync_api import sync_playwright
try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

URL = "https://hyshin6664.github.io/hwpx-editor/?cb=" + str(int(time.time()*1000))
PDF = Path(r"C:\Users\신현식\Desktop\예약이체 내역.pdf")
OUT = Path(__file__).parent / "out_pdf_colors"; OUT.mkdir(exist_ok=True)

def main():
    if not PDF.exists():
        print(f"❌ PDF 없음: {PDF}"); sys.exit(1)
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        page = b.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function("() => window.__editorReady === true", timeout=60000)
        page.set_input_files("#picker", str(PDF))
        page.wait_for_function("() => window.__currentMode === 'pdf'", timeout=60000)
        page.wait_for_timeout(1500)

        # textBoxes / fillRects / lineRects 통계
        info = page.evaluate("""() => {
          const pg = window.__pdfState.pages[0];
          // textBox color 분포
          const tcs = (pg.textBoxes || []).map(tb => tb.color).filter(c => c);
          const colorBins = {};
          tcs.forEach(c => { const k = c.join(','); colorBins[k] = (colorBins[k]||0)+1; });
          return {
            textBoxes: pg.textBoxes ? pg.textBoxes.length : 0,
            fillRects: pg.fillRects ? pg.fillRects.length : 0,
            lineRects: pg.lineRects ? pg.lineRects.length : 0,
            textColors: colorBins,
            sampleFillRects: (pg.fillRects || []).slice(0, 5).map(f => ({color:f.color, x:Math.round(f.x), y:Math.round(f.y), w:Math.round(f.w), h:Math.round(f.h)})),
          };
        }""")
        print("페이지 분석:")
        print(f"  textBoxes: {info['textBoxes']}개")
        print(f"  fillRects (셀 배경): {info['fillRects']}개")
        print(f"  lineRects (테두리): {info['lineRects']}개")
        print(f"  텍스트 색상 분포: {info['textColors']}")
        print(f"  샘플 fillRect: {info['sampleFillRects']}")

        # DOCX 변환
        with page.expect_download(timeout=120000) as di:
            page.evaluate("document.getElementById('saveDocxBtn').click()")
        dl = di.value
        out = OUT / "color_test.docx"; dl.save_as(str(out))

        # docx 안에 색상 정보 있는지
        with zipfile.ZipFile(out) as z:
            xml = z.read("word/document.xml").decode("utf-8")
            shading = re.findall(r'<w:shd[^/]*w:fill="([^"]+)"', xml)
            colors  = re.findall(r'<w:color\s+w:val="([^"]+)"', xml)
            tbl_borders = re.findall(r'<w:tcBorders>', xml)
            print(f"\n변환된 DOCX:")
            print(f"  셀 shading 수: {len(shading)} → {set(shading)}")
            print(f"  텍스트 color 수: {len(colors)} → {set(colors)}")
            print(f"  cell borders: {tbl_borders}")
        b.close()

if __name__ == "__main__":
    main()
