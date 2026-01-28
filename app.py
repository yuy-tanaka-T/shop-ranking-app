import streamlit as st
import pandas as pd
import math

# --- ページ設定 ---
st.set_page_config(page_title="店舗目標達成シミュレーター", layout="wide")

st.title("🏆 店舗目標達成シミュレーター")
st.markdown("全社平均と比較し、改善インパクトの大きい5項目を自動抽出して計画を立案します。")

# --- 1. 固定設定（ここを変更すればデフォルトが変わります） ---
DEFAULT_HEADER_ROW = 17      # Excelの17行目がタイトル
COL_NAME_STORE = "部門名"     # R列相当
COL_NAME_RANK = "Rank"       # S列相当
COL_NAME_POINT = "総合P"      # T列相当 (ここを変更しました！)

# --- 2. データ読み込み ---
uploaded_file = st.sidebar.file_uploader("ランキングデータ（Excel）をアップロード", type=["xlsx", "xls", "csv"])

if uploaded_file is not None:
    try:
        # ヘッダー行を指定して読み込み（Pythonは0始まりなので -1）
        header_idx = DEFAULT_HEADER_ROW - 1
        
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, header=header_idx)
        else:
            df = pd.read_excel(uploaded_file, header=header_idx)
        
        # 必要な列が存在するかチェック
        missing_cols = []
        for c in [COL_NAME_STORE, COL_NAME_RANK, COL_NAME_POINT]:
            if c not in df.columns:
                missing_cols.append(c)
        
        if missing_cols:
            st.error(f"エラー: Excelの中に以下の列名が見つかりません。\n{missing_cols}")
            st.info(f"Excelの{DEFAULT_HEADER_ROW}行目に正確にこの名前が入っているか確認してください。")
            st.stop()

        # データ型変換とクリーニング
        df[COL_NAME_STORE] = df[COL_NAME_STORE].astype(str).str.strip()
        df[COL_NAME_POINT] = pd.to_numeric(df[COL_NAME_POINT], errors='coerce').fillna(0)
        
        # 不要な列（空白など）を削除
        df = df.dropna(how='all', axis=1)

        st.toast(f"✅ 読み込み完了: 全 {len(df)} 店舗")

        # --- 3. 分析エンジンの準備 ---
        
        # 全社平均（Average）の計算
        # 数値列だけを抽出して平均を出す
        numeric_df = df.select_dtypes(include=['number'])
        avg_series = numeric_df.mean()

        # --- 4. 店舗選択 ---
        st.markdown("---")
        stores_list = sorted(df[COL_NAME_STORE].unique().tolist())
        
        # サイドバーでなくメイン画面で選択
        col_sel_1, col_sel_2 = st.columns([1, 2])
        with col_sel_1:
            selected_store = st.selectbox("📍 分析する店舗を選択", stores_list)
        
        # 自店舗データ抽出
        my_data = df[df[COL_NAME_STORE] == selected_store].iloc[0]
        my_point = my_data[COL_NAME_POINT]
        my_rank = my_data[COL_NAME_RANK]

        # --- 5. 目標設定とギャップ ---
        
        with col_sel_2:
            st.info(f"店舗名: **{selected_store}**")
            c1, c2 = st.columns(2)
            c1.metric("現在のランク", f"{my_rank}")
            c2.metric("現在の総合ポイント", f"{int(my_point):,} pt")

        st.markdown("### 🎯 目標設定")
        
        # 簡易的に目標ポイントを設定（デフォルトは今の1.1倍）
        target_point = st.number_input("目標とする総合ポイントを入力", value=int(my_point * 1.1))
        gap = target_point - my_point

        if gap <= 0:
            st.success("🎉 目標達成済みです！")
        else:
            st.warning(f"目標まであと **{int(gap):,} pt** 必要です。")
            
            # --- 6. 弱点分析とアクションプラン (AI分析) ---
            st.markdown("---")
            st.subheader("📊 重点改善 5項目 (対平均 乖離分析)")
            st.markdown("全社の平均値と比較して、**伸びしろ（乖離）が大きいワースト5項目**を自動抽出しました。")

            # 乖離の計算ロジック
            diff_dict = {}
            
            # 除外する列（ポイントそのものや、意味のない数値列）
            exclude_cols = [COL_NAME_POINT, '順位', 'No', 'No.', 'row', 'id']
            
            for col in numeric_df.columns:
                if col in exclude_cols:
                    continue
                
                # 自店の値
                val_store = my_data[col]
                # 全社平均
                val_avg = avg_series[col]
                
                # 平均が0より大きい場合のみ計算
                if val_avg > 0:
                    # 達成率 (自店 / 平均)
                    achievement_rate = (val_store / val_avg) * 100
                    
                    # 乖離ポイント（単純な数値差分ではなく、達成率の低さを重視）
                    if achievement_rate < 100:
                        diff_dict[col] = achievement_rate

            # 達成率が低い順（ワースト順）にソートしてトップ5を抽出
            worst_5_items = sorted(diff_dict.items(), key=lambda x: x[1])[:5]

            # --- アクションプランテーブルの作成 ---
            
            st.markdown(f"**残り営業日数で、この5項目をどう埋めますか？**")
            
            # テーブルヘッダー
            h1, h2, h3, h4, h5 = st.columns([2, 1.5, 1.5, 2, 2])
            h1.markdown("**項目名**")
            h2.markdown("**現状 / 平均**")
            h3.markdown("**対平均達成率**")
            h4.markdown("**計画 (月末までの獲得)**")
            h5.markdown("**獲得見込みポイント**")

            total_plan_points = 0

            for item_name, rate in worst_5_items:
                current_val = my_data[item_name]
                avg_val = avg_series[item_name]
                
                with st.container():
                    c1, c2, c3, c4, c5 = st.columns([2, 1.5, 1.5, 2, 2])
                    
                    # 1. 項目名
                    c1.markdown(f"**{item_name}**")
                    
                    # 2. 現状/平均
                    c2.caption(f"{current_val:,.1f} / {avg_val:,.1f}")
                    
                    # 3. 達成率 (赤字で強調)
                    c3.markdown(f":red[**{rate:.1f}%**]")
                    
                    # 4. 計画入力
                    with c4:
                        col_input_1, col_input_2 = st.columns(2)
                        target_num = col_input_1.number_input(f"獲得数", key=f"num_{item_name}", min_value=0, value=1)
                        points_per_unit = col_input_2.number_input(f"係数", key=f"coef_{item_name}", value=100, help="この項目の1件あたりのポイント")
                    
                    # 5. 結果計算
                    plan_points = target_num * points_per_unit
                    c5.metric("加算Pt", f"+ {int(plan_points):,}")
                    
                    total_plan_points += plan_points
                    st.divider()

            # --- 合計結果 ---
            st.markdown("### 📝 計画まとめ")
            
            col_res_1, col_res_2 = st.columns(2)
            
            with col_res_1:
                st.metric("目標までのギャップ", f"{int(gap):,} pt")
            
            with col_res_2:
                if total_plan_points >= gap:
                    st.success(f"見込み合計: + {int(total_plan_points):,} pt (達成！)")
                else:
                    remaining = gap - total_plan_points
                    st.error(f"見込み合計: + {int(total_plan_points):,} pt (あと {int(remaining):,} pt 不足)")

    except Exception as e:
        st.error("エラーが発生しました。")
        st.write("詳細:", e)
        st.warning(f"Excelの{DEFAULT_HEADER_ROW}行目に『部門名』『Rank』『{COL_NAME_POINT}』という列名があるか確認してください。")

else:
    st.info("👈 左側のサイドバーからExcelファイルをアップロードしてください。")
