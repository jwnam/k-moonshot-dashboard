#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_projects.py — K-문샷 사업별 「마일스톤·성과관리 양식」 docx → 대시보드 JSON 변환

용도
  연구책임자가 Google Drive(/사업관리/__전략·__핵심·__협력사업현황/<사업명>/)에 올린
  「마일스톤·성과관리 양식_<사업명>.docx」를 파싱하여 data/projects/<id>.json 을 생성/갱신한다.

운영 흐름 (월간)
  · 매월 25일 : 연구책임자에게 성과 업데이트 문의 + 작성 안내 메일 자동 발송 (별도 routine)
  · 매월  1일 : docx 동기화 → 본 스크립트로 JSON 갱신 → 신호등 재계산 → wiki 반영 → 배포
  ※ 실제 월간 동기화는 Claude가 Google Drive MCP로 docx를 읽어 수행하며,
    본 스크립트는 로컬에 내려받은 .docx 를 파싱하거나 파싱 로직의 단일 기준(SSOT)으로 쓴다.

사용법
  pip install python-docx
  python3 scripts/sync_projects.py --docx "마일스톤·성과관리 양식_디지털AI세포.docx" --id digital-ai-cell
  python3 scripts/sync_projects.py --recompute-lights   # 전체 JSON 신호등만 재계산

이메일 추출
  사업개요 '이메일 주소' 행에서 주관/공동 연구책임자·작성담당자 이메일을
  쉼표(,)·세미콜론(;)·공백으로 구분된 문자열에서 정규식으로 추출하여 overview.emails 에 기록.
