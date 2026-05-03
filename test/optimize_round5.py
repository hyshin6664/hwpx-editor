"""
Round 5 — 표 모양 라이브러리 round 단위 최적값 찾기 + 추가 normalize
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
OUT = Path(__file__).parent / "out_optimize5"; OUT.mkdir(exist_ok=True)
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

# round 단위 변경 — 50(2%), 100(1%), 25(4%), 20(5%), 200(0.5%), 1000(0.1%)
# 또는 normalize 비활성
attempts = [
    ("41", "round 단위 50(2%) → 100(1%)",
     [("Math.round(r * 50) / 50", "Math.round(r * 100) / 100"),
      ("Math.max(0.02, Math.round(r * 100) / 100)", "Math.max(0.01, Math.round(r * 100) / 100)")], "22.45"),
    ("42", "round 단위 100(1%) → 200(0.5%)",
     [("Math.max(0.01, Math.round(r * 100) / 100)", "Math.max(0.005, Math.round(r * 200) / 200)")], "22.46"),
    ("43", "round 단위 200 → 25(4%)",
     [("Math.max(0.005, Math.round(r * 200) / 200)", "Math.max(0.04, Math.round(r * 25) / 25)")], "22.47"),
    ("44", "normalize 비활성 (round 안 함)",
     [("ratios = ratios.map(r => Math.max(0.04, Math.round(r * 25) / 25));",
       "// ratios = ratios.map(r => Math.max(0.04, Math.round(r * 25) / 25)); // disabled")], "22.48"),
    ("45", "round 단위 1000(0.1%) — 거의 그대로",
     [("// ratios = ratios.map(r => Math.max(0.04, Math.round(r * 25) / 25)); // disabled",
       "ratios = ratios.map(r => Math.max(0.001, Math.round(r * 1000) / 1000));")], "22.49"),
    ("46", "round 비활성 (사실상 baseline)",
     [("ratios = ratios.map(r => Math.max(0.001, Math.round(r * 1000) / 1000));",
       "// no round")], "22.50"),
    ("47", "round 단위 200(0.5%) 복원 + spacing line 200 (있으면)",
     [("// no round",
       "ratios = ratios.map(r => Math.max(0.005, Math.round(r * 200) / 200));")], "22.51"),
]

log = []
print("="*70); print("📊 Round 5 baseline (v22.44, round 2%)")
deploy("R5 baseline"); time.sleep(50)
r = measure("baseline_r5")
log.append({'iter':'base', 'desc':'baseline v22.44 (2% round)', **r})
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
        if r['page_match'] and (not best.get('page_match') or r['avg'] < best['avg']):
            best = log[-1]
    except Exception as e:
        log.append({'iter':it, 'desc':desc, 'error':str(e)[:120]})
        print(f"  ❌ {str(e)[:120]}")

print("\n"+"="*70); print("📊 Round 5 결과")
for L in log:
    if 'avg' in L:
        m = "👑" if L is best else ("✅" if L['page_match'] else "  ")
        print(f"  {m} iter {str(L['iter']):>4}: {L.get('ver','base'):<6} | {L['orig']}p→{L['new']}p, 차이 {L['avg']:.2f}% — {L['desc']}")
