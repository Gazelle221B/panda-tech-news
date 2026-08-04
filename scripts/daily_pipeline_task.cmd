@echo off
rem panda-tech-news daily delivery runner for Task Scheduler (T44/Issue #40 Windows port)
rem Runs daily_pipeline.sh via Git Bash and keeps the scheduler-layer log under data/logs/
rem ASCII only below: cmd.exe misparses UTF-8 Japanese comments as cp932 and can
rem execute the resulting fragments as commands, silently breaking following lines
rem (Issue #95 root cause 4). Keep every rem/echo line in this file ASCII-only.
set PYTHONUTF8=1
rem Enable daily YouTube unlisted publish (product owner decision 2026-08-03;
rem public release still requires human approve, same as before)
set PUBLISH_YOUTUBE=1
"C:\Program Files\Git\usr\bin\bash.exe" -lc "cd /d/_Development/Github/panda-tech-news && bash scripts/daily_pipeline.sh >> data/logs/task_scheduler.log 2>&1"
