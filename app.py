import streamlit as st
import pandas as pd
import math
from datetime import datetime
import calendar
import re

# --- ページ設定 ---
st.set_page_config(page_title="店舗目標達成シミュレーター", layout="wide")
st.title("🏆 店舗目標達成シミュレーター")
st.markdown("C13セルの日付基準で残り日数を自動計算し、目標ランク達成のためのアクションプランを提示します。")

# --- 設定: 表示する店舗リスト（指定） ---
ALLOWED_STORES = [
    "町田", "矢野口", "西八王子", "田無ｱｽﾀ", "狛江", 
    "東久留米前沢", "MINANO府中･分倍河原", "八王子", "ﾓﾘﾀｳﾝ昭島", 
    "八王子楢原", "河辺青梅街道", "花小金井", "ｺｺﾘｱ多摩ｾﾝﾀｰ", 
    "東大和向原", "ｲﾄｰﾖｰｶﾄﾞｰ南大沢", "ｸﾞﾘﾅｰﾄﾞ永山", "京王八王子駅前"
]

# --- 設定: 列などの定義 ---
TARGET_ITEM_NAMES = [
    "UPG", "SB機種変更", "固定純新規", "固定新規ALL", "Air機変", 
    "ｱｸｾｻﾘｰ売上", "IDﾌﾟﾛﾃｸｼｮﾝ", "PayPayｶｰﾄﾞ", "PayPayｶｰﾄﾞｺﾞｰﾙﾄﾞ", 
    "DMMﾌﾟﾚﾐｱﾑ", "LINE", "おうちでんき", "ﾀﾌﾞﾚｯﾄ総販", "ﾌﾙﾌﾟﾗﾝ", "ﾗｲﾄﾌﾟﾗﾝ"
]

# 列の相対位置（項目名の列=0とした場合）
# 右に 順位・目標・実績・着地・達成率 が並んでいる
OFFSET_RANK_VAL = 1  # 順位
OFFSET_TARGET = 2    # 目標
OFFSET_ACTUAL = 3    # 実績
OFFSET_LANDING = 4   # 着地
OFFSET_RATE = 5      # 達成率

# 固定位置情報（Excelの行列）
COEFF_ROW_NUM = 9   # 係数が記載されている行（9行目）
HEADER_ROW_NUM = 17 # ヘッダー行（17行目）
COL_IDX_STORE = 17  # R列
COL_IDX_RANK = 18   # S列
COL_IDX_TOTAL = 19  # T列

# --- 1. データ読み込みと日付判定 ---
st.sidebar.header("⚙️ 設定")
uploaded_file = st.sidebar.file_uploader("ランキングデータ（Excel）", type=["xlsx", "xls"])

remaining_days = 1 # 初期値

