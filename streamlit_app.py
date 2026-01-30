import streamlit as st
from supabase import create_client, Client
import pandas as pd
import os
import random

# --- 1. Supabase の初期化 ---
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 2. データ管理関数 ---

def initialize_data():
    """初期化：Supabaseが空ならCSVからデータを投入"""
    try:
        res = supabase.table("physics_words").select("id", count="exact").limit(1).execute()
        if res.count == 0 and os.path.exists('physics_data.csv'):
            df_csv = pd.read_csv('physics_data.csv')
            data_to_insert = df_csv.to_dict(orient='records')
            supabase.table("physics_words").insert(data_to_insert).execute()
            st.toast("CSVデータをクラウドへ同期しました！")
    except Exception as e:
        st.error(f"初期化エラー: {e}")

def get_physics_data(mode='all', level_filter=None):
    """問題データを Supabase から取得（レベル絞り込み対応）"""
    try:
        if mode == 'review':
            res_records = supabase.table("records").select("word_id").eq("is_correct", 0).execute()
            wrong_ids = list(set([item['word_id'] for item in res_records.data]))
            if not wrong_ids:
                return pd.DataFrame()
            query = supabase.table("physics_words").select("*").in_("id", wrong_ids)
        else:
            query = supabase.table("physics_words").select("*")
            # --- レベル絞り込みの追加 ---
            if level_filter and level_filter != "すべて":
                query = query.eq("level", int(level_filter))
        
        res = query.execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        return pd.DataFrame()

initialize_data()

# --- 3. UI設定 ---
st.set_page_config(page_title="電磁気学マスター", layout="centered")
st.title("⚡️ 電磁気学 レベル別マスター")

# --- サイドバー設定 ---
st.sidebar.header("設定")
menu = st.sidebar.radio("メニュー", ["クイズに挑戦", "復習モード", "苦手リストと解説"])

# レベル選択（クイズモードの時のみ表示）
level_selection = "すべて"
if menu == "クイズに挑戦":
    level_selection = st.sidebar.selectbox("難易度を選択", ["すべて", "1", "2"])
    st.sidebar.info("1: 基礎・公式\n2: 発展・マクスウェル方程式")

# --- 4. クイズ・復習モードの処理 ---
if menu in ["クイズに挑戦", "復習モード"]:
    # 選択されたレベルを引数に渡す
    df = get_physics_data(mode='all' if menu == "クイズに挑戦" else 'review', level_filter=level_selection)
    
    if df.empty:
        st.info("対象の問題がありません。他のレベルを選ぶか、まずは学習を進めましょう！")
    else:
        # 問題が変わるタイミングでセッションをリセットするために、レベル選択が変わったらquizを消去
        if 'last_level' in st.session_state and st.session_state.last_level != level_selection:
            if 'quiz' in st.session_state: del st.session_state.quiz
        st.session_state.last_level = level_selection

        if 'quiz' not in st.session_state:
            q = df.sample(n=1).iloc[0]
            
            # 選択肢用（全データから取得）
            all_means_res = supabase.table("physics_words").select("mean").execute()
            all_means = list(set([item['mean'] for item in all_means_res.data]))
            
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
        st.caption(f"難易度: Level {quiz['level']}")
        st.subheader(f"Q: {quiz['word']}")

        for opt in quiz['options']:
            if st.button(opt, use_container_width=True, disabled=st.session_state.answered, key=f"opt_{opt}"):
                st.session_state.answered = True
                is_correct = (opt == quiz['ans'])
                
                try:
                    supabase.table("records").insert({
                        "word_id": int(quiz['id']),
                        "is_correct": 1 if is_correct else 0
                    }).execute()
                except Exception as e:
                    st.warning(f"保存失敗: {e}")
                
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

# --- 5. 苦手リストと解説モード ---
elif menu == "苦手リストと解説":
    st.subheader("📚 復習が必要な項目")
    try:
        res = supabase.table("records").select("word_id").eq("is_correct", 0).execute()
        if not res.data:
            st.success("苦手な項目はありません！")
        else:
            miss_df = pd.DataFrame(res.data)
            counts = miss_df['word_id'].value_counts()
            
            for w_id, count in counts.items():
                word_res = supabase.table("physics_words").select("*").eq("id", int(w_id)).single().execute()
                word_info = word_res.data
                with st.expander(f"{word_info['word']} (Level {word_info['level']} / ミス: {count}回)"):
                    formula = word_info['mean'].replace('$', '')
                    st.latex(formula)
                    st.write(f"**解説:** {word_info['explanation']}")
    except Exception as e:
        st.error(f"データ取得エラー: {e}")


#####

def upload_examples_only():
    try:
        # 1. 例題CSVのみを読み込む
        df = pd.read_csv('electromagnetics.csv')
        
        # 2. 分野やカテゴリの補完（CSVにない場合）
        df['field'] = "電磁気学"
        df['category'] = "example" # 確実にexampleとして投入
        df = df.fillna("")
        
        records = df.to_dict(orient='records')

        # 3. 削除(delete)はせず、追加(insert)のみ実行
        # 同一の問題が重複するのを防ぎたい場合は .upsert(records, on_conflict="word") を使用
        res = supabase.table("physics_words").insert(records).execute()
        
        st.success(f"例題の追加に成功しました！ ({len(res.data)} 件)")
        
    except Exception as e:
        # もしこれでもエラーが出る場合は、既に同じ 'word' が登録されている可能性があります
        st.error(f"エラーが発生しました: {e}")

# UI
if st.button("例題データのみを追加投入"):
    upload_examples_only()

