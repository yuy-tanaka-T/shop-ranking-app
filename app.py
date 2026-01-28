import streamlit as st
import pandas as pd
import math
from datetime import datetime
import calendar
import re

# --- ページ設定 ---
st.set_page_config(page_title="店舗目標達成シミュレーター", layout="wide")
st.title("🏆 店舗目標達成シミュレーター")
st.markdown("C13の日付で残り日数を計算し、**全社平均(11行目)**と比較して不足分を埋めるアクションプランを提示します。")

# --- 設定: 読み込むシート名 ---
SHEET_NAME = "総合Ranking_達成率"

# --- 設定: 表示する店舗リスト ---
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
OFFSET_TARGET = 2    # 目標
OFFSET_ACTUAL = 3    # 実績
OFFSET_RATE = 5      # 達成率

# 固定位置情報（Excelの行列・0始まりのインデックス）
ROW_IDX_COEFF = 8      # 9行目（係数）
ROW_IDX_AVG = 10       # 11行目（全社平均）
ROW_IDX_DATE = 12      # 13行目（日付）
ROW_IDX_ITEM_NAME = 15 # 16行目（項目名）
ROW_IDX_HEADER = 16    # 17行目（ヘッダー）

COL_IDX_STORE = 17  # R列
COL_IDX_RANK = 18   # S列
COL_IDX_TOTAL = 19  # T列

# --- 1. データ読み込み ---
st.sidebar.header("⚙️ 設定")
uploaded_file = st.sidebar.file_uploader("ランキングデータ（Excel）", type=["xlsx", "xls"])

remaining_days = 1 

