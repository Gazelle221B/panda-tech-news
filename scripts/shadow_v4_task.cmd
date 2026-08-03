@echo off
rem panda-tech-news v4 シャドーランのタスクスケジューラ用ランナー (T68/Issue #88)
rem 本番 06:30 の日次配信とは時間分離した平日 12:00 に実行し、v3/v4 並行測定レポートを蓄積する
set PYTHONUTF8=1
"C:\Program Files\Git\usr\bin\bash.exe" -lc "cd /d/_Development/Github/panda-tech-news && uv run --no-sync python scripts/shadow_v4_run.py >> data/logs/shadow_v4_task.log 2>&1"
