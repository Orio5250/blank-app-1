import streamlit as st
from supabase import create_client, Client
import pandas as pd
import random

# --- 2. データ取得関数 ---
def get_physics_data(level_filter=None):
    try:
        query = supabase.table("electromagnetics").select("*")
        if level_filter and level_filter != "すべて":
            query = query.eq("level", int(level_filter))
        res = query.execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        return pd.DataFrame()

# --- 3. UI設定 ---
st.set_page_config(page_title="電磁気学マスター", layout="centered")

# サイドバーでモード切り替え
st.sidebar.header("学習設定")
study_mode = st.sidebar.selectbox("クイズモード", ["単語クイズ", "例題クイズ"])
level_selection = st.sidebar.selectbox("難易度を選択", ["すべて", "1", "2"])

st.title(f"⚡️ {study_mode}")

# --- 4. クイズロジック ---
df = get_physics_data(level_filter=level_selection)

if df.empty:
    st.info("データがありません。")
else:
    # モードやレベルが変わったらリセット
    state_keys = ['quiz', 'answered', 'last_mode', 'last_level']
    if 'last_mode' in st.session_state and (st.session_state.last_mode != study_mode or st.session_state.last_level != level_selection):
        if 'quiz' in st.session_state: del st.session_state.quiz
    
    st.session_state.last_mode = study_mode
    st.session_state.last_level = level_selection

    if 'quiz' not in st.session_state:
        q = df.sample(n=1).iloc[0]
        all_means = list(set(df['mean'].tolist()))
        other_means = [m for m in all_means if m != q['mean']]
        distractors = random.sample(other_means, min(len(other_means), 3))
        options = distractors + [q['mean']]
        random.shuffle(options)
        
        st.session_state.quiz = {
            "id": q['id'], "word": q['word'], "ans": q['mean'], 
            "exp": q['explanation'], "options": options, "level": q['level']
        }
        st.session_state.answered = False

    quiz = st.session_state.quiz

    # --- モードに応じた問題文の表示 ---
    if study_mode == "単語クイズ":
        st.subheader("この用語の定義・公式を選べ")
        st.title(f"🔍 {quiz['word']}")
    else:
        st.subheader("この例題に合う公式を選べ")
        st.info(f"💡 {quiz['exp']}") # explanationを問題文として提示

    # 回答ボタン
    for opt in quiz['options']:
        if st.button(opt, use_container_width=True, disabled=st.session_state.answered, key=f"btn_{opt}"):
            st.session_state.answered = True
            st.session_state.is_correct = (opt == quiz['ans'])
            # 記録保存 (略)
            st.rerun()

    # フィードバック
    if st.session_state.answered:
        if st.session_state.is_correct:
            st.success("⭕️ 正解！")
        else:
            st.error(f"❌ 不正解！ 正解は: {quiz['ans']}")
        
        st.markdown("### 解説")
        if study_mode == "単語クイズ":
            st.write(f"**解説:** {quiz['exp']}")
        else:
            st.write(f"**単語:** {quiz['word']}")
        
        if st.button("次の問題へ ➡️"):
            del st.session_state.quiz
            st.rerun()
