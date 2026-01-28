import streamlit as st
import pandas as pd
import math

# --- ページ設定 ---
st.set_page_config(page_title="成果評価シミュレーター", layout="wide")

st.title("🏆 成果評価シミュレーター")
st.markdown("データがR列・S列・T列にあっても、読み込み位置を調整して分析できます。")

# --- 関数: ランクボーダー計算 ---
def calculate_rank_borders(df_group, points_col):
    sorted_df = df_group.sort_values(by=points_col, ascending=False).reset_index(drop=True)
    total = len(sorted_df)
    
    if total == 0:
        return {"S": 0, "A": 0, "B": 0}, sorted_df

    s_limit = math.ceil(total * 0.20)
    a_limit = math.ceil(total * 0.50)
    b_limit = math.ceil(total * 0.80)
    
    borders = {
        "S": sorted_df.iloc[s_limit - 1][points_col] if total > 0 else 0,
        "A": sorted_df.iloc[a_limit - 1][points_col] if total > s_limit else 0,
        "B": sorted_df.iloc[b_limit - 1][points_col] if total > a_limit else 0,
    }
    return borders, sorted_df

# --- 1. データ読み込み設定エリア ---
st.sidebar.header("📂 データ読み込み設定")
uploaded_file = st.sidebar.file_uploader("Excel/CSVをアップロード", type=["xlsx", "xls", "csv"])

# ヘッダー行の指定（重要！）
header_row_idx = st.sidebar.number_input(
    "表のタイトル（項目名）は何行目にありますか？", 
    min_value=1, 
    value=1, 
    help="Excelの1行目が空白で、5行目から表が始まる場合などはここを『5』にしてください"
) - 1  # プログラム用に行番号を補正

