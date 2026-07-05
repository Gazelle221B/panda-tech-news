# ADR-0007: YouTube 配信は httpx 直叩き + CLI 承認フローとし、SDK と Discord Bot を導入しない

- 日付: 2026-07-06
- ステータス: Accepted (Sprint 3 実装)
- 関連: [requirements-v1.0.md](../requirements-v1.0.md) §8.13 FR-120〜122 / §15.4、[IMPLEMENTATION_PLAN-3.md](../IMPLEMENTATION_PLAN-3.md)、[ADR-0003](./ADR-0003-discord-webhook-first.md)

## 背景

Sprint 3 は「波形動画 mp4 を YouTube に限定公開でアップロードし、朝確認フローで人間が公開判断する」まで (v0.5)。実現手段として次の 2 つの選択があった。

1. **YouTube API クライアント**: 公式 SDK (`google-api-python-client` + `google-auth-oauthlib`) か、httpx での直接実装か。
2. **朝確認フロー**: Discord Bot でリアクション (✅/🔁/❌) を拾って自動公開するか、CLI 承認に留めるか。

## 決定

1. **httpx で YouTube Data API v3 を直接叩く**。OAuth は refresh token 方式 (`YOUTUBE_CLIENT_ID` / `YOUTUBE_CLIENT_SECRET` / `YOUTUBE_REFRESH_TOKEN` を .env に置き、access token は都度 refresh)。初回の refresh token 取得は `karyu youtube-auth` (loopback リダイレクト) を人間が一度だけ実行する。
2. **朝確認フローは CLI 承認**とする。`publish` が unlisted でアップロードし Discord に確認メッセージを投稿 → 人間が視聴し、✅ なら `karyu approve` で public 化、🔁 なら再生成、❌ なら放置 (unlisted のまま)。Discord Bot は導入しない。

## 根拠

### httpx 直叩き (SDK 不採用)

- **依存最小 (AGENTS §5 / DESIGN §1)**: 公式 SDK は google-api-python-client + google-auth + google-auth-oauthlib + protobuf 系で推移依存が大きい。本プロジェクトが使う API は実質 3 エンドポイント (token refresh / videos.insert resumable / videos.list+update) のみで、httpx (既存コア依存) で ~200 行に収まる。
- **失敗の追跡可能性 (要件 §9.2)**: HTTP レベルで何が起きたか直接見える。SDK の内部リトライ・キャッシュ層を挟まない。
- discovery ドキュメント取得 (SDK の実行時依存) が無く、オフラインでもテスト可能。

### CLI 承認 (Bot 不採用)

- **Webhook 起点の原則 (ADR-0003)**: 受信 (リアクション読み取り) には Bot トークン・Gateway 常駐・イベントループが要り、常駐プロセスの運用負担が発生する。個人運用 (要件 §9.2) では割に合わない。
- 公開はどのみち**人間の判断そのもの** (roadmap 配信フェーズ 1: 限定公開 2 週間で運用を詰める)。1 日 1 回 `karyu approve` を打つコストは朝確認 5 分以内の目標を破らない。
- 要件 §15.4 も「必要ならDiscord Bot化」であり必須ではない。承認頻度が上がって CLI が苦になった時点で Bot 化を再検討する (その際は本 ADR を改訂)。

## 影響

- `.env` に YouTube OAuth の 3 変数が増える (値は管理外、`.env.example` に名前のみ)。
- `videos.update` は part 指定フィールドの全置換のため、privacy 変更は videos.list で現 status を取得してから差し替えて送る (実装規約として `deliver/youtube.py` に固定)。
- アップロードは 1 本 1600 quota units (既定 10,000 units/日)。日次 1 本 + 再生成数回でも余裕があるが、**自動テストから実 API を叩くことを禁止**する (IMPLEMENTATION_PLAN-3 §8)。
- AI 開示 (FR-121) は説明欄文言 + `status.containsSyntheticMedia=true` の二重で行う。
