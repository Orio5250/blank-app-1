if menu in ["クイズに挑戦", "復習モード"]:
    df = get_data(mode='all' if menu == "クイズに挑戦" else 'review')
    
    if df.empty:
        st.info("対象のデータがありません。")
    else:
        # セッション状態の初期化
        if 'quiz' not in st.session_state:
            q = df.sample(n=1).iloc[0]
            # 4択作成
            all_means = pd.read_sql("SELECT mean FROM physics_words", conn)['mean'].tolist()
            # 重複を除去してランダムにハズレを選択
            other_means = list(set([m for m in all_means if m != q['mean']]))
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
            st.session_state.user_choice = None # どのボタンを押したか記憶

        quiz = st.session_state.quiz
        st.subheader(f"Q: {quiz['word']}")

        # 4択ボタンの配置
        for opt in quiz['options']:
            # 解答済みの場合はボタンを無効化(disabled)
            if st.button(opt, use_container_width=True, disabled=st.session_state.answered, key=f"btn_{opt}"):
                st.session_state.answered = True
                st.session_state.user_choice = opt
                
                # 正誤判定と保存
                is_correct = (opt == quiz['ans'])
                c = conn.cursor()
                c.execute("INSERT INTO records (word_id, is_correct) VALUES (?, ?)", (int(quiz['id']), 1 if is_correct else 0))
                conn.commit()
                st.session_state.feedback = is_correct
                st.rerun() # 状態を確定させるために即再描画

        # 解答後の表示
        if st.session_state.answered:
            if st.session_state.feedback:
                st.success(f"⭕️ 正解！: {quiz['ans']}")
            else:
                st.error(f"❌ 不正解！ あなたの選択: {st.session_state.user_choice}")
                st.info(f"正しい公式: {quiz['ans']}")
            
            # 解説表示
            with st.container(border=True):
                st.markdown("**💡 この公式のポイント**")
                st.markdown(quiz['exp'])
            
            if st.button("次の問題へ ➡️", type="primary"):
                # セッション情報をクリアして次へ
                del st.session_state.quiz
                if 'user_choice' in st.session_state: del st.session_state.user_choice
                if 'feedback' in st.session_state: del st.session_state.feedback
                st.rerun()
