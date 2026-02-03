import streamlit as st
from supabase import create_client, Client
import pandas as pd
import random

# --- 1. Supabase の初期化 ---
# streamlitのSecrets (SUPABASE_URL, SUPABASE_KEY) を使用
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 2. テーブル名の設定 (ここを実際のテーブル名に変更してください) ---
TABLE_WORDS = "physics_words"      # 単語・公式用
TABLE_PROBLEMS = "electromagnetics"  # 例題用
TABLE_RECORDS = "records"                    # 学習記録用

# --- 3. データ取得関数 ---
def get_physics_data(mode, level_filter="すべて"):
    """モードに応じて参照するテーブルを切り替えてデータを取得"""
    try:
        # モードによってテーブルを選択
        target_table = TABLE_WORDS if mode == "単語クイズ" else TABLE_PROBLEMS
        
        query = supabase.table(target_table).select("*")
        
        # レベル絞り込み (数値と文字列の不一致を防ぐため str で比較)
        if level_filter != "すべて":
            query = query.eq("level", str(level_filter))
            
        res = query.execute()
        
        if not res.data:
            return pd.DataFrame()
        return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"データ取得エラー ({mode}): {e}")
        return pd.DataFrame()

# --- 4. UI・設定 ---
st.set_page_config(page_title="電磁気マスター", layout="centered")

st.sidebar.header("⚙️ 学習設定")
study_mode = st.sidebar.selectbox("クイズモード", ["単語クイズ", "例題クイズ"])
level_selection = st.sidebar.selectbox("難易度を選択", ["すべて", "1", "2"])

st.title(f"⚡️ {study_mode}")

# --- 5. クイズロジック ---
df = get_physics_data(study_mode, level_selection)

if df.empty:
    st.warning(f"現在、選択したモード（{study_mode}）とレベル（{level_selection}）に該当するデータがありません。")
    st.info("💡 Supabaseのテーブルにデータが入っているか、または『すべて』を選択して確認してください。")
else:
    # モードやレベルが変わったらセッションをリセット
    if 'last_mode' in st.session_state and (st.session_state.last_mode != study_mode or st.session_state.last_level != level_selection):
        if 'quiz' in st.session_state: del st.session_state.quiz
    
    st.session_state.last_mode = study_mode
    st.session_state.last_level = level_selection

    # 新しい問題を作成
    if 'quiz' not in st.session_state:
        q = df.sample(n=1).iloc[0]
        
        # 選択肢用のデータを取得（常に単語テーブルの 'mean' から取得）
        all_words_res = supabase.table(TABLE_WORDS).select("mean").execute()
        all_means = list(set([item['mean'] for item in all_words_res.data]))
        
        # 正解以外のダミーを作成
        other_means = [m for m in all_means if m != q['mean']]
        distractors = random.sample(other_means, min(len(other_means), 3))
        
        options = distractors + [q['mean']]
        random.shuffle(options)
        
        # セッションに保存
        st.session_state.quiz = {
            "id": q['id'],
            "target_word": q['word'] if 'word' in q else "この問題の公式",
            "ans": q['mean'],
            "display_text": q['word'] if study_mode == "単語クイズ" else q['explanation'],
            "explanation": q['explanation'],
            "options": options
        }
        st.session_state.answered = False

    quiz = st.session_state.quiz

    # 問題の表示
    if study_mode == "単語クイズ":
        st.subheader("この用語の『公式・意味』を選べ")
        st.title(f"**{quiz['display_text']}**")
    else:
        st.subheader("この例題に『最も適した公式』を選べ")
        st.info(quiz['display_text']) # 例題文を表示

    st.write("---")

    # 回答ボタンの生成
    for opt in quiz['options']:
        # LaTeXが含まれる場合はプレーンテキストとして表示しつつ、ボタンにする
        if st.button(opt, use_container_width=True, disabled=st.session_state.answered, key=f"btn_{opt}"):
            st.session_state.answered = True
            st.session_state.is_correct = (opt == quiz['ans'])
            
            # 学習記録を保存
            try:
                supabase.table(TABLE_RECORDS).insert({
                    "word_id": int(quiz['id']),
                    "is_correct": 1 if st.session_state.is_correct else 0
                }).execute()
            except:
                pass # 記録用テーブルがない場合はスキップ
            st.rerun()

    # 回答後の処理
    if st.session_state.answered:
        if st.session_state.is_correct:
            st.success("⭕️ 正解です！")
        else:
            st.error(f"❌ 不正解... 正解は: {quiz['ans']}")
        
        # 物理公式を大きく綺麗に表示
        st.markdown("#### ✅ 正解の公式")
        if "$" in str(quiz['ans']):
            st.latex(quiz['ans'].replace('$', ''))
        else:
            st.code(quiz['ans'])

        st.markdown("#### 📖 解説")
        st.write(quiz['explanation'])

        if st.button("次の問題へ ➡️"):
            del st.session_state.quiz
            st.rerun()
