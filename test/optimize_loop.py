"""
PDF→Word→PDF 자동 비교 루프 — 차이 < 10% 까지.
파라미터 조합 grid search.
"""
import sys, time, subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright
import win32com.client as wc
import fitz
from PIL import Image, ImageChops
try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

URL_TPL = "https://hyshin6664.github.io/hwpx-editor/?cb={}"
PDF = Path(r"C:\Users\신현식\Desktop\1.판교글로벌비즈센터 산업시설(B-301~303호) 처분 수의계약 공고문.pdf")
OUT = Path(__file__).parent / "out_optimize"; OUT.mkdir(exist_ok=True)
HTML_PATH = Path(__file__).parent.parent / "index.html"

def deploy():
    """git commit + push"""
    subprocess.run(['git', '-c', 'user.email=hyshin6664@solbox.com', '-c', 'user.name=hyshin6664',
                    'add', '-A'], cwd=str(HTML_PATH.parent), check=False, capture_output=True)
    subprocess.run(['git', '-c', 'user.email=hyshin6664@solbox.com', '-c', 'user.name=hyshin6664',
                    'commit', '-m', 'optimize loop iter'], cwd=str(HTML_PATH.parent), check=False, capture_output=True)
    r = subprocess.run(['git', 'push'], cwd=str(HTML_PATH.parent), check=False, capture_output=True, text=True)
    return r.returncode == 0

def measure():
    """1회 PDF→Word→PDF→이미지 비교 → 평균 차이 % + 페이지 수"""
    cb = int(time.time()*1000)
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        page = b.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(URL_TPL.format(cb), wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function("() => window.__editorReady === true", timeout=60000)
        page.set_input_files("#picker", str(PDF))
        page.wait_for_function("() => window.__currentMode === 'pdf'", timeout=120000)
        page.wait_for_timeout(2000)
        with page.expect_download(timeout=180000) as di:
            page.evaluate("document.getElementById('saveDocxBtn').click()")
        dl = di.value
        docx = OUT / f"iter_{cb}.docx"; dl.save_as(str(docx))
        b.close()

    pdf2 = OUT / f"iter_{cb}.pdf"
    word = wc.Dispatch("Word.Application")
    word.Visible = False
    try:
        doc = word.Documents.Open(str(docx.absolute()))
        doc.SaveAs(str(pdf2.absolute()), FileFormat=17)
        doc.Close(SaveChanges=False)
    finally:
        word.Quit()

    # 페이지 이미지 + 비교
    def render(p):
        d = fitz.open(p)
        imgs = []
        for pg in d:
            pix = pg.get_pixmap(matrix=fitz.Matrix(120/72, 120/72))
            imgs.append(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))
        d.close()
        return imgs

    a = render(PDF); b = render(pdf2)
    n = min(len(a), len(b))
    diffs = []
    for i in range(n):
        ia, ib = a[i], b[i]
        if ia.size != ib.size: ib = ib.resize(ia.size)
        diff = ImageChops.difference(ia, ib)
        diff_px = sum(1 for px in diff.getdata() if any(v > 30 for v in px))
        total = ia.size[0] * ia.size[1]
        diffs.append(diff_px / total * 100)
    avg = sum(diffs) / len(diffs) if diffs else 100
    return {'avg_diff': avg, 'orig_pages': len(a), 'new_pages': len(b), 'per_page': diffs}

def edit_param(pattern, replacement):
    """index.html 의 파라미터 변경"""
    txt = HTML_PATH.read_text(encoding='utf-8')
    if pattern not in txt:
        return False
    new_txt = txt.replace(pattern, replacement, 1)
    HTML_PATH.write_text(new_txt, encoding='utf-8')
    return True

def bump_version(new_ver):
    """버전 표시 변경"""
    txt = HTML_PATH.read_text(encoding='utf-8')
    import re
    txt = re.sub(r'>v22\.\d+<', f'>v{new_ver}<', txt, count=1)
    HTML_PATH.write_text(txt, encoding='utf-8')

