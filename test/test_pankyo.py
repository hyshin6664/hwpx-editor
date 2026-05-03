"""
판교글로벌비즈센터 PDF 진단 — 사용자 보고 이슈 확인:
1) 표가 많거나 작거나
2) 텍스트 불명확 (그림으로 인식하는 케이스)
3) 모바일 필치/줌 문제
"""
import sys, time, zipfile, re
from pathlib import Path
from playwright.sync_api import sync_playwright
try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

URL = "https://hyshin6664.github.io/hwpx-editor/?cb=" + str(int(time.time()*1000))
PDF = Path(r"C:\Users\신현식\Desktop\1.판교글로벌비즈센터 산업시설(B-301~303호) 처분 수의계약 공고문.pdf")
OUT = Path(__file__).parent / "out_pankyo"; OUT.mkdir(exist_ok=True)

def main():
    if not PDF.exists():
        print(f"❌ PDF 없음"); sys.exit(1)
    print(f"📄 {PDF.name} ({PDF.stat().st_size/1024:.1f} KB)\n")

    results = []
    def step(name, ok, detail=""):
        em = "✅" if ok else "❌"
        results.append((em, name, detail))
        print(f"  {em} {name}{(' — ' + detail) if detail else ''}")

    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        page = ctx.new_page()
        msgs = []
        page.on("console", lambda m: msgs.append(f"[{m.type}] {m.text[:200]}"))
        page.on("pageerror", lambda e: msgs.append(f"[ERR] {str(e)[:200]}"))
        page.on("dialog", lambda d: d.accept())

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function("() => window.__editorReady === true", timeout=60000)
        page.set_input_files("#picker", str(PDF))
        page.wait_for_function("() => window.__currentMode === 'pdf'", timeout=120000)
        page.wait_for_timeout(2500)

        # 페이지/textBoxes 정보
        info = page.evaluate("""() => {
          const pages = window.__pdfState.pages;
          return pages.map((pg, i) => ({
            page: i+1,
            textBoxes: pg.textBoxes ? pg.textBoxes.length : 0,
            lineRects: pg.lineRects ? pg.lineRects.length : 0,
            fillRects: pg.fillRects ? pg.fillRects.length : 0,
            canvasW: pg.canvas.width, canvasH: pg.canvas.height,
          }));
        }""")
        print(f"\n📊 PDF 페이지별 분석 (총 {len(info)} 페이지):")
        for p in info:
            empty = p['textBoxes'] == 0
            mark = "📷" if empty else "📝"
            print(f"  {mark} 페이지 {p['page']}: textBoxes={p['textBoxes']}, lineRects={p['lineRects']}, fillRects={p['fillRects']}, canvas={p['canvasW']}x{p['canvasH']}")

        empty_pages = [p for p in info if p['textBoxes'] == 0]
        step(f"모든 페이지 텍스트 추출 가능", len(empty_pages) == 0,
             f"빈 페이지 {len(empty_pages)}개 (이미지/스캔)" if empty_pages else "모두 텍스트 PDF")

        # docx 변환
        try:
            with page.expect_download(timeout=180000) as di:
                page.evaluate("document.getElementById('saveDocxBtn').click()")
            dl = di.value
            out_docx = OUT / "pankyo.docx"
            dl.save_as(str(out_docx))
            step(".docx 변환", out_docx.stat().st_size > 1000, f"{out_docx.stat().st_size/1024:.1f}KB")

            with zipfile.ZipFile(out_docx) as z:
                xml = z.read("word/document.xml").decode("utf-8")
                tables = xml.count("<w:tbl>")
                cells = xml.count("<w:tc>")
                drawings = xml.count("<w:drawing>")  # 이미지 박힌 거
                texts = re.findall(r'<w:t[^>]*>([^<]*)</w:t>', xml)
                total_text = ''.join(texts)
                images = [n for n in z.namelist() if n.startswith("word/media/")]
            print(f"\n  docx 분석: 표{tables}, 셀{cells}, 이미지{len(images)}, 텍스트{len(total_text)}자, drawings{drawings}")
            step("표 추출", tables > 0, f"{tables}개")
            step("이미지 박기 (스캔 페이지만 image fallback)", len(images) <= len(empty_pages), f"이미지 {len(images)}개 / 빈 페이지 {len(empty_pages)}개")
        except Exception as e:
            step(".docx 변환", False, str(e)[:120])

        # xlsx 변환
        try:
            with page.expect_download(timeout=120000) as di:
                page.evaluate("(async () => { document.getElementById('saveBtn').click(); await new Promise(r=>setTimeout(r,300)); document.querySelector('#saveMenu .save-item[data-fmt=\"xlsx\"]').click(); })()")
            dl = di.value
            out_xlsx = OUT / "pankyo.xlsx"; dl.save_as(str(out_xlsx))
            step(".xlsx 변환", out_xlsx.stat().st_size > 1000, f"{out_xlsx.stat().st_size/1024:.1f}KB")
        except Exception as e:
            step(".xlsx 변환", False, str(e)[:120])

        # 페이지 첫 화면 캡처
        page.screenshot(path=str(OUT/"pdf_first.png"))

        b.close()

    pc = sum(1 for r in results if r[0]=='✅')
    print(f"\n결과: {pc} / {len(results)} PASS")
    for r in results:
        if r[0] == '❌': print(f"  ❌ {r[1]} — {r[2]}")
    sys.exit(0 if pc == len(results) else 1)

if __name__ == "__main__":
    main()
