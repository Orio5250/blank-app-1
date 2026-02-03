import streamlit as st
from supabase import create_client, Client
import pandas as pd
import random

# --- 1. Supabase の設定 ---
# 実際のテーブル名に書き換えてください
TABLE_WORDS = "physics_words"      
TABLE_PROBLEMS = "electromagnetics" 
TABLE_RECORDS = "records"                    

url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 2. データ取得関数 ---
def get_data(mode, level_filter):
    table = TABLE_WORDS if mode == "単語クイズ" else TABLE_PROBLEMS
    try:
        query = supabase.table(table).select("*")
        if level_filter != "すべて":
            query = query.eq("level", level_filter)
        res = query.execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"取得エラー: {e}")
        return pd.DataFrame()

# --- 3. UI設定 ---
st.set_page_config(page_title="電磁気学マスター")
st.sidebar.header("メニュー")
study_mode = st.sidebar.selectbox("モード", ["単語クイズ", "例題クイズ"])
level_sel = st.sidebar.selectbox("レベル", ["すべて", "1", "2"])

st.title(f"⚡️ {study_mode}")

# --- 4. クイズ処理 ---
df = get_data(study_mode, level_sel)

if df.empty:
    st.warning(f"【{study_mode}】テーブルにデータが見つかりません。名前を確認してください。")
else:
    # 状態リセット
    if "current_mode" not in st.session_state or st.session_state.current_mode != study_mode:
        st.session_state.current_mode = study_mode
        if "quiz" in st.session_state: del st.session_state.quiz

    if "quiz" not in st.session_state:
        q = df.sample(n=1).iloc[0]
        
        # 選択肢は単語テーブルの 'mean' から作成
        all_res = supabase.table(TABLE_WORDS).select("mean").execute()
        all_means = list(set([item['mean'] for item in all_res.data]))
        other = [m for m in all_means if m != q['mean']]
        options = random.sample(other, min(len(other), 3)) + [q['mean']]
        random.shuffle(options)
        
        st.session_state.quiz = {
            "id": q.get('id'),
            "q_text": q['word'] if study_mode == "単語クイズ" else q['explanation'],
            "ans": q['mean'],
            "exp": q['explanation'],
            "options": options
        }
        st.session_state.answered = False

    quiz = st.session_state.quiz
    st.subheader("問題")
    if study_mode == "単語クイズ":
        st.title(f"「{quiz['q_text']}」の公式は？")
    else:
        st.info(quiz['q_text']) # 例題を表示

    # ボタン表示
    for opt in quiz['options']:
        if st.button(opt, use_container_width=True, disabled=st.session_state.answered, key=opt):
            st.session_state.answered = True
            st.session_state.is_correct = (opt == quiz['ans'])
            st.rerun()

    if st.session_state.answered:
        if st.session_state.is_correct:
            st.success("⭕️ 正解！")
        else:
            st.error(f"❌ 不正解... 正解は: {quiz['ans']}")
        
        st.latex(quiz['ans'].replace('$', ''))
        st.write(f"**解説:** {quiz['exp']}")
        
        if st.button("次の問題へ"):
            del st.session_state.quiz
            st.rerun()
