# Solbox Docs · 문서 편집기

어떤 문서든, 브라우저 안에서.
**`.hwp` · `.hwpx` · `.pdf` · `.docx`** 한 곳에서 보고, 편집하고, 받습니다.

👉 **[바로 사용하기](https://hyshin6664.github.io/hwpx-editor/)**

## 지원 포맷

| 포맷 | 화면 | 편집 | 다운로드 |
|---|---|---|---|
| **`.hwpx`** (신 한글) | 100% (rhwp 엔진) | 클릭해서 그 자리 편집 | `.hwpx` · `.hwp` · PDF |
| **`.hwp`** (구 한글) | 100% (rhwp 엔진) | 클릭해서 그 자리 편집 | `.hwpx` · `.hwp` · PDF |
| **`.docx`** (워드) | 텍스트 | 문단 단위 편집 | `.docx` · PDF |
| **`.pdf`** | 100% (PDF.js) | 🩹 지우개 드래그 + ✏️ 글씨 클릭 입력 (한글 폰트 임베딩) | PDF |

## 특징

- **서버 없음** — 파일이 여러분의 브라우저 안에서만 처리됩니다.
- **설치 없음** — 맥 · 윈도우 · 안드로이드 · 아이폰 다 됨.
- **자동저장** — 편집 중 5초마다 자동 보관, 다음 방문 때 복구 제안.
- **되돌리기** — Ctrl+Z / Ctrl+Shift+Z (PDF 지우개·글씨).
- **모바일 터치** — 안드로이드/아이폰에서 터치로 PDF 지우개·글씨.
- **광고 · 추적 없음**.
- **100% 무료, 오픈소스 (MIT)**.

## 사용 방법

1. 화면 가운데에 파일 끌어다 놓기 (또는 [📁 파일 열기])
2. 자동으로 형식 감지 → 적절한 화면
3. 글자 클릭해서 편집
4. 상단 다운로드 버튼 — 받고 싶은 형식 선택

## 기술 스택

- 한글: [`@rhwp/editor`](https://github.com/edwardkim/rhwp) (Rust + WASM, MIT)
- PDF: [PDF.js](https://mozilla.github.io/pdf.js/) (Mozilla)
- DOCX: [JSZip](https://stuk.github.io/jszip/) + DOMParser (zip + XML 직접 편집)
- 디자인: 파스텔 (라벤더 · 민트 · 피치)
- HTML 한 파일 (`index.html`) · GitHub Pages 호스팅

## 자체 검증 (Playwright)

- `test/selftest.py` — HWP/HWPX 7MB 80페이지 종합 ALL PASS
- `test/selftest_pdf_docx.py` — PDF + DOCX ALL PASS

## 한계

- **`.pdf` 편집** — "지우개"로 글자를 지우고(주변 색으로 채움) "글씨" 도구로 빈 자리에 새 글 입력. 한글 폰트(Noto Sans KR / Pretendard / 나눔고딕/명조) 자동 임베딩. 본문 글자 직접 변경은 PDF 포맷 한계.
- **`.docx`** — 단순 텍스트 편집만. 표·이미지 편집은 안 됨.
- **첫 방문 5~10초** — 엔진 다운로드, 이후 캐시.

## 라이선스

MIT.

---

CDN & Cloud is by Solbox..
