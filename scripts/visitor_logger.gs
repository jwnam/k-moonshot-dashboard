/**
 * K-문샷 AI신약 미션 대시보드 — 방문자 로거 (Google Apps Script)
 * 배포 방법은 scripts/VISITOR_SETUP.md 참고.
 *
 * - doPost : 방문 기록(소속·이메일·IP·지역 등)을 시트에 추가
 * - doGet  : 관리자 비밀번호 확인 후 전체 기록을 JSON 으로 반환 (admin.html 용)
 */

// ⚠️ 반드시 바꾸세요: 관리자 페이지(admin.html) 비밀번호
const ADMIN_PW = 'CHANGE_ME_관리자비밀번호';
const SHEET_NAME = 'visits';

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    const sh = getSheet_();
    sh.appendRow([
      new Date(),
      String(data.affiliation || ''),
      String(data.email || ''),
      String(data.ip || ''),
      String(data.country || ''),
      String(data.region || ''),
      String(data.city || ''),
      String(data.org || ''),
      data.consent ? 'Y' : 'N',
      String(data.userAgent || '').slice(0, 300),
      String(data.referrer || ''),
      String(data.page || '')
    ]);
    return json_({ ok: true });
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  }
}

function doGet(e) {
  const p = (e && e.parameter) || {};
  if (p.pw !== ADMIN_PW) {
    return json_({ ok: false, error: 'unauthorized' });
  }
  const sh = getSheet_();
  const values = sh.getDataRange().getValues();
  values.shift(); // 헤더 제거
  const rows = values.map(function (r) {
    return {
      ts: r[0], affiliation: r[1], email: r[2], ip: r[3],
      country: r[4], region: r[5], city: r[6], org: r[7],
      consent: r[8], userAgent: r[9], referrer: r[10], page: r[11]
    };
  });
  return json_({ ok: true, count: rows.length, rows: rows });
}

function getSheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(SHEET_NAME);
  if (!sh) {
    sh = ss.insertSheet(SHEET_NAME);
    sh.appendRow(['timestamp', '소속', '이메일', 'IP', '국가', '지역', '도시', '기관(ISP)', '동의', 'UserAgent', 'Referrer', 'Page']);
    sh.setFrozenRows(1);
  }
  return sh;
}

function json_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
