# ⚡️ 電磁気学マスター

電磁気学の公式、単位、法則を効率よく暗記するための、一問一答形式のクイズアプリです。

[https://blank-app-z5h8gss6zh9.streamlit.app/]


## 🚀 主な機能
- **レベル別出題**: 基礎からマクスウェル方程式などの発展内容まで選択可能。
- **解答履歴の永続化**: Supabase（データベース）を使用し、苦手な問題を自動記録。
- **苦手リスト**: 過去に間違えた問題だけを抽出して復習可能。


## 🛠 使用技術
- **Frontend**: [Streamlit](https://streamlit.io/)
- **Backend/DB**: [Supabase](https://supabase.com/)
- **Language**: Python 3.x

## 💡 開発のポイント
- GitHub上にあったCSVデータを初期起動時に自動でSupabaseへ移行する機能を実装しました。
- `st.latex()` を活用し、物理学において重要な数式の視認性を高めています。

## ⚙️ セットアップ方法
ローカルで実行する場合：
1. リポジトリをクローン
2. `pip install -r requirements.txt`
3. `.streamlit/secrets.toml` にSupabaseのAPI情報を設定
4. `streamlit run main.py`

## ⚡ 今後の改良案
- アプリ上から覚えたい公式などを入力できる機能の実装
- より具体的な応用問題の追加
