"""
PDF → 편집 가능한 워드 변환 검증
- 실제 예약이체 PDF
- 표 구조 자동 감지되어 docx Table 로 변환됐는지
- Word 본문 텍스트가 편집 가능한지 (image 가 아닌 실제 <w:t>)
"""
import sys, time, zipfile, re
from pathlib import Path
from playwright.sync_api import sync_playwright
try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

URL = "http://127.0.0.1:8765/?cb=" + str(int(time.time()*1000))
PDF = Path(r"C:\Users\신현식\Desktop\예약이체 내역.pdf")
OUT = Path(__file__).parent / "out_pdf_editable"; OUT.mkdir(exist_ok=True)

def main():
    print("=" * 60)
    print(" PDF → 편집 가능한 워드 (표·텍스트 분리 구조)")
    print("=" * 60)
    if not PDF.exists():
        print(f"❌ PDF 없음: {PDF}"); sys.exit(1)
    results = []
    def step(name, ok, detail=""):
        em = "✅" if ok else "❌"
        results.append((em, name, detail))
        print(f"  {em} {name}{(' — ' + detail) if detail else ''}", flush=True)

    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        page = b.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function("() => window.__editorReady === true", timeout=60000)
        page.set_input_files("#picker", str(PDF))
        page.wait_for_function("() => window.__currentMode === 'pdf'", timeout=60000)
        page.wait_for_timeout(1000)
        step("PDF 로드", True, f"{page.evaluate('() => window.__pdfState.pages.length')} 페이지")

        with page.expect_download(timeout=120000) as di:
            page.evaluate("document.getElementById('saveDocxBtn').click()")
        dl = di.value
        out = OUT / "예약이체_편집가능.docx"; dl.save_as(str(out))
        sz = out.stat().st_size
        step("DOCX 다운로드", sz > 1000, f"{sz} bytes ({sz/1024:.1f} KB)")

        # 압축 해제 후 검증
        with zipfile.ZipFile(out) as z:
            doc_xml = z.read("word/document.xml").decode("utf-8")
            # 1) <w:tbl> 표 존재
            tables = doc_xml.count("<w:tbl>")
            step("표 구조 감지", tables > 0, f"{tables}개 표")
            # 2) <w:tr> 행 수
            rows = doc_xml.count("<w:tr ") + doc_xml.count("<w:tr>")
            step("표 행 수", rows >= 4, f"{rows}개 행")
            # 3) <w:tc> 셀 수
            cells = doc_xml.count("<w:tc>")
            step("셀 수", cells >= 8, f"{cells}개 셀")
            # 4) 텍스트 추출 (간단)
            texts = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", doc_xml)
            full_text = "".join(texts)
            step("텍스트 추출 가능", len(full_text) > 50, f"{len(full_text)}자")
            # 5) 핵심 키워드 포함 (표 내용 매칭)
            keywords = ["이체", "은행", "솔박스", "조회기간"]
            found = [k for k in keywords if k in full_text]
            step(f"표 핵심 단어 포함", len(found) >= 2, f"{found}")
            # 6) 이미지 포함 (배경/로고 등)
            images = [n for n in z.namelist() if n.startswith("word/media/")]
            step("이미지 자료 수", True, f"{len(images)}개 ({'있음' if images else '없음 - 텍스트 전용'})")
            # 7) 페이지 크기 PDF 와 일치
            pgsz_match = re.search(r'<w:pgSz[^/]*w:w="(\d+)"[^/]*w:h="(\d+)"', doc_xml)
            step("페이지 크기 명시", bool(pgsz_match), str(pgsz_match.groups()) if pgsz_match else 'X')

        b.close()
    pc = sum(1 for r in results if r[0]=='✅')
    print(f"\n결과: {pc} / {len(results)} PASS")
    for r in results:
        if r[0] == '❌': print(f"  ❌ {r[1]} — {r[2]}")
    sys.exit(0 if pc == len(results) else 1)

if __name__ == "__main__":
    main()
