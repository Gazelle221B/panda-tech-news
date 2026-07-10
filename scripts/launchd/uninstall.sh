#!/usr/bin/env bash
# 華流テック通信 — 日次自動配信 launchd エージェントの撤去 (T44)
#
# 使い方: bash scripts/launchd/uninstall.sh
set -euo pipefail

LABEL="com.karyu.daily-pipeline"
DEST="${HOME}/Library/LaunchAgents/${LABEL}.plist"

if [ -f "$DEST" ]; then
  launchctl unload "$DEST" 2>/dev/null || true
  rm -f "$DEST"
  echo "撤去完了: ${DEST} を unload + 削除した"
else
  echo "撤去対象なし: ${DEST} は存在しない"
fi

# 取りこぼしがないか確認。
if launchctl list | grep -qF "$LABEL"; then
  echo "WARNING: launchctl list に ${LABEL} がまだ残っている — 手動で launchctl remove ${LABEL} を検討" >&2
else
  echo "登録なしを確認 (launchctl list クリーン)"
fi
