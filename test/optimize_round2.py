"""
2라운드 최적화 — best v22.11 기반 + 더 강한 변경 시도.
목표: 페이지 수 5→5 일치 + 차이 < 10%.
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
OUT = Path(__file__).parent / "out_optimize2"; OUT.mkdir(exist_ok=True)
HTML_PATH = Path(__file__).parent.parent / "index.html"

def deploy(commit_msg="iter"):
    subprocess.run(['git', '-c', 'user.email=hyshin6664@solbox.com', '-c', 'user.name=hyshin6664',
                    'add', '-A'], cwd=str(HTML_PATH.parent), check=False, capture_output=True)
    subprocess.run(['git', '-c', 'user.email=hyshin6664@solbox.com', '-c', 'user.name=hyshin6664',
                    'commit', '-m', commit_msg], cwd=str(HTML_PATH.parent), check=False, capture_output=True)
    subprocess.run(['git', 'push'], cwd=str(HTML_PATH.parent), check=False, capture_output=True)

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
    ("11", "landscape 비활성 (pgNeedsLandscape=false 강제)",
     [("if (tblTotalTwips > portraitUsable) {\n              pgNeedsLandscape = true;\n              usable = landscapeUsable;\n            }",
       "if (tblTotalTwips > portraitUsable) {\n              // portrait 유지 — landscape 안 쓰면 페이지 수 일치 가능\n              usable = portraitUsable;\n            }")], "22.12"),
    ("12", "size 12→10",
     [("size: 12,", "size: 10,")], "22.13"),
    ("13", "셀 최소 500→300",
     [("Math.max(500, len * 60 + 150)", "Math.max(300, len * 60 + 150)")], "22.14"),
    ("14", "글자 너비 60→45",
     [("len * 60 + 150", "len * 45 + 150")], "22.15"),
    ("15", "여백 150→80",
     [("len * 45 + 150", "len * 45 + 80")], "22.16"),
    ("16", "spacing line 240 → 180",
     [("spacing: { before: 0, after: 0, line: 240 }", "spacing: { before: 0, after: 0, line: 180 }")], "22.17"),
    ("17", "셀 마진 30→10, 50→20",
     [("margins: { top: 30, bottom: 30, left: 50, right: 50 }", "margins: { top: 10, bottom: 10, left: 20, right: 20 }")], "22.18"),
    ("18", "page margin 500→300",
     [("margin: { top: 500, right: 500, bottom: 500, left: 500 }", "margin: { top: 300, right: 300, bottom: 300, left: 300 }")], "22.19"),
    ("19", "글자 너비 45→35",
     [("len * 45 + 80", "len * 35 + 80")], "22.20"),
    ("20", "셀 최소 300→200",
     [("Math.max(300, len * 35 + 80)", "Math.max(200, len * 35 + 80)")], "22.21"),
]

log = []
print("=" * 70)
print("📊 BASELINE (현재 best v22.11)")
deploy("baseline retest"); time.sleep(50)
r = measure("baseline")
log.append({'iter': 'base', 'desc': 'baseline v22.11', **r})
print(f"  원본 {r['orig']}p, 변환 {r['new']}p, 차이 {r['avg']:.2f}%")
best = log[0]

for it, desc, edits, ver in attempts:
    print("=" * 70); print(f"📊 ITER {it}: {desc}")
    all_ok = True
    for pat, rep in edits:
        if not edit(pat, rep): print(f"  ❌ 패턴 안 맞음: {pat[:50]}"); all_ok = False
    if not all_ok: continue
    bump(ver); deploy(f"iter {it}: {desc}"); time.sleep(50)
    try:
        r = measure(f"iter{it}")
        log.append({'iter': it, 'desc': desc, 'ver': ver, **r})
        match = "✅" if r['page_match'] else " "
        print(f"  {match} v{ver} | {r['orig']}p→{r['new']}p, 차이 {r['avg']:.2f}%")
        if r['avg'] < best['avg']: best = log[-1]
    except Exception as e:
        log.append({'iter': it, 'desc': desc, 'error': str(e)[:120]})
        print(f"  ❌ {str(e)[:120]}")

print("\n" + "=" * 70); print("📊 라운드 2 결과")
for L in log:
    if 'avg' in L:
        m = "👑" if L is best else ("✅" if L['page_match'] else "  ")
        print(f"  {m} iter {str(L['iter']):>4}: {L.get('ver','base'):<6} | {L['orig']}p→{L['new']}p, 차이 {L['avg']:.2f}% — {L['desc']}")
