# 한글 간단 편집기

브라우저에서 `.hwp` · `.hwpx` 한글 문서를 **폴라리스 오피스 수준 화면 충실도**로 보고 편집해서 `.hwp · .hwpx · PDF` 로 다시 받는 무료 편집기.

👉 **[바로 사용하기](https://hyshin6664.github.io/hwpx-editor/)**

## 특징

- **서버 없음**: 파일이 여러분의 브라우저 안에서만 처리됩니다. 어디에도 업로드되지 않습니다.
- **설치 없음**: 맥 · 윈도우 · 안드로이드 · 아이폰 · 어떤 브라우저든 동작.
- **100% 화면 충실도**: 한컴 한글 엔진을 (Rust + WebAssembly 로) 그대로 구현한 [`@rhwp/editor`](https://github.com/edwardkim/rhwp) 임베드.
- **클릭해서 그 자리에서 편집**: 글자를 직접 클릭/선택해서 수정.
- **3가지 형식 다운로드**: `.hwpx · .hwp · PDF`.
- **구버전 `.hwp` · 신버전 `.hwpx` 모두 지원**.
- **광고 · 추적 없음**.
- **오픈소스 MIT**.

## 사용 방법

1. **파일 열기**: 화면에 끌어다 놓거나 [📁 파일 열기] 버튼.
2. **편집**: 본문에서 글자를 직접 클릭해서 수정.
3. **저장**: 상단 [.hwpx · .hwp · PDF] 버튼 중 원하는 형식.

## 기술 스택

- 메인 엔진: [`@rhwp/editor`](https://www.npmjs.com/package/@rhwp/editor) (Rust + WASM, MIT, Edward Kim 작)
- HWP→HWPX 변환 폴백: [`@ssabrojs/hwpxjs`](https://www.npmjs.com/package/@ssabrojs/hwpxjs)
- PDF 저장: 모든 페이지를 SVG 로 추출 → 새 창에 모아 브라우저 인쇄 → "PDF로 저장"
- HTML 한 파일 (`index.html`)
- GitHub Pages 호스팅

## 자체 검증

`test/selftest.py` (Playwright 기반):
- 7MB `.hwpx` (80페이지): 로드 2초, 모든 다운로드 버튼 통과
- 7.4MB `.hwp` (구버전, 80페이지): 로드 2초, 모든 다운로드 버튼 통과
- `python test/selftest.py` 로 직접 실행 가능

## 한계

- 차트 · OLE · 글맵시 등 일부 복잡 요소는 화면에 단순화되어 보일 수 있음 (rhwp 엔진 한계).
- PDF 저장은 브라우저 인쇄 다이얼로그를 사용 — "대상: PDF로 저장" 선택 필요.
- 처음 한 번 5~10초 로딩 (rhwp 엔진 + 폰트 다운로드, 이후 캐시).

## 라이선스

MIT.

이 편집기 자체 코드와 사용한 모든 의존성(`@rhwp/editor`, `@ssabrojs/hwpxjs`, JSZip)은 모두 MIT 호환.
