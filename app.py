import streamlit as st
import pandas as pd
import math

# --- ページ設定 ---
st.set_page_config(page_title="成果評価シミュレーター", layout="wide")

st.title("🏆 成果評価シミュレーター")
st.markdown("全店のランキングデータを分析し、目標ランク達成のための具体的なアクションプランを提示します。")

# --- 関数: ランクボーダー計算ロジック ---
def calculate_rank_borders(df_group, points_col):
    """
    グループごとのランクボーダー点数を算出する関数
    (仮の配分: S上位20%, A次の30%, B次の30%, C以下)
    ※実際の規定に合わせて調整可能です
    """
    sorted_df = df_group.sort_values(by=points_col, ascending=False).reset_index()
    total = len(sorted_df)
    
    # ランクの人数の区切り位置を計算
    s_limit = math.ceil(total * 0.20) # 上位20%
    a_limit = math.ceil(total * 0.50) # 次の30% (計50%)
    b_limit = math.ceil(total * 0.80) # 次の30% (計80%)
    
    borders = {
        "S": sorted_df.iloc[s_limit - 1][points_col] if total > 0 else 0,
        "A": sorted_df.iloc[a_limit - 1][points_col] if total > s_limit else 0,
        "B": sorted_df.iloc[b_limit - 1][points_col] if total > a_limit else 0,
    }
    return borders, sorted_df

# --- 1. データ読み込み ---
uploaded_file = st.file_uploader("全店ランキングデータ（Excel/CSV）をアップロード", type=["xlsx", "xls", "csv"])

