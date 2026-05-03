"""
PDF → Word (우리 앱) → PDF (Microsoft Word COM) → 페이지 이미지로 비교
사용자 보고 시점: "변환된 워드를 다시 PDF 로 만들어서 원본과 비교 가능?"
"""
import sys, time, os
from pathlib import Path
from playwright.sync_api import sync_playwright
import win32com.client as wc
import fitz  # PyMuPDF
from PIL import Image, ImageChops
try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

URL = "https://hyshin6664.github.io/hwpx-editor/?cb=" + str(int(time.time()*1000))
PDF = Path(r"C:\Users\신현식\Desktop\1.판교글로벌비즈센터 산업시설(B-301~303호) 처분 수의계약 공고문.pdf")
OUT = Path(__file__).parent / "out_compare3"; OUT.mkdir(exist_ok=True)

def step1_pdf_to_docx():
    print("📥 1) PDF → DOCX (우리 앱)")
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
        out = OUT / "pankyo.docx"; dl.save_as(str(out))
        b.close()
        print(f"   → {out.name} ({out.stat().st_size/1024:.1f} KB)")
        return out

def step2_docx_to_pdf(docx_path):
    print("📥 2) DOCX → PDF (Word COM)")
    out = OUT / "pankyo_round_trip.pdf"
    word = wc.Dispatch("Word.Application")
    word.Visible = False
    try:
        doc = word.Documents.Open(str(docx_path.absolute()))
        doc.SaveAs(str(out.absolute()), FileFormat=17)  # wdFormatPDF
        doc.Close(SaveChanges=False)
    finally:
        word.Quit()
    print(f"   → {out.name} ({out.stat().st_size/1024:.1f} KB)")
    return out

def step3_render_pages(pdf_path, prefix, dpi=120):
    """PDF 의 모든 페이지 이미지로 추출"""
    images = []
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        mat = fitz.Matrix(dpi/72, dpi/72)
        pix = page.get_pixmap(matrix=mat)
        img_path = OUT / f"{prefix}_page{i+1}.png"
        pix.save(str(img_path))
        images.append(img_path)
    doc.close()
    return images

def step4_compare(orig_imgs, new_imgs):
    """페이지 이미지 비교"""
    print("\n📊 페이지별 비교:")
    diffs = []
    n = min(len(orig_imgs), len(new_imgs))
    for i in range(n):
        a = Image.open(orig_imgs[i]).convert('RGB')
        b = Image.open(new_imgs[i]).convert('RGB')
        # 크기 맞춤
        if a.size != b.size:
            b = b.resize(a.size)
        diff_img = ImageChops.difference(a, b)
        bbox = diff_img.getbbox()
        # 픽셀 diff %
        diff_pixels = sum(1 for px in diff_img.getdata() if any(v > 30 for v in px))
        total = a.size[0] * a.size[1]
        diff_pct = diff_pixels / total * 100
        # 차이 시각화
        diff_path = OUT / f"diff_page{i+1}.png"
        diff_img.save(str(diff_path))
        diffs.append({'page': i+1, 'diff_pct': diff_pct, 'size_a': a.size, 'size_b': b.size})
        emoji = "✅" if diff_pct < 5 else ("⚠️" if diff_pct < 20 else "❌")
        print(f"   {emoji} page {i+1}: 차이 {diff_pct:.2f}%, 원본 {a.size}, 변환 {b.size}")

    # 요약
    print("\n📊 요약:")
    print(f"   원본: {len(orig_imgs)} 페이지")
    print(f"   변환: {len(new_imgs)} 페이지")
    avg = sum(d['diff_pct'] for d in diffs) / len(diffs) if diffs else 0
    print(f"   평균 차이: {avg:.2f}%")
    return diffs, avg

def main():
    if not PDF.exists():
        print(f"❌ PDF 없음"); sys.exit(1)
    print(f"🔬 PDF 변환 정확도 비교 — {PDF.name}\n")

    # 1) PDF → DOCX
    docx_path = step1_pdf_to_docx()
    # 2) DOCX → PDF (Word COM)
    new_pdf = step2_docx_to_pdf(docx_path)
    # 3) 양쪽 PDF 페이지 이미지 추출
    print("\n📷 3) 양쪽 PDF 페이지 이미지 추출")
    orig_imgs = step3_render_pages(PDF, "orig")
    new_imgs = step3_render_pages(new_pdf, "new")
    print(f"   원본 {len(orig_imgs)} 페이지, 변환 {len(new_imgs)} 페이지")
    # 4) 비교
    diffs, avg = step4_compare(orig_imgs, new_imgs)
    print(f"\n📁 결과 저장: {OUT}")
    sys.exit(0 if avg < 30 else 1)

if __name__ == "__main__":
    main()