if uploaded_file is not None:
    try:
        # --- A. 日付の取得 (C13セル) ---
        try:
            date_df = pd.read_excel(uploaded_file, header=None, usecols="C", skiprows=12, nrows=1)
            raw_text = str(date_df.iloc[0, 0])
            
            match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', raw_text)
            
            if match:
                date_str = match.group(1)
                base_date = pd.to_datetime(date_str, errors='coerce')
                
                if pd.notnull(base_date):
                    last_day = calendar.monthrange(base_date.year, base_date.month)[1]
                    calc_days = max(1, last_day - base_date.day)
                    st.sidebar.success(f"📅 基準日: {base_date.strftime('%Y/%m/%d')}")
                    remaining_days = st.sidebar.number_input("今月の残り日数", min_value=1, value=calc_days, help="C13セルの日付から自動計算")
                else:
                    raise ValueError("日付変換失敗")
            else:
                st.sidebar.warning(f"C13セルから日付が見つかりませんでした。")
                remaining_days = st.sidebar.number_input("今月の残り日数", min_value=1, value=10)

        except Exception as e:
            st.sidebar.error(f"日付読み取りエラー: {e}")
            remaining_days = st.sidebar.number_input("今月の残り日数", min_value=1, value=10)

        # ファイルポインタを戻す
        uploaded_file.seek(0)

        # --- B. 係数行（9行目）の読み込み ---
        # 9行目だけを読み込み（列位置の基準とするため、ヘッダーなしで読む）
        coeff_df = pd.read_excel(uploaded_file, header=None, skiprows=COEFF_ROW_NUM - 1, nrows=1)
        
        uploaded_file.seek(0)

        # --- C. メインデータの読み込み（17行目ヘッダー） ---
        df = pd.read_excel(uploaded_file, header=HEADER_ROW_NUM - 1)
        df.columns = df.columns.astype(str).str.strip().str.replace('　', '')

        # 基本情報の抽出
        col_name_store = df.columns[COL_IDX_STORE]
        
        df = df.dropna(subset=[col_name_store])
        df.iloc[:, COL_IDX_TOTAL] = pd.to_numeric(df.iloc[:, COL_IDX_TOTAL], errors='coerce').fillna(0)
        df.iloc[:, COL_IDX_RANK] = df.iloc[:, COL_IDX_RANK].astype(str).str.strip()

        # 詳細項目の列位置を特定
        found_items = {} 
        for item in TARGET_ITEM_NAMES:
            if item in df.columns:
                found_items[item] = df.columns.get_loc(item)

        # --- 2. 店舗選択 ---
        st.markdown("---")
        
        excel_stores = df.iloc[:, COL_IDX_STORE].astype(str).unique().tolist()
        available_stores = [s for s in excel_stores if s in ALLOWED_STORES]
        
        if not available_stores:
            available_stores = sorted(excel_stores)
        else:
            available_stores = sorted(available_stores)

        col_main_1, col_main_2 = st.columns([1, 2])
        
        with col_main_1:
            selected_store = st.selectbox("📍 分析する店舗を選択", available_stores)
            
            my_row = df[df.iloc[:, COL_IDX_STORE] == selected_store].iloc[0]
            my_current_rank = my_row.iloc[COL_IDX_RANK]
            my_current_pt = my_row.iloc[COL_IDX_TOTAL]

        # --- 3. 目標設定 ---
        with col_main_2:
            st.info(f"店舗: **{selected_store}** （現在: {my_current_rank}ランク / {int(my_current_pt):,} pt）")
            
            unique_ranks = sorted(df.iloc[:, COL_IDX_RANK].unique().tolist())
            
            st.markdown("##### 🎯 目標ランク設定")
            target_rank = st.selectbox("目指すランクを選択してください", unique_ranks, index=0)
            
            target_rank_df = df[df.iloc[:, COL_IDX_RANK] == target_rank]
            if len(target_rank_df) > 0:
                target_avg_pt = target_rank_df.iloc[:, COL_IDX_TOTAL].mean()
            else:
                target_avg_pt = 0
            
            gap = target_avg_pt - my_current_pt

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

            analysis_list = []

            for item_name, col_idx in found_items.items():
                try:
                    # 【ここが変更点】
                    # 1. 係数: 9行目 (coeff_df) の 同じ列 (col_idx) を参照
                    unit_pt_val = coeff_df.iloc[0, col_idx]
                    unit_pt = pd.to_numeric(unit_pt_val, errors='coerce') or 0
                    
                    # 2. 実績・目標・率: メインデータ (df) の 右隣の列 (+2, +5) を参照
                    my_rate = pd.to_numeric(my_row.iloc[col_idx + OFFSET_RATE], errors='coerce') or 0
                    my_target_vol = pd.to_numeric(my_row.iloc[col_idx + OFFSET_TARGET], errors='coerce') or 0
                    
                    # 3. 目標ランク平均率 (dfの右隣の列 +5)
                    rank_rate_col_idx = col_idx + OFFSET_RATE
                    rank_avg_rate = target_rank_df.iloc[:, rank_rate_col_idx].apply(pd.to_numeric, errors='coerce').mean()
                    
                    target_rate = max(rank_avg_rate, my_rate)
                    rate_gap = target_rate - my_rate
                    
                    # 係数が0でも、rate_gapがあればリストに入れる
                    if rate_gap > 0:
                        needed_vol = (rate_gap / 100) * my_target_vol
                        needed_vol = math.ceil(needed_vol)
                        gain_pt = needed_vol * unit_pt
                        daily_vol = needed_vol / remaining_days

                        analysis_list.append({
                            "name": item_name,
                            "current_rate": my_rate,
                            "target_rate": target_rate,
                            "gain_pt": gain_pt,
                            "needed_vol": needed_vol,
                            "daily_vol": daily_vol,
                            "unit_pt": unit_pt
                        })
                except Exception as e:
                    pass

            # 獲得Ptが多い順にソート
            top_5_items = sorted(analysis_list, key=lambda x: x['gain_pt'], reverse=True)[:5]

            if not top_5_items:
                st.warning("改善可能な項目が見つかりませんでした。（すべての項目で平均を上回っています）")
            else:
                # テーブル表示
                h_cols = st.columns([2, 1.5, 1.5, 1.5, 1.5, 1.5])
                h_cols[0].markdown("**項目名 (係数)**")
                h_cols[1].markdown("**①現在率**")
                h_cols[2].markdown(f"**②{target_rank}平均率**")
                h_cols[3].markdown("**③獲得Pt**")
                h_cols[4].markdown("**④不足数**")
                h_cols[5].markdown(f"**⑤日割り(残{int(remaining_days)}日)**")

                total_gain = 0
                
                for item in top_5_items:
                    cols = st.columns([2, 1.5, 1.5, 1.5, 1.5, 1.5])
                    
                    # 係数が0の場合は警告色
                    pt_val = int(item['unit_pt'])
                    pt_display = f"{pt_val}"
                    if pt_val == 0:
                         pt_display = "⚠️0 (設定確認)"
                    
                    cols[0].markdown(f"**{item['name']}** <br><small>係数: {pt_display}</small>", unsafe_allow_html=True)
                    cols[1].write(f"{item['current_rate']:.1f}%")
                    cols[2].write(f"{item['target_rate']:.1f}%")
                    
                    # 獲得Pt
                    gain_disp = f"+ {int(item['gain_pt']):,}"
                    if pt_val == 0:
                        cols[3].write(gain_disp)
                    else:
                        cols[3].markdown(f":red[**{gain_disp}**]")
                        
                    cols[4].write(f"{int(item['needed_vol']):,} 件")
                    cols[5].write(f"**{item['daily_vol']:.1f}** 件/日")
                    
                    total_gain += item['gain_pt']
                    st.divider()

                st.markdown("### 📝 シミュレーション結果")
                c_final1, c_final2 = st.columns(2)
                c_final1.metric("目標までの不足分", f"{int(gap):,} pt")
                
                remaining_gap = gap - total_gain
                
                if total_gain == 0 and len(top_5_items) > 0:
                     c_final2.warning("獲得Ptが0になっています。9行目の係数が正しく読み込まれているか確認してください。")
                elif remaining_gap <= 0:
                    c_final2.success(f"この5項目で + {int(total_gain):,} pt 獲得し、目標達成可能です！")
                else:
                    c_final2.warning(f"5項目で + {int(total_gain):,} pt ですが、まだ {int(remaining_gap):,} pt 足りません。")
                
        else:
            st.balloons()
            st.success("現在、目標ランクの平均値を上回っています！")

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
        st.info("Excelの形式を確認してください。")

else:
    st.info("👈 サイドバーからExcelファイルをアップロードしてください。")

