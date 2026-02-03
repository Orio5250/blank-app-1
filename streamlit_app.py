import streamlit as st
from supabase import create_client, Client
import pandas as pd
import random

# --- 1. Supabase の初期化 ---
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

TABLE_WORDS = "physics_words" 
TABLE_PROBLEMS = "electromagnetics" 

# --- 2. データ取得関数 ---
def get_physics_data(mode, level_filter="すべて"):
    try:
        target_table = TABLE_WORDS if mode == "単語クイズ" else TABLE_PROBLEMS
        res = supabase.table(target_table).select("*").execute()
        df = pd.DataFrame(res.data)
        if df.empty:
            return df
        if level_filter != "すべて":
            df['level'] = pd.to_numeric(df['level'], errors='coerce')
            df = df[df['level'] == int(level_filter)]
        return df
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        return pd.DataFrame()

# --- 3. UI設定 ---
st.set_page_config(page_title="電磁気マスター", layout="centered")
study_mode = st.sidebar.selectbox("クイズモード", ["単語クイズ", "例題クイズ"])
level_selection = st.sidebar.selectbox("難易度を選択", ["すべて", 1, 2], "1: 基礎", "2: 応用")

st.title(f"⚡️ {study_mode}")

# --- 4. クイズロジック ---
df = get_physics_data(study_mode, level_selection)

if df.empty:
    st.warning("データが見つかりません。")
else:
    if 'last_mode' in st.session_state and st.session_state.last_mode != study_mode:
        if 'quiz' in st.session_state: del st.session_state.quiz
    st.session_state.last_mode = study_mode

    if 'quiz' not in st.session_state:
        q = df.sample(n=1).iloc[0]
        
        # --- 【ここがポイント！】モードに応じて選択肢の「元ネタ」を変える ---
        if study_mode == "単語クイズ":
            # 単語テーブルの mean 列から選択肢を作る
            choice_res = supabase.table(TABLE_WORDS).select("mean").execute()
        else:
            # 例題テーブルの mean 列から選択肢を作る
            choice_res = supabase.table(TABLE_PROBLEMS).select("mean").execute()
        
        all_means = list(set([item['mean'] for item in choice_res.data if item['mean']]))
        
        # 正解を除いたリストからダミーを3つ選ぶ
        other_means = [m for m in all_means if m != q['mean']]
        distractors = random.sample(other_means, min(len(other_means), 3))
        
        options = distractors + [q['mean']]
        random.shuffle(options)
        
        st.session_state.quiz = {
            "q_text": q.get('word', ''),
            "ans": q.get('mean', ''),
            "exp": q.get('explanation', q.get('explanatio', '解説なし')),
            "options": options
        }
        st.session_state.answered = False

    quiz = st.session_state.quiz

    if study_mode == "単語クイズ":
        st.subheader("この用語の公式・意味は？")
        st.title(f"**{quiz['q_text']}**")
    else:
        st.subheader("例題の解答として正しいものは？")
        st.info(quiz['q_text'])

    for opt in quiz['options']:
        if st.button(opt, use_container_width=True, disabled=st.session_state.answered, key=f"btn_{opt}"):
            st.session_state.answered = True
            st.session_state.is_correct = (opt == quiz['ans'])
            st.rerun()

    if st.session_state.answered:
        if st.session_state.is_correct:
            st.success("⭕️ 正解！")
        else:
            st.error(f"❌ 不正解... 正解は: {quiz['ans']}")
        
        st.markdown("#### ✅ 解説")
        st.latex(str(quiz['exp']).replace('$', ''))

        if st.button("次の問題へ"):
            del st.session_state.quiz
            st.rerun()
