import streamlit as st
from supabase import create_client, Client
import pandas as pd
import os
import random

# --- 1. Supabase の初期化 ---
# Streamlit の Secrets (URLとKey) を使用
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 2. データ管理関数 (すべて Supabase を使用) ---

def initialize_data():
    """アプリ起動時に一度だけ実行：Supabaseが空ならCSVからデータを投入する"""
    try:
        res = supabase.table("physics_words").select("id", count="exact").limit(1).execute()
        if res.count == 0 and os.path.exists('physics_data.csv'):
            df_csv = pd.read_csv('physics_data.csv')
            data_to_insert = df_csv.to_dict(orient='records')
            supabase.table("physics_words").insert(data_to_insert).execute()
            st.toast("CSVデータをクラウドへ移行しました！")
    except Exception as e:
        st.error(f"初期化エラー: {e}")

def get_physics_data(mode='all'):
    """問題データを Supabase から取得する"""
    try:
        if mode == 'review':
            # 復習モード: recordsテーブルから不正解(is_correct=0)のIDを取得
            res_records = supabase.table("records").select("word_id").eq("is_correct", 0).execute()
            wrong_ids = list(set([item['word_id'] for item in res_records.data]))
            
            if not wrong_ids:
                return pd.DataFrame()
            
            # 不正解だったIDの問題を physics_words から取得
            res_words = supabase.table("physics_words").select("*").in_("id", wrong_ids).execute()
            return pd.DataFrame(res_words.data)
        else:
            # 全件取得
            res = supabase.table("physics_words").select("*").execute()
            return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        return pd.DataFrame()

# 起動時に一度チェック
initialize_data()

# --- 3. UI設定 ---
st.set_page_config(page_title="電磁気学マスター", layout="centered")
st.title("⚡️ 電磁気学 単語・公式マスター")

menu = st.sidebar.radio("メニュー", ["クイズに挑戦", "復習モード", "苦手リストと解説"])

# --- 4. クイズ・復習モード ---
if menu in ["クイズに挑戦", "復習モード"]:
    df = get_physics_data(mode='all' if menu == "クイズに挑戦" else 'review')
    
    if df.empty:
        st.info("対象のデータがありません。")
    else:
        if 'quiz' not in st.session_state:
            q = df.sample(n=1).iloc[0]
            # 選択肢用に全データから意味を取得
            all_means_res = supabase.table("physics_words").select("mean").execute()
            all_means = list(set([item['mean'] for item in all_means_res.data]))
            
            other_means = [m for m in all_means if m != q['mean']]
            distractors = random.sample(other_means, min(len(other_means), 3))
            options = distractors + [q['mean']]
            random.shuffle(options)
            
            st.session_state.quiz = {
                "id": q['id'], "word": q['word'], "ans": q['mean'], 
                "exp": q['explanation'], "options": options
            }
            st.session_state.answered = False

        quiz = st.session_state.quiz
        st.subheader(f"Q: {quiz['word']}")

        for opt in quiz['options']:
            if st.button(opt, use_container_width=True, disabled=st.session_state.answered, key=f"opt_{opt}"):
                st.session_state.answered = True
                is_correct = (opt == quiz['ans'])
                
                # 正誤判定を Supabase の records テーブルに保存
                supabase.table("records").insert({
                    "word_id": int(quiz['id']),
                    "is_correct": 1 if is_correct else 0
                }).execute()
                
                st.session_state.feedback = is_correct
                st.rerun()

        if st.session_state.answered:
            if st.session_state.feedback:
                st.success(f"⭕️ 正解！: {quiz['ans']}")
            else:
                st.error(f"❌ 不正解！ 正解は: {quiz['ans']}")
            
            st.info(f"**解説:**\n{quiz['exp']}")
            
            if st.button("次の問題へ ➡️"):
                del st.session_state.quiz
                st.rerun()

# --- 5. 統計・解説モード ---
elif menu == "苦手リストと解説":
    st.subheader("📚 復習が必要な項目")
    
    try:
        res = supabase.table("records").select("word_id").eq("is_correct", 0).execute()
        if not res.data:
            st.write("まだ間違いはありません。")
        else:
            miss_df = pd.DataFrame(res.data)
            counts = miss_df['word_id'].value_counts()
            
            for w_id, count in counts.items():
                word_res = supabase.table("physics_words").select("*").eq("id", int(w_id)).single().execute()
                word_info = word_res.data
                with st.expander(f"{word_info['word']} (ミス: {count}回)"):
                # st.write(word_info['mean']) ではなく、st.latex() を使う
                st.latex(word_info['mean'])
                    
                    st.write(f"**解説:** {word_info['explanation']}")
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
