"""
Round 3 — 페이지 5p 일치 + 차이 < 12% 목표.
"""
import sys, time, subprocess, re
from pathlib import Path
from playwright.sync_api import sync_playwright
import win32com.client as wc
import fitz
from PIL import Image, ImageChops
try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

PDF = Path(r"C:\Users\신현식\Desktop\1.판교글로벌비즈센터 산업시설(B-301~303호) 처분 수의계약 공고문.pdf")
OUT = Path(__file__).parent / "out_optimize3"; OUT.mkdir(exist_ok=True)
HTML_PATH = Path(__file__).parent.parent / "index.html"

def deploy(m="iter"):
    for cmd in [
        ['git', '-c', 'user.email=hyshin6664@solbox.com', '-c', 'user.name=hyshin6664', 'add', '-A'],
        ['git', '-c', 'user.email=hyshin6664@solbox.com', '-c', 'user.name=hyshin6664', 'commit', '-m', m],
        ['git', 'push']
    ]:
        subprocess.run(cmd, cwd=str(HTML_PATH.parent), capture_output=True, check=False)

def measure(label):
    cb = int(time.time()*1000)
    URL = f"https://hyshin6664.github.io/hwpx-editor/?cb={cb}"
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
        docx = OUT / f"{label}.docx"; dl.save_as(str(docx))
        b.close()
    pdf2 = OUT / f"{label}.pdf"
    word = wc.Dispatch("Word.Application"); word.Visible = False
    try:
        doc = word.Documents.Open(str(docx.absolute())); doc.SaveAs(str(pdf2.absolute()), FileFormat=17); doc.Close(SaveChanges=False)
    finally: word.Quit()
    def render(p):
        d = fitz.open(p); imgs = []
        for pg in d:
            pix = pg.get_pixmap(matrix=fitz.Matrix(120/72, 120/72))
            imgs.append(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))
        d.close(); return imgs
    a = render(PDF); b = render(pdf2)
    diffs = []
    for i in range(min(len(a), len(b))):
        ia, ib = a[i], b[i]
        if ia.size != ib.size: ib = ib.resize(ia.size)
        diff_px = sum(1 for px in ImageChops.difference(ia, ib).getdata() if any(v > 30 for v in px))
        diffs.append(diff_px / (ia.size[0]*ia.size[1]) * 100)
    return {'avg': sum(diffs)/len(diffs) if diffs else 100, 'orig': len(a), 'new': len(b), 'page_match': len(a)==len(b)}

def edit(pat, rep):
    txt = HTML_PATH.read_text(encoding='utf-8')
    if pat not in txt: return False
    HTML_PATH.write_text(txt.replace(pat, rep, 1), encoding='utf-8')
    return True

def bump(ver):
    txt = HTML_PATH.read_text(encoding='utf-8')
    txt = re.sub(r'>v22\.\d+<', f'>v{ver}<', txt, count=1)
    HTML_PATH.write_text(txt, encoding='utf-8')

attempts = [
    ("21", "page margin 300→100",
     [("margin: { top: 300, right: 300, bottom: 300, left: 300 }", "margin: { top: 100, right: 100, bottom: 100, left: 100 }")], "22.22"),
    ("22", "셀 마진 10→0",
     [("margins: { top: 10, bottom: 10, left: 20, right: 20 }", "margins: { top: 0, bottom: 0, left: 10, right: 10 }")], "22.23"),
    ("23", "spacing 0",
     [("spacing: { before: 0, after: 0, line: 240 }", "spacing: { before: 0, after: 0, line: 200 }")], "22.24"),
    ("24", "size 10→9",
     [("size: 10,", "size: 9,")], "22.25"),
    ("25", "글자 너비 35→30",
     [("len * 35 + 80", "len * 30 + 80")], "22.26"),
    ("26", "셀 최소 200→150",
     [("Math.max(200, len * 30 + 80)", "Math.max(150, len * 30 + 80)")], "22.27"),
    ("27", "page height 16838→18000 (페이지 길게 → 5p 일치)",
     [("Math.round(pg.pdfPageHeight * 20)", "Math.round(pg.pdfPageHeight * 20 * 1.10)")], "22.28"),
    ("28", "page height 1.10 → 1.20",
     [("Math.round(pg.pdfPageHeight * 20 * 1.10)", "Math.round(pg.pdfPageHeight * 20 * 1.20)")], "22.29"),
    ("29", "spacing 200→160",
     [("spacing: { before: 0, after: 0, line: 200 }", "spacing: { before: 0, after: 0, line: 160 }")], "22.30"),
    ("30", "size 9→8",
     [("size: 9,", "size: 8,")], "22.31"),
]

log = []
print("="*70); print("📊 Round 3 baseline (v22.21)")
deploy("R3 baseline"); time.sleep(50)
r = measure("baseline_r3")
log.append({'iter':'base', 'desc':'baseline v22.21', **r})
print(f"  {r['orig']}p→{r['new']}p, 차이 {r['avg']:.2f}%")
best = log[0]

for it, desc, edits, ver in attempts:
    print("="*70); print(f"📊 ITER {it}: {desc}")
    all_ok = True
    for pat, rep in edits:
        if not edit(pat, rep): print(f"  ❌ 패턴: {pat[:50]}"); all_ok = False
    if not all_ok: continue
    bump(ver); deploy(f"iter {it}: {desc}"); time.sleep(50)
    try:
        r = measure(f"iter{it}")
        log.append({'iter':it, 'desc':desc, 'ver':ver, **r})
        m = "✅" if r['page_match'] else " "
        print(f"  {m} v{ver} | {r['orig']}p→{r['new']}p, 차이 {r['avg']:.2f}%")
        if r['avg'] < best['avg']: best = log[-1]
    except Exception as e:
        log.append({'iter':it, 'desc':desc, 'error':str(e)[:120]})
        print(f"  ❌ {str(e)[:120]}")

print("\n"+"="*70); print("📊 Round 3 결과")
for L in log:
    if 'avg' in L:
        m = "👑" if L is best else ("✅" if L['page_match'] else "  ")
        print(f"  {m} iter {str(L['iter']):>4}: {L.get('ver','base'):<6} | {L['orig']}p→{L['new']}p, 차이 {L['avg']:.2f}% — {L['desc']}")
