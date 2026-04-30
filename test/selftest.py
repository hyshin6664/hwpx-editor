"""
hwpx-editor 자체 검증 (Playwright)
"""
import sys, os, time, base64, json
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# Windows 콘솔 인코딩 강제 UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

LIVE_URL = "https://hyshin6664.github.io/hwpx-editor/"
TEST_FILE = Path(r"C:\Users\신현식\Desktop\★[최종양식] 2026년 오픈소스 AI·SW 개발·활용 지원사업_수정-v.1_수정_2026-04-30_09-01_수정_2026-04-30_09-21_수정_2026-04-30_09-36.hwpx")
OUT_DIR = Path(__file__).parent / "out"
OUT_DIR.mkdir(exist_ok=True)


def p(msg):
    print(msg, flush=True)


def main():
    if not TEST_FILE.exists():
        p(f"FAIL: TEST FILE NOT FOUND: {TEST_FILE}")
        sys.exit(2)

    p(f"=== hwpx-editor self-test ===")
    p(f"URL: {LIVE_URL}")
    p(f"FILE: {TEST_FILE.name}")
    p(f"SIZE: {TEST_FILE.stat().st_size:,} bytes")

    file_bytes = TEST_FILE.read_bytes()
    file_b64 = base64.b64encode(file_bytes).decode()

    console_logs = []
    page_errors = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        page = ctx.new_page()

        page.on("console", lambda m: console_logs.append(f"[{m.type}] {m.text}"))
        page.on("pageerror", lambda e: page_errors.append(str(e)))

        try:
            p("[1] Page goto (commit, 90s)...")
            page.goto(LIVE_URL, wait_until="commit", timeout=90000)
            p("    OK page committed")

            p("[2] Wait domcontentloaded (30s)...")
            page.wait_for_load_state("domcontentloaded", timeout=30000)
            p("    OK DOMContentLoaded")

            p("[3] Wait window.__editor + __loadFileFromBuffer (90s)...")
            page.wait_for_function(
                "() => (typeof window.__editor === 'object') && (typeof window.__loadFileFromBuffer === 'function') && (typeof window.__probe === 'function')",
                timeout=90000,
            )
            p("    OK editor ready")
            page.screenshot(path=str(OUT_DIR / "01_ready.png"))

            p("[3a] PROBE: pageCount before loadFile...")
            probe_before = page.evaluate("() => window.__probe('pageCount')")
            p(f"    probe_before: {probe_before}")

            p("[3b] PROBE: ready before loadFile...")
            probe_ready = page.evaluate("() => window.__probe('ready')")
            p(f"    probe_ready: {probe_ready}")

            p("[4] Inject 7MB file via __loadFileFromBuffer...")
            t0 = time.time()
            result = page.evaluate(
                """async ([b64, name]) => {
                    const bin = atob(b64);
                    const len = bin.length;
                    const u8 = new Uint8Array(len);
                    for (let i = 0; i < len; i++) u8[i] = bin.charCodeAt(i);
                    try {
                      const r = await window.__loadFileFromBuffer(u8, name);
                      return { ok: true, result: r };
                    } catch (err) {
                      return { ok: false, error: String(err && err.message ? err.message : err) };
                    }
                }""",
                [file_b64, TEST_FILE.name],
            )
            elapsed = time.time() - t0
            p(f"[5] loadFile response in {elapsed:.1f}s")
            p(f"    result: {json.dumps(result, ensure_ascii=False)}")
            try:
                page.screenshot(path=str(OUT_DIR / "02_after_load.png"), full_page=True)
            except Exception as ex:
                p(f"    screenshot fail: {ex}")

            p("[5a] PROBE after loadFile: pageCount...")
            probe_after = page.evaluate("() => window.__probe('pageCount')")
            p(f"    probe_after: {probe_after}")

            if not result.get("ok"):
                p(f"\nFAIL: load failed - {result.get('error')}")
                _dump_logs(console_logs, page_errors)
                sys.exit(1)

            p(f"\nPASS: file loaded in {elapsed:.1f}s")
            page_count = result.get("result", {}).get("pageCount", "?")
            p(f"  pageCount: {page_count}")

            p("[6] Try editor.exportHwp() (verify save works)...")
            t0 = time.time()
            export_result = page.evaluate(
                """async () => {
                    try {
                      const bytes = await window.__editor.exportHwp();
                      return { ok: true, length: bytes.length || bytes.byteLength };
                    } catch (err) {
                      return { ok: false, error: String(err && err.message ? err.message : err) };
                    }
                }"""
            )
            elapsed = time.time() - t0
            p(f"  exportHwp in {elapsed:.1f}s: {export_result}")

        except PWTimeout as e:
            p(f"\nFAIL: playwright timeout - {e}")
            try:
                page.screenshot(path=str(OUT_DIR / "99_timeout.png"))
            except Exception:
                pass
            _dump_logs(console_logs, page_errors)
            sys.exit(1)
        except Exception as e:
            p(f"\nFAIL: exception - {e}")
            try:
                page.screenshot(path=str(OUT_DIR / "99_error.png"))
            except Exception:
                pass
            _dump_logs(console_logs, page_errors)
            sys.exit(1)
        finally:
            (OUT_DIR / "console.log").write_text(
                "\n".join(console_logs), encoding="utf-8"
            )
            (OUT_DIR / "errors.log").write_text(
                "\n".join(page_errors), encoding="utf-8"
            )
            browser.close()


def _dump_logs(console_logs, page_errors):
    p("\n--- last console logs ---")
    for line in console_logs[-40:]:
        p(f"  {line}")
    if page_errors:
        p("\n--- page errors ---")
        for err in page_errors[-10:]:
            p(f"  {err}")


if __name__ == "__main__":
    main()
