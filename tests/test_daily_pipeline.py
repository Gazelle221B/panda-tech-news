"""scripts/daily_pipeline.sh の契約テスト (Sprint 3 T41, PUBLISH_YOUTUBE オプトイン, Codex レビュー Medium).

fake `uv` シェルスタブを PATH の代わりに `KARYU_UV` へ直接渡し、スクリプトを実サブ
プロセスとして起動する。publish 段の呼び出し条件 (既定 off / produce 失敗時はスキップ /
rc 伝播) を検証する。Irodori サーバ・YouTube API・Discord はいずれも fake uv 側で
応答するため実際には叩かない (`KARYU_HEALTH_URL` を file:// にして「既に稼働中」扱いに
し起動処理そのものを回避する。test_produce_pipeline.py の daily_pipeline smoke と同じ手法)。
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("curl") is None,
    reason="daily_pipeline smoke requires bash and curl",
)

_ROOT = Path(__file__).resolve().parents[1]


def _write_fake_uv(path: Path, *, produce_rc: int, publish_rc: int) -> None:
    """collect/draft は常に成功、produce/publish は指定 rc で応答する uv スタブを書く.

    daily_pipeline.sh は各段を `>> "$LOG" 2>&1` でリダイレクトするため、stderr へ
    書いた `UV:$*` はそのままログファイルへ残る (呼び出しの有無をログ本文で検証できる)。
    """
    path.write_text(
        f"""#!/usr/bin/env bash
echo "UV:$*" >&2
case "$*" in
  *"karyu_tech_news collect --post"*) exit 0 ;;
  *"karyu_tech_news draft --variant A --post"*) exit 0 ;;
  *"karyu_tech_news produce --engine irodori-tts-v3 --post"*) exit {produce_rc} ;;
  *"karyu_tech_news publish --post"*) exit {publish_rc} ;;
  run\\ python\\ -\\ *) cat >/dev/null; echo "Discord failure alert: sent"; exit 0 ;;
  *) exit 0 ;;
esac
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _run_daily_pipeline(
    tmp_path: Path, fake_uv: Path, *, publish_youtube: str | None
) -> subprocess.CompletedProcess[str]:
    health = tmp_path / "health.txt"
    health.write_text("ok", encoding="utf-8")
    env = os.environ.copy()
    env.update(
        {
            "KARYU_PROJECT_DIR": str(tmp_path),
            "KARYU_UV": str(fake_uv),
            "KARYU_HEALTH_URL": health.as_uri(),
            "KARYU_IRODORI_DIR": str(tmp_path),
        }
    )
    if publish_youtube is None:
        env.pop("PUBLISH_YOUTUBE", None)
    else:
        env["PUBLISH_YOUTUBE"] = publish_youtube
    return subprocess.run(
        ["bash", str(_ROOT / "scripts/daily_pipeline.sh")],
        cwd=_ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def _log_text(tmp_path: Path) -> str:
    logs = sorted((tmp_path / "data" / "logs").glob("daily_*.log"))
    assert logs, "daily_*.log が生成されていません"
    return logs[-1].read_text(encoding="utf-8")


def test_publish_not_called_when_opt_out_by_default(tmp_path: Path) -> None:
    """PUBLISH_YOUTUBE 未設定 (既定) では publish 段が呼ばれない."""
    fake_uv = tmp_path / "uv"
    _write_fake_uv(fake_uv, produce_rc=0, publish_rc=0)
    result = _run_daily_pipeline(tmp_path, fake_uv, publish_youtube=None)
    assert result.returncode == 0
    log_text = _log_text(tmp_path)
    assert "karyu_tech_news publish --post" not in log_text


def test_publish_skipped_when_produce_fails(tmp_path: Path) -> None:
    """PUBLISH_YOUTUBE=1 でも produce が非 0 なら publish は実行されず、rc は produce のもの."""
    fake_uv = tmp_path / "uv"
    _write_fake_uv(fake_uv, produce_rc=5, publish_rc=1)
    result = _run_daily_pipeline(tmp_path, fake_uv, publish_youtube="1")
    assert result.returncode == 5
    log_text = _log_text(tmp_path)
    assert "karyu_tech_news publish --post" not in log_text
    assert "publish スキップ" in log_text


def test_publish_failure_propagates_return_code(tmp_path: Path) -> None:
    """PUBLISH_YOUTUBE=1 で publish が非 0 なら全体 rc へ伝播する."""
    fake_uv = tmp_path / "uv"
    _write_fake_uv(fake_uv, produce_rc=0, publish_rc=9)
    result = _run_daily_pipeline(tmp_path, fake_uv, publish_youtube="1")
    assert result.returncode == 9
    log_text = _log_text(tmp_path)
    assert "karyu_tech_news publish --post" in log_text
    assert "WARNING: publish 失敗 (rc=9)" in log_text
    # notify_failure の成功ログは label を無視した固定文言 (既存のスクリプト側の挙動。
    # 本チケットのスコープ外のため修正はせず、Discord 通知が実行された事実だけを確認する)。
    assert "Discord failure alert: sent" in log_text