if uploaded_file is not None:
    try:
        # --- A. メタデータ読み込み（上部20行分） ---
        try:
            meta_df = pd.read_excel(uploaded_file, sheet_name=SHEET_NAME, header=None, nrows=20)
        except ValueError:
            st.error(f"エラー: シート名「{SHEET_NAME}」が見つかりません。")
            st.stop()

        # 1. 日付の取得 (C13)
        try:
            raw_text = str(meta_df.iloc[ROW_IDX_DATE, 2])
            match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', raw_text)
            
            if match:
                date_str = match.group(1)
                base_date = pd.to_datetime(date_str, errors='coerce')
                
                if pd.notnull(base_date):
                    last_day = calendar.monthrange(base_date.year, base_date.month)[1]
                    calc_days = max(1, last_day - base_date.day)
                    st.sidebar.success(f"📅 基準日: {base_date.strftime('%Y/%m/%d')}")
                    remaining_days = st.sidebar.number_input("今月の残り日数", min_value=1, value=calc_days)
                else:
                    raise ValueError
            else:
                st.sidebar.warning("C13セルから日付が見つかりませんでした。")
                remaining_days = st.sidebar.number_input("今月の残り日数", min_value=1, value=10)
        except:
            remaining_days = st.sidebar.number_input("今月の残り日数", min_value=1, value=10)

        # 2. 項目名の列位置を特定 (16行目)
        item_row = meta_df.iloc[ROW_IDX_ITEM_NAME]
        found_items = {} 
        for col_idx, cell_val in enumerate(item_row):
            val_str = str(cell_val).strip().replace('　', '')
            if val_str in TARGET_ITEM_NAMES:
                found_items[val_str] = col_idx

        # --- B. メインデータの読み込み ---
        uploaded_file.seek(0)
        df = pd.read_excel(uploaded_file, sheet_name=SHEET_NAME, header=ROW_IDX_HEADER)
        df.columns = df.columns.astype(str).str.strip().str.replace('　', '')

        # 基本情報の抽出
        col_name_store = df.columns[COL_IDX_STORE]
        df = df.dropna(subset=[col_name_store])
        df.iloc[:, COL_IDX_TOTAL] = pd.to_numeric(df.iloc[:, COL_IDX_TOTAL], errors='coerce').fillna(0)
        df.iloc[:, COL_IDX_RANK] = df.iloc[:, COL_IDX_RANK].astype(str).str.strip()

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
            target_avg_pt = target_rank_df.iloc[:, COL_IDX_TOTAL].mean() if len(target_rank_df) > 0 else 0
            
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
            st.subheader("📊 平均比改善 重点 5項目")
            st.markdown("全社平均達成率（11行目）を下回っている項目を抽出します。")

            analysis_list = []
            debug_data = []

            for item_name, col_idx in found_items.items():
                try:
                    # 1. 係数 (9行目)
                    unit_pt_val = meta_df.iloc[ROW_IDX_COEFF, col_idx]
                    unit_pt = pd.to_numeric(unit_pt_val, errors='coerce') or 0
                    
                    # 2. 全社平均 (11行目, 達成率列 = 項目列 + 5)
                    avg_rate_col_idx = col_idx + OFFSET_RATE
                    avg_rate_val = meta_df.iloc[ROW_IDX_AVG, avg_rate_col_idx]
                    company_avg_rate = pd.to_numeric(avg_rate_val, errors='coerce') or 0

                    # 3. 自店データ (データ行, 達成率列 = 項目列 + 5)
                    my_rate = pd.to_numeric(my_row.iloc[col_idx + OFFSET_RATE], errors='coerce') or 0
                    my_target_vol = pd.to_numeric(my_row.iloc[col_idx + OFFSET_TARGET], errors='coerce') or 0
                    
                    # 4. ギャップ計算（単位自動判定）
                    rate_gap = company_avg_rate - my_rate
                    
                    # 【重要修正】データが「91」なのか「0.91」なのかで計算を変える
                    # 平均値が 2.0 (200%) を超える場合は「整数(%)」とみなす、それ以下は「小数」とみなす
                    is_percentage_integer = (company_avg_rate > 5) 
                    
                    # 表示用の補正（%表示のため）
                    disp_my_rate = my_rate if is_percentage_integer else my_rate * 100
                    disp_avg_rate = company_avg_rate if is_percentage_integer else company_avg_rate * 100
                    
                    debug_data.append({
                        "項目": item_name,
                        "自店(生)": my_rate,
                        "平均(生)": company_avg_rate,
                        "目標": my_target_vol,
                        "係数": unit_pt
                    })

                    if rate_gap > 0:
                        # 整数(91)なら 100で割る、小数(0.91)なら そのまま差分を使う
                        factor = (rate_gap / 100) if is_percentage_integer else rate_gap
                        
                        needed_vol = factor * my_target_vol
                        needed_vol = math.ceil(needed_vol)
                        
                        gain_pt = needed_vol * unit_pt
                        daily_vol = needed_vol / remaining_days

                        analysis_list.append({
                            "name": item_name,
                            "current_rate": disp_my_rate,
                            "target_rate": disp_avg_rate,
                            "gain_pt": gain_pt,
                            "needed_vol": needed_vol,
                            "daily_vol": daily_vol,
                            "unit_pt": unit_pt
                        })
                except Exception as e:
                    pass

            top_5_items = sorted(analysis_list, key=lambda x: x['gain_pt'], reverse=True)[:5]

            if not top_5_items:
                st.warning("平均を下回っている項目はありません。")
                with st.expander("詳細デバッグ"):
                    st.dataframe(pd.DataFrame(debug_data))
            else:
                # テーブル表示
                h_cols = st.columns([2, 1.5, 1.5, 1.5, 1.5, 1.5])
                h_cols[0].markdown("**項目名 (係数)**")
                h_cols[1].markdown("**①現在率**")
                h_cols[2].markdown("**②全社平均**")
                h_cols[3].markdown("**③獲得Pt**")
                h_cols[4].markdown("**④不足数**")
                h_cols[5].markdown(f"**⑤日割り(残{int(remaining_days)}日)**")

                total_gain = 0
                for item in top_5_items:
                    cols = st.columns([2, 1.5, 1.5, 1.5, 1.5, 1.5])
                    
                    pt_val = int(item['unit_pt'])
                    pt_display = f"{pt_val}" if pt_val > 0 else "⚠️0"
                    
                    cols[0].markdown(f"**{item['name']}** <br><small>係数: {pt_display}</small>", unsafe_allow_html=True)
                    cols[1].write(f"{item['current_rate']:.1f}%")
                    cols[2].write(f"{item['target_rate']:.1f}%")
                    
                    gain_disp = f"+ {int(item['gain_pt']):,}"
                    if pt_val == 0: cols[3].write(gain_disp)
                    else: cols[3].markdown(f":red[**{gain_disp}**]")
                        
                    cols[4].write(f"{int(item['needed_vol']):,} 件")
                    cols[5].write(f"**{item['daily_vol']:.1f}** 件/日")
                    total_gain += item['gain_pt']
                    st.divider()

                st.markdown("### 📝 シミュレーション結果")
                c_final1, c_final2 = st.columns(2)
                c_final1.metric("目標ランクまでの不足分", f"{int(gap):,} pt")
                
                remaining_gap = gap - total_gain
                if remaining_gap <= 0:
                    c_final2.success(f"平均並みに改善で + {int(total_gain):,} pt！ 達成可能です！")
                else:
                    c_final2.warning(f"平均並みに改善で + {int(total_gain):,} pt ですが、まだ {int(remaining_gap):,} pt 不足。")

        else:
            st.balloons()
            st.success("現在、目標ランクの平均値を上回っています！")

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")

else:
    st.info("👈 サイドバーからExcelファイルをアップロードしてください。")

