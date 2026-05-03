"""
판교 PDF → docx 변환 후, docx 안의 실제 표 너비 측정 + 페이지 폭 비교.
표가 페이지 폭 초과하는지 정확히 진단.
"""
import sys, time, zipfile, re
from pathlib import Path
from playwright.sync_api import sync_playwright
try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

URL = "https://hyshin6664.github.io/hwpx-editor/?cb=" + str(int(time.time()*1000))
PDF = Path(r"C:\Users\신현식\Desktop\1.판교글로벌비즈센터 산업시설(B-301~303호) 처분 수의계약 공고문.pdf")
OUT = Path(__file__).parent / "out_diagnose"; OUT.mkdir(exist_ok=True)

def diagnose_docx(docx_path):
    with zipfile.ZipFile(docx_path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    # 섹션별 페이지 크기 + orientation
    sections = []
    for sect in re.finditer(r'<w:sectPr[^>]*>(.*?)</w:sectPr>', xml, re.DOTALL):
        body = sect.group(1)
        pgsz = re.search(r'<w:pgSz[^>]*w:w="(\d+)"[^>]*w:h="(\d+)"(?:[^>]*w:orient="(\w+)")?', body)
        if pgsz:
            sections.append({
                'w': int(pgsz.group(1)),
                'h': int(pgsz.group(2)),
                'orient': pgsz.group(3) or 'portrait',
            })
    # 표별 너비 (tblW + 합계)
    tables = []
    for tbl in re.finditer(r'<w:tbl>(.*?)</w:tbl>', xml, re.DOTALL):
        body = tbl.group(1)
        tblW = re.search(r'<w:tblW[^>]*w:w="(\d+)"', body)
        tcWs = re.findall(r'<w:tc>.*?<w:tcW[^>]*w:w="(\d+)"', body[:5000], re.DOTALL)
        rows = body.count('<w:tr ') + body.count('<w:tr>')
        cols = len(tcWs[:rows]) if rows else 0  # 첫 행의 셀 수
        # 첫 행 셀 너비 합 (정확한 표 너비)
        first_row = re.search(r'<w:tr[^>]*>(.*?)</w:tr>', body, re.DOTALL)
        if first_row:
            first_tcWs = re.findall(r'<w:tc>.*?<w:tcW[^>]*w:w="(\d+)"', first_row.group(1), re.DOTALL)
            sum_tc = sum(int(x) for x in first_tcWs)
        else:
            sum_tc = 0
        tables.append({
            'tblW': int(tblW.group(1)) if tblW else 0,
            'sum_first_row_tcW': sum_tc,
            'rows': rows,
            'first_row_cells': len(first_tcWs) if first_row else 0,
        })
    return sections, tables

def main():
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        page = b.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function("() => window.__editorReady === true", timeout=60000)
        page.set_input_files("#picker", str(PDF))
        page.wait_for_function("() => window.__currentMode === 'pdf'", timeout=120000)
        page.wait_for_timeout(2000)
        with page.expect_download(timeout=180000) as di:
            page.evaluate("document.getElementById('saveDocxBtn').click()")
        dl = di.value
        out = OUT / "pankyo_diag.docx"; dl.save_as(str(out))
        b.close()

    sections, tables = diagnose_docx(out)
    print(f"📊 docx 진단: {out.name}\n")
    print(f"섹션 ({len(sections)}개):")
    for i, s in enumerate(sections):
        usable = s['w'] - 1440  # 좌우 마진 720*2
        print(f"  [{i+1}] {s['orient']}  pgSz={s['w']}×{s['h']} twips, 가용폭={usable}")
    print(f"\n표 ({len(tables)}개):")
    for i, t in enumerate(tables):
        print(f"  [{i+1}] tblW={t['tblW']}, 첫행 셀너비합={t['sum_first_row_tcW']}, {t['rows']}행 × {t['first_row_cells']}열")

    # 어떤 표가 어떤 섹션의 가용 폭 초과하는지
    print("\n⚠️  페이지 폭 초과 표:")
    found_overflow = False
    if sections:
        # 모든 표가 어떤 섹션에 속하는지 모름 — 가장 큰 표를 가장 큰 섹션과 비교
        max_usable = max(s['w'] - 1440 for s in sections)
        for i, t in enumerate(tables):
            actual_w = t['tblW'] if t['tblW'] > 0 else t['sum_first_row_tcW']
            if actual_w > max_usable:
                print(f"  ❌ 표[{i+1}] {actual_w} > 가용폭 {max_usable} (초과 {actual_w - max_usable} twips)")
                found_overflow = True
        if not found_overflow:
            print("  ✅ 모든 표 페이지 폭 안에 들어감")

if __name__ == "__main__":
    main()
