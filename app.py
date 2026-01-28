import streamlit as st
import pandas as pd
import math
from datetime import datetime
import calendar

# --- ページ設定 ---
st.set_page_config(page_title="店舗目標達成シミュレーター", layout="wide")
st.title("🏆 店舗目標達成シミュレーター")
st.markdown("目標ランクを選択すると、そのランクの平均値との差分を埋めるための具体的アクション（5項目）を算出します。")

# --- 設定: 列などの定義 ---
TARGET_ITEM_NAMES = [
    "UPG", "SB機種変更", "固定純新規", "固定新規ALL", "Air機変", 
    "アクセサリー売上", "IDﾌﾟﾛﾃｸｼｮﾝ", "PayPayｶｰﾄﾞ", "PayPayｶｰﾄﾞｺﾞｰﾙﾄﾞ", 
    "DMMﾌﾟﾚﾐｱﾑ", "LINE", "おうちでんき", "ﾀﾌﾞﾚｯﾄ総販", "ﾌﾙﾌﾟﾗﾝ", "ﾗｲﾄﾌﾟﾗﾝ"
]

# 列の相対位置（項目名の列=0とした場合）
OFFSET_PT = 0        # ポイント
OFFSET_RANK_VAL = 1  # 順位（項目別）
OFFSET_TARGET = 2    # 目標数
OFFSET_ACTUAL = 3    # 実績数
OFFSET_LANDING = 4   # 着地
OFFSET_RATE = 5      # 達成率
OFFSET_UNIT_PT = 6   # 1件あたりのPt

# 固定位置情報（Excelの行列）
HEADER_ROW_NUM = 17 
COL_IDX_STORE = 17  # R列
COL_IDX_RANK = 18   # S列
COL_IDX_TOTAL = 19  # T列

# --- 1. サイドバー設定（ファイル＆日数） ---
st.sidebar.header("⚙️ 設定")
uploaded_file = st.sidebar.file_uploader("ランキングデータ（Excel）", type=["xlsx", "xls"])

# 残り日数の自動計算（または手動入力）
today = datetime.now()
last_day = calendar.monthrange(today.year, today.month)[1]
default_days = max(1, last_day - today.day)
remaining_days = st.sidebar.number_input("今月の残り営業日数", min_value=1, value=default_days)

