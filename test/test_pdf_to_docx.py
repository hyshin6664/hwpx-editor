"""
PDF → 동일 워드 (이미지 복제) 검증
- 예약이체 내역.pdf 열고
- saveDocxBtn 클릭 → 변환 → 다운로드
- DOCX 파일 크기 + 압축 풀어서 image/png 확인
"""
import sys, time, zipfile, io
from pathlib import Path
from playwright.sync_api import sync_playwright

try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

URL = "https://hyshin6664.github.io/hwpx-editor/?cb=" + str(int(time.time()*1000))
PDF = Path(r"C:\Users\신현식\Desktop\예약이체 내역.pdf")
OUT = Path(__file__).parent / "out_pdf_to_docx"; OUT.mkdir(exist_ok=True)

def main():
    print("=" * 60)
    print(" 🎯 PDF → 동일 워드 (이미지 복제) 검증")
    print("=" * 60)
    if not PDF.exists():
        print(f"❌ 테스트 PDF 없음: {PDF}"); sys.exit(1)

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
        n = page.evaluate("() => window.__pdfState.pages.length")
        step(f"PDF 로드 ({n} 페이지)", n > 0)

        # saveDocxBtn 클릭 → 변환 → 다운로드
        try:
            with page.expect_download(timeout=120000) as di:
                page.evaluate("document.getElementById('saveDocxBtn').click()")
            dl = di.value
            p = OUT / "예약이체_원본동일.docx"; dl.save_as(str(p))
            sz = p.stat().st_size
            step(f"DOCX 다운로드", sz > 10000, f"{sz} bytes ({sz/1024:.1f} KB)")
        except Exception as e:
            step("DOCX 다운로드", False, str(e))
            print("Console:")
            for m in msgs[-15:]: print(" ", m)
            b.close()
            sys.exit(1)

        # DOCX 압축 풀어서 검증
        try:
            with zipfile.ZipFile(p, 'r') as z:
                names = z.namelist()
                images = [n for n in names if n.startswith('word/media/') and n.endswith(('.png','.jpeg','.jpg'))]
                step("DOCX 안에 이미지 포함", len(images) > 0, f"{len(images)}개 이미지 ({images[:3]})")
                # 각 이미지 크기 확인
                if images:
                    img_sz = sum(z.getinfo(n).file_size for n in images)
                    step("이미지 총 크기", img_sz > 5000, f"{img_sz/1024:.1f} KB")
                # document.xml 에 <w:drawing> 있는지
                doc_xml = z.read('word/document.xml').decode('utf-8')
                has_drawing = '<w:drawing>' in doc_xml or '<w:drawing ' in doc_xml
                step("워드 XML 에 drawing 객체", has_drawing)
                # sectPr 페이지 크기 확인
                has_pgsz = '<w:pgSz' in doc_xml
                step("페이지 크기 명시(pgSz)", has_pgsz)
        except Exception as e:
            step("DOCX 검증", False, str(e))

        b.close()

    pass_cnt = sum(1 for r in results if r[0]=='✅')
    print(f"\n결과: {pass_cnt} / {len(results)} PASS")
    for r in results:
        if r[0] == '❌': print(f"  ❌ {r[1]} — {r[2]}")
    sys.exit(0 if pass_cnt == len(results) else 1)

if __name__ == "__main__":
    main()
