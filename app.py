import streamlit as st
import pandas as pd
import math
from streamlit_gsheets import GSheetsConnection

# --- 設定：各商材の係数とカテゴリ ---
ITEMS_CONFIG = {
    "SB機種変更": {"col_actual": "SB機種変更実績", "coef": 8, "category": "HS"},
    "Y→S UP": {"col_actual": "UPG実績", "coef": 5, "category": "HS"},
    "SB他社MNP": {"col_actual": "SB他社MNP実績", "coef": 3, "category": "HS"},
    "YM他社MNP": {"col_actual": "YM他社MNP実績", "coef": 3, "category": "HS"},
    "固定純新規": {"col_actual": "固定純新規実績", "coef": 3, "category": "提案"},
    "Air機変": {"col_actual": "Air機変実績", "coef": 2, "category": "提案"},
    "PayPayカード": {"col_actual": "PayPayｶｰﾄﾞ実績", "coef": 2, "category": "提案"},
    "PayPayゴールド": {"col_actual": "PayPayｶｰﾄﾞｺﾞｰﾙﾄﾞ実績", "coef": 1, "category": "提案"},
    "アクセサリ売上(千円)": {"col_actual": "ｱｸｾｻﾘｰ売上実績", "coef": 0.3, "category": "提案"},
    "スマサポ(フル)": {"col_actual": "ﾌﾙﾌﾟﾗﾝ実績", "coef": 5, "category": "サポート"},
    "スマサポ(ライト)": {"col_actual": "ﾗｲﾄﾌﾟﾗﾝ実績", "coef": 1, "category": "サポート"},
}

# --- ランク定義（上位%） ---
RANK_THRESHOLDS = {
    "大型": {"S": 0.20, "A": 0.45, "B": 0.85, "C": 0.95, "D": 1.00},
    "中型": {"S": 0.20, "A": 0.40, "B": 0.60, "C": 0.80, "D": 1.00},
    "小型": {"S": 0.15, "A": 0.35, "B": 0.55, "C": 0.75, "D": 1.00},
}

# --- クラスタマッピング ---
CLUSTER_MAP = {
    "S": "大型", "A": "大型", "B": "大型",
    "C": "中型", "D": "中型",
    "E": "小型", "F": "小型"
}

def get_data():
    """Googleスプレッドシートからデータを取得"""
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # ttl=3600 (1時間) に設定することで、頻繁なリロードを防ぎつつ定期的に最新化
    # skiprows=124 でヘッダー行の位置を指定（ファイルの構造に合わせて調整してください）
    try:
        # worksheet引数でシート名またはインデックス(0始まり)を指定可能
        df = conn.read(skiprows=124, ttl=3600, usecols=None) 
        return df
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        return pd.DataFrame()

def get_rank_borders(df, size_category):
    """ ランクボーダー点数を計算 """
    target_df = df[df['規模判定'] == size_category].copy()
    target_df['総合P'] = pd.to_numeric(target_df['総合P'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    target_df = target_df.sort_values('総合P', ascending=False)
    
    total_count = len(target_df)
    borders = {}
    
    if total_count == 0:
        return borders

    thresholds = RANK_THRESHOLDS.get(size_category, RANK_THRESHOLDS["大型"])
    
    for rank, percentile in thresholds.items():
        border_index = int(total_count * percentile) - 1
        border_index = max(0, min(border_index, total_count - 1))
        score = target_df.iloc[border_index]['総合P']
        borders[rank] = score
        
    return borders

def main():
    st.set_page_config(page_title="店舗成果評価シミュレーター", layout="wide")
    st.title("🏆 店舗成果評価シミュレーター")
    st.caption("データソース: SYショップランキング (自動連携)")

    # 1. データ自動読み込み
    with st.spinner('最新のランキングデータを取得中...'):
        df = get_data()
    
    if not df.empty:
        # 列名チェックとクリーニング
        if '部門名' not in df.columns or '総合P' not in df.columns:
             # ヘッダー位置がずれている可能性の処理
             st.warning("列名が見つかりません。シートの形式が変わった可能性があります。")
             st.write("取得した列名:", df.columns.tolist())
             return

        # クラスタから規模を判定
        df['規模判定'] = df['ｸﾗｽﾀ'].map(CLUSTER_MAP).fillna("その他")
        
        # 2. 店舗選択
        stores = df['部門名'].unique()
        # 検索しやすいようにサイドバーに配置
        selected_store = st.sidebar.selectbox("自店舗を選択してください", stores)
        
        if selected_store:
            # 自店データの取得
            my_data = df[df['部門名'] == selected_store].iloc[0]
            my_score = float(str(my_data['総合P']).replace(',', ''))
            my_size = my_data['規模判定']
            my_rank = my_data['Rank'] if 'Rank' in my_data else '-'

            # メイン画面表示
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.header(f"{selected_store}")
                st.info(f"規模: {my_size} | 現在ランク: {my_rank}")
                st.metric(label="現在ポイント", value=f"{my_score:,.0f} pt")

            # 3. ランクボーダーの計算
            borders = get_rank_borders(df, my_size)
            
            with col2:
                st.subheader(f"📊 {my_size}店舗 ランクボーダー")
                b_cols = st.columns(len(borders))
                for i, (rank, score) in enumerate(borders.items()):
                    b_cols[i].metric(label=f"{rank}", value=f"{score:,.0f}")

            # 4. 目標設定とシミュレーション
            st.divider()
            st.subheader("🚀 ランクアップ・シミュレーション")
            
            target_rank = st.selectbox("目指すランクを選択", list(borders.keys()), index=0)
            target_score = borders[target_rank]
            gap = target_score - my_score
            
            if gap <= 0:
                st.success(f"🎉 現在 {target_rank} ランクの圏内です！（余裕: {abs(gap):,.0f} pt）")
            else:
                st.warning(f"🔥 {target_rank} ランクまで あと **{gap:,.0f} pt** 必要です")
                st.write("▼ 達成のための獲得目安（いずれか1つで達成）")
                
                sim_cols = st.columns(4)
                col_idx = 0
                
                for item_name, config in ITEMS_CONFIG.items():
                    needed_num = math.ceil(gap / config['coef'])
                    if needed_num > 0:
                        with sim_cols[col_idx % 4]:
                            st.metric(label=item_name, value=f"+{needed_num} 件", delta=f"係数 {config['coef']}")
                        col_idx += 1
                
            # データ更新時刻の目安（TTLの設定に依存）
            st.caption("※データは最大1時間キャッシュされます。最新の数値を反映するには右上のメニューから「Clear cache」を行ってください。")

if __name__ == "__main__":
    main()