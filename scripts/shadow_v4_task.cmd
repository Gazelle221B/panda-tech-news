@echo off
rem panda-tech-news v4 shadow run runner for Task Scheduler (T68/Issue #88)
rem Runs weekdays at 12:00, time-separated from the 06:30 production daily
rem pipeline, to accumulate v3/v4 parallel measurement reports.
rem ASCII only below: cmd.exe misparses UTF-8 Japanese comments as cp932 and can
rem execute the resulting fragments as commands, silently breaking following lines
rem (Issue #95 root cause 4). Keep every rem/echo line in this file ASCII-only.
set PYTHONUTF8=1
"C:\Program Files\Git\usr\bin\bash.exe" -lc "cd /d/_Development/Github/panda-tech-news && PYTHONUTF8=1 uv run --no-sync python scripts/shadow_v4_run.py >> data/logs/shadow_v4_task.log 2>&1"
