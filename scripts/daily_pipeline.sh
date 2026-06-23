#!/usr/bin/env bash
# 華流テック通信 — 日次自動配信パイプライン (T33)
#
# collect → draft(variant A) → produce(Irodori 参照音声) を順に実行し、各段で Discord へ
# ニュースサマリー / 台本 / 完パケ mp3 を配信する。launchd から平日朝に 1 回起動される想定。
#
# 設計方針:
#   - 各 CLI は内部で fail-open (1 ソース失敗で止めない / Discord 失敗で collect を fail させない)。
#     本スクリプトはその思想を引き継ぎ、1 段が失敗しても次段へ進む (set -e は使わない)。
#   - 段間は SQLite で疎結合 (collect→store←deliver)。draft が失敗しても produce は直近 draft を使える。
#   - Irodori サーバ (ローカル) は produce に必須。未起動なら起動し health を待ち、本ジョブが
#     起動した場合のみ終了時に停止する (外部起動分は残す)。
#   - launchd は最小環境で動くため PATH / cwd / 必要 env をすべて明示する。
set -uo pipefail

# launchd の最小 PATH を先に補う (以降の command -v が解決できるように)
export PATH="${HOME}/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

# パスは env で上書き可。既定はスクリプト位置 / $HOME / PATH から解決しポータビリティを確保する。
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${KARYU_PROJECT_DIR:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
IRODORI_DIR="${KARYU_IRODORI_DIR:-${HOME}/tools/Irodori-TTS-Server}"
UV="${KARYU_UV:-$(command -v uv || echo "${HOME}/.local/bin/uv")}"
# サーバは localhost のみにバインドし LAN 露出を避ける (Copilot 指摘)。health も同 host。
HEALTH_URL="${KARYU_HEALTH_URL:-http://127.0.0.1:8088/health}"

export IRODORI_TIMEOUT="${IRODORI_TIMEOUT:-300}"  # 参照音声の遅い 1 文を救う (irodori.py 既定と同値)
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
  else
    local rc=$?
    log "WARNING: ${label} 失敗 (rc=${rc}) — fail-open で次段へ"
  fi
}

run_step "collect" "$UV" run python -m karyu_tech_news collect --post
run_step "draft"   "$UV" run python -m karyu_tech_news draft --variant A --post
run_step "produce" "$UV" run python -m karyu_tech_news produce --engine irodori-tts-v3 --post

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

log "=== 日次パイプライン終了 (log: ${LOG}) ==="
