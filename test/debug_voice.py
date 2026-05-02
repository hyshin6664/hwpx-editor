"""실제 voice FAB 클릭 시 무슨 일이 일어나는지 추적."""
import sys, time
from playwright.sync_api import sync_playwright
try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

URL = "https://hyshin6664.github.io/hwpx-editor/?cb=" + str(int(time.time()*1000))

with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True, args=['--use-fake-ui-for-media-stream'])
    ctx = b.new_context(viewport={"width": 1280, "height": 800}, permissions=['microphone'])
    page = ctx.new_page()
    msgs = []
    page.on("console", lambda m: msgs.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: msgs.append(f"[ERR] {e}"))
    page.on("dialog", lambda d: (msgs.append(f"[ALERT] {d.message}"), d.accept()))
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_function("() => window.__editorReady === true", timeout=60000)
    print("페이지 로드 완료\n")

    # 새 docx 만들기
    page.click("#newBtn"); page.wait_for_timeout(200)
    page.click('#newMenu .newm-item[data-fmt="docx"]')
    page.wait_for_function("() => document.querySelectorAll('#docxHost .docx p[contenteditable]').length>0", timeout=20000)
    page.wait_for_timeout(500)

    # 첫 문단 클릭 → focus
    page.click('#docxHost .docx p[contenteditable]')
    page.wait_for_timeout(300)

    # 1) micBtn.click() 직접 호출
    msgs.clear()
    print("=== micBtn.click() 직접 호출 ===")
    page.evaluate("document.getElementById('micBtn').click()")
    page.wait_for_timeout(2000)
    state1 = page.evaluate("""() => ({
      recording: document.getElementById('voiceFab').classList.contains('recording'),
      bubble: document.getElementById('voiceBubble').classList.contains('visible'),
    })""")
    print("STATE after micBtn.click:", state1)
    print("logs:")
    for m in msgs[-10:]: print(" ", m)

    page.wait_for_timeout(500)
    msgs.clear()
    print("\n=== voiceFab.click() 직접 호출 ===")
    page.evaluate("document.getElementById('voiceFab').click()")
    page.wait_for_timeout(2000)

    state = page.evaluate("""() => ({
      recognizing: typeof recognizing !== 'undefined' ? recognizing : 'N/A',
      hasRecognition: typeof recognition !== 'undefined' ? !!recognition : 'N/A',
      _userStoppedVoice: typeof _userStoppedVoice !== 'undefined' ? _userStoppedVoice : 'N/A',
      _voicePermChecked: typeof _voicePermChecked !== 'undefined' ? _voicePermChecked : 'N/A',
      voiceFabRecording: document.getElementById('voiceFab').classList.contains('recording'),
      voiceBubbleVisible: document.getElementById('voiceBubble').classList.contains('visible'),
      hasSpeechRec: !!(window.SpeechRecognition || window.webkitSpeechRecognition),
      activeEl: document.activeElement ? document.activeElement.tagName + (document.activeElement.id ? '#'+document.activeElement.id : '') : null,
    })""")
    print("STATE:", state)
    print("\n=== 콘솔 로그 ===")
    for m in msgs[-20:]:
        print(m)
    b.close()
