"""
모든 기능 한 번씩 직접 호출 + 측정 → 회귀 방지 종합 감사.
로컬(http://127.0.0.1:8765/?cb=...) 에서 돌리며 SW/캐시 영향 받지 않게.
"""
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

URL = "http://127.0.0.1:8765/?cb=" + str(int(time.time()*1000))
HWPX = Path(r"C:\Users\신현식\Desktop\★[최종양식] 2026년 오픈소스 AI·SW 개발·활용 지원사업_수정-v.1_수정_2026-04-30_09-01_수정_2026-04-30_09-21_수정_2026-04-30_09-36.hwpx")
PDF  = Path(r"C:\Users\신현식\Desktop\예약이체 내역.pdf")
OUT  = Path(__file__).parent / "out_audit"; OUT.mkdir(exist_ok=True)

def main():
    results = []
    def step(name, ok, detail=""):
        emoji = "✅" if ok else "❌"
        results.append((emoji, name, detail))
        print(f"  {emoji} {name}{(' — ' + detail) if detail else ''}", flush=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)

        # ─── PC 1280 ───
        ctx_pc = browser.new_context(viewport={"width": 1280, "height": 800}, accept_downloads=True)
        page = ctx_pc.new_page()
        page.on("dialog", lambda d: d.accept())
        try:
            page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_function("() => window.__editorReady === true", timeout=60000)
            step("PC: 페이지 로드", True)

            # 1) 새 docx → 폭 측정
            page.click("#newBtn"); page.wait_for_timeout(150)
            page.click('#newMenu .newm-item[data-fmt="docx"]')
            page.wait_for_function("() => document.querySelectorAll('#docxHost .docx p[contenteditable]').length>0", timeout=20000)
            page.wait_for_timeout(400)
            r = page.evaluate("""() => { const sec=document.querySelector('#docxHost section'); const rect=sec.getBoundingClientRect(); return { vp:innerWidth, secCSS:getComputedStyle(sec).width, vw:Math.round(rect.width), inline:sec.getAttribute('style') }; }""")
            ok = r['vw'] >= 700
            step(f"PC: 새 docx 페이지 폭", ok, f"vp={r['vp']} secCSS={r['secCSS']} 시각폭={r['vw']}px (inline={r['inline']!r})")

            # 2) 타이핑
            page.click('#docxHost .docx p[contenteditable]'); page.wait_for_timeout(150)
            page.keyboard.press("End"); page.keyboard.type(" PC타이핑", delay=15)
            page.wait_for_timeout(200)
            txt = page.evaluate("() => document.querySelector('#docxHost .docx p[contenteditable]').textContent")
            step("PC: 타이핑", "PC타이핑" in txt, txt[:60])

            # 3) 굵게
            page.evaluate("""() => { const p=document.querySelector('#docxHost .docx p[contenteditable]'); p.focus(); const sel=getSelection(); const r=document.createRange(); r.selectNodeContents(p); sel.removeAllRanges(); sel.addRange(r); document.getElementById('docxBold').click(); }""")
            page.wait_for_timeout(150)
            html = page.evaluate("() => document.querySelector('#docxHost .docx p[contenteditable]').innerHTML")
            step("PC: 굵게", "font-weight" in html or "<b>" in html, html[:80])

            # 4) 폰트 변경
            r = page.evaluate("""() => { const sel=document.getElementById('docxFont'); const opts=[...sel.options].map(o=>o.value); const t=opts.find(v=>/pretendard/i.test(v))||opts[1]; sel.value=t; sel.dispatchEvent(new Event('change',{bubbles:true})); return { target:t, n:opts.length }; }""")
            step("PC: 폰트 picker", r['n']>=20 and bool(r['target']), f"{r['n']}개, target={r['target']}")

            # 5) 검색·바꾸기
            page.fill("#searchInput", "타이핑")
            page.wait_for_timeout(300)
            cnt = page.evaluate("() => document.querySelectorAll('.search-result-card, #searchResults > *, .search-item').length")
            step("PC: 검색 결과", cnt > 0, f"{cnt}개")
            page.fill("#replaceInput", "텍스트")
            page.click("#replaceAllBtn"); page.wait_for_timeout(400)
            txt2 = page.evaluate("() => document.querySelector('#docxHost .docx p[contenteditable]').textContent")
            step("PC: 일괄 바꾸기", "텍스트" in txt2, txt2[:60])

            # 6) docx 저장
            with page.expect_download(timeout=15000) as di:
                page.evaluate("document.getElementById(\"saveDocxBtn\").click()")
            dl = di.value; p = OUT/"audit_pc.docx"; dl.save_as(str(p))
            step("PC: .docx 다운로드", p.exists() and p.stat().st_size>500, f"{p.stat().st_size}바이트")

            # 7) cross-format → .hwpx
            with page.expect_download(timeout=30000) as di:
                page.evaluate("document.getElementById(\"saveHwpxBtn\").click()")
            dl = di.value; p = OUT/"audit_pc.hwpx"; dl.save_as(str(p))
            step("PC: docx→hwpx 변환 다운로드", p.exists() and p.stat().st_size>500, f"{p.stat().st_size}바이트")

            # 8) 닫기
            page.click("#closeBtn"); page.wait_for_timeout(300)
            step("PC: 닫기", page.evaluate("() => !window.__currentMode"))

            # 9) 새 hwpx → 즉시 편집 (docx 마운트)
            page.click("#newBtn"); page.wait_for_timeout(150)
            page.click('#newMenu .newm-item[data-fmt="hwpx"]')
            page.wait_for_function("() => document.querySelectorAll('#docxHost .docx p[contenteditable]').length>0", timeout=20000)
            page.click('#docxHost .docx p[contenteditable]')
            page.keyboard.press("End"); page.keyboard.type(" 한글편집", delay=15)
            page.wait_for_timeout(200)
            with page.expect_download(timeout=30000) as di:
                page.evaluate("document.getElementById(\"saveHwpxBtn\").click()")
            dl = di.value; p = OUT/"audit_new.hwpx"; dl.save_as(str(p))
            step("PC: 새 hwpx 즉시 편집+저장", p.exists() and p.stat().st_size>500, f"{p.stat().st_size}바이트")

            page.click("#closeBtn"); page.wait_for_timeout(300)

            # 10) PDF 마운트 + 글씨 + 저장
            if PDF.exists():
                page.set_input_files("#picker", str(PDF))
                page.wait_for_function("() => window.__currentMode === 'pdf'", timeout=60000)
                page.wait_for_timeout(500)
                step("PC: PDF 로드", True)

                box = page.query_selector("#pdfHost canvas").bounding_box()
                page.click('button[data-tool="text"]'); page.wait_for_timeout(150)
                page.mouse.click(box['x']+100, box['y']+200)
                page.wait_for_timeout(150)
                page.keyboard.type("PDF글씨", delay=10)
                page.keyboard.press("Enter")
                page.wait_for_timeout(200)
                edits = page.evaluate("() => window.__pdfState.pages[0].edits.length")
                step("PC: PDF 글씨", edits > 0, f"{edits}개 edit")

                # PDF Ctrl+Z
                edits_before = edits
                page.keyboard.press("Control+z"); page.wait_for_timeout(200)
                edits_after = page.evaluate("() => window.__pdfState.pages[0].edits.length")
                step("PC: PDF Ctrl+Z", edits_after < edits_before, f"{edits_before}→{edits_after}")

                # 도장 버튼
                stamp_exists = page.evaluate("() => !!document.querySelector('button[data-tool=\\\"stamp\\\"]')")
                step("PC: PDF 도장 버튼", stamp_exists)

                # PDF 저장
                with page.expect_download(timeout=30000) as di:
                    page.evaluate("document.getElementById(\"savePdfBtn\").click()")
                dl = di.value; p = OUT/"audit.pdf"; dl.save_as(str(p))
                step("PC: PDF 저장", p.exists() and p.stat().st_size>1000, f"{p.stat().st_size}바이트")

                page.click("#closeBtn"); page.wait_for_timeout(300)

            # 11) HWPX 파일 (사전 보정)
            if HWPX.exists():
                page.set_input_files("#picker", str(HWPX))
                page.wait_for_function("() => window.__currentMode === 'hwp'", timeout=180000)
                page.wait_for_timeout(1000)
                step("PC: HWPX 로드 (사전 보정)", True)
                # cross-format → docx
                with page.expect_download(timeout=120000) as di:
                    page.evaluate("document.getElementById(\"saveDocxBtn\").click()")
                dl = di.value; p = OUT/"audit_hwpx_to.docx"; dl.save_as(str(p))
                step("PC: HWPX→docx 변환", p.exists() and p.stat().st_size>500, f"{p.stat().st_size}바이트")
                page.click("#closeBtn"); page.wait_for_timeout(300)

            # 12) PWA / 📌 라벨 / SW
            r = page.evaluate("""async () => {
              const reg = await navigator.serviceWorker.getRegistration();
              return {
                ver: document.getElementById('verBtn').textContent,
                installLabel: document.getElementById('installBtn').textContent,
                manifest: !!document.querySelector('link[rel=manifest]'),
                swActive: !!(reg && reg.active),
              };
            }""")
            step("PC: PWA + 📌 라벨", r['manifest'] and r['swActive'] and ('바탕화면' in r['installLabel']), str(r))

            # 13) 음성 mock interim → final (핵심 회귀 방지)
            page.click("#newBtn"); page.wait_for_timeout(150)
            page.click('#newMenu .newm-item[data-fmt="docx"]')
            page.wait_for_function("() => document.querySelectorAll('#docxHost .docx p[contenteditable]').length>0", timeout=20000)
            r = page.evaluate("""async () => {
              class Mock { constructor(){this.lang='';this.interimResults=true;this.continuous=true;} start(){this.onstart && this.onstart();} stop(){this.onend && this.onend();} }
              window.SpeechRecognition = Mock;
              window.webkitSpeechRecognition = Mock;
              if (window.__resetVoiceRecognition) window.__resetVoiceRecognition();
              const p = document.querySelector('#docxHost .docx p[contenteditable]');
              p.focus();
              const sel=getSelection(); const r0=document.createRange(); r0.selectNodeContents(p); r0.collapse(false); sel.removeAllRanges(); sel.addRange(r0);
              document.getElementById('voiceFab').click();
              await new Promise(r=>setTimeout(r,300));
              window.__voiceMockResult('실시간', null);
              await new Promise(r=>setTimeout(r,150));
              const interim = document.querySelector('.voice-interim-inline')?.textContent || '';
              window.__voiceMockResult(null, '실시간음성');
              await new Promise(r=>setTimeout(r,200));
              return { interim, final: p.textContent };
            }""")
            step("PC: 음성 interim→final", r['interim']=='실시간' and '실시간음성' in r['final'], f"interim={r['interim']!r} → 본문={r['final']!r}")

            page.screenshot(path=str(OUT/"pc_final.png"), full_page=False)
        finally:
            ctx_pc.close()

        # ─── 모바일 375 ───
        ctx_m = browser.new_context(viewport={"width": 375, "height": 812}, accept_downloads=True)
        pageM = ctx_m.new_page()
        pageM.on("dialog", lambda d: d.accept())
        try:
            pageM.goto(URL, wait_until="domcontentloaded", timeout=60000)
            pageM.wait_for_function("() => window.__editorReady === true", timeout=60000)
            step("📱: 페이지 로드", True)
            pageM.click("#hamburgerBtn"); pageM.wait_for_timeout(200)
            pageM.click('#hamDrawer .ham-item[data-act="new-docx"]')
            pageM.wait_for_function("() => document.querySelectorAll('#docxHost .docx p[contenteditable]').length>0", timeout=20000)
            pageM.wait_for_timeout(500)
            r = pageM.evaluate("""() => { const sec=document.querySelector('#docxHost section'); const rect=sec.getBoundingClientRect(); const docx=document.querySelector('#docxHost .docx'); return { vp:innerWidth, secVw:Math.round(rect.width), transform:docx.style.transform, hostScrollX: document.getElementById('docxHost').scrollWidth - document.getElementById('docxHost').clientWidth }; }""")
            no_overflow = r['hostScrollX'] <= 5
            fits = r['secVw'] <= 380
            step("📱: 새 docx 화면 맞춤 + 잘림 없음", no_overflow and fits, str(r))
            # 타이핑
            first_p = pageM.query_selector('#docxHost .docx p[contenteditable]')
            first_p.click(); pageM.wait_for_timeout(200)
            pageM.keyboard.press("End"); pageM.keyboard.type(" 폰타이핑", delay=15)
            pageM.wait_for_timeout(200)
            txt = pageM.evaluate("() => document.querySelector('#docxHost .docx p[contenteditable]').textContent")
            step("📱: 타이핑", "폰타이핑" in txt, txt[:60])
            # 모바일 하단바 저장
            with pageM.expect_download(timeout=15000) as di:
                pageM.click("#mbSaveBtn")
            dl = di.value; p = OUT/"audit_m.docx"; dl.save_as(str(p))
            step("📱: 하단바 저장", p.exists() and p.stat().st_size>500, f"{p.stat().st_size}바이트")
            # 라벨 모바일 분기 + 가시성
            r = pageM.evaluate("() => { const b=document.getElementById('installBtn'); return { label:b.textContent, hidden:b.hidden, visible: b.offsetParent !== null }; }")
            step("📱: 📌 라벨 모바일", '홈 화면' in r['label'], f"label={r['label']}")
            step("📱: 📌 버튼 가시", r['visible'] and not r['hidden'], str(r))
            pageM.screenshot(path=str(OUT/"m_final.png"), full_page=False)
        finally:
            ctx_m.close()
        browser.close()

    pass_cnt = sum(1 for r in results if r[0] == '✅')
    print(f"\n  결과: {pass_cnt} / {len(results)} PASS")
    fails = [r for r in results if r[0] == '❌']
    if fails:
        for r in fails: print(f"    ❌ {r[1]} — {r[2]}")
    sys.exit(0 if pass_cnt == len(results) else 1)


if __name__ == "__main__":
    main()
