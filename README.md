# 한글 · PDF · 워드 간단 편집기

브라우저에서 **`.hwp` · `.hwpx` · `.pdf` · `.docx`** 문서를 보고 간단히 편집해서 다시 받는 무료 편집기.

👉 **[바로 사용하기](https://hyshin6664.github.io/hwpx-editor/)**

## 지원 포맷

| 포맷 | 화면 | 편집 | 다운로드 |
|---|---|---|---|
| **`.hwpx`** (신 한글) | 100% (rhwp 엔진) | 클릭해서 그 자리 편집 | `.hwpx` · `.hwp` · PDF |
| **`.hwp`** (구 한글) | 100% (rhwp 엔진) | 클릭해서 그 자리 편집 | `.hwpx` · `.hwp` · PDF |
| **`.docx`** (워드) | 텍스트 | 문단 단위 편집 | `.docx` · PDF |
| **`.pdf`** | 100% (PDF.js) | (보기·다운로드만) | PDF |

## 특징

- **서버 없음** — 파일이 여러분의 브라우저 안에서만 처리됩니다.
- **설치 없음** — 맥 · 윈도우 · 안드로이드 · 아이폰 다 됨.
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

- **`.pdf` 편집** — 현재는 보기·다운로드만. 본문 텍스트 편집은 PDF 포맷 한계 (다음 버전).
- **`.docx`** — 단순 텍스트 편집만. 표·이미지 편집은 안 됨.
- **첫 방문 5~10초** — 엔진 다운로드, 이후 캐시.

## 라이선스

MIT.

---

CDN & Cloud is by Solbox..
