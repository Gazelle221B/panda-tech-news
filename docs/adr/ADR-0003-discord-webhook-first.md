# ADR-0003: Discord は Webhook から開始し、Bot は将来検討

- 日付: 2026-05-28
- ステータス: Accepted
- 関連: [requirements-v1.0.md](../requirements-v1.0.md) §8.8, DL-004, §2.4

## 背景

Sprint 1A の出力先は Discord 1 チャンネル。Sprint 1B 以降は ✅/🔁/❌ のリアクション承認で YouTube 自動アップロード制御を入れたい意図がある。

実装手段の選択肢:

- **Webhook**: 一方向 POST のみ。常駐不要、認証は URL に内包、添付25MB制限。
- **Bot 常駐**: Gateway 接続、リアクション監視、双方向通信、認証は Token、添付制限は同じ。

## 決定

**Sprint 1A は Webhook のみ。Bot 常駐は Sprint 2 以降で必要性が確認できたら検討。**

## 根拠

- Sprint 1A はサマリー投稿の片方向通信しかなく、Bot 常駐の双方向性を使う場面が無い。
- Bot 常駐は再起動復帰、権限管理、Gateway 切断時のリトライ、ホスティング (24/7) などの運用負荷を伴う。要件 §9.2 持続可能性を直撃する。
- リアクション承認フローは要件 §2.4 で **初期スコープ外** 明示。Sprint 2 以降の話。
- Webhook URL は秘密扱いで `.env` 管理し、`.env.example` のみ commit する (DESIGN.md §6, §7)。
- 25MB 制限は Sprint 1A では問題にならない (テキストのみ)。mp3/mp4 を扱う Sprint 2 で R2/S3 リンク投稿への切替を ADR で再判定。

## 影響

- `src/karyu_tech_news/deliver/discord.py` は httpx で POST する純粋関数として実装。Bot SDK (discord.py) は Sprint 1A では依存に加えない。
- 投稿失敗は ERROR ログのみで run を fail させない (FR-071)。

## 不採用案の代替検討

- Bot 常駐前倒し: ✅ リアクション承認を 1A から入れたい誘惑があるが、要件 §2.4 で意図的にスコープ外にされており、これを破ると Sprint 1A の本質 (収集基盤の安定性検証) がブレる。
