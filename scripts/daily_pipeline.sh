#!/usr/bin/env bash
# 華流テック通信 — 日次自動配信パイプライン (T33)
#
# collect → draft(variant A) → produce(Irodori 参照音声) を順に実行し、各段で Discord へ
# ニュースサマリー / 台本 / 完パケ mp3 を配信する。launchd から平日朝に 1 回起動される想定。
#
# 設計方針:
#   - 各 CLI は内部で fail-open (1 ソース失敗で止めない / Discord 失敗で collect を fail させない)。
#     本スクリプトはその思想を引き継ぎ、1 段が失敗しても次段へ進む (set -e は使わない)。
#     ただし最終 produce の品質ゲート失敗は、通知と cleanup 後に非 0 終了して外部監視へ伝える。
#   - 段間は SQLite で疎結合 (collect→store←deliver)。draft が失敗しても produce は直近 draft を使える。
#   - Irodori サーバ (ローカル) は produce に必須。未起動なら起動し health を待ち、本ジョブが
#     起動した場合のみ終了時に停止する (外部起動分は残す)。
#   - launchd は最小環境で動くため PATH / cwd / 必要 env をすべて明示する。
#   - T55 (Issue #49): swap 枯渇下では TTS 合成が最大 10 倍劣化し、client timeout → 503 連鎖 →
#     fail-fast する事象を実運用で観測した。produce 直前に軽量な資源チェック (swap/load) を行い、
#     閾値超過時は produce を実行せずスキップする ("資源不足なら最初から挑まない")。
#     collect / draft は軽量なため対象外 (常に実行)。
set -uo pipefail

# launchd の最小 PATH を先に補う (以降の command -v が解決できるように)。
# Homebrew (ffmpeg = T30 マスタリング必須) を含める: launchd は bare PATH のため
# /opt/homebrew/bin (Apple Silicon) / /usr/local/bin (Intel) を明示しないと ffmpeg 不在で produce が rc=1。
export PATH="${HOME}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

