import streamlit as st
from supabase import create_client, Client
import pandas as pd
import random

# --- 1. Supabase の初期化 ---
# streamlitのSecretsに設定した値を使用します
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# あなたの実際のテーブル名
TABLE_WORDS = "physics_words" 
TABLE_PROBLEMS = "electromagnetics" 

# --- 2. データ取得関数 ---
def get_physics_data(mode, level_filter="すべて"):
    try:
        # モードによってテーブルを切り替え
        target_table = TABLE_WORDS if mode == "単語クイズ" else TABLE_PROBLEMS
        
        # データを取得
        res = supabase.table(target_table).select("*").execute()
        df = pd.DataFrame(res.data)
        
        if df.empty:
            return df

        # レベル絞り込み (数値と文字列の不一致を回避)
        if level_filter != "すべて":
            df['level'] = pd.to_numeric(df['level'], errors='coerce')
            df = df[df['level'] == int(level_filter)]
            
        return df
    except Exception as e:
        st.error(f"データ取得中にエラーが発生しました: {e}")
        return pd.DataFrame()

# --- 3. UI設定 ---
st.set_page_config(page_title="電磁気マスター", layout="centered")

st.sidebar.header("⚙️ 学習設定")
study_mode = st.sidebar.selectbox("クイズモード", ["単語クイズ", "例題クイズ"])
level_selection = st.sidebar.selectbox("難易度を選択", ["すべて", 1, 2])

st.title(f"⚡️ {study_mode}")

# --- 4. クイズロジック ---
df = get_physics_data(study_mode, level_selection)

if df.empty:
    st.warning("表示できるデータが見つかりません。")
    st.info(f"テーブル '{TABLE_WORDS if study_mode == '単語クイズ' else TABLE_PROBLEMS}' のRLS設定や、中身を確認してください。")
else:
    # モード切り替え時にセッションをリセット
    if 'last_mode' in st.session_state and st.session_state.last_mode != study_mode:
        if 'quiz' in st.session_state: del st.session_state.quiz
    st.session_state.last_mode = study_mode

    # 新しい問題を作成
    if 'quiz' not in st.session_state:
        # ランダムに1件選択
        q = df.sample(n=1).iloc[0]
        
        # 選択肢は常に「単語テーブル」から取得（正解の公式が単語テーブルにあるため）
        try:
            words_res = supabase.table(TABLE_WORDS).select("mean").execute()
            all_means = list(set([item['mean'] for item in words_res.data]))
        except:
            # 万が一単語テーブルが取れない場合は、現在のデータから生成
            all_means = list(set(df['mean'].tolist()))
            
        # 正解以外の選択肢を3つ作成
        other_means = [m for m in all_means if m != q['mean']]
        distractors = random.sample(other_means, min(len(other_means), 3))
        
        options = distractors + [q['mean']]
        random.shuffle(options)
        
        # セッションに保存（KeyError対策のため .get() を使用）
        st.session_state.quiz = {
            "id": q.get('id', 0), # idがなければ0を代入
            "q_text": q.get('word', '問題文が見つかりません'),
            "ans": q.get('mean', ''),
            "exp": q.get('explanation', q.get('explanatio', '解説はありません')), # 綴りミス対策
            "options": options
        }
        st.session_state.answered = False

    quiz = st.session_state.quiz

    # 問題文の表示
    if study_mode == "単語クイズ":
        st.subheader("この用語の公式・意味を選んでください")
        st.title(f"**{quiz['q_text']}**")
    else:
        st.subheader("この例題に適した解答・公式を選んでください")
        # 例題モードでは問題文を枠付きで表示
        st.info(quiz['q_text'])

    st.write("---")

    # 回答ボタン
    for opt in quiz['options']:
        if st.button(opt, use_container_width=True, disabled=st.session_state.answered, key=f"btn_{opt}"):
            st.session_state.answered = True
            st.session_state.is_correct = (opt == quiz['ans'])
            st.rerun()

    # 回答後の表示
    if st.session_state.answered:
        if st.session_state.is_correct:
            st.success("⭕️ 正解です！")
        else:
            st.error(f"❌ 不正解... 正解は: {quiz['ans']}")
        
        st.markdown("### 📖 解説・公式")
        # LaTeX形式であれば数式表示
        display_exp = str(quiz['exp']).replace('$', '')
        if display_exp != '解説はありません':
            st.latex(display_exp)
        else:
            st.write("解説が登録されていません。")

        if st.button("次の問題へ ➡️"):
            del st.session_state.quiz
            st.rerun()
