# 実装計画: Sprint 3 — 配信 (波形動画 + YouTube 限定公開)

> 起点: [requirements-v1.0.md](./requirements-v1.0.md) §8.12 (FR-110〜112) / §8.13 (FR-120〜122) / §15.4、[roadmap.md](./roadmap.md) Sprint 3 節。
> 受け入れ基準: **v0.5 — 限定公開 YouTube 動画が生成・投稿できる** (要件 §18)。
> 判断記録: [ADR-0007](./adr/ADR-0007-youtube-httpx-cli-approval.md) (httpx 直叩き + CLI 承認フロー)。

## 1. ゴールと DoD

`produce` が生成した完パケ mp3 から **波形動画 mp4 を生成し、YouTube に限定公開でアップロードし、Discord に確認依頼を投稿し、人間の承認で公開に切り替える** までを CLI で通す。

### Sprint 3 DoD (要件 §15.4 + v0.5)

- [ ] `publish` が audio_versions の mp3 から mp4 (H.264/AAC, showwaves 波形 + ロゴ静止画) を生成する (FR-110/111/112)
- [ ] `publish` が YouTube Data API v3 で **unlisted** アップロードできる (FR-120/122)
- [ ] 動画説明欄に AI 開示文言が**常に**含まれる (FR-121, コードで強制)
- [ ] `video_versions` テーブルに動画パス・YouTube video id・privacy が永続化される
- [ ] Discord に「✅ approve / 🔁 再生成 / ❌ 見送り」の朝確認メッセージが届く (要件 §15.4 朝確認フロー)
- [ ] `approve` が限定公開 → 公開への切り替えを CLI で行える
- [ ] pytest / ruff / mypy strict / shellcheck 全緑、新規依存ゼロ (§5 依存最小)

## 2. 設計の所在

| 対象 | 正とする文書 |
|---|---|
| 動画仕様 (解像度/コーデック/波形) | 本書 §3 + `video/render.py` docstring |
| YouTube API 呼び出し・OAuth | [ADR-0007](./adr/ADR-0007-youtube-httpx-cli-approval.md) + `deliver/youtube.py` docstring |
| AI 開示文言 | FR-121。定数 `AI_DISCLOSURE` (`deliver/youtube.py`)。例文どおり「本番組はAI音声キャスターHALによる自動生成番組です。」 |
| 朝確認フロー | 本書 §3.4 (Bot 化しない。承認は `approve` CLI) |

## 3. レイヤー・データの追加

依存方向は既存の `collect → store ← deliver` を維持し、`video` は `mix` と同格の純変換レイヤーとする。

### 3.1 `video/render.py` (T38, FR-110/111/112)

- 入力: mp3 パス + ロゴ画像パス (任意)。出力: mp4 (H.264 yuv420p / AAC 192k / 48kHz / 1280x720 / 30fps)。
- ffmpeg 単発呼び出しで完結: ロゴがあれば `-loop 1` 静止画を背景に、無ければ `color=` 単色背景に縮退 (fail-open。ロゴ素材は人間ゲートのため素材無しでも経路を止めない)。`showwaves` を下部にオーバーレイ (FR-111)。
- `-shortest` で音声尺に合わせる。タイムアウト必須 (AGENTS §3.3 準拠、既定 900s)。
- 純ロジック (filter_complex 文字列と ffmpeg 引数の構築) は関数分離し ffmpeg 無しでテスト可能にする (T30 `mix/master.py` と同じ流儀)。

### 3.2 `deliver/youtube.py` (T39, FR-120/121/122)

- **新規依存ゼロ**: httpx で OAuth token refresh + resumable upload を直接実装 (ADR-0007)。
- 環境変数: `YOUTUBE_CLIENT_ID` / `YOUTUBE_CLIENT_SECRET` / `YOUTUBE_REFRESH_TOKEN` (.env、値は管理外)。
- `refresh_access_token()` → `upload_video()` (uploadType=resumable、privacyStatus 既定 unlisted、`selfDeclaredMadeForKids=false`、`containsSyntheticMedia=true` = プラットフォーム側の AI 開示)。
- 説明欄に `AI_DISCLOSURE` が無ければ**先頭に自動挿入** (FR-121 をコードで強制)。
- `get_privacy_status()` / `set_privacy_status()` (videos.list → status 差し替え → videos.update。update は指定外フィールドが消えるため list で現状を取得してから送る)。
- ログに URL・トークンを出さない (discord.py と同じ流儀: 型名 / status code のみ)。

### 3.3 `store` 追加 (T40)

```text
video_versions
  id INTEGER PK AUTOINCREMENT
  draft_id INTEGER FK episode_drafts.id NOT NULL
  audio_version_id INTEGER FK audio_versions.id NOT NULL
  created_at DATETIME NOT NULL
  path TEXT NOT NULL              -- mp4 ローカルパス (本体は git 管理外)
  youtube_video_id TEXT NULL      -- アップロード成功時のみ
  youtube_url TEXT NULL
  privacy_status TEXT NULL        -- unlisted / public / private
```

