# ADR-0004: RSSHub をセルフホストする

- 日付: 2026-05-28
- ステータス: Accepted
- 関連: [requirements-v1.0.md](../requirements-v1.0.md) §10, DL-005, [source-selection-spike-v0.1.md](../source-selection-spike-v0.1.md) §2

## 背景

掘金 (juejin)、bilibili、知乎、微博、小红书など中華圏ソースの一部は公式 RSS を提供しておらず、RSSHub が事実上の RSS 入口となる。RSSHub は公開インスタンス (rsshub.app など) もあるが、レート制限・突然のルート停止・Cookie 管理が外部任せになる。

## 決定

**Docker Compose で RSSHub をローカルに常駐させる。** Sprint 1A の sources.yaml では `http://localhost:1200/...` を指す。

## 根拠

- Cookie が必要なルート (将来) を環境変数で安全に管理できる。
- ルート障害・バージョン差異の調査・パッチ適用がローカルで完結する。
- レート制限を自前運用の範囲でコントロールでき、複数ソースの一括取得で外部公開インスタンスに迷惑をかけない。
- Spike §2 で「RSSHub の掘金カテゴリルートは公式ドキュメントで `/juejin/category/:category` が確認できる」ため、ローカル接続の妥当性が裏取りできている。

## 影響

- `docker-compose.yml` (RSSHub サービス: image=`diygod/rsshub`, port `1200:1200`, env でキャッシュ TTL 等を設定) を Sprint 1A T2 で導入。
- 開発マシン (Windows 11 + Docker Desktop) で起動できることを確認するのが T2 の DoD。
- 本番運用 (Sprint 3 以降) では Linux ホスト常駐を再評価。
- RSSHub のルートが将来壊れた場合、`source_health` が `consecutive_failures >= 3` で Discord 警告を出すので、fail-open を維持しつつ気づけるはず。

## 不採用案

- **公開インスタンス利用**: Cookie 不可、突然の停止、レート制限が外部要因 → 個人運用の安定性に致命的。
- **RSSHub 不使用 (掘金等を諦める)**: 中華圏コミュニティソースが Tier3 として失われ、番組の独自性が弱まる。
