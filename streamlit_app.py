import streamlit as st
from supabase import create_client, Client
import pandas as pd
import os
import random

# --- 1. Supabase の初期化 ---
# Streamlit の Secrets (URLとKey) を使用
# 注意: 事前に Streamlit Cloud または .streamlit/secrets.toml に登録が必要です
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 2. データ管理関数 ---

def initialize_data():
    """初期化：Supabaseの physics_words が空ならCSVからデータを投入する"""
    try:
        res = supabase.table("physics_words").select("id", count="exact").limit(1).execute()
        # 既にデータがある場合は何もしない
        if res.count == 0 and os.path.exists('physics_data.csv'):
            df_csv = pd.read_csv('physics_data.csv')
            data_to_insert = df_csv.to_dict(orient='records')
            supabase.table("physics_words").insert(data_to_insert).execute()
            st.toast("CSVデータをクラウド(Supabase)へ同期しました！")
    except Exception as e:
        st.error(f"初期化エラー: {e}")

def get_physics_data(mode='all'):
    """問題データを Supabase から取得する"""
    try:
        if mode == 'review':
            # 復習モード: recordsテーブルから不正解(is_correct=0)のword_idを重複なしで取得
            res_records = supabase.table("records").select("word_id").eq("is_correct", 0).execute()
            wrong_ids = list(set([item['word_id'] for item in res_records.data]))
            
            if not wrong_ids:
                return pd.DataFrame()
            
            # 不正解履歴があるIDの問題のみを取得
            res_words = supabase.table("physics_words").select("*").in_("id", wrong_ids).execute()
            return pd.DataFrame(res_words.data)
        else:
            # クイズモード: 全件取得
            res = supabase.table("physics_words").select("*").execute()
            return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        return pd.DataFrame()

# アプリ起動時にデータ移行チェック
initialize_data()

# --- 3. UI設定 ---
st.set_page_config(page_title="電磁気学マスター", layout="centered")
st.title("⚡️ 電磁気学 単語・公式マスター")

menu = st.sidebar.radio("メニュー", ["クイズに挑戦", "復習モード", "苦手リストと解説"])

# --- 4. クイズ・復習モードの処理 ---
if menu in ["クイズに挑戦", "復習モード"]:
    df = get_physics_data(mode='all' if menu == "クイズに挑戦" else 'review')
    
    if df.empty:
        if menu == "復習モード":
            st.info("現在、復習が必要な（間違えた）問題はありません！素晴らしい！")
        else:
            st.info("問題データが見つかりません。Supabaseの physics_words テーブルを確認してください。")
    else:
        # セッション内で現在の問題を保持
        if 'quiz' not in st.session_state:
            q = df.sample(n=1).iloc[0]
            
            # 選択肢用に全ての「意味」をリスト化
            all_means_res = supabase.table("physics_words").select("mean").execute()
            all_means = list(set([item['mean'] for item in all_means_res.data]))
            
            # 正解以外の選択肢をランダムに3つ選ぶ
            other_means = [m for m in all_means if m != q['mean']]
            distractors = random.sample(other_means, min(len(other_means), 3))
            options = distractors + [q['mean']]
            random.shuffle(options)
            
            st.session_state.quiz = {
                "id": q['id'],
                "word": q['word'],
                "ans": q['mean'],
                "exp": q['explanation'],
                "options": options
            }
            st.session_state.answered = False

        quiz = st.session_state.quiz
        st.subheader(f"Q: {quiz['word']}")

        # 選択肢ボタンの表示
        for opt in quiz['options']:
            if st.button(opt, use_container_width=True, disabled=st.session_state.answered, key=f"opt_{opt}"):
                st.session_state.answered = True
                is_correct = (opt == quiz['ans'])
                
                # --- 重要: 解答結果を Supabase に保存 ---
                try:
                    supabase.table("records").insert({
                        "word_id": int(quiz['id']),
                        "is_correct": 1 if is_correct else 0
                    }).execute()
                except Exception as e:
                    st.warning(f"記録の保存に失敗しました: {e}")
                
                st.session_state.feedback = is_correct
                st.rerun()

        # 回答後のフィードバック表示
        if st.session_state.answered:
            if st.session_state.feedback:
                st.success(f"⭕️ 正解！: {quiz['ans']}")
            else:
                st.error(f"❌ 不正解！ 正解は: {quiz['ans']}")
            
            st.info(f"**解説:**\n{quiz['exp']}")
            
            if st.button("次の問題へ ➡️"):
                del st.session_state.quiz
                st.rerun()

# --- 5. 苦手リストと解説モード ---
elif menu == "苦手リストと解説":
    st.subheader("📚 復習が必要な項目")
    st.write("過去に間違えた問題と、その頻度を表示します。")
    
    try:
        # 不正解データを取得
        res = supabase.table("records").select("word_id").eq("is_correct", 0).execute()
        
        if not res.data:
            st.success("苦手な項目はありません。この調子で頑張りましょう！")
        else:
            miss_df = pd.DataFrame(res.data)
            counts = miss_df['word_id'].value_counts()
            
            for w_id, count in counts.items():
                # 各単語の詳細を Supabase から取得
                word_res = supabase.table("physics_words").select("*").eq("id", int(w_id)).single().execute()
                word_info = word_res.data
                
                with st.expander(f"{word_info['word']} (ミス: {count}回)"):
                    # 数式を綺麗に表示するために st.latex を使用
                    # データに $ が含まれている場合は除去して渡す
                    formula = word_info['mean'].replace('$', '')
                    st.latex(formula)
                    st.write(f"**解説:** {word_info['explanation']}")
    except Exception as e:
        st.error(f"データの取得中にエラーが発生しました: {e}")
