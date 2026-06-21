#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
자료실 자동 등록 스크립트 — K-Moonshot 대시보드

파일을 files/ 로 복사하고 data/resources.json 에 항목을 추가/삭제/조회한다.
대시보드 '📚 자료실' 탭이 resources.json 을 읽어 게시판처럼 표시한다.

사용 예:
  # 등록 (출처는 여러 번 반복 가능, "라벨|URL" 형식)
  python3 add_resource.py add report.pdf \
      --title "2026 글로벌 신약 트렌드" \
      --category "동향분석" \
      --desc "주요 모달리티별 시장 전망 요약" \
      --source "출처기관 원문|https://example.com/report"

  python3 add_resource.py list                 # 현재 목록 보기
  python3 add_resource.py remove 3             # id=3 항목 삭제(파일도 삭제 옵션)
  python3 add_resource.py add x.docx --title "..." --commit   # 등록 후 git add/commit/push

분류(category) 예: 동향분석 · 정책 · 보고서 · 논문 · 회의자료 · 기타
"""
import argparse, json, shutil, subprocess, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES_DIR = ROOT / "files"
JSON_PATH = ROOT / "data" / "resources.json"

EXT_TYPE = {
    ".docx": "DOCX", ".doc": "DOC", ".pdf": "PDF", ".xlsx": "XLSX", ".xls": "XLS",
    ".pptx": "PPTX", ".ppt": "PPT", ".hwpx": "HWPX", ".hwp": "HWP",
    ".csv": "CSV", ".txt": "TXT", ".md": "MD", ".zip": "ZIP", ".json": "JSON",
}


def load():
    if JSON_PATH.exists():
        return json.loads(JSON_PATH.read_text(encoding="utf-8"))
    return {"updated": "", "items": []}


def save(data):
    data["updated"] = date.today().isoformat()
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git_commit(paths, msg):
    try:
        subprocess.run(["git", "-C", str(ROOT), "add", *map(str, paths)], check=True)
        subprocess.run(["git", "-C", str(ROOT), "commit", "-q", "-m", msg], check=True)
        subprocess.run(["git", "-C", str(ROOT), "push", "origin", "HEAD"], check=True)
        print("✅ git commit & push 완료")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ git 작업 실패: {e}")


def cmd_add(args):
    src = Path(args.file).expanduser()
    if not src.is_file():
        sys.exit(f"❌ 파일을 찾을 수 없음: {src}")

    FILES_DIR.mkdir(parents=True, exist_ok=True)
    dest = FILES_DIR / src.name
    # 이미 files/ 안의 파일이면 복사 생략
    if src.resolve() != dest.resolve():
        if dest.exists() and not args.overwrite:
            sys.exit(f"❌ 이미 존재: {dest.name} (덮어쓰려면 --overwrite)")
        shutil.copy2(src, dest)
        print(f"📁 복사: {dest.relative_to(ROOT)}")

    sources = []
    for s in (args.source or []):
        if "|" in s:
            label, url = s.split("|", 1)
            sources.append({"label": label.strip(), "url": url.strip()})
        else:
            sources.append({"label": s.strip(), "url": s.strip()})

    data = load()
    next_id = max([it.get("id", 0) for it in data["items"]], default=0) + 1
    item = {
        "id": next_id,
        "title": args.title,
        "category": args.category,
        "date": args.date or date.today().isoformat(),
        "file": f"files/{dest.name}",
        "filetype": EXT_TYPE.get(dest.suffix.lower(), dest.suffix.lstrip(".").upper() or "FILE"),
        "desc": args.desc or "",
        "sources": sources,
    }
    data["items"].insert(0, item)  # 최신이 맨 위
    save(data)
    print(f"✅ 등록 완료 (id={next_id}): {args.title}")
    print(f"   {JSON_PATH.relative_to(ROOT)} · 총 {len(data['items'])}건")

    if args.commit:
        git_commit([JSON_PATH, dest], f"자료실 등록: {args.title}")


def cmd_attach(args):
    """기존 게시물(id)에 원본/추가 파일을 첨부한다."""
    data = load()
    item = next((it for it in data["items"] if it.get("id") == args.id), None)
    if not item:
        sys.exit(f"❌ id={args.id} 항목 없음")
    src = Path(args.file).expanduser()
    if not src.is_file():
        sys.exit(f"❌ 파일을 찾을 수 없음: {src}")
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    dest = FILES_DIR / src.name
    if src.resolve() != dest.resolve():
        if dest.exists() and not args.overwrite:
            sys.exit(f"❌ 이미 존재: {dest.name} (덮어쓰려면 --overwrite)")
        shutil.copy2(src, dest)
        print(f"📁 복사: {dest.relative_to(ROOT)}")
    ftype = EXT_TYPE.get(dest.suffix.lower(), dest.suffix.lstrip(".").upper() or "FILE")
    att = {"label": args.label or f"원본({ftype})", "file": f"files/{dest.name}", "filetype": ftype}
    item.setdefault("attachments", []).append(att)
    save(data)
    print(f"✅ 첨부 완료: [{args.id}] {item['title']} ← {att['label']}")
    if args.commit:
        git_commit([JSON_PATH, dest], f"자료실 첨부: {item['title']} ({att['label']})")


def cmd_list(args):
    data = load()
    if not data["items"]:
        print("(자료 없음)")
        return
    print(f"📚 자료실 {len(data['items'])}건 (updated: {data.get('updated','—')})\n")
    for it in data["items"]:
        print(f"  [{it['id']:>2}] {it['date']} · {it['category']:<6} · {it['title']}")
        print(f"       {it['file']}  ({it.get('filetype','')})")
        for a in it.get("attachments", []):
            print(f"        └ 첨부: {a['file']}  ({a.get('label','')})")


def cmd_remove(args):
    data = load()
    before = len(data["items"])
    target = next((it for it in data["items"] if it.get("id") == args.id), None)
    if not target:
        sys.exit(f"❌ id={args.id} 항목 없음")
    data["items"] = [it for it in data["items"] if it.get("id") != args.id]
    save(data)
    print(f"🗑️  삭제: [{args.id}] {target['title']} ({before}→{len(data['items'])}건)")
    if args.delete_file:
        f = ROOT / target["file"]
        if f.exists():
            f.unlink(); print(f"   파일 삭제: {target['file']}")
    if args.commit:
        git_commit([JSON_PATH], f"자료실 삭제: {target['title']}")


def main():
    ap = argparse.ArgumentParser(description="K-Moonshot 대시보드 자료실 등록 스크립트")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="자료 등록")
    a.add_argument("file", help="등록할 파일 경로")
    a.add_argument("--title", required=True, help="제목")
    a.add_argument("--category", default="기타", help="분류 (예: 동향분석·정책·보고서·논문·회의자료)")
    a.add_argument("--desc", default="", help="내용 요약")
    a.add_argument("--source", action="append", help='출처 "라벨|URL" (반복 가능)')
    a.add_argument("--date", help="등록일 YYYY-MM-DD (기본: 오늘)")
    a.add_argument("--overwrite", action="store_true", help="같은 이름 파일 덮어쓰기")
    a.add_argument("--commit", action="store_true", help="등록 후 git commit & push")
    a.set_defaults(func=cmd_add)

    at = sub.add_parser("attach", help="기존 게시물에 원본/추가 파일 첨부")
    at.add_argument("id", type=int, help="대상 게시물 id")
    at.add_argument("file", help="첨부할 파일 경로")
    at.add_argument("--label", help='첨부 라벨 (기본: "원본(확장자)")')
    at.add_argument("--overwrite", action="store_true", help="같은 이름 파일 덮어쓰기")
    at.add_argument("--commit", action="store_true", help="첨부 후 git commit & push")
    at.set_defaults(func=cmd_attach)

    l = sub.add_parser("list", help="목록 보기")
    l.set_defaults(func=cmd_list)

    r = sub.add_parser("remove", help="자료 삭제")
    r.add_argument("id", type=int, help="삭제할 항목 id")
    r.add_argument("--delete-file", action="store_true", help="files/ 의 실제 파일도 삭제")
    r.add_argument("--commit", action="store_true", help="삭제 후 git commit & push")
    r.set_defaults(func=cmd_remove)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
