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

# サイドバーでの設定
st.sidebar.header("⚙️ 学習設定")
study_mode = st.sidebar.selectbox("クイズモードを選択", ["単語クイズ", "例題クイズ"])

level_display = { "すべて": "すべて", 1: "1: 基礎", 2: "2: 応用" }
level_selection = st.sidebar.selectbox(
    "難易度を選択", 
    options=["すべて", 1, 2], 
    format_func=lambda x: level_display[x]
)

# クイズ開始フラグの管理
if 'started' not in st.session_state:
    st.session_state.started = False

# --- 4. メイン画面の表示切り替え ---
if not st.session_state.started:
    # --- スタート画面 ---
    st.title("⚡️ 電磁気学クイズ")
    st.write(f"現在の設定:")
    st.write(f"- モード: **{study_mode}**")
    st.write(f"- 難易度: **{level_display[level_selection]}**")
    
    if st.button("クイズを開始する 🚀", use_container_width=True):
        st.session_state.started = True
        st.rerun()

else:
    # --- クイズ本編 ---
    st.title(f"⚡️ {study_mode}")
    
    # 戻るボタン（設定を変えたい時用）
    if st.sidebar.button("⚙️ 設定画面に戻る"):
        st.session_state.started = False
        if 'quiz' in st.session_state: del st.session_state.quiz
        st.rerun()

    df = get_physics_data(study_mode, level_selection)

    if df.empty:
        st.warning("条件に合うデータがありません。設定を変更してください。")
    else:
        # クイズの生成
        if 'quiz' not in st.session_state:
            q = df.sample(n=1).iloc[0]
            
            # 選択肢の元ネタをモードで分ける
            target_choice_table = TABLE_WORDS if study_mode == "単語クイズ" else TABLE_PROBLEMS
            choice_res = supabase.table(target_choice_table).select("mean").execute()
            
            all_means = list(set([item['mean'] for item in choice_res.data if item['mean']]))
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

        # 問題の表示
        if study_mode == "単語クイズ":
            st.subheader("この用語の公式・意味は？")
            st.title(f"**{quiz['q_text']}**")
        else:
            st.subheader("例題の解答として正しいものは？")
            st.info(quiz['q_text'])

        st.write("---")

        # 回答ボタン
        for opt in quiz['options']:
            if st.button(opt, use_container_width=True, disabled=st.session_state.answered, key=f"btn_{opt}"):
                st.session_state.answered = True
                st.session_state.is_correct = (opt == quiz['ans'])
                st.rerun()

        # 正誤判定
        if st.session_state.answered:
            if st.session_state.is_correct:
                st.success("⭕️ 正解！")
            else:
                st.error(f"❌ 不正解... 正解は: {quiz['ans']}")
            
            st.markdown("#### ✅ 解説")
            st.latex(str(quiz['exp']).replace('$', ''))

            if st.button("次の問題へ ➡️"):
                del st.session_state.quiz
                st.rerun()
