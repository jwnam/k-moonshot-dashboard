#!/bin/bash
# ─────────────────────────────────────────────────────────────
# k-moonshot-dashboard (canonical, GitHub 최종 기준) → k-moonshot-wiki/docs 미러 동기화
#   · index.html + 대시보드 데이터(json) + 자료실 파일(files/)을 wiki/docs로 복사
#   · news.json 은 wiki 자체 뉴스 파이프라인이 관리하므로 제외
#   · post-commit 훅에서 자동 실행되며, wiki repo의 자동 동기화 크론이 커밋·푸시
# ─────────────────────────────────────────────────────────────
set -e
SRC="/Users/jwnam/k-moonshot-dashboard"
DST="/Users/jwnam/k-moonshot-wiki/docs"

[ -d "$DST" ] || { echo "[sync] 대상 없음: $DST"; exit 0; }

cp "$SRC/index.html" "$DST/index.html"
mkdir -p "$DST/data"
for f in dashboard.json kddf_pipeline.json pipeline_clinical_ctgov.json resources.json; do
  [ -f "$SRC/data/$f" ] && cp "$SRC/data/$f" "$DST/data/$f"
done
# 자료실 첨부(files/) 변경분만 동기화
if [ -d "$SRC/files" ]; then
  rsync -a --delete "$SRC/files/" "$DST/files/"
fi
echo "[sync] canonical → wiki/docs 완료 ($(date '+%F %T'))"