if uploaded_file is not None:
    try:
        # ファイル読み込み
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        else:
            df = pd.read_excel(uploaded_file)
        
        st.success(f"✅ データ読み込み完了: 全 {len(df)} 店舗")

        # --- 2. 列の割り当て（マッピング） ---
        st.sidebar.header("⚙️ データ項目の設定")
        st.sidebar.info("Excelのどの列を使うか教えてください")
        
        cols = df.columns.tolist()
        
        # 必須項目の選択
        col_store = st.sidebar.selectbox("「店舗名」の列", cols, index=0)
        col_cluster = st.sidebar.selectbox("「クラスタ(S~F)」の列", cols, index=1 if len(cols)>1 else 0)
        col_points = st.sidebar.selectbox("「評価ポイント(総点)」の列", cols, index=2 if len(cols)>2 else 0)

        # データ型変換（ポイント列を数値化）
        df[col_points] = pd.to_numeric(df[col_points], errors='coerce').fillna(0)

        # --- 3. グループ分けとランク計算 ---
        # クラスタに基づいてグループ定義
        def classify_group(cluster):
            cluster = str(cluster).upper().strip()
            if cluster in ['S', 'A', 'B']: return '大型店'
            elif cluster in ['C', 'D']: return '中型店'
            elif cluster in ['E', 'F']: return '小型店'
            else: return 'その他'

        df['分析グループ'] = df[col_cluster].apply(classify_group)

        # --- 4. 店舗選択と現状分析 ---
        st.markdown("---")
        
        # 店舗選択プルダウン
        stores_list = df[col_store].unique()
        selected_store_name = st.selectbox("📍 分析する自店舗を選択してください", stores_list)
        
        # 自店舗のデータ取得
        my_data = df[df[col_store] == selected_store_name].iloc[0]
        my_group = my_data['分析グループ']
        my_points = my_data[col_points]

        # 同じグループのデータを抽出してランキング計算
        group_df = df[df['分析グループ'] == my_group].copy()
        borders, ranked_df = calculate_rank_borders(group_df, col_points)
        
        # 自店舗の順位を取得
        my_rank = ranked_df[ranked_df[col_store] == selected_store_name].index[0] + 1
        total_in_group = len(ranked_df)

        # 現在地の表示
        st.header(f"店舗: {selected_store_name}")
        c1, c2, c3 = st.columns(3)
        c1.metric("所属グループ", f"{my_group} ({my_data[col_cluster]})")
        c2.metric("現在の獲得ポイント", f"{int(my_points):,} pt")
        c3.metric("グループ内順位", f"{my_rank}位 / {total_in_group}店舗中")

        # --- 5. 目標設定とギャップ計算 ---
        st.subheader("🎯 目標ランクの設定")
        
        target_rank = st.radio("目指すランクを選択", ["S", "A", "B"], horizontal=True, index=0)
        target_points = borders.get(target_rank, 0)
        
        gap = target_points - my_points

        # ギャップ表示
        st.info(f"**{target_rank}ランク** のボーダーライン: **{int(target_points):,} pt**")
        
        if gap > 0:
            st.error(f"あと **{int(gap):,} pt** 足りません！ 😱")
            
            # --- 6. シミュレーション（アクションプラン） ---
            st.markdown("### 🛠 どうやって埋めますか？ 具体的なアクションプラン")
            
            # 案①：パワープレイ（件数で稼ぐ）
            with st.expander("案①：パワープレイ（高ポイント商材で稼ぐ）", expanded=True):
                st.markdown("獲得数を積み上げて逆転するプランです。")
                
                col_sim_1, col_sim_2 = st.columns(2)
                with col_sim_1:
                    item_name_1 = st.text_input("商材名A (例: SB機変)", "SB機変")
                    item_point_1 = st.number_input(f"{item_name_1} の1件あたりポイント", value=8.0)
                    needed_1 = math.ceil(gap / item_point_1) if item_point_1 > 0 else 0
                    st.markdown(f"👉 {item_name_1} ならあと **{needed_1} 件**")

                with col_sim_2:
                    item_name_2 = st.text_input("商材名B (例: Y→S)", "Y→S")
                    item_point_2 = st.number_input(f"{item_name_2} の1件あたりポイント", value=5.0)
                    needed_2 = math.ceil(gap / item_point_2) if item_point_2 > 0 else 0
                    st.markdown(f"👉 {item_name_2} ならあと **{needed_2} 件**")

            # 案②：ディフェンス改善（係数回復）
            with st.expander("案②：ディフェンス改善（係数・品質を上げる）"):
                st.markdown("獲得数はそのままで、係数（品質）を上げてポイントを増やすプランです。")
                
                # 係数シミュレーション
                current_base_score = st.number_input("現在の「獲得ボリューム（素点）」を入力", value=int(my_points), help="係数をかける前の元々の点数")
                current_coeff = st.slider("現在の係数", 0.5, 1.5, 1.0, 0.1)
                
                target_coeff = st.slider("目標の係数（改善後）", 0.5, 1.5, current_coeff + 0.1, 0.1)
                
                # 計算
                predicted_points = current_base_score * target_coeff
                improvement = predicted_points - (current_base_score * current_coeff)
                
                if improvement >= gap:
                    st.success(f"🎉 係数を **{target_coeff}** に上げれば、+ {int(improvement)} pt でランクアップ確定です！")
                else:
                    st.warning(f"係数を上げると + {int(improvement)} pt ですが、まだ {int(gap - improvement)} pt 足りません。")
                
                st.markdown("例：PayPayカード設定率を上げる、オプション歩留まりを改善するなど")

            # 案③：コンビネーション
            with st.expander("案③：コンビネーション（合わせ技）"):
                st.write(f"残り {int(gap)} pt を組み合わせで解決します。")
                combo_item1 = st.number_input(f"{item_name_1} を何件やりますか？", min_value=0, value=1)
                combo_pts = combo_item1 * item_point_1
                remaining_gap = gap - combo_pts
                
                if remaining_gap <= 0:
                    st.success("それだけで達成可能です！")
                else:
                    needed_combo_2 = math.ceil(remaining_gap / item_point_2) if item_point_2 > 0 else 0
                    st.info(f"{item_name_1}を {combo_item1}件 やると、残りは {item_name_2} が **{needed_combo_2} 件** 必要です。")

        else:
            st.balloons()
            st.success(f"🎉 おめでとうございます！ 現在 **{target_rank}ランク** の圏内です（+ {abs(int(gap)):,} pt 余裕あり）")
            st.metric("次のランクまでの差", f"あと {int(borders.get('S', 0) - my_points):,} pt")

        # --- 参考：ランキング表 ---
        st.markdown("---")
        st.subheader(f"📊 {my_group} ランキング一覧")
        st.dataframe(ranked_df[[col_store, col_cluster, col_points]])

    except Exception as e:
        st.error("エラーが発生しました。")
        st.warning("Excelの列名が正しく選択されているか、サイドバーの設定を確認してください。")
        st.expander("エラー詳細").write(e)
else:
    st.info("👆 上のボックスからランキングデータ（Excel/CSV）をアップロードしてください。")
