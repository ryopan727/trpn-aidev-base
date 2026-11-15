# trpn-aidev-base

GPTを使い始めた初学者が、AIと相談しながら開発を進めるためのAI駆動開発キットです。
Python・FastAPIでREST APIを作り、Docker Composeで開発環境を起動する方針です。

## フォルダ構成

```text
.
├── README.md
├── AGENTS.md          # AIへの指示と開発モードの指定方法
├── steering/          # プロジェクト全体の方針・取り決め
│   ├── aidd/          # AI駆動開発の進め方
│   ├── api/           # APIの技術スタック・設計方針
│   └── templates/     # 取り決めを記載するためのテンプレート
├── specs/             # サブドメインごとの要求仕様・設計
│   └── templates/     # 仕様を記載するためのテンプレート
└── apps/              # アプリケーションの実装
    └── backend/       # Python・FastAPIによるREST API
```

`steering` に共通のルール、`specs` にサブドメインごとの仕様・設計、`apps` にコードを置きます。
AIへの作業指示と2つの開発モードの指定方法は [AGENTS.md](AGENTS.md) にまとめています。
まずはこの構成を土台に、必要な取り決めを一つずつ追加します。
[AI駆動開発の進め方](steering/aidd/README.md)、[APIの技術方針](steering/api/README.md)、[仕様・設計の成果物とテンプレート](specs/README.md)を整備しています。具体的なサブドメインの仕様・実装は、必要になった時点で追加します。空フォルダはGitには保存されません。
