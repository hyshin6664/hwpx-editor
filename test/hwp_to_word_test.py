"""
사용자의 HWP 파일을 우리 앱으로 열어서:
1. rhwp 로 모든 페이지 렌더링 (SVG 추출)
2. SVG 파싱해서 text 요소 + 색상 추출
3. 워드 표 변환 시도 (또는 SVG → 이미지 → PDF → 우리 변환)
"""
import sys, time, os, re
from pathlib import Path
from playwright.sync_api import sync_playwright
try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

URL = "https://hyshin6664.github.io/hwpx-editor/?cb=" + str(int(time.time()*1000))
HWP = r"G:\.shortcut-targets-by-id\1S7kgDYheqAlHUZNbfj-zza3vyYZy9K3m\sbsI 협업과제(오픈소스 멀티모달 AI 기반 방송 콘텐츠 지능형 재가공 서비스 개발 및 사업화)\5. 관련규정\3. (세부) 기금사업 협약체결 및 사업비 관리 등에 관한 지침(과학기술정보통신부훈령)(제279호)(20241024) (1).hwp"
OUT = Path(__file__).parent / "out_hwp_test"; OUT.mkdir(exist_ok=True)

def main():
    if not os.path.exists(HWP):
        print("❌ HWP 파일 없음:", HWP)
        sys.exit(1)
    print(f"파일: {HWP}")
    print(f"크기: {os.path.getsize(HWP)/1024:.1f} KB")

    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        page = ctx.new_page()
        msgs = []
        page.on("console", lambda m: msgs.append(f"[{m.type}] {m.text[:200]}"))
        page.on("pageerror", lambda e: msgs.append(f"[ERR] {str(e)[:200]}"))
        page.on("dialog", lambda d: d.accept())

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function("() => window.__editorReady === true", timeout=120000)
        print("✅ 페이지 로드")

        # HWP 마운트 (큰 파일이니 timeout 길게)
        page.set_input_files("#picker", HWP)
        try:
            page.wait_for_function("() => window.__currentMode === 'hwp'", timeout=300000)
            page.wait_for_timeout(3000)
            print("✅ HWP 마운트")
        except Exception as e:
            print(f"❌ HWP 마운트 실패: {e}")
            print("\nConsole 로그 (최근 15):")
            for m in msgs[-15:]: print(f"  {m}")
            b.close()
            sys.exit(1)

        # rhwp 페이지 카운트
        try:
            n = page.evaluate("async () => { const r = await window.__probe('pageCount'); return r.result || 0; }")
            print(f"✅ 페이지 수: {n}")
        except Exception as e:
            print(f"⚠️ pageCount 실패: {e}")
            n = 0

        # SVG 추출 시도 (1페이지만)
        if n > 0:
            try:
                svg = page.evaluate("""async () => {
                  const r = await window.__probe('getPageSvg', { index: 0 });
                  return r.result ? r.result.length : null;
                }""")
                print(f"✅ 1페이지 SVG: {svg if svg else '없음'} 글자")
            except Exception as e:
                print(f"⚠️ getPageSvg 실패: {e}")

        # .hwpx 로 저장 시도 (cross-format)
        try:
            with page.expect_download(timeout=180000) as di:
                page.evaluate("document.getElementById('saveHwpxBtn').click()")
            dl = di.value
            p = OUT / "converted.hwpx"; dl.save_as(str(p))
            print(f"✅ HWPX 저장: {p.stat().st_size/1024:.1f} KB")
        except Exception as e:
            print(f"⚠️ HWPX 저장: {e}")

        b.close()
        print("\n--- Console 로그 (마지막 10) ---")
        for m in msgs[-10:]: print(f"  {m}")

if __name__ == "__main__":
    main()