def main():
    log = []

    # iter 0: 기준선
    print("=" * 70)
    print("📊 ITER 0 (기준선)")
    deploy(); time.sleep(45)
    r = measure()
    log.append({'iter': 0, 'desc': 'baseline', **r})
    print(f"  원본 {r['orig_pages']}p, 변환 {r['new_pages']}p, 평균 차이 {r['avg_diff']:.2f}%")

    # 시도할 파라미터 변경 시리즈
    attempts = [
        # iter, desc, [(pattern, replacement)], version
        (1, "글자 너비 110→90 (한국어 220→180)",
         [("len * 110 + 200", "len * 90 + 200")], "22.2"),
        (2, "글자 size 18 → 14",
         [("new docxLib.TextRun({\n                      text,\n                      size: 18,",
           "new docxLib.TextRun({\n                      text,\n                      size: 14,")], "22.3"),
        (3, "셀 마진 50→30, 80→50",
         [("margins: { top: 50, bottom: 50, left: 80, right: 80 }",
           "margins: { top: 30, bottom: 30, left: 50, right: 50 }")], "22.4"),
        (4, "글자 너비 90→75",
         [("len * 90 + 200", "len * 75 + 200")], "22.5"),
        (5, "셀 최소 800→600",
         [("Math.max(800, len * 75 + 200)", "Math.max(600, len * 75 + 200)")], "22.6"),
        (6, "셀 최소 600→500",
         [("Math.max(600, len * 75 + 200)", "Math.max(500, len * 75 + 200)")], "22.7"),
        (7, "글자 너비 75→60",
         [("len * 75 + 200", "len * 60 + 200")], "22.8"),
        (8, "여백 200→150",
         [("len * 60 + 200", "len * 60 + 150")], "22.9"),
        (9, "page margin 720→500",
         [("margin: { top: 720, right: 720, bottom: 720, left: 720 }",
           "margin: { top: 500, right: 500, bottom: 500, left: 500 }")], "22.10"),
        (10, "글자 size 14 → 12",
         [("new docxLib.TextRun({\n                      text,\n                      size: 14,",
           "new docxLib.TextRun({\n                      text,\n                      size: 12,")], "22.11"),
    ]

    best = log[0]
    for it, desc, edits, ver in attempts:
        print("=" * 70)
        print(f"📊 ITER {it}: {desc}")
        all_ok = True
        for pat, rep in edits:
            if not edit_param(pat, rep):
                print(f"  ❌ 패턴 안 맞음: {pat[:60]}")
                all_ok = False
        if not all_ok: continue
        bump_version(ver)
        deploy()
        time.sleep(50)
        try:
            r = measure()
            log.append({'iter': it, 'desc': desc, 'ver': ver, **r})
            print(f"  v{ver} | 원본 {r['orig_pages']}p, 변환 {r['new_pages']}p, 평균 차이 {r['avg_diff']:.2f}%")
            if r['avg_diff'] < best['avg_diff']: best = log[-1]
        except Exception as e:
            print(f"  ❌ 측정 실패: {str(e)[:120]}")
            log.append({'iter': it, 'desc': desc, 'error': str(e)[:200]})

    # 결과 정리
    print("\n" + "=" * 70)
    print("📊 결과 요약 (낮을수록 좋음)")
    print("=" * 70)
    for L in log:
        if 'avg_diff' in L:
            mark = "👑" if L is best else "  "
            print(f"  {mark} iter {L['iter']:>2}: {L.get('ver','base'):<6} | {L['orig_pages']}p→{L.get('new_pages',0)}p, 차이 {L['avg_diff']:.2f}% — {L['desc']}")
        else:
            print(f"     iter {L['iter']:>2}: 실패 — {L.get('error','')[:80]}")

if __name__ == "__main__":
    main()
