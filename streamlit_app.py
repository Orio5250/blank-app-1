import streamlit as st
from supabase import create_client, Client
import pandas as pd
import random

# --- 1. Supabase の初期化 ---
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# 【重要】あなたの実際のテーブル名に書き換えてください
TABLE_WORDS = "physics_words"  # 単語用テーブル名
TABLE_PROBLEMS = "electromagnetics"      # 画像で確認した例題用テーブル名

# --- 2. データ取得関数 ---
def get_physics_data(mode, level_filter="すべて"):
    try:
        # モードによってテーブルを切り替える
        target_table = TABLE_WORDS if mode == "単語クイズ" else TABLE_PROBLEMS
        
        query = supabase.table(target_table).select("*")
        
        res = query.execute()
        df = pd.DataFrame(res.data)
        
        if df.empty:
            return df

        # レベルによるフィルタリング（文字列として安全に比較）
        if level_filter != "すべて":
            df = df[df['level'].astype(str) == str(level_filter)]
            
        return df
    except Exception as e:
        st.error(f"データ取得エラー ({mode}): {e}")
        return pd.DataFrame()

# --- 3. UI設定 ---
st.set_page_config(page_title="電磁気マスター", layout="centered")
st.sidebar.header("⚙️ 学習設定")
study_mode = st.sidebar.selectbox("クイズモード", ["単語クイズ", "例題クイズ"])
level_selection = st.sidebar.selectbox("難易度を選択", ["すべて", "1", "2"])

st.title(f"⚡️ {study_mode}")

# --- 4. クイズロジック ---
df = get_physics_data(study_mode, level_selection)

if df.empty:
    st.warning(f"該当するデータがありません。（テーブル: {TABLE_WORDS if study_mode == '単語クイズ' else TABLE_PROBLEMS}）")
else:
    # モードが変わったらリセット
    if 'last_mode' in st.session_state and st.session_state.last_mode != study_mode:
        if 'quiz' in st.session_state: del st.session_state.quiz
    st.session_state.last_mode = study_mode

    if 'quiz' not in st.session_state:
        q = df.sample(n=1).iloc[0]
        
        # 選択肢は常に「単語テーブル」の mean（正解候補）から取得
        words_res = supabase.table(TABLE_WORDS).select("mean").execute()
        all_means = list(set([item['mean'] for item in words_res.data]))
        
        other_means = [m for m in all_means if m != q['mean']]
        distractors = random.sample(other_means, min(len(other_means), 3))
        
        options = distractors + [q['mean']]
        random.shuffle(options)
        
        st.session_state.quiz = {
            "id": q['id'],
            "q_text": q['word'], # 例題モードではここに「例題：...」が入る
            "ans": q['mean'],
            "exp": q['explanation'],
            "options": options
        }
        st.session_state.answered = False

    quiz = st.session_state.quiz

    # 問題の表示
    if study_mode == "単語クイズ":
        st.subheader("この用語の『公式・意味』を選べ")
        st.title(f"**{quiz['q_text']}**")
    else:
        st.subheader("この例題に『最も適した解答』を選べ")
        st.info(quiz['q_text']) # 文章を表示

    # 回答ボタン
    for opt in quiz['options']:
        if st.button(opt, use_container_width=True, disabled=st.session_state.answered, key=opt):
            st.session_state.answered = True
            st.session_state.is_correct = (opt == quiz['ans'])
            st.rerun()

    # フィードバック
    if st.session_state.answered:
        if st.session_state.is_correct:
            st.success("⭕️ 正解です！")
        else:
            st.error(f"❌ 不正解... 正解は: {quiz['ans']}")
        
        st.markdown("#### ✅ 解説・公式")
        # 数式の表示
        if "$" in str(quiz['exp']):
            st.latex(quiz['exp'].replace('$', ''))
        else:
            st.write(quiz['exp'])

        if st.button("次の問題へ ➡️"):
            del st.session_state.quiz
            st.rerun()
