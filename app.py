import streamlit as st
import pandas as pd

# --- ページ設定 ---
st.set_page_config(page_title="店舗目標達成シミュレーター", layout="wide")
st.title("🏆 店舗目標達成シミュレーター")
st.markdown("Excelの項目名を自動検索し、列がずれても柔軟に対応して分析します。")

# --- 設定: 検索する項目名リスト ---
# ※ここに記載された名前をExcelの16行目から探します
TARGET_ITEM_NAMES = [
    "UPG",
    "SB機種変更",
    "固定純新規",
    "固定新規ALL",
    "Air機変",
    "アクセサリー売上",
    "IDﾌﾟﾛﾃｸｼｮﾝ",      # 半角カナに注意
    "PayPayｶｰﾄﾞ",     # 半角カナ
    "PayPayｶｰﾄﾞｺﾞｰﾙﾄﾞ", # 半角カナ
    "DMMﾌﾟﾚﾐｱﾑ",      # 半角カナ
    "LINE",
    "おうちでんき",
    "ﾀﾌﾞﾚｯﾄ総販",      # 半角カナ
    "ﾌﾙﾌﾟﾗﾝ",         # 半角カナ
    "ﾗｲﾄﾌﾟﾗﾝ"         # 半角カナ
]

# データの並び順（項目名の列を基準「0」とした時の位置）
# 0: Pt, 1: 順位, 2: 目標, 3: 実績, 4: 着地, 5: 達成率, 6: 1件Pt
OFFSET_PT = 0
OFFSET_ACTUAL = 3
OFFSET_RATE = 5
OFFSET_UNIT_PT = 6

# 基本情報の列名（これらも探します）
COL_KEY_STORE = "部門名"
COL_KEY_RANK = "Rank"
COL_KEY_TOTAL = "総合P" # または「総合ﾎﾟｲﾝﾄ」など

# ヘッダー行番号（Excelの行番号）
HEADER_ROW_NUM = 16 

