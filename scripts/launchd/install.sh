#!/usr/bin/env bash
# 華流テック通信 — 日次自動配信 launchd エージェントのインストール (T44)
#
# テンプレート plist の __HOME__ プレースホルダを実 $HOME へ展開し、
# ~/Library/LaunchAgents に配置して launchctl へ登録する。冪等 (再実行で置換)。
#
# 使い方:   bash scripts/launchd/install.sh
# 撤去:     bash scripts/launchd/uninstall.sh
set -euo pipefail

LABEL="com.karyu.daily-pipeline"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE="${SCRIPT_DIR}/${LABEL}.plist"
DEST_DIR="${HOME}/Library/LaunchAgents"
DEST="${DEST_DIR}/${LABEL}.plist"

[ -f "$TEMPLATE" ] || { echo "FATAL: テンプレートが見つからない: ${TEMPLATE}" >&2; exit 1; }

mkdir -p "$DEST_DIR"
mkdir -p "${HOME}/projects/panda-tech-news/data/logs"

# __HOME__ を実 $HOME へ展開 (launchd は StandardOutPath 等で $HOME を展開しないため)。
# 一時ファイルへ展開 → lint → 成功時のみ本配置へ mv。壊れたテンプレートで
# live plist を破損状態に上書きしない (Codex T44 レビュー Medium)。
# HOME に & や | が含まれても壊れないよう index/substr で完全 literal 置換する
# (sed も awk gsub も置換文字列側で特殊文字を解釈するため使わない)。__HOME__ は 8 文字。
TMP="$(mktemp "${DEST}.tmp.XXXXXX")"
trap 'rm -f "$TMP"' EXIT
awk -v home="$HOME" '{
  while ((i = index($0, "__HOME__")) > 0)
    $0 = substr($0, 1, i - 1) home substr($0, i + 8)
  print
}' "$TEMPLATE" > "$TMP"

# 構文検証 (壊れた plist を load しない)。
plutil -lint "$TMP"
mv "$TMP" "$DEST"
trap - EXIT

# 既存登録があれば解除してから再登録 (冪等)。別 path から同一 label が load 済みでも
# 取りこぼさないよう remove も試す (launchctl load の "already loaded" 失敗を防ぐ)。
launchctl unload "$DEST" 2>/dev/null || true
launchctl remove "$LABEL" 2>/dev/null || true
launchctl load "$DEST"

echo "インストール完了: ${DEST}"
echo "登録確認:"
launchctl list | grep "$LABEL" || echo "  (launchctl list に未表示 — load 直後は反映遅延の場合あり)"
echo
echo "次回発火: 平日 (月〜金) 06:30。Mac がスリープ中は発火せず次回 wake 時に catch-up。"
echo "確実な wake が必要なら: pmset repeat wakeorpoweron MTWRF 06:25:00 (要 sudo)"