if uploaded_file is not None:
    try:
        # データ読み込み
        df = pd.read_excel(uploaded_file, header=HEADER_ROW_NUM - 1)
        df.columns = df.columns.astype(str).str.strip()

        # 基本情報の抽出
        col_name_store = df.columns[COL_IDX_STORE]
        col_name_rank = df.columns[COL_IDX_RANK]
        col_name_total = df.columns[COL_IDX_TOTAL]
        
        df = df.dropna(subset=[col_name_store])
        df.iloc[:, COL_IDX_TOTAL] = pd.to_numeric(df.iloc[:, COL_IDX_TOTAL], errors='coerce').fillna(0)
        
        # ランク列の空白削除（S, A, B...）
        df.iloc[:, COL_IDX_RANK] = df.iloc[:, COL_IDX_RANK].astype(str).str.strip()

        # 詳細項目の列位置を特定
        found_items = {} 
        for item in TARGET_ITEM_NAMES:
            if item in df.columns:
                found_items[item] = df.columns.get_loc(item)

        # --- 2. 店舗選択 ---
        st.markdown("---")
        stores_list = sorted(df.iloc[:, COL_IDX_STORE].astype(str).unique().tolist())
        
        col_main_1, col_main_2 = st.columns([1, 2])
        
        with col_main_1:
            selected_store = st.selectbox("📍 分析する店舗を選択", stores_list)
            
            # 自店舗データ取得
            my_row = df[df.iloc[:, COL_IDX_STORE] == selected_store].iloc[0]
            my_current_rank = my_row.iloc[COL_IDX_RANK]
            my_current_pt = my_row.iloc[COL_IDX_TOTAL]

        # --- 3. 目標設定（ランク選択方式） ---
        with col_main_2:
            st.info(f"店舗: **{selected_store}** （現在: {my_current_rank}ランク / {int(my_current_pt):,} pt）")
            
            # ランクのリストを作成（S, A, B...）
            unique_ranks = sorted(df.iloc[:, COL_IDX_RANK].unique().tolist())
            
            # 目標ランク選択
            st.markdown("##### 🎯 目標ランク設定")
            target_rank = st.selectbox("目指すランクを選択してください", unique_ranks, index=0)
            
            # 選択されたランクの平均ポイントを計算
            target_rank_df = df[df.iloc[:, COL_IDX_RANK] == target_rank]
            
            if len(target_rank_df) > 0:
                target_avg_pt = target_rank_df.iloc[:, COL_IDX_TOTAL].mean()
            else:
                target_avg_pt = 0
            
            gap = target_avg_pt - my_current_pt

            # ギャップ表示
            c_res1, c_res2 = st.columns(2)
            c_res1.metric(f"目標（{target_rank}平均）", f"{int(target_avg_pt):,} pt")
            
            if gap <= 0:
                c_res2.success(f"🎉 達成圏内（+ {abs(int(gap)):,} pt）")
            else:
                c_res2.error(f"あと **{int(gap):,} pt** 不足")

        # --- 4. 弱点分析＆アクションプラン ---
        if gap > 0:
            st.markdown("---")
            st.subheader(f"📊 {target_rank}ランク平均に追いつくための重点 5項目")
            st.markdown(f"目標ランク（{target_rank}）の平均達成率に届いていない項目を抽出し、**目標率に到達した場合のポイント増**を試算します。")

            # 分析データの作成
            analysis_list = []

            for item_name, base_idx in found_items.items():
                try:
                    # 自店データ
                    my_rate = pd.to_numeric(my_row.iloc[base_idx + OFFSET_RATE], errors='coerce') or 0 # ①現在の達成率
                    my_target_vol = pd.to_numeric(my_row.iloc[base_idx + OFFSET_TARGET], errors='coerce') or 0 # 目標数（④計算用）
                    my_actual_vol = pd.to_numeric(my_row.iloc[base_idx + OFFSET_ACTUAL], errors='coerce') or 0 # 実績数（④計算用）
                    unit_pt = pd.to_numeric(my_row.iloc[base_idx + OFFSET_UNIT_PT], errors='coerce') or 0 # 係数/単価
                    
                    # 目標ランク（SやAなど）の平均達成率を計算 → ②目標達成率とする
                    # 該当ランクの店舗の「達成率列」の平均をとる
                    rank_rate_col_idx = base_idx + OFFSET_RATE
                    rank_avg_rate = target_rank_df.iloc[:, rank_rate_col_idx].apply(pd.to_numeric, errors='coerce').mean()
                    
                    # ②目標達成率（ランク平均が自分の実績より低い場合は、現状維持=目標とする）
                    target_rate = max(rank_avg_rate, my_rate)
                    
                    # 達成率のギャップ
                    rate_gap = target_rate - my_rate
                    
                    if rate_gap > 0 and unit_pt > 0:
                        # ④残数（目標件数から算出した②に対しての不足数）
                        # 計算式： (目標率 - 現在率) / 100 * 分母(目標数)
                        # ※もし「分母」が目標数(Target)列にある場合
                        needed_vol = (rate_gap / 100) * my_target_vol
                        needed_vol = math.ceil(needed_vol) # 切り上げ
                        
                        # ③上がるポイント (不足数 * 係数)
                        gain_pt = needed_vol * unit_pt
                        
                        # ⑤日割り
                        daily_vol = needed_vol / remaining_days

                        analysis_list.append({
                            "name": item_name,
                            "current_rate": my_rate,        # ①
                            "target_rate": target_rate,     # ②
                            "gain_pt": gain_pt,             # ③
                            "needed_vol": needed_vol,       # ④
                            "daily_vol": daily_vol,         # ⑤
                            "unit_pt": unit_pt              # 参考：係数
                        })
                except Exception as e:
                    pass

            # ③獲得ポイント（インパクト）が大きい順にソートして5つ表示
            top_5_items = sorted(analysis_list, key=lambda x: x['gain_pt'], reverse=True)[:5]

            # --- テーブル表示 ---
            # ヘッダー
            h_cols = st.columns([2, 1.5, 1.5, 1.5, 1.5, 1.5])
            h_cols[0].markdown("**項目名 (係数)**")
            h_cols[1].markdown("**①現在率**")
            h_cols[2].markdown(f"**②{target_rank}平均率**")
            h_cols[3].markdown("**③獲得Pt**")
            h_cols[4].markdown("**④不足数**")
            h_cols[5].markdown(f"**⑤日割り(残{remaining_days}日)**")

            total_gain = 0
            
            for item in top_5_items:
                cols = st.columns([2, 1.5, 1.5, 1.5, 1.5, 1.5])
                
                # 0. 項目名
                cols[0].markdown(f"**{item['name']}** <small>(Pt:{int(item['unit_pt'])})</small>", unsafe_allow_html=True)
                
                # 1. 現在率
                cols[1].write(f"{item['current_rate']:.1f}%")
                
                # 2. 目標率（ランク平均）
                cols[2].write(f"{item['target_rate']:.1f}%")
                
                # 3. 獲得ポイント
                cols[3].markdown(f":red[**+ {int(item['gain_pt']):,}**]")
                
                # 4. 残数
                cols[4].write(f"{int(item['needed_vol']):,} 件")
                
                # 5. 日割り
                cols[5].write(f"**{item['daily_vol']:.1f}** 件/日")
                
                total_gain += item['gain_pt']
                st.divider()

            # --- 結果まとめ ---
            st.markdown("### 📝 シミュレーション結果")
            c_final1, c_final2 = st.columns(2)
            
            c_final1.metric("目標までの不足分", f"{int(gap):,} pt")
            
            remaining_gap = gap - total_gain
            
            if remaining_gap <= 0:
                c_final2.success(f"この5項目で + {int(total_gain):,} pt 獲得し、目標達成可能です！")
            else:
                c_final2.warning(f"5項目で + {int(total_gain):,} pt ですが、まだ {int(remaining_gap):,} pt 足りません。")
                
        else:
            st.balloons()
            st.success("現在、目標ランクの平均値を上回っています！")

    except Exception as e:
        st.error("エラーが発生しました。")
        st.write(f"詳細: {e}")
        st.info("Excelの形式（17行目タイトル、列の並び）が正しいか確認してください。")

else:
    st.info("👈 サイドバーからExcelファイルをアップロードしてください。")
