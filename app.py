import streamlit as st
import pandas as pd

# --- ページ設定 ---
st.set_page_config(page_title="店舗目標達成シミュレーター", layout="wide")
st.title("🏆 店舗目標達成シミュレーター")
st.markdown("基本情報(R,S,T列)は固定位置から、詳細項目は自動検索して分析します。")

# --- 設定: 検索する項目名リスト ---
# 詳細項目は列がずれてもいいように名前で探します
TARGET_ITEM_NAMES = [
    "UPG",
    "SB機種変更",
    "固定純新規",
    "固定新規ALL",
    "Air機変",
    "アクセサリー売上",
    "IDﾌﾟﾛﾃｸｼｮﾝ",      
    "PayPayｶｰﾄﾞ",     
    "PayPayｶｰﾄﾞｺﾞｰﾙﾄﾞ", 
    "DMMﾌﾟﾚﾐｱﾑ",      
    "LINE",
    "おうちでんき",
    "ﾀﾌﾞﾚｯﾄ総販",      
    "ﾌﾙﾌﾟﾗﾝ",         
    "ﾗｲﾄﾌﾟﾗﾝ"         
]

# データの並び順（項目名の列を基準「0」とした時の位置）
# 0: Pt, 1: 順位, 2: 目標, 3: 実績, 4: 着地, 5: 達成率, 6: 1件Pt
OFFSET_PT = 0
OFFSET_ACTUAL = 3
OFFSET_RATE = 5
OFFSET_UNIT_PT = 6

# --- 重要変更箇所：基本情報の固定位置設定 ---
# Excelの17行目（プログラム上はindex 16）
HEADER_ROW_NUM = 17 

# 列番号（A=0, B=1, ... R=17, S=18, T=19）
COL_IDX_STORE = 17  # R列
COL_IDX_RANK = 18   # S列
COL_IDX_TOTAL = 19  # T列

