import streamlit as st
from supabase import create_client, Client
import pandas as pd
import sqlite3
import os
import random

# --- 1. Supabase の初期化 ---
# Streamlit Secrets (Community Cloudの設定画面) に登録した値を使用
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- DB設定 (問題データ用はSQLiteを維持、記録用をSupabaseへ) ---
def init_db():
    conn = sqlite3.connect('physics_quiz.db', check_same_thread=False)
    c = conn.cursor()
    # physics_words はアプリ内の問題集なので SQLite のままでOK
    c.execute('''CREATE TABLE IF NOT EXISTS physics_words 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, word TEXT, mean TEXT, explanation TEXT, level INTEGER)''')
    
    if os.path.exists('physics_data.csv'):
        c.execute("SELECT count(*) FROM physics_words")
        if c.fetchone()[0] == 0:
            try:
                df_csv = pd.read_csv('physics_data.csv')
                df_csv.to_sql('physics_words', conn, if_exists='append', index=False)
            except Exception as e:
                st.error(f"CSVの読み込みに失敗しました: {e}")
    conn.commit()
    return conn

conn = init_db()

def get_data(mode='all'):
    if mode == 'review':
        # --- 2. 復習モードのクエリを Supabase から取得するように変更 ---
        try:
            # Supabase から不正解(is_correct=0)のデータを取得
            response = supabase.table("records").select("word_id").eq("is_correct", 0).execute()
            wrong_ids = list(set([item['word_id'] for item in response.data]))
            
            if not wrong_ids:
                return pd.DataFrame()
            
            # SQLite側の問題データから、該当するIDを抽出
            query = f"SELECT * FROM physics_words WHERE id IN ({','.join(map(str, wrong_ids))})"
        except Exception as e:
            st.error(f"履歴の取得に失敗しました: {e}")
            return pd.DataFrame()
    else:
        query = "SELECT * FROM physics_words"
    
    return pd.read_sql(query, conn)

# --- UI設定 ---
st.set_page_config(page_title="電磁気学マスター", layout="centered")
st.title("⚡️ 電磁気学 単語・公式マスター")

menu = st.sidebar.radio("メニュー", ["クイズに挑戦", "復習モード", "苦手リストと解説"])

# --- クイズ・復習モード ---
if menu in ["クイズに挑戦", "復習モード"]:
    df = get_data(mode='all' if menu == "クイズに挑戦" else 'review')
    
    if df.empty:
        st.info("対象のデータがありません。")
    else:
        if 'quiz' not in st.session_state:
            q = df.sample(n=1).iloc[0]
            all_means = pd.read_sql("SELECT mean FROM physics_words", conn)['mean'].unique().tolist()
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

        for opt in quiz['options']:
            if st.button(opt, use_container_width=True, disabled=st.session_state.answered, key=f"opt_{opt}"):
                st.session_state.answered = True
                is_correct = (opt == quiz['ans'])
                
                # --- 3. 正誤判定を Supabase に保存 ---
                try:
                    data = {
                        "word_id": int(quiz['id']),
                        "is_correct": 1 if is_correct else 0
                    }
                    supabase.table("records").insert(data).execute()
                except Exception as e:
                    st.warning(f"クラウドへの保存に失敗しました(オフライン): {e}")
                
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

# --- 統計・解説モード ---
elif menu == "苦手リストと解説":
    st.subheader("📚 復習が必要な項目")
    
    # --- 4. 統計データも Supabase から取得 ---
    try:
        res = supabase.table("records").select("word_id").eq("is_correct", 0).execute()
        if not res.data:
            st.write("まだ間違いはありません。")
        else:
            # ミス回数をカウント
            miss_df = pd.DataFrame(res.data)
            counts = miss_df['word_id'].value_counts()
            
            for w_id, count in counts.items():
                # SQLiteから単語情報を取得
                word_info = pd.read_sql(f"SELECT * FROM physics_words WHERE id = {w_id}", conn).iloc[0]
                with st.expander(f"{word_info['word']} (ミス: {count}回)"):
                    st.latex(word_info['mean'])
                    st.write(f"**解説:** {word_info['explanation']}")
    except Exception as e:
        st.error(f"データの取得中にエラーが発生しました: {e}")
