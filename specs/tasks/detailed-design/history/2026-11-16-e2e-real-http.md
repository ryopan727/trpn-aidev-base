# E2EをCompose上のAPIへの実HTTP通信に変更

| 項目 | 内容 |
| --- | --- |
| 日付 | 2026-11-16 |
| サブドメイン | tasks（初回実装として共通テスト方針にも反映） |

## 1. 変更内容

- 変更前：TestClientがプロセス内のFastAPIを呼び出し、実PostgreSQLまで検証していた。
- 変更後：Composeのapi-testを起動し、別のtestコンテナからHTTPXで実HTTP通信する。Uvicorn・FastAPI・4層・db-test・HTTP応答を通し、DBの保存結果も別接続で確認する。
- E2Eを `tests/e2e/` に配置し、TaskがDB準備・Flyway適用・APIの起動待機・テスト・API停止を管理する。

## 2. 変更理由

ユーザーが、実際にDocker Composeで起動したAPIへHTTP通信し、DBまで含めるE2Eを指定した。これによりAPIサーバーの起動とコンテナ間の通信も検証対象に含める。

## 3. 影響範囲

| 対象 | 対応 |
| --- | --- |
| E2Eの受入検証 | TASK-AC-001〜007に関係する主要シナリオを実HTTPに変更。通常の再起動後の永続化TASK-AC-009は別途検証を維持。 |
| Compose・Task・fixture | api-testを追加し、テスト専用DBへ接続。テストの成功・失敗後に専用APIを停止する。開発用サービスは操作しない。 |
| 共通方針・テンプレート | テスト範囲・サービス・配置の記載を更新し、今後の領域設計でも同じ境界を使う。 |

## 4. 関連資料

- [テスト設計](../testing.md)、[実行手順](../operations.md)、[環境構成](../infrastructure.md)
- [共通のテスト方針](../../../../steering/api/testing.md)、[Compose方針](../../../../steering/api/docker-compose.md)
- [PR #1](https://github.com/ryopan727/trpn-aidev-base/pull/1)