# パスは env で上書き可。既定はスクリプト位置 / $HOME / PATH から解決しポータビリティを確保する。
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${KARYU_PROJECT_DIR:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
IRODORI_DIR="${KARYU_IRODORI_DIR:-${HOME}/tools/Irodori-TTS-Server}"
UV="${KARYU_UV:-$(command -v uv || echo "${HOME}/.local/bin/uv")}"
# サーバは localhost のみにバインドし LAN 露出を避ける (Copilot 指摘)。health も同 host。
HEALTH_URL="${KARYU_HEALTH_URL:-http://127.0.0.1:8088/health}"

export IRODORI_TIMEOUT="${IRODORI_TIMEOUT:-1800}"  # T55/Issue #49: 07-13朝の最悪実測1211sに対する余裕 (旧300は503連鎖の一因)

# T55 (Issue #49): produce 前の資源プリフライト閾値。env で上書き可。
# 不正値 (非数値/空/負) は resources_ok() 内で既定値へ置換して WARN する (Codex レビュー指摘:
# 例えば KARYU_MAX_SWAP_MB=abc は awk の文字列比較でチェックが無効化され produce が走ってしまう)。
DEFAULT_MAX_SWAP_MB=12000  # swap 使用量 (MB)。実RAM 16GB機で12〜22GB枯渇を観測
DEFAULT_MAX_LOAD=25        # load average 1分値
KARYU_MAX_SWAP_MB="${KARYU_MAX_SWAP_MB:-$DEFAULT_MAX_SWAP_MB}"
KARYU_MAX_LOAD="${KARYU_MAX_LOAD:-$DEFAULT_MAX_LOAD}"
# T34: 本スクリプトが起動する Irodori サーバは 600M VoiceDesign checkpoint を使う
# (caption 話法制御を有効化)。既存稼働サーバを health チェックで再利用する場合は、
# そのサーバが 600M であることが前提 (人間が 500M を停止し 600M を起動済みのこと)。
export IRODORI_HF_CHECKPOINT="${IRODORI_HF_CHECKPOINT:-Aratako/Irodori-TTS-600M-v3-VoiceDesign}"

LOG_DIR="${PROJECT_DIR}/data/logs"
mkdir -p "$LOG_DIR"
STAMP="$(date '+%Y%m%d_%H%M%S')"
LOG="${LOG_DIR}/daily_${STAMP}.log"
PIDFILE="${LOG_DIR}/.irodori.pid"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

health_ok() { curl -fsS -o /dev/null --max-time 5 "$HEALTH_URL"; }

# T55 (Issue #49): 有限の非負数 (整数または小数) のみ受理する数値検証。
# 負数・nan・inf・空・非数値を弾く (Codex レビュー: awk へ非数値を渡すと文字列比較になり
# 閾値チェックが黙って無効化されるため、比較前に必ず通す)。
is_nonneg_number() { [[ "$1" =~ ^[0-9]+([.][0-9]+)?$ ]]; }

# T55 (Issue #49): sysctl から swap 使用量 (MB) を解析する。macOS の
# "total = ... used = 12345.67M free = ..." 形式 (取得失敗時は空文字)。
get_swap_used_mb_sysctl() {
  sysctl -n vm.swapusage 2>/dev/null | sed -n 's/.*used = \([0-9.]*\)M.*/\1/p'
}

# T55 (Issue #49): sysctl から load average 1分値を解析する。macOS の
# "{ 1.23 2.34 3.45 }" 先頭値 (取得失敗時は空文字)。
get_load_1min_sysctl() {
  sysctl -n vm.loadavg 2>/dev/null | awk '{print $2}'
}

# T55 (Issue #49): produce 前の資源プリフライトチェック。swap 使用量が KARYU_MAX_SWAP_MB
# を超える、または load average 1分値が KARYU_MAX_LOAD を超える場合に false (1) を返す。
# 資源値は KARYU_SWAP_USED_MB / KARYU_LOAD_1MIN の注入 (契約テスト経路) を優先し、
# 未設定・不正値なら sysctl 実測へフォールバック。最終的に数値を得られない場合
# (sysctl 非対応環境など) は fail-open で true (0) を返す。
# RESOURCE_SWAP_USED_MB / RESOURCE_LOAD_1MIN に取得値を残し、呼び出し側の通知文言に使う。
RESOURCE_SWAP_USED_MB=""
RESOURCE_LOAD_1MIN=""
resources_ok() {
  local swap_used load1 max_swap max_load swap_exceeded load_exceeded

  # 閾値の検証: 不正値は安全側 = 既定値へ置換 (チェックの黙殺を防ぐ)
  max_swap="$KARYU_MAX_SWAP_MB"
  if ! is_nonneg_number "$max_swap"; then
    log "WARNING: KARYU_MAX_SWAP_MB 不正値 '${max_swap}' — 既定 ${DEFAULT_MAX_SWAP_MB} で判定"
    max_swap="$DEFAULT_MAX_SWAP_MB"
  fi
  max_load="$KARYU_MAX_LOAD"
  if ! is_nonneg_number "$max_load"; then
    log "WARNING: KARYU_MAX_LOAD 不正値 '${max_load}' — 既定 ${DEFAULT_MAX_LOAD} で判定"
    max_load="$DEFAULT_MAX_LOAD"
  fi

  # 資源値の検証: 注入値が不正なら sysctl 実測へフォールバック (= 既定の取得経路)
  swap_used="${KARYU_SWAP_USED_MB:-}"
  if [ -n "$swap_used" ] && ! is_nonneg_number "$swap_used"; then
    log "WARNING: KARYU_SWAP_USED_MB 不正値 '${swap_used}' — sysctl 実測へフォールバック"
    swap_used=""
  fi
  [ -z "$swap_used" ] && swap_used="$(get_swap_used_mb_sysctl)"

  load1="${KARYU_LOAD_1MIN:-}"
  if [ -n "$load1" ] && ! is_nonneg_number "$load1"; then
    log "WARNING: KARYU_LOAD_1MIN 不正値 '${load1}' — sysctl 実測へフォールバック"
    load1=""
  fi
  [ -z "$load1" ] && load1="$(get_load_1min_sysctl)"

  if ! is_nonneg_number "$swap_used" || ! is_nonneg_number "$load1"; then
    log "WARNING: 資源チェック値を取得できず (swap=${swap_used:-N/A}, load=${load1:-N/A}) — fail-open で続行"
    return 0
  fi

  RESOURCE_SWAP_USED_MB="$swap_used"
  RESOURCE_LOAD_1MIN="$load1"

  swap_exceeded="$(awk -v v="$swap_used" -v max="$max_swap" 'BEGIN { print (v + 0 > max + 0) ? 1 : 0 }')"
  load_exceeded="$(awk -v v="$load1" -v max="$max_load" 'BEGIN { print (v + 0 > max + 0) ? 1 : 0 }')"

  if [ "$swap_exceeded" = "1" ] || [ "$load_exceeded" = "1" ]; then
    log "資源不足のため produce をスキップ (swap=${swap_used}M [閾値 ${max_swap}M] / load=${load1} [閾値 ${max_load}])"
    return 1
  fi

  log "資源チェック OK (swap=${swap_used}M, load=${load1})"
  return 0
}

cd "$PROJECT_DIR" || { echo "FATAL: cd $PROJECT_DIR 失敗" >&2; exit 1; }

# 多重起動ガード: mkdir は POSIX で原子的。catch-up 発火と手動実行が produce(~30-40分)中に
# 重なって同一 DB へ並走するのを防ぐ。取得失敗 = 既に実行中なら即終了。
LOCK_DIR="${LOG_DIR}/.daily_pipeline.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  log "別の daily_pipeline が実行中 (lock: ${LOCK_DIR}) — 多重起動を回避して終了"
  exit 0
fi
trap 'rm -rf "$LOCK_DIR"' EXIT

log "=== 日次パイプライン開始 (engine=irodori-tts-v3 参照音声, IRODORI_TIMEOUT=${IRODORI_TIMEOUT}) ==="

# --- Irodori サーバ存命確認 (down なら起動し health を待つ) ---
STARTED_SERVER=0
if health_ok; then
  log "Irodori サーバ: 既に稼働中 (既存を利用)"
else
  log "Irodori サーバ: 未起動 → 起動"
  ( cd "$IRODORI_DIR" && nohup "$UV" run python -m irodori_openai_tts --host 127.0.0.1 --port 8088 \
      >> "${LOG_DIR}/irodori_server_${STAMP}.log" 2>&1 & echo $! > "$PIDFILE" )
  STARTED_SERVER=1
  # 初回はモデルロードがあるため最大 180s 待つ
  for _ in $(seq 1 60); do
    health_ok && { log "Irodori サーバ: 起動完了 (health OK)"; break; }
    sleep 3
  done
  health_ok || log "WARNING: Irodori サーバが health に未到達。produce 失敗の可能性 (fail-open 続行)"
fi

# --- 各段を fail-open で順次実行 ---
run_step() {
  local label="$1"; shift
  log "--- ${label} 開始 ---"
  if "$@" >> "$LOG" 2>&1; then
    log "--- ${label} 成功 ---"
    return 0
  else
    local rc=$?
    log "WARNING: ${label} 失敗 (rc=${rc}) — fail-open で次段へ"
    return "$rc"
  fi
}

notify_failure() {
  local label="$1"
  local rc="$2"
  local log_path="$3"

  if "$UV" run python - "$label" "$rc" "$log_path" >> "$LOG" 2>&1 <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

from karyu_tech_news.config import load_settings
from karyu_tech_news.deliver.discord import post_summary

label, rc, log_path = sys.argv[1], sys.argv[2], sys.argv[3]
settings = load_settings(Path.cwd() / ".env")
webhook_url = settings.discord_error_webhook_url or settings.discord_webhook_url
if not webhook_url:
    print("WARNING: Discord failure alert skipped (webhook not set)")
    raise SystemExit(0)

content = (
    "⚠️ 華流テック通信 daily_pipeline 失敗通知\n"
    f"- step: {label}\n"
    f"- rc: {rc}\n"
    f"- log: {log_path}\n"
    "音声配信がスキップされた可能性があります。"
)
ok = post_summary(webhook_url, content)
print("Discord failure alert: " + ("sent" if ok else "failed"))
PY
  then
    log "${label} 失敗通知: 処理完了"
  else
    log "WARNING: ${label} 失敗通知コマンドが失敗"
  fi
}

# --- state.db バックアップ (T47) ---
# collect が新規 items を書き込む前に SQLite スナップショットを取る。item_key 履歴が
# 失われると重複配信を招くため、破損・誤削除からの復旧手段を用意する。
# fail-open: バックアップ失敗はパイプラインを止めない (ログのみ、配信は継続)。
backup_state_db() {
  local db="${PROJECT_DIR}/data/state.db"
  local backup_dir="${PROJECT_DIR}/data/backups"
  local keep=7  # 平日運用で約 1.5 週間分を保持
  [ -f "$db" ] || { log "state.db 未作成 — バックアップをスキップ"; return 0; }
  # 本スクリプトは set -e 非使用のため mkdir 失敗でも即終了しないが、意図を明示して
  # fail-open を自己文書化する (バックアップ不能でも collect 以降は継続)。
  mkdir -p "$backup_dir" 2>>"$LOG" || {
    log "WARNING: バックアップ先ディレクトリ作成失敗 (パイプラインは継続): ${backup_dir}"
    return 0
  }
  local dest="${backup_dir}/state_${STAMP}.db"
  # sqlite3 .backup はオンライン整合バックアップ (WAL 中でも安全)。cp より堅い。
  if sqlite3 "$db" ".backup '${dest}'" 2>>"$LOG"; then
    log "state.db バックアップ成功: ${dest} ($(du -h "$dest" | cut -f1))"
    # 世代ローテーション: 新しい keep 件を残し、古いものを削除。
    # shellcheck disable=SC2012
    ls -1t "${backup_dir}"/state_*.db 2>/dev/null | tail -n +$((keep + 1)) | while IFS= read -r old; do
      rm -f "$old" && log "古いバックアップを削除: $(basename "$old")"
    done
  else
    log "WARNING: state.db バックアップ失敗 (パイプラインは継続)"
  fi
}

backup_state_db

run_step "collect" "$UV" run python -m karyu_tech_news collect --post
run_step "draft"   "$UV" run python -m karyu_tech_news draft --variant A --post

# T55 (Issue #49): produce 前の資源プリフライト。閾値超過なら produce を実行せずスキップする
# (音声ゼロを success 扱いしない既存方針を維持: rc は非 0 で終了する)。
if resources_ok; then
  run_step "produce" "$UV" run python -m karyu_tech_news produce --engine irodori-tts-v3 --post
  PRODUCE_RC=$?
else
  PRODUCE_RC=97  # 資源不足スキップの専用 rc (実 produce 失敗と区別するための sentinel)
fi
FINAL_RC=0
if [ "$PRODUCE_RC" -ne 0 ]; then
  if [ "$PRODUCE_RC" -eq 97 ]; then
    notify_failure "資源不足のため produce をスキップ (swap=${RESOURCE_SWAP_USED_MB}M, load=${RESOURCE_LOAD_1MIN})" "$PRODUCE_RC" "$LOG"
  else
    notify_failure "produce" "$PRODUCE_RC" "$LOG"
  fi
  FINAL_RC="$PRODUCE_RC"
fi

# --- Sprint 3 (T41): YouTube 限定公開配信 (オプトイン。既定 off) ---
# 恒久運用の判断は人間ゲート (PROJECT_STATE「人間判断待ち」) のため、
# PUBLISH_YOUTUBE=1 を明示した環境でのみ実行する。公開 (public) 化は含まない
# (人間が朝確認後に `karyu approve`)。
if [ "${PUBLISH_YOUTUBE:-0}" = "1" ]; then
  if [ "$PRODUCE_RC" -eq 0 ]; then
    run_step "publish" "$UV" run python -m karyu_tech_news publish --post
    PUBLISH_RC=$?
    if [ "$PUBLISH_RC" -ne 0 ]; then
      notify_failure "publish" "$PUBLISH_RC" "$LOG"
      if [ "$FINAL_RC" -eq 0 ]; then
        FINAL_RC="$PUBLISH_RC"
      fi
    fi
  else
    log "publish スキップ (produce rc=${PRODUCE_RC} — 当日音声が無いまま古い音声を配信しない)"
  fi
fi

# --- 本ジョブが起動したサーバのみ停止 (外部起動分は温存) ---
if [ "$STARTED_SERVER" = "1" ] && [ -f "$PIDFILE" ]; then
  PID="$(cat "$PIDFILE")"
  # PID 再利用 (TOCTOU) を避け、対象が確かに irodori サーバの場合のみ kill する
  if [ -n "$PID" ] && ps -p "$PID" -o command= 2>/dev/null | grep -q "irodori_openai_tts"; then
    kill "$PID" 2>/dev/null && log "Irodori サーバ停止 (PID ${PID}, 本ジョブ起動分)"
  else
    log "PID ${PID} は irodori プロセスでない/不在 — kill をスキップ (PID 再利用ガード)"
  fi
  rm -f "$PIDFILE"
fi

log "=== 日次パイプライン終了 (rc=${FINAL_RC}, log: ${LOG}) ==="
exit "$FINAL_RC"
