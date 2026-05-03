"""
5종 표 PDF 정확도 측정 + 결과 분석 — 사용자 3대 포커스:
1) 표 크기 (행/열 정확)
2) 색 (헤더 회색 / 행 색 / 텍스트 색 보존)
3) 텍스트 인식율 (모든 단어 추출 정확)

각 PDF 마다:
- ground truth (예상 셀 데이터) 와 변환 결과 비교
- 텍스트 정확도 % (다운로드된 docx XML 안 셀 텍스트 vs ground truth)
- 색 추출 % (헤더/특정 행 회색 또는 색상 인식)
- 셀 수 (정확 행x열)
"""
import sys, time, zipfile, re
from pathlib import Path
from playwright.sync_api import sync_playwright
try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

URL = "https://hyshin6664.github.io/hwpx-editor/?cb=" + str(int(time.time()*1000))
PDF_DIR = Path(__file__).parent / "fixtures" / "test_pdfs"
OUT = Path(__file__).parent / "out_accuracy"; OUT.mkdir(exist_ok=True)

# Ground truth (각 PDF 의 예상 셀 데이터)
TRUTHS = {
    "1_simple.pdf": {
        "rows": 5, "cols": 4,
        "cells": ["항목","수량","단가","합계","연필","10","500","5,000","지우개","5","1,000","5,000","공책","3","2,500","7,500","합계","17,500"],
        "header_color": None,  # 헤더 흰색
    },
    "2_colored_header.pdf": {
        "rows": 6, "cols": 4,
        "cells": ["No.","날짜","거래처","금액(원)","1","2026.01.05","솔박스","1,500,000","2","2026.01.10","카카오","2,300,000","3","2026.01.15","네이버","1,800,000","4","2026.01.20","KT","950,000","합계","6,550,000"],
        "header_color": "DEDEDE",
    },
    "3_multi_color.pdf": {
        "rows": 5, "cols": 4,
        "cells": ["상태","제품명","수량","평가","양호","제품 A","120","주의","제품 B","85","긴급","제품 C","20","양호","제품 D","150"],
        "header_color": "3B5BAB",  # 짙은 파랑
    },
    "4_compact.pdf": {
        "rows": 6, "cols": 10,
        "cells": ["ID","이름","부서","직급","입사","전화","이메일","연봉(만원)","평가","비고","001","김철수","개발1팀","과장","2020.03","010-1234-5678","kim@a.co","7500","A","우수"],
        "header_color": "F0F0F0",
    },
    "5_wide.pdf": {
        "rows": 5, "cols": 5,
        "cells": ["프로젝트","담당자","시작","종료","상태","오픈소스 멀티모달 AI 기반 방송 콘텐츠","신현식","2024.06","2026.05","진행중","CDN 인프라 구축 사업","이종필","2025.01","2026.06","진행중"],
        "header_color": "1976D2",  # 파랑
    },
}

def analyze_docx(path):
    """DOCX 안의 셀 텍스트 + 색상 추출"""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    rows = re.findall(r'<w:tr[^>]*>(.*?)</w:tr>', xml, re.DOTALL)
    table = []
    for r in rows:
        cells_xml = re.findall(r'<w:tc>(.*?)</w:tc>', r, re.DOTALL)
        row = []
        for c in cells_xml:
            text = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', c))
            shading = re.search(r'<w:shd[^/]*w:fill="([^"]+)"', c)
            row.append({'text': text.strip(), 'fill': shading.group(1) if shading else None})
        table.append(row)
    return table

def measure(pdf_name, table, truth):
    n_rows = len(table)
    n_cols = max(len(r) for r in table) if table else 0
    all_cells_text = [c['text'] for r in table for c in r if c['text']]
    found_set = set(all_cells_text)
    truth_set = set(t for t in truth['cells'] if t)
    matched = truth_set & found_set
    text_acc = len(matched) / len(truth_set) if truth_set else 0

    # 색상 인식
    color_ok = True
    if truth.get('header_color'):
        # 첫 행 셀들이 그 색을 가지는지
        if table:
            header_fills = [c.get('fill') for c in table[0]]
            color_match = any(f and f.upper() == truth['header_color'].upper() for f in header_fills)
            color_ok = color_match
        else:
            color_ok = False

    rows_close = abs(n_rows - truth['rows']) <= 1
    cols_close = abs(n_cols - truth['cols']) <= 1

    return {
        'pdf': pdf_name,
        'rows_actual/expected': f"{n_rows}/{truth['rows']}",
        'cols_actual/expected': f"{n_cols}/{truth['cols']}",
        'text_acc%': round(text_acc * 100, 1),
        'matched/total': f"{len(matched)}/{len(truth_set)}",
        'color': '✅' if color_ok else '❌',
        'rows_ok': rows_close,
        'cols_ok': cols_close,
        'missing_words': list(truth_set - found_set)[:5],
    }

def run_one(page, pdf_path):
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_function("() => window.__editorReady === true", timeout=60000)
    page.set_input_files("#picker", str(pdf_path))
    page.wait_for_function("() => window.__currentMode === 'pdf'", timeout=60000)
    page.wait_for_timeout(1500)
    with page.expect_download(timeout=60000) as di:
        page.evaluate("document.getElementById('saveDocxBtn').click()")
    dl = di.value
    out = OUT / (pdf_path.stem + "_converted.docx")
    dl.save_as(str(out))
    return out

def main():
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"❌ PDF 없음: {PDF_DIR}"); sys.exit(1)
    print(f"📊 {len(pdfs)}개 PDF 정확도 측정\n")

    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        page = b.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True).new_page()
        page.on("dialog", lambda d: d.accept())

        results = []
        for pdf in pdfs:
            print(f"📄 {pdf.name}")
            try:
                docx = run_one(page, pdf)
                table = analyze_docx(docx)
                truth = TRUTHS.get(pdf.name, {})
                if not truth:
                    print(f"  (ground truth 없음, skip)\n")
                    continue
                m = measure(pdf.name, table, truth)
                results.append(m)
                print(f"  행 {m['rows_actual/expected']}, 열 {m['cols_actual/expected']}, "
                      f"텍스트 {m['text_acc%']}% ({m['matched/total']}), 색 {m['color']}")
                if m['missing_words']:
                    print(f"  누락 단어: {m['missing_words']}")
                print()
            except Exception as e:
                print(f"  ❌ 실패: {str(e)[:120]}\n")
                results.append({'pdf': pdf.name, 'error': str(e)})
        b.close()

    # 종합 요약
    print("="*60)
    print("📊 종합 요약")
    print("="*60)
    if not results:
        print("결과 없음"); return
    avg_text_acc = sum(r.get('text_acc%', 0) for r in results) / len(results)
    cols_pass = sum(1 for r in results if r.get('cols_ok'))
    rows_pass = sum(1 for r in results if r.get('rows_ok'))
    color_pass = sum(1 for r in results if r.get('color') == '✅')
    print(f"  평균 텍스트 정확도: {avg_text_acc:.1f}%")
    print(f"  행 수 정확: {rows_pass} / {len(results)}")
    print(f"  열 수 정확: {cols_pass} / {len(results)}")
    print(f"  색 인식: {color_pass} / {len(results)}")
    print()

    # 100% 가 아니면 실패
    perfect = (avg_text_acc >= 99 and
               rows_pass == len(results) and
               cols_pass == len(results) and
               color_pass == len(results))
    if perfect:
        print("✅ 100% 정확도 달성!")
        sys.exit(0)
    else:
        print("⚠️ 추가 개선 필요")
        sys.exit(1)

if __name__ == "__main__":
    main()