# --- 1. データ読み込み ---
uploaded_file = st.sidebar.file_uploader("ランキングデータ（Excel）をアップロード", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        # 17行目をヘッダーとして読み込む（index = 16）
        df = pd.read_excel(uploaded_file, header=HEADER_ROW_NUM - 1)
        
        # 列名の空白除去
        df.columns = df.columns.astype(str).str.strip()

        # --- 基本情報の読み込み（列位置固定） ---
        try:
            # 指定された列番号（R, S, T）が範囲内かチェック
            if df.shape[1] <= COL_IDX_TOTAL:
                st.error(f"Excelの列数が足りません。T列（{COL_IDX_TOTAL+1}列目）までデータがあるか確認してください。")
                st.stop()
            
            # 列番号(iloc)で強制的に取得
            # 列名が変わっても「場所」で抜きます
            col_name_store = df.columns[COL_IDX_STORE] # R列の名前
            col_name_rank = df.columns[COL_IDX_RANK]   # S列の名前
            col_name_total = df.columns[COL_IDX_TOTAL] # T列の名前
            
            # データクリーニング（店舗名がない行を削除）
            df = df.dropna(subset=[col_name_store])
            
            # 総合ポイントを数値化（エラー回避）
            df.iloc[:, COL_IDX_TOTAL] = pd.to_numeric(df.iloc[:, COL_IDX_TOTAL], errors='coerce').fillna(0)

            st.toast(f"✅ 読み込み成功: {len(df)} 店舗")
            
        except Exception as e:
            st.error(f"基本データ（R, S, T列）の読み込みに失敗しました。詳細: {e}")
            st.stop()

        # --- 2. 詳細項目の列位置特定＆全社平均計算 ---
        
        found_items = {} # {項目名: 列番号}
        avg_rates = {}   # {項目名: 全社平均達成率}

        for item in TARGET_ITEM_NAMES:
            # Excelの全列名から、この項目名を探す
            if item in df.columns:
                base_idx = df.columns.get_loc(item)
                found_items[item] = base_idx
                
                # 平均達成率の計算（基準列 + 5列目）
                try:
                    rate_col_idx = base_idx + OFFSET_RATE
                    if rate_col_idx < len(df.columns):
                        rate_series = pd.to_numeric(df.iloc[:, rate_col_idx], errors='coerce')
                        avg_rates[item] = rate_series.mean()
                except:
                    pass

        # --- 3. 店舗選択と分析 ---
        st.markdown("---")
        
        # 店舗リスト作成（R列のデータを使う）
        stores_list = sorted(df.iloc[:, COL_IDX_STORE].astype(str).unique().tolist())
        
        col_sel_1, col_sel_2 = st.columns([1, 2])
        with col_sel_1:
            selected_store = st.selectbox("📍 分析する店舗を選択", stores_list)
        
        # 自店舗データ行を取得
        my_row = df[df.iloc[:, COL_IDX_STORE] == selected_store].iloc[0]
        
        # 基本情報取得（S列, T列）
        my_rank_val = my_row.iloc[COL_IDX_RANK]
        my_total_pt = my_row.iloc[COL_IDX_TOTAL]
        
        with col_sel_2:
            st.info(f"店舗名: **{selected_store}**")
            c1, c2 = st.columns(2)
            c1.metric("現在のRank (S列)", f"{my_rank_val}")
            c2.metric("現在の総合P (T列)", f"{int(my_total_pt):,} pt")

        # --- 4. 目標設定 ---
        st.markdown("### 🎯 目標設定")
        
        target_point = st.number_input("目標総合ポイント", value=int(my_total_pt * 1.1))
        gap = target_point - my_total_pt

        if gap <= 0:
            st.success("🎉 目標達成済みです！")
        else:
            st.warning(f"目標まであと **{int(gap):,} pt** 必要です。")

            # --- 5. 弱点分析（ワースト5抽出） ---
            st.markdown("---")
            st.subheader("📊 重点改善 5項目 (対平均 乖離分析)")
            st.caption("全社平均と比較して、達成率の乖離が大きい（伸びしろがある）項目を表示します。")

            analysis_list = []
            
            for item_name, base_idx in found_items.items():
                try:
                    val_pt = pd.to_numeric(my_row.iloc[base_idx + OFFSET_PT], errors='coerce') or 0
                    val_actual = pd.to_numeric(my_row.iloc[base_idx + OFFSET_ACTUAL], errors='coerce') or 0
                    val_rate = pd.to_numeric(my_row.iloc[base_idx + OFFSET_RATE], errors='coerce') or 0
                    val_unit_pt = pd.to_numeric(my_row.iloc[base_idx + OFFSET_UNIT_PT], errors='coerce') or 0
                    
                    avg_rate = avg_rates.get(item_name, 0)
                    diff = val_rate - avg_rate
                    
                    analysis_list.append({
                        "name": item_name,
                        "rate": val_rate,
                        "avg_rate": avg_rate,
                        "unit_pt": val_unit_pt,
                        "diff": diff
                    })
                except:
                    pass

            # ワースト5抽出
            worst_5 = sorted(analysis_list, key=lambda x: x['diff'])[:5]

            # --- 6. アクションプラン ---
            h1, h2, h3, h4, h5 = st.columns([2, 1.5, 1.5, 2, 2])
            h1.markdown("**項目名**")
            h2.markdown("**達成率 (自店/平均)**")
            h3.markdown("**1件Pt (実績)**")
            h4.markdown("**追加獲得計画**")
            h5.markdown("**獲得見込みPt**")

            total_plan_points = 0
            
            for item in worst_5:
                name = item['name']
                unit_pt = item['unit_pt']
                rate_disp = f"{item['rate']:.1f}% / {item['avg_rate']:.1f}%"
                
                with st.container():
                    c1, c2, c3, c4, c5 = st.columns([2, 1.5, 1.5, 2, 2])
                    c1.markdown(f"**{name}**")
                    c2.caption(rate_disp)
                    if item['diff'] < 0:
                        c2.progress(min(max(item['rate']/150, 0), 1.0))
                    
                    c3.write(f"{int(unit_pt):,} pt")
                    
                    with c4:
                        add_num = st.number_input(f"あと何件？", min_value=0, value=1, key=f"plan_{name}", label_visibility="collapsed")
                    
                    add_pt = add_num * unit_pt
                    c5.metric("見込み", f"+ {int(add_pt):,}")
                    total_plan_points += add_pt
                    st.divider()

            # --- 結果 ---
            st.markdown("### 📝 シミュレーション結果")
            r1, r2 = st.columns(2)
            with r1:
                st.metric("必要ポイント", f"{int(gap):,} pt")
            with r2:
                remaining = gap - total_plan_points
                if remaining <= 0:
                    st.success(f"合計 + {int(total_plan_points):,} pt (達成予定！)")
                else:
                    st.error(f"合計 + {int(total_plan_points):,} pt (あと {int(remaining):,} pt 不足)")

    except Exception as e:
        st.error("エラーが発生しました。")
        st.write(f"詳細: {e}")
        st.info("Excelの17行目にタイトルがあり、R, S, T列にデータがあるか確認してください。")

else:
    st.info("👈 左側のメニューからExcelファイルをアップロードしてください。")

