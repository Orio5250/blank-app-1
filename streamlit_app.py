word,mean,explanation,level
"ガウスの法則",$\oint \mathbf{E} \cdot d\mathbf{A} = \frac{Q}{\varepsilon_0}$,"閉曲面を貫く電束の総量は、内部の電荷に比例するという法則です。",1
"オームの法則",$V = RI$,"電圧は電流と抵抗の積に等しいという回路の基本法則です。",1
"静電エネルギー","$U = \frac{1}{2}CV^2$","コンデンサに蓄えられるエネルギーの式です。",1
"磁束密度の単位",テスラ [T],"磁界の強さを表す単位で、1T = 1N/(A・m) です。",1
"誘電率の単位","[F/m]","ファラド毎メートル。真空の誘電率は $8.85 \times 10^{-12}$ です。",1
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
            df_csv = pd.read_csv('physics_data.csv')
            df_csv.to_sql('physics_words', conn, if_exists='append', index=False)
    conn.commit()
    return conn

conn = init_db()

def get_data(mode='all'):
    if mode == 'review':
        query = "SELECT DISTINCT w.* FROM physics_words w JOIN records r ON w.id = r.word_id WHERE r.is_correct = 0"
    else:
        query = "SELECT * FROM physics_words"
    return pd.read_sql(query, conn)

# --- UI ---
st.set_page_config(page_title="電磁気学マスター", layout="centered")
st.title("⚡️ 電磁気学 公式・単位マスター")

menu = st.sidebar.radio("メニュー", ["クイズに挑戦", "復習モード", "苦手リストと解説"])

if menu in ["クイズに挑戦", "復習モード"]:
    df = get_data(mode='all' if menu == "クイズに挑戦" else 'review')
    
    if df.empty:
        st.info("対象のデータがありません。")
    else:
        if 'quiz' not in st.session_state:
            q = df.sample(n=1).iloc[0]
            # 4択作成
            all_means = pd.read_sql("SELECT mean FROM physics_words", conn)['mean'].tolist()
            distractors = random.sample([m for m in all_means if m != q['mean']], 3)
            options = distractors + [q['mean']]
            random.shuffle(options)
            st.session_state.quiz = {"id": q['id'], "word": q['word'], "ans": q['mean'], "exp": q['explanation'], "options": options}
            st.session_state.answered = False

        quiz = st.session_state.quiz
        st.subheader(f"Q: {quiz['word']}")

        for opt in quiz['options']:
            if st.button(opt, use_container_width=True, disabled=st.session_state.answered):
                st.session_state.answered = True
                is_correct = (opt == quiz['ans'])
                c = conn.cursor()
                c.execute("INSERT INTO records (word_id, is_correct) VALUES (?, ?)", (int(quiz['id']), 1 if is_correct else 0))
                conn.commit()
                st.session_state.feedback = is_correct

        if st.session_state.answered:
            if st.session_state.feedback:
                st.success("⭕️ 正解！")
            else:
                st.error(f"❌ 不正解！ 正解は: {quiz['ans']}")
            
            # 解説表示
            st.markdown(f"**【解説】**\n{quiz['exp']}")
            
            if st.button("次の問題へ"):
                del st.session_state.quiz
                st.rerun()

elif menu == "苦手リストと解説":
    st.subheader("📚 復習が必要な項目")
    data = pd.read_sql("""SELECT w.word, w.mean, w.explanation, COUNT(*) as miss_count 
                          FROM records r JOIN physics_words w ON r.word_id = w.id 
                          WHERE r.is_correct = 0 GROUP BY w.id ORDER BY miss_count DESC""", conn)
    if data.empty:
        st.write("まだ間違いはありません。完璧です！")
    else:
        for i, row in data.iterrows():
            with st.expander(f"{row['word']} (ミス: {row['miss_count']}回)"):
                st.write(f"**正解:** {row['mean']}")
                st.write(f"**解説:** {row['explanation']}")
