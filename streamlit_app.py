import streamlit as st
import pandas as pd
import sqlite3
import os
import random

# --- DB設定 ---
def init_db():
    conn = sqlite3.connect('physics_quiz.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS physics_words 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, word TEXT, mean TEXT, explanation TEXT, level INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS records 
                 (word_id INTEGER, is_correct INTEGER, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
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
        query = """
        SELECT DISTINCT w.* FROM physics_words w 
        JOIN records r ON w.id = r.word_id 
        WHERE r.is_correct = 0
        """
    else:
        query = "SELECT * FROM physics_words"
    return pd.read_sql(query, conn)

# --- UI設定 ---
st.set_page_config(page_title="電磁気学マスター", layout="centered")
st.title("⚡️ 電磁気学 単語・公式マスター")

# サイドバーメニュー（ここで menu を定義）
menu = st.sidebar.radio("メニュー", ["クイズに挑戦", "復習モード", "苦手リストと解説"])

# --- クイズ・復習モード ---
if menu in ["クイズに挑戦", "復習モード"]:
    df = get_data(mode='all' if menu == "クイズに挑戦" else 'review')
    
    if df.empty:
        st.info("対象のデータがありません。")
    else:
        # クイズの初期化
        if 'quiz' not in st.session_state:
            q = df.sample(n=1).iloc[0]
            # 4択作成
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
            st.session_state.user_choice = None

        quiz = st.session_state.quiz
        st.subheader(f"Q: {quiz['word']}")

        # ボタンの表示
        for opt in quiz['options']:
            # st.session_state.answered が True になると全ボタンが押せなくなる
            if st.button(opt, use_container_width=True, disabled=st.session_state.answered, key=f"opt_{opt}"):
                st.session_state.answered = True
                st.session_state.user_choice = opt
                
                # 正誤判定
                is_correct = (opt == quiz['ans'])
                c = conn.cursor()
                c.execute("INSERT INTO records (word_id, is_correct) VALUES (?, ?)", (int(quiz['id']), 1 if is_correct else 0))
                conn.commit()
                st.session_state.feedback = is_correct
                st.rerun()

        # 回答後の表示
        if st.session_state.answered:
            if st.session_state.feedback:
                st.success(f"⭕️ 正解！: {quiz['ans']}")
            else:
                st.error(f"❌ 不正解！ 正解は: {quiz['ans']}")
            
            # 詳細解説
            st.info(f"**解説:**\n{quiz['exp']}")
            
            if st.button("次の問題へ ➡️"):
                del st.session_state.quiz
                st.rerun()

# --- 統計・解説モード ---
elif menu == "苦手リストと解説":
    st.subheader("📚 復習が必要な項目")
    data = pd.read_sql("""
        SELECT w.word, w.mean, w.explanation, COUNT(*) as miss_count 
        FROM records r 
        JOIN physics_words w ON r.word_id = w.id 
        WHERE r.is_correct = 0 
        GROUP BY w.id 
        ORDER BY miss_count DESC
    """, conn)
    
    if data.empty:
        st.write("まだ間違いはありません。")
    else:
        for i, row in data.iterrows():
            with st.expander(f"{row['word']} (ミス: {row['miss_count']}回)"):
                st.latex(row['mean'])  # 数式をきれいに表示
                st.write(f"**解説:** {row['explanation']}")
