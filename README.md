# Multi-Agent AI Chat System

## 概要
このプロジェクトは、複数のAIエージェントを用いたチャットシステムです。各エージェントは異なる専門性と役割を持ち、協力して複雑な問題に取り組みます。

## 機能
- 複数のAIエージェントによる協調的な問題解決
- 動的なトピック管理とエージェントの優先順位付け
- ユーザー承認によるコマンド実行の制御
- 議論のサマリーと次の質問の自動生成

## 必要条件
- Python 3.11
    - OpenInterpreterの絡みでこれを推奨
- OpenAI API キー

## インストール
1. リポジトリをクローンします：
   ```
   git clone https://github.com/yourusername/multi-agent-ai-chat.git
   cd multi-agent-ai-chat
   ```

2. 必要なパッケージをインストールします：
   ```
   pip install -r requirements.txt
   ```

3. 'sample.env'から`.env`ファイルを作成し、OpenAI APIキーを設定します：
   ```
   OPENAI_API_KEY='your_api_key_here'
   ```

## 使用方法
1. `config.json`ファイルでエージェントの設定を行います。

2. プログラムを実行します：
   ```
   python multi_agent.py
   ```

3. プロンプトに従って質問を入力し、AIエージェントとの対話を開始します。

## 設定
`config.json`ファイルで以下の設定が可能です：
- エージェントの名前、性格、専門分野、役割
- 使用するAIモデル
- 最大イテレーション数
- デバッグモードの有効/無効
- ログレベルとログファイル

## ライセンス
このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 謝辞
このプロジェクトは[OpenInterpreter](https://github.com/KillianLucas/open-interpreter)を使用しています。OpenInterpreterはMITライセンスの下で公開されています。

## 貢献
バグ報告や機能リクエストは、GitHubのIssuesページでお願いします。

## 注意事項
- このシステムはOpenAI APIを使用しています。APIの使用には料金が発生する可能性があります。
- 複数のエージェントを利用しますので使用料金は結構発生するかもしれません。
- 生成されたコンテンツの正確性や適切性については、ユーザーの責任で確認してください。
- このバージョンは作ったばかりで抜けも多いです。利用は注意してください。
