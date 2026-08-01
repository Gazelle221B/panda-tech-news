@echo off
rem panda-tech-news 日次配信のタスクスケジューラ用ランナー (T44/Issue #40 の Windows 移行版)
rem Git Bash 経由で daily_pipeline.sh を実行し、スケジューラ層のログを data/logs/ に残す
set PYTHONUTF8=1
"C:\Program Files\Git\usr\bin\bash.exe" -lc "cd /d/_Development/Github/panda-tech-news && bash scripts/daily_pipeline.sh >> data/logs/task_scheduler.log 2>&1"
