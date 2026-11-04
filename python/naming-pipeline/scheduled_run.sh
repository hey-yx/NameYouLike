#!/bin/zsh
# naming-pipeline 每日定时任务：增量抓取 → 全量重算统计 → 刷新 brandgen 内置瘦身数据。
# 由 launchd（com.nameyoulike.pipeline，每天 03:00）调起；手动执行也安全（data/.lock 防并发）。
# 日志追加到同目录 cron.log。
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PY="$HERE/.venv/bin/python"
LOG="$HERE/cron.log"

cd "$HERE" || exit 1
exec >> "$LOG" 2>&1

echo "===== $(date '+%F %T') scheduled_run 开始 ====="
"$PY" -m pipeline.run --max-f10 300
pipeline_rc=$?
if [ "$pipeline_rc" -ne 0 ]; then
  # 管道失败时统计可能没更新：继续导出会把旧数据或半截写入内置 slim。
  echo "===== $(date '+%F %T') scheduled_run 结束 pipeline_rc=$pipeline_rc（跳过导出）====="
  exit "$pipeline_rc"
fi
"$PY" ../scripts/extract_slim.py output/naming_patterns.v1.json ../brandgen/data/naming_patterns.slim.json
slim_rc=$?
echo "===== $(date '+%F %T') scheduled_run 结束 pipeline_rc=$pipeline_rc slim_rc=$slim_rc ====="
exit "$slim_rc"