if uploaded_file is not None:
    try:
        # --- ファイル読み込み ---
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, header=header_row_idx)
        elif uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file, engine='openpyxl', header=header_row_idx)
        else:
            df = pd.read_excel(uploaded_file, header=header_row_idx)
        
        # 空白列（Unnamed）の削除とデータのクリーニング
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]  # 列名がない列を削除
        df = df.dropna(how='all', axis=1) # 中身が空の列を削除
        
        st.toast(f"データを読み込みました！ ({len(df)}行)")

        # --- 2. 列の割り当て（マッピング） ---
        st.sidebar.markdown("---")
        st.sidebar.header("⚙️ 列の指定")
        st.sidebar.info("R, S, T列に相当する項目名を選んでください")
        
        cols = df.columns.tolist()
        
        # もし列が見つからない場合の救済措置
        if len(cols) < 3:
            st.error("有効な列が見つかりません。「表のタイトル行」の数値を変更してみてください。")
            st.stop()

        # 列選択（デフォルト値を自動推定）
        # R列：店舗名
        idx_store = next((i for i, c in enumerate(cols) if "店舗" in str(c) or "店名" in str(c)), 0)
        col_store = st.sidebar.selectbox("「店舗名」の列 (R列相当)", cols, index=idx_store)
        
        # S列：ランク（クラスタ）
        idx_cluster = next((i for i, c in enumerate(cols) if "ランク" in str(c) or "クラスタ" in str(c)), 1 if len(cols)>1 else 0)
        col_cluster = st.sidebar.selectbox("「ランク/クラスタ」の列 (S列相当)", cols, index=idx_cluster)
        
        # T列：総合ポイント
        idx_points = next((i for i, c in enumerate(cols) if "ポイント" in str(c) or "点" in str(c) or "総合" in str(c)), 2 if len(cols)>2 else 0)
        col_points = st.sidebar.selectbox("「総合ポイント」の列 (T列相当)", cols, index=idx_points)

        # データ型変換（文字列の空白除去と数値化）
        df[col_store] = df[col_store].astype(str).str.strip()  # 店舗名の前後の空白を削除
        df[col_cluster] = df[col_cluster].astype(str).str.strip() # ランクの空白削除
        df[col_points] = pd.to_numeric(df[col_points], errors='coerce').fillna(0) # ポイントを数値化

        # --- 3. グループ分け ---
        def classify_group(cluster):
            cluster = str(cluster).upper().strip()
            # データの「S, A, B」などを判定
            if cluster in ['S', 'A', 'B', '大型']: return '大型店'
            elif cluster in ['C', 'D', '中型']: return '中型店'
            elif cluster in ['E', 'F', '小型']: return '小型店'
            return 'その他'

        df['分析グループ'] = df[col_cluster].apply(classify_group)

        # --- 4. 店舗選択と分析 ---
        st.markdown("---")
        
        # 店舗リスト作成（ソートして探しやすく）
        stores_list = sorted(df[col_store].unique().tolist())
        
        col_main_1, col_main_2 = st.columns([1, 2])
        
        with col_main_1:
            selected_store_name = st.selectbox("📍 分析する店舗を選択", stores_list)
        
        # データ抽出（エラー回避ロジック入り）
        my_data_rows = df[df[col_store] == selected_store_name]
        
        if my_data_rows.empty:
            st.error("選択された店舗のデータが見つかりません。")
            st.stop()
            
        my_data = my_data_rows.iloc[0]
        my_group = my_data['分析グループ']
        my_points = my_data[col_points]

        # ランキング計算
        group_df = df[df['分析グループ'] == my_group].copy()
        borders, ranked_df = calculate_rank_borders(group_df, col_points)
        
        # 順位取得
        try:
            my_rank = ranked_df[ranked_df[col_store] == selected_store_name].index[0] + 1
        except:
            my_rank = "-"
        
        total_in_group = len(ranked_df)

        # 結果表示
        with col_main_2:
            st.info(f"**{selected_store_name}** （{my_group} / {my_data[col_cluster]}ランク）")
            m1, m2, m3 = st.columns(3)
            m1.metric("現在ポイント", f"{int(my_points):,} pt")
            m2.metric("グループ順位", f"{my_rank}位")
            m3.metric("母数", f"{total_in_group} 店舗")

        # --- 5. 目標シミュレーション ---
        st.markdown("### 🎯 目標達成シミュレーション")
        
        # 目標ランク選択
        target_rank = st.radio("目指すランク", ["S", "A", "B"], horizontal=True)
        target_pt = borders.get(target_rank, 0)
        gap = target_pt - my_points

        # ギャップ表示
        if gap > 0:
            st.warning(f"あと **{int(gap):,} pt** 必要です（ボーダー: {int(target_pt):,} pt）")
            
            st.markdown("#### 🛠 具体的なアクションプラン")
            
            with st.expander("詳細プランニングを開く", expanded=True):
                # 案① パワープレイ
                st.markdown("**① 件数で稼ぐ (Power Play)**")
                c_p1, c_p2 = st.columns(2)
                with c_p1:
                    item1 = st.text_input("商材名1", "SB機変")
                    pt1 = st.number_input(f"{item1} のポイント", value=8.0)
                    if pt1 > 0:
                        st.markdown(f"👉 あと **{math.ceil(gap/pt1)} 件**")
                
                with c_p2:
                    item2 = st.text_input("商材名2", "Y→S")
                    pt2 = st.number_input(f"{item2} のポイント", value=5.0)
                    if pt2 > 0:
                        st.markdown(f"👉 あと **{math.ceil(gap/pt2)} 件**")

        else:
            st.success(f"🎉 {target_rank}ランク 達成圏内です！（+ {abs(int(gap))} pt 余裕あり）")
            # 次のランクがあれば表示
            if target_rank == "B":
                 st.caption(f"次はAランク（{int(borders['A']):,} pt）を目指しましょう！")
            elif target_rank == "A":
                 st.caption(f"次はSランク（{int(borders['S']):,} pt）を目指しましょう！")

        # データ確認用
        with st.expander("📊 ランキング表を確認"):
            st.dataframe(ranked_df[[col_store, col_cluster, col_points]])

    except Exception as e:
        st.error("エラーが発生しました。設定を確認してください。")
        st.code(e)
else:
    st.info("👈 左側のサイドバーからファイルをアップロードしてください。")
