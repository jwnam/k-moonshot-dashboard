#!/bin/bash
# ─────────────────────────────────────────────────────────────
# k-moonshot-dashboard (canonical, GitHub 최종 기준) → k-moonshot-wiki/docs 미러 동기화
#   · index.html + 대시보드 데이터(json) + 자료실 파일(files/)을 wiki/docs로 복사
#   · news.json 은 wiki 자체 뉴스 파이프라인이 관리하므로 제외
#   · post-commit 훅에서 자동 실행 → 파일 미러 후 wiki docs 커밋·푸시(best-effort)
# ─────────────────────────────────────────────────────────────
set -e
SRC="/Users/jwnam/k-moonshot-dashboard"
WIKI="/Users/jwnam/k-moonshot-wiki"
DST="$WIKI/docs"

[ -d "$DST" ] || { echo "[sync] 대상 없음: $DST"; exit 0; }

# ① 파일 미러
cp "$SRC/index.html" "$DST/index.html"
mkdir -p "$DST/data"
for f in dashboard.json kddf_pipeline.json pipeline_clinical_ctgov.json resources.json; do
  [ -f "$SRC/data/$f" ] && cp "$SRC/data/$f" "$DST/data/$f"
done
if [ -d "$SRC/files" ]; then
  rsync -a --delete "$SRC/files/" "$DST/files/"
fi
echo "[sync] 파일 미러 완료 ($(date '+%F %T'))"

# ② wiki docs 커밋·푸시 (best-effort — 실패해도 훅 중단 안 함)
{
  git -C "$WIKI" add docs/
  if ! git -C "$WIKI" diff --cached --quiet; then
    git -C "$WIKI" commit -q -m "sync: 대시보드 미러 (canonical→docs) $(date '+%F %T')"
    git -C "$WIKI" pull --rebase --autostash origin main || true
    git -C "$WIKI" push origin main && echo "[sync] wiki docs 푸시 완료"
  else
    echo "[sync] wiki docs 변경 없음"
  fi
} || echo "[sync] wiki 커밋/푸시 스킵(오류 무시)"
