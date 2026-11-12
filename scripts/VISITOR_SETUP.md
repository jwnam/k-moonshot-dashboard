# 방문자 로그 · 관리자 페이지 설정 가이드

K-문샷 대시보드는 GitHub Pages(정적 호스팅)라 방문 기록을 저장할 백엔드가 필요합니다.
**Google 스프레드시트 + Apps Script 웹앱**으로 구성합니다. (무료, PD실 Google 계정 내에서 관리)

## 1) 구글 시트 + Apps Script 만들기

1. [sheets.new](https://sheets.new) 로 새 구글 시트를 만들고 이름을 `K-문샷 대시보드 방문자 로그` 로 지정
2. 시트 상단 메뉴 **확장 프로그램 → Apps Script** 클릭
3. 열린 편집기의 코드를 모두 지우고 **`scripts/visitor_logger.gs`** 내용을 붙여넣기
4. 맨 위 `ADMIN_PW` 값을 **원하는 관리자 비밀번호**로 변경 → 저장(💾)

## 2) 웹앱으로 배포

1. 우측 상단 **배포 → 새 배포**
2. 유형 선택(톱니바퀴) → **웹 앱**
3. 설정:
   - 설명: `방문자 로거`
   - **실행 계정: 나(본인)**
   - **액세스 권한: 모든 사용자(Anyone)**  ← 중요
4. **배포** → 권한 승인(본인 계정) → **웹 앱 URL 복사**
   (형식: `https://script.google.com/macros/s/XXXX/exec`)

> 코드를 수정하면 매번 **배포 → 배포 관리 → 편집(연필) → 버전: 새 버전 → 배포** 로 갱신해야 반영됩니다.

## 3) 대시보드에 URL 연결

복사한 웹앱 URL을 아래 **두 파일**의 `VISITOR_ENDPOINT` 에 붙여넣기:

- `index.html` — `const VISITOR_ENDPOINT = '...';` (방문자 게이트 상단 스크립트)
- `admin.html` — `const VISITOR_ENDPOINT = '...';`

```js
const VISITOR_ENDPOINT = 'https://script.google.com/macros/s/XXXX/exec';
```

그 후 커밋·푸시하면 적용됩니다.

## 4) 사용

- 방문자: `index.html` 접속 시 **소속·이메일 입력 + 개인정보 동의** 후 입장 (매 방문마다 입력)
- 관리자: **`admin.html`** 접속 → `ADMIN_PW` 입력 → 방문수·방문기관·지역 현황 확인

## 동작·보안 메모

- 방문 전송은 `text/plain` 본문으로 보내 CORS preflight 를 회피합니다(Apps Script 제약 때문).
- URL 미설정 상태에서도 게이트는 동작하며, 열람은 허용되고 기록만 저장되지 않습니다(fail-open).
- 관리자 데이터는 비밀번호(`pw`)가 일치할 때만 반환됩니다. 비밀번호는 주기적으로 교체 권장.
- 수집 개인정보(소속·이메일·IP·지역)는 동의 기반이며, 동의 내역은 `index.html` 의 모달에 고지됩니다.