repo 関数: `insert_video_version` / `get_latest_audio_version` / `get_latest_uploaded_video` / `update_video_privacy`。

### 3.4 CLI (T40)

- `publish [--audio-id] [--logo assets/logo.png] [--out-dir data/videos] [--privacy unlisted] [--post] [--dry-run]`
  - 最新 (または指定) audio_version → mp4 生成 → YouTube unlisted アップロード → `video_versions` 記録 → `--post` で Discord に朝確認メッセージ (✅ `approve` / 🔁 `produce`+`publish` 再実行 / ❌ 何もしない=限定公開のまま)。
  - `--dry-run` は mp4 生成まで (アップロード・DB・Discord なし)。アップロード失敗は fail-fast (publish の目的そのものなので rc≠0)。Discord 通知失敗は fail-open。
- `approve [--video-id] [--post]`
  - 対象 video_version の YouTube 動画を public へ切り替え、DB を更新。`--post` で Discord に公開完了を通知。
- `youtube-auth [--client-id ...] [--port 8765] [--manual]`
  - 一度だけ人間が実行する OAuth 補助。loopback リダイレクトで code を受け、refresh token を表示 → 人間が .env に貼る。`--manual` はリダイレクト URL の手貼りフォールバック。

### 3.5 日次パイプライン (T41)

`scripts/daily_pipeline.sh` に `PUBLISH_YOUTUBE=1` のときのみ publish を実行するオプトインステップを追加 (既定 off。恒久運用の判断は人間ゲートのため)。失敗時は既存の Discord 失敗通知経路に載せ、rc を伝播する。

## 4. タスク分解 (T38〜)

| ID | 内容 | 依存 | 完了の定義 |
|---|---|---|---|
| T38 | `video/render.py` 波形動画生成 + テスト | — | filter/引数構築の純テスト + 実 ffmpeg で小さな mp3 → mp4 統合テスト (ffmpeg 不在は skip)。mp4 が非空で生成される |
| T39 | `deliver/youtube.py` OAuth + resumable upload + privacy 変更 + `youtube-auth` CLI + テスト | — | httpx モックで token refresh / upload / 開示文言強制 / privacy 変更 / エラー正規化が緑 |
| T40 | `video_versions` + repo + `publish` / `approve` CLI + Discord 朝確認 + テスト | T38, T39 | CLI 統合テスト (render/upload をモック) で DB 記録・dry-run・fail 経路が緑 |
| T41 | docs 同期 (.env.example / README / AGENTS / PROJECT_STATE / TEST_LOG / ADR INDEX) + daily_pipeline オプトイン | T40 | shellcheck / plutil 相当の静的チェック緑、ドキュメントドリフトなし |

## 5. テスト方針

- ffmpeg 依存: `tests/test_mix_master.py` と同じ skipif パターン。動画エンコードは 1〜2 秒のトーン mp3 で最小化。
- YouTube API: `httpx.MockTransport` 相当のモック (実 API は叩かない)。resumable の 2 段階 (initiate → PUT) を個別に検証。
- CLI: `typer.testing.CliRunner` + monkeypatch で `render_video` / `upload_video` を差し替え (既存 test_produce_pipeline.py の流儀)。

## 6. 人間判断待ち (ブロッカー粒度つき)

| 判断 | いつまでに | 準備済み材料 |
|---|---|---|
| GCP プロジェクト作成 + YouTube Data API v3 有効化 + OAuth クライアント (デスクトップ) 作成 | 実アップロード smoke 前 | 手順は README「YouTube 配信セットアップ」節 |
| YouTube チャンネル (名前・アカウント) | 実アップロード smoke 前 | 要件 §16 未確定事項 |
| 番組ロゴ画像 (`assets/logo.png`) | 任意 (無くても単色背景で配信可) | §3.1 の縮退仕様 |
| 限定公開 2 週間運用テスト開始の Go | 実 smoke 後 | roadmap 配信フェーズ 1 |

## 7. 着手手順 (ゲート)

1. T38 → T39 → T40 → T41 の順に同一ブランチ `agent/T38-sprint3-impl` で実装 (チケット単位コミット)。
2. 各チケットで pytest / ruff / mypy strict を fresh 実行。
3. 全体完了後に Codex 独立レビュー → 指摘反映 → PR (人間 merge)。

## 8. 絶対 NG (Sprint 3 固有)

- **実 YouTube アップロードを自動テストで叩かない** (クォータ 1600 units/upload、誤爆で本番チャンネルを汚す)。
- **公開 (public) を既定にしない**。既定は unlisted (FR-120)。public 化は人間の `approve` のみ。
- **AI 開示無しの説明欄でアップロードしない** (FR-121。コードで強制し、テストで担保)。
- **OAuth シークレット・トークンを ログ / リポジトリ / Discord に出さない** (要件 §9.5)。
- google-api-python-client 等の SDK 追加禁止 (ADR-0007。依存最小 §5)。
