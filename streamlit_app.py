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

# --- 2. データ保持の初期化 ---
if 'started' not in st.session_state:
    st.session_state.started = False
if 'wrong_list' not in st.session_state:
    st.session_state.wrong_list = [] # 間違えた問題を保存するリスト

# --- 3. UI設定 ---
st.set_page_config(page_title="電磁気マスター", layout="centered")

st.sidebar.header("⚙️ 学習設定")
# モードに「復習モード」を追加
mode_options = ["単語クイズ", "例題クイズ"]
if st.session_state.wrong_list:
    mode_options.append("🔥 復習モード")

study_mode = st.sidebar.selectbox("クイズモードを選択", mode_options)

level_display = { "すべて": "すべて", 1: "1: 基礎", 2: "2: 応用" }
level_selection = st.sidebar.selectbox(
    "難易度を選択", 
    options=["すべて", 1, 2], 
    format_func=lambda x: level_display[x]
)

# --- 4. 画面切り替え ---
if not st.session_state.started:
    st.title("⚡️ 電磁気学クイズ")
    if study_mode == "🔥 復習モード":
        st.warning(f"現在、復習リストには {len(st.session_state.wrong_list)} 問あります。")
    
    if st.button("クイズを開始する 🚀", use_container_width=True):
        st.session_state.started = True
        st.rerun()

else:
    st.title(f"⚡️ {study_mode}")
    
    if st.sidebar.button("⚙️ 設定画面に戻る"):
        st.session_state.started = False
        if 'quiz' in st.session_state: del st.session_state.quiz
        st.rerun()

    # --- データ取得ロジック ---
    if study_mode == "🔥 復習モード":
        # 復習モードなら、間違えたリストからデータフレーム作成
        df = pd.DataFrame(st.session_state.wrong_list)
    else:
        # 通常モードならSupabaseから取得
        try:
            target_table = TABLE_WORDS if study_mode == "単語クイズ" else TABLE_PROBLEMS
            res = supabase.table(target_table).select("*").execute()
            df = pd.DataFrame(res.data)
            if level_selection != "すべて":
                df['level'] = pd.to_numeric(df['level'], errors='coerce')
                df = df[df['level'] == int(level_selection)]
        except Exception as e:
            st.error(f"エラー: {e}")
            df = pd.DataFrame()

    if df.empty:
        st.warning("対象の問題がありません。")
        if st.button("戻る"):
            st.session_state.started = False
            st.rerun()
    else:
        # クイズ生成
        if 'quiz' not in st.session_state:
            q = df.sample(n=1).iloc[0]
            
            # 選択肢の生成
            target_choice_table = TABLE_WORDS if study_mode != "例題クイズ" else TABLE_PROBLEMS
            choice_res = supabase.table(target_choice_table).select("mean").execute()
            all_means = list(set([item['mean'] for item in choice_res.data if item['mean']]))
            other_means = [m for m in all_means if m != q['mean']]
            distractors = random.sample(other_means, min(len(other_means), 3))
            
            options = distractors + [q['mean']]
            random.shuffle(options)
            
            st.session_state.quiz = {
                "raw_data": q.to_dict(), # 復習用に全データを保存
                "q_text": q.get('word', ''),
                "ans": q.get('mean', ''),
                "exp": q.get('explanation', q.get('explanatio', '解説なし')),
                "options": options
            }
            st.session_state.answered = False

        quiz = st.session_state.quiz
        st.info(quiz['q_text']) if study_mode != "単語クイズ" else st.title(f"**{quiz['q_text']}**")

        for opt in quiz['options']:
            if st.button(opt, use_container_width=True, disabled=st.session_state.answered, key=f"btn_{opt}"):
                st.session_state.answered = True
                st.session_state.is_correct = (opt == quiz['ans'])
                
                # 間違えたらリストに追加（重複チェック付き）
                if not st.session_state.is_correct:
                    if quiz['raw_data'] not in st.session_state.wrong_list:
                        st.session_state.wrong_list.append(quiz['raw_data'])
                # 正解して、かつ復習モードならリストから削除
                elif st.session_state.is_correct and study_mode == "🔥 復習モード":
                    st.session_state.wrong_list = [item for item in st.session_state.wrong_list if item.get('word') != quiz['q_text']]
                
                st.rerun()

        if st.session_state.answered:
            if st.session_state.is_correct:
                st.success("⭕️ 正解！")
            else:
                st.error(f"❌ 不正解... (復習リストに追加されました)")
            
            st.markdown("#### ✅ 解説")
            st.latex(str(quiz['exp']).replace('$', ''))

            if st.button("次の問題へ ➡️"):
                del st.session_state.quiz
                st.rerun()