# --- 1. データ読み込み ---
uploaded_file = st.sidebar.file_uploader("ランキングデータ（Excel）をアップロード", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        # 16行目をヘッダーとして読み込む（Pythonのインデックスは0始まりなので 16-1=15）
        df = pd.read_excel(uploaded_file, header=HEADER_ROW_NUM - 1)
        
        # 列名の空白除去（" UPG " → "UPG"）
        df.columns = df.columns.astype(str).str.strip()

        # 必須列の検索
        # 店舗名などの列がどこにあるか探す
        try:
            col_store = df.columns.get_loc(COL_KEY_STORE)
            # Rankや総合Pが見つからない場合の予備検索
            col_rank_name = next((c for c in df.columns if "Rank" in c or "ランク" in c), None)
            col_total_name = next((c for c in df.columns if "総合" in c and ("P" in c or "ﾎﾟｲﾝﾄ" in c)), None)
            
            if col_rank_name is None or col_total_name is None:
                st.error(f"「{COL_KEY_RANK}」または「{COL_KEY_TOTAL}」列が見つかりません。Excelの項目名を確認してください。")
                st.stop()
                
            col_rank = df.columns.get_loc(col_rank_name)
            col_total = df.columns.get_loc(col_total_name)

        except KeyError:
            st.error(f"Excelの16行目に「{COL_KEY_STORE}」という列が見つかりません。")
            st.stop()

        # データクリーニング（店舗名がない行を削除）
        df = df.dropna(subset=[df.columns[col_store]])
        st.toast(f"✅ 読み込み成功: {len(df)} 店舗")

        # --- 2. 項目ごとの列位置を特定＆全社平均計算 ---
        
        found_items = {} # {項目名: 列番号(インデックス)}
        avg_rates = {}   # {項目名: 全社平均達成率}

        for item in TARGET_ITEM_NAMES:
            # Excelの列名リストの中に、この項目名があるか？
            if item in df.columns:
                # あればその列番号を記憶
                base_idx = df.columns.get_loc(item)
                found_items[item] = base_idx
                
                # 平均達成率の計算（基準列 + 5列目）
                try:
                    # 達成率列のデータを数値化
                    rate_col_idx = base_idx + OFFSET_RATE
                    if rate_col_idx < len(df.columns):
                        rate_series = pd.to_numeric(df.iloc[:, rate_col_idx], errors='coerce')
                        avg_rates[item] = rate_series.mean()
                except:
                    pass
            else:
                # 見つからない場合は警告を出さずにスキップ（またはログ出力）
                # st.warning(f"項目「{item}」が見つかりませんでした。")
                pass

        # --- 3. 店舗選択と分析 ---
        st.markdown("---")
        
        # 店舗リスト作成
        stores_list = sorted(df.iloc[:, col_store].astype(str).unique().tolist())
        
        col_sel_1, col_sel_2 = st.columns([1, 2])
        with col_sel_1:
            selected_store = st.selectbox("📍 分析する店舗を選択", stores_list)
        
        # 自店舗データ行を取得
        my_row = df[df.iloc[:, col_store] == selected_store].iloc[0]
        
        # 基本情報取得
        my_rank_val = my_row.iloc[col_rank]
        my_total_pt = pd.to_numeric(my_row.iloc[col_total], errors='coerce')
        
        with col_sel_2:
            st.info(f"店舗名: **{selected_store}**")
            c1, c2 = st.columns(2)
            c1.metric("現在のRank", f"{my_rank_val}")
            c2.metric("現在の総合P", f"{int(my_total_pt):,} pt")

        # --- 4. 目標設定 ---
        st.markdown("### 🎯 目標設定")
        
        # デフォルト目標（現在の1.1倍）
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
                    # 各種データの取得（列位置はずれる前提で計算）
                    # 0: Pt, 3: 実績, 5: 達成率, 6: 1件Pt
                    val_pt = pd.to_numeric(my_row.iloc[base_idx + OFFSET_PT], errors='coerce') or 0
                    val_actual = pd.to_numeric(my_row.iloc[base_idx + OFFSET_ACTUAL], errors='coerce') or 0
                    val_rate = pd.to_numeric(my_row.iloc[base_idx + OFFSET_RATE], errors='coerce') or 0
                    val_unit_pt = pd.to_numeric(my_row.iloc[base_idx + OFFSET_UNIT_PT], errors='coerce') or 0
                    
                    avg_rate = avg_rates.get(item_name, 0)
                    
                    # 乖離（自店 - 平均）※マイナスが大きいほど悪い
                    diff = val_rate - avg_rate
                    
                    analysis_list.append({
                        "name": item_name,
                        "rate": val_rate,
                        "avg_rate": avg_rate,
                        "unit_pt": val_unit_pt,
                        "diff": diff
                    })
                except Exception as e:
                    pass

            # 乖離が小さい順（マイナスが大きい順）にソートして5つ
            worst_5 = sorted(analysis_list, key=lambda x: x['diff'])[:5]

            # --- 6. アクションプラン ---
            
            # テーブルヘッダー
            h1, h2, h3, h4, h5 = st.columns([2, 1.5, 1.5, 2, 2])
            h1.markdown("**項目名**")
            h2.markdown("**達成率 (自店/平均)**")
            h3.markdown("**1件Pt (実績)**")
            h4.markdown("**追加獲得計画**")
            h5.markdown("**獲得見込みPt**")

            total_plan_points = 0
            
            for item in worst_5:
                # データの取り出し
                name = item['name']
                unit_pt = item['unit_pt']
                rate_disp = f"{item['rate']:.1f}% / {item['avg_rate']:.1f}%"
                
                with st.container():
                    c1, c2, c3, c4, c5 = st.columns([2, 1.5, 1.5, 2, 2])
                    
                    c1.markdown(f"**{name}**")
                    
                    # 達成率の可視化
                    c2.caption(rate_disp)
                    if item['diff'] < 0:
                        c2.progress(min(max(item['rate']/150, 0), 1.0))
                    
                    c3.write(f"{int(unit_pt):,} pt")
                    
                    # 計画入力
                    with c4:
                        add_num = st.number_input(f"あと何件？", min_value=0, value=1, key=f"plan_{name}", label_visibility="collapsed")
                    
                    # 計算
                    add_pt = add_num * unit_pt
                    c5.metric("見込み", f"+ {int(add_pt):,}")
                    
                    total_plan_points += add_pt
                    st.divider()

            # --- 最終結果 ---
            st.markdown("### 📝 シミュレーション結果")
            r1, r2 = st.columns(2)
            
            with r1:
                st.metric("必要ポイント", f"{int(gap):,} pt")
            
            with r2:
                remaining = gap - total_plan_points
                if remaining <= 0:
                    st.success(f"合計 + {int(total_plan_points):,} pt (達成予定！)")
                else:
                    st.error(f"合計 + {int(total_plan_points):,} pt (あと {int(remaining):,} pt 足りません)")

    except Exception as e:
        st.error("エラーが発生しました。")
        st.write(f"詳細: {e}")
        st.info("Excelの16行目に項目名が入っているか確認してください。")

else:
    st.info("👈 左側のメニューからExcelファイルをアップロードしてください。")
