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
import sys
from pathlib import Path

import pytest

# Windows では CreateProcess が PATH より先に System32 を探すため、subprocess の
# "bash" は常に WSL bash (System32\bash.exe) に解決される。WSL bash は Windows パス
# (スクリプト絶対パス・fake uv スタブ・KARYU_* env) を解釈できず rc=127 になるため、
# この smoke は POSIX 環境 (macOS / Linux / WSL 内実行) 専用とする。
pytestmark = pytest.mark.skipif(
    sys.platform == "win32" or shutil.which("bash") is None or shutil.which("curl") is None,
    reason="daily_pipeline smoke requires POSIX bash and curl",
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
    tmp_path: Path,
    fake_uv: Path,
    *,
    publish_youtube: str | None,
    swap_used_mb: str | None = None,
    load_1min: str | None = None,
    max_swap_mb: str | None = None,
    max_load: str | None = None,
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
    # T55 (Issue #49): 資源チェック値の注入経路。未指定ならスクリプトが実 sysctl から取得する
    # (このマシンの実測が閾値内であることを前提にした既存テストを壊さないため、資源チェックを
    # 明示的に検証するテストのみ指定する)。
    for key, value in (
        ("KARYU_SWAP_USED_MB", swap_used_mb),
        ("KARYU_LOAD_1MIN", load_1min),
        ("KARYU_MAX_SWAP_MB", max_swap_mb),
        ("KARYU_MAX_LOAD", max_load),
    ):
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return subprocess.run(
        ["bash", str(_ROOT / "scripts/daily_pipeline.sh")],
        cwd=_ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def _write_fake_uv_capturing_notify_args(path: Path, *, args_out: Path) -> None:
    """collect/draft/produce は常に成功させ、notify_failure() の Python 呼び出し引数
    (label/rc/log_path/custom_message) を args_out へ書き出す (Issue #98: リソースガード
    発動時に custom_message が正しく組み立てられ notify_failure() へ渡ることを検証するため)。

    produce は既定で成功させる (このテストの主眼は資源プリフライトでの skip であり、
    produce 自体は資源チェックを通過しなければ呼ばれない)。
    """
    args_out_str = str(args_out).replace("\\", "\\\\")
    path.write_text(
        f"""#!/usr/bin/env bash
echo "UV:$*" >&2
case "$*" in
  *"karyu_tech_news collect --post"*) exit 0 ;;
  *"karyu_tech_news draft --variant A --post"*) exit 0 ;;
  *"karyu_tech_news produce --engine irodori-tts-v3 --post"*) exit 0 ;;
  run\\ python\\ -\\ *)
    cat >/dev/null
    shift 3
    printf '%s\\n' "$#" > "{args_out_str}"
    for a in "$@"; do
      printf '%s\\n' "$a" >> "{args_out_str}"
    done
    echo "Discord failure alert: sent"
    exit 0
    ;;
  *) exit 0 ;;
esac
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _log_text(tmp_path: Path) -> str:
    logs = sorted((tmp_path / "data" / "logs").glob("daily_*.log"))
    assert logs, "daily_*.log が生成されていません"
    return logs[-1].read_text(encoding="utf-8")


# T55 (Issue #49): 既存 (publish 系) テストは produce の実行そのものを前提にしているため、
# ホストマシンの実際の swap/load に関わらず必ず資源チェックを通過するよう安全な値を明示注入する
# (このリポジトリの実測 swap は既定閾値 12000M に近い/超えることがあり、注入なしだと
# ホスト状態次第でテストが不安定になる)。
_SAFE_RESOURCE_KWARGS = {"swap_used_mb": "500", "load_1min": "1"}


def test_publish_not_called_when_opt_out_by_default(tmp_path: Path) -> None:
    """PUBLISH_YOUTUBE 未設定 (既定) では publish 段が呼ばれない."""
    fake_uv = tmp_path / "uv"
    _write_fake_uv(fake_uv, produce_rc=0, publish_rc=0)
    result = _run_daily_pipeline(
        tmp_path, fake_uv, publish_youtube=None, **_SAFE_RESOURCE_KWARGS
    )
    assert result.returncode == 0
    log_text = _log_text(tmp_path)
    assert "karyu_tech_news publish --post" not in log_text


def test_publish_skipped_when_produce_fails(tmp_path: Path) -> None:
    """PUBLISH_YOUTUBE=1 でも produce が非 0 なら publish は実行されず、rc は produce のもの."""
    fake_uv = tmp_path / "uv"
    _write_fake_uv(fake_uv, produce_rc=5, publish_rc=1)
    result = _run_daily_pipeline(
        tmp_path, fake_uv, publish_youtube="1", **_SAFE_RESOURCE_KWARGS
    )
    assert result.returncode == 5
    log_text = _log_text(tmp_path)
    assert "karyu_tech_news publish --post" not in log_text
    assert "publish スキップ" in log_text


def test_publish_failure_propagates_return_code(tmp_path: Path) -> None:
    """PUBLISH_YOUTUBE=1 で publish が非 0 なら全体 rc へ伝播する."""
    fake_uv = tmp_path / "uv"
    _write_fake_uv(fake_uv, produce_rc=0, publish_rc=9)
    result = _run_daily_pipeline(
        tmp_path, fake_uv, publish_youtube="1", **_SAFE_RESOURCE_KWARGS
    )
    assert result.returncode == 9
    log_text = _log_text(tmp_path)
    assert "karyu_tech_news publish --post" in log_text
    assert "WARNING: publish 失敗 (rc=9)" in log_text
    assert "Discord failure alert: sent" in log_text
    # notify_failure() の成功ログが label を正しく反映していること (T50, Issue #42:
    # 以前は label を無視した "produce 失敗通知" 固定文言だった)。
    assert "publish 失敗通知: 処理完了" in log_text


# --- T55 (Issue #49): 資源プリフライトチェックの契約テスト ---


def test_produce_skipped_when_swap_exceeds_threshold(tmp_path: Path) -> None:
    """swap 使用量が KARYU_MAX_SWAP_MB を超えると produce (fake uv) は呼ばれず rc 非 0 + 通知ログ."""
    fake_uv = tmp_path / "uv"
    _write_fake_uv(fake_uv, produce_rc=0, publish_rc=0)
    result = _run_daily_pipeline(
        tmp_path,
        fake_uv,
        publish_youtube=None,
        swap_used_mb="13000",
        load_1min="1",
        max_swap_mb="12000",
    )
    # rc=97 は「資源不足スキップ」専用 sentinel (実 produce 失敗の rc と区別する外部監視契約)
    assert result.returncode == 97
    log_text = _log_text(tmp_path)
    assert "karyu_tech_news produce --engine irodori-tts-v3 --post" not in log_text
    assert "資源不足のため produce をスキップ" in log_text
    assert "swap=13000M" in log_text
    assert "Discord failure alert: sent" in log_text


def test_produce_skipped_when_load_exceeds_threshold(tmp_path: Path) -> None:
    """load average 1分値が KARYU_MAX_LOAD を超えると produce (fake uv) は呼ばれず rc=97 + 通知ログ."""
    fake_uv = tmp_path / "uv"
    _write_fake_uv(fake_uv, produce_rc=0, publish_rc=0)
    result = _run_daily_pipeline(
        tmp_path,
        fake_uv,
        publish_youtube=None,
        swap_used_mb="500",
        load_1min="30",
        max_load="25",
    )
    assert result.returncode == 97
    log_text = _log_text(tmp_path)
    assert "karyu_tech_news produce --engine irodori-tts-v3 --post" not in log_text
    assert "資源不足のため produce をスキップ" in log_text
    assert "load=30" in log_text
    assert "Discord failure alert: sent" in log_text


def test_produce_runs_when_resources_within_threshold(tmp_path: Path) -> None:
    """swap/load とも閾値内なら produce (fake uv) が呼ばれ rc 0 で完走する."""
    fake_uv = tmp_path / "uv"
    _write_fake_uv(fake_uv, produce_rc=0, publish_rc=0)
    result = _run_daily_pipeline(
        tmp_path,
        fake_uv,
        publish_youtube=None,
        swap_used_mb="500",
        load_1min="1",
        max_swap_mb="12000",
        max_load="25",
    )
    assert result.returncode == 0
    log_text = _log_text(tmp_path)
    assert "karyu_tech_news produce --engine irodori-tts-v3 --post" in log_text
    assert "資源チェック OK" in log_text


def test_resource_thresholds_are_env_overridable(tmp_path: Path) -> None:
    """KARYU_MAX_SWAP_MB / KARYU_MAX_LOAD の env 上書きが効く (既定閾値内でも上書き値で判定される)."""
    fake_uv = tmp_path / "uv"
    _write_fake_uv(fake_uv, produce_rc=0, publish_rc=0)
    # 既定閾値 (12000M) 内の swap でも、上書きした低い閾値 (100M) を超えていればスキップされる。
    result = _run_daily_pipeline(
        tmp_path,
        fake_uv,
        publish_youtube=None,
        swap_used_mb="500",
        load_1min="1",
        max_swap_mb="100",
    )
    assert result.returncode == 97
    log_text = _log_text(tmp_path)
    assert "karyu_tech_news produce --engine irodori-tts-v3 --post" not in log_text
    assert "swap=500M" in log_text
    assert "閾値 100M" in log_text


def test_invalid_threshold_falls_back_to_default(tmp_path: Path) -> None:
    """KARYU_MAX_SWAP_MB=abc など不正閾値は既定値へ置換され、チェックは無効化されない.

    Codex レビュー指摘: 非数値の閾値を awk へそのまま渡すと文字列比較になり、
    swap 超過でも produce が走ってしまう。不正値は WARN ログ + 既定値 (12000M) で判定する。
    """
    fake_uv = tmp_path / "uv"
    _write_fake_uv(fake_uv, produce_rc=0, publish_rc=0)
    result = _run_daily_pipeline(
        tmp_path,
        fake_uv,
        publish_youtube=None,
        swap_used_mb="13000",  # 既定閾値 12000M を超過
        load_1min="1",
        max_swap_mb="abc",  # 不正値 — 既定 12000 で判定されるべき
    )
    assert result.returncode == 97
    log_text = _log_text(tmp_path)
    assert "karyu_tech_news produce --engine irodori-tts-v3 --post" not in log_text
    assert "WARNING: KARYU_MAX_SWAP_MB 不正値 'abc'" in log_text
    assert "閾値 12000M" in log_text
    assert "資源不足のため produce をスキップ" in log_text


# --- Issue #98: 資源ガード発動時の Discord 通知文言 ---


def test_resource_guard_notification_uses_dedicated_message(tmp_path: Path) -> None:
    """swap 超過による produce スキップ時、notify_failure() へ渡る Discord 本文 (第4引数)
    が専用のリソースガード文言になっていること (汎用の「失敗通知」固定文言に埋もれない)。

    08-06/08-07 の実インシデントでは通知自体は送信されていたが、他の失敗通知と見た目が
    同じ汎用テンプレートだったため 3 営業日気づけなかった (Issue #98)。緊急性が伝わる
    専用文言であることと、実測値・閾値が埋め込まれていることを検証する。
    """
    fake_uv = tmp_path / "uv"
    args_out = tmp_path / "notify_args.txt"
    _write_fake_uv_capturing_notify_args(fake_uv, args_out=args_out)
    result = _run_daily_pipeline(
        tmp_path,
        fake_uv,
        publish_youtube=None,
        swap_used_mb="26639",
        load_1min="1",
        max_swap_mb="12000",
        max_load="25",
    )
    assert result.returncode == 97
    assert args_out.exists(), "notify_failure() の Python 呼び出しが行われていません"
    lines = args_out.read_text(encoding="utf-8").splitlines()
    argc = int(lines[0])
    assert argc == 4, f"notify_failure() へ渡る引数は label/rc/log_path/custom_message の4件のはず (実際: {argc})"
    custom_message = lines[4]  # lines[1..3] = label, rc, log_path / lines[4] = custom_message
    assert custom_message.startswith("⚠️ リソースガード発動:")
    assert "swap 26639M" in custom_message
    assert "閾値 12000M" in custom_message
    assert "配信は行われません" in custom_message
    assert "Issue #98" in custom_message
    # 汎用テンプレート固有の曖昧な文言 (可能性があります) は使われていないこと
    assert "可能性があります" not in custom_message


def test_produce_failure_notification_has_no_custom_message(tmp_path: Path) -> None:
    """実 produce 失敗 (rc!=0, !=97) では custom_message は空文字のまま (第4引数)、
    従来どおり notify_failure() 内の汎用テンプレートにフォールバックすること
    (資源ガード専用文言が誤って他の失敗ケースにも流用されないことの回帰防止)。
    """
    fake_uv = tmp_path / "uv"
    args_out = tmp_path / "notify_args.txt"
    _write_fake_uv_capturing_notify_args(fake_uv, args_out=args_out)
    # produce を非0で終了させたいので、fake uv を書き換えて produce だけ失敗させる。
    fake_uv.write_text(
        fake_uv.read_text(encoding="utf-8").replace(
            '*"karyu_tech_news produce --engine irodori-tts-v3 --post"*) exit 0 ;;',
            '*"karyu_tech_news produce --engine irodori-tts-v3 --post"*) exit 5 ;;',
        ),
        encoding="utf-8",
    )
    fake_uv.chmod(0o755)
    result = _run_daily_pipeline(
        tmp_path,
        fake_uv,
        publish_youtube=None,
        **_SAFE_RESOURCE_KWARGS,
    )
    assert result.returncode == 5
    lines = args_out.read_text(encoding="utf-8").splitlines()
    argc = int(lines[0])
    assert argc == 4
    label, rc, custom_message = lines[1], lines[2], lines[4]
    assert label == "produce"
    assert rc == "5"
    assert custom_message == ""