"""
import argparse, json, re, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJ_DIR = ROOT / "data" / "projects"

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
MS_SYMBOLS = {"●", "◑", "○"}


def extract_emails(text: str):
    """쉼표/세미콜론/공백 등으로 구분된 문자열에서 이메일 주소만 추출 (중복 제거, 순서 유지)."""
    if not text:
        return []
    found = EMAIL_RE.findall(text)
    seen, out = set(), []
    for e in found:
        el = e.strip().rstrip(".,;")
        if el.lower() not in seen:
            seen.add(el.lower())
            out.append(el)
    return out


def detect_status(cell: str) -> str:
    """달성현황 셀에서 마일스톤 상태 기호(●/◑/○) 판별. 없으면 '' 반환."""
    for sym in ("●", "◑", "○"):
        if sym in (cell or ""):
            return sym
    return ""


def months_overdue(due_str: str, now: datetime) -> int:
    try:
        due = datetime.strptime(due_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return 0
    if due >= now:
        return 0
    return (now.year - due.year) * 12 + (now.month - due.month)


def compute_light(project: dict, now: datetime = None):
    """신호등 자동 판정 — index.html computeLight() 와 동일 규칙."""
    now = now or datetime.now()
    st = project.get("status") or {}
    verdicts = sum(1 for c in (project.get("check_history") or []) if c.get("delayed"))
    if st.get("override"):
        return {"light": st["override"], "reasons": ["관리자 수동 지정"],
                "delay_quarters": 0, "delay_verdicts": verdicts}

    dated = [m for m in (project.get("milestones") or []) if m.get("due")]
    if not dated:
        return {"light": "미정", "reasons": ["마일스톤 일정(분기말) 정보 미입력 — 판정 보류"],
                "delay_quarters": 0, "delay_verdicts": verdicts}

    max_over, n_delayed = 0, 0
    for m in dated:
        if m.get("status") == "●":
            continue
        ov = months_overdue(m["due"], now)
        if ov > 0:
            n_delayed += 1
            max_over = max(max_over, ov)

    reasons = []
    if n_delayed == 0:
        light = "green"; reasons.append("마일스톤 일정대로 진행")
    elif max_over <= 6:
        light = "yellow"; reasons.append(f"마일스톤 지체 {max_over}개월(2분기 이내), 지체 {n_delayed}건")
    elif max_over <= 12:
        light = "orange"; reasons.append(f"마일스톤 지체 {max_over}개월(3분기~1년), 지체 {n_delayed}건")
    else:
        light = "red"; reasons.append(f"마일스톤 지체 {max_over}개월(1년 이상), 지체 {n_delayed}건")

    rank = {"green": 0, "yellow": 1, "orange": 2, "red": 3}
    def worse(a, b):
        return b if rank[b] > rank[a] else a
    if verdicts >= 3:
        light = worse(light, "red"); reasons.append(f"분기점검 지체판정 {verdicts}회(3회 이상)")
    elif verdicts >= 2:
        light = worse(light, "orange"); reasons.append(f"분기점검 지체판정 {verdicts}회(2회 이상)")
    elif verdicts == 1:
        reasons.append("분기점검 지체판정 1회")

    return {"light": light, "reasons": reasons,
            "delay_quarters": round(max_over / 3, 1), "delay_verdicts": verdicts}


def _rows(table):
    return [[c.text.strip() for c in r.cells] for r in table.rows]


def parse_docx(path: Path, pid: str) -> dict:
    try:
        from docx import Document
    except ImportError:
        sys.exit("python-docx 필요: pip install python-docx")

    doc = Document(str(path))
    tables = [_rows(t) for t in doc.tables]

    proj = {
        "id": pid, "name": pid,
        "overview": {"lead_org": None, "pi": None, "co_pi": None, "period_raw": None,
                     "period_start": None, "period_end": None, "budget_total_mw": None,
                     "objective": None, "research_content": None, "mission_relevance": None,
                     "emails": []},
        "milestones": [], "outcomes": {"data": [], "ai_model": [], "drug": []},
        "progress_log": [], "needs": {"difficulties": None, "resources": None, "issues": None},
        "status": {"light": "미정", "auto": True, "override": None}, "check_history": [],
        "source_doc": {"last_synced": datetime.now().strftime("%Y-%m-%d")}, "rfp_url": None,
    }

    # --- 사업개요 테이블 (라벨→값) ---
    for tbl in tables:
        flat = {}
        for row in tbl:
            for i in range(0, len(row) - 1, 2):
                k, v = row[i], row[i + 1]
                if k:
                    flat[k] = v
        ov = proj["overview"]
        if "사업명" in flat:
            proj["name"] = flat["사업명"] or pid
        if "주관기관" in flat: ov["lead_org"] = flat["주관기관"] or None
        if "연구책임자" in flat: ov["pi"] = flat["연구책임자"] or None
        if "사업기간" in flat: ov["period_raw"] = flat["사업기간"] or None
        if "사업 목표" in flat: ov["objective"] = flat["사업 목표"] or None
        if "주요 연구 내용" in flat: ov["research_content"] = flat["주요 연구 내용"] or None
        for k in flat:
            if "관련성" in k: ov["mission_relevance"] = flat[k] or None
            if "이메일" in k: ov["emails"] = extract_emails(flat[k])

    proj["status"].update(compute_light(proj))
    return proj


def save(proj: dict):
    PROJ_DIR.mkdir(parents=True, exist_ok=True)
    out = PROJ_DIR / f"{proj['id']}.json"
    out.write_text(json.dumps(proj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✔ {out.relative_to(ROOT)}  신호등={proj['status']['light']}  emails={proj['overview']['emails']}")


def recompute_lights():
    for f in sorted(PROJ_DIR.glob("*.json")):
        if f.name == "index.json":
            continue
        p = json.loads(f.read_text(encoding="utf-8"))
        p.setdefault("status", {}).update(compute_light(p))
        f.write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"✔ {f.name}  신호등={p['status']['light']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--docx", help="파싱할 .docx 경로")
    ap.add_argument("--id", help="사업 id (예: digital-ai-cell)")
    ap.add_argument("--recompute-lights", action="store_true", help="전체 JSON 신호등만 재계산")
    a = ap.parse_args()
    if a.recompute_lights:
        recompute_lights()
    elif a.docx and a.id:
        save(parse_docx(Path(a.docx), a.id))
    else:
        ap.print_help()
