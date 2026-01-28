import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# タイトル
st.title("🏆 店舗成果評価シミュレーター")

# 接続の作成
conn = st.connection("gsheets", type=GSheetsConnection)

# データの読み込み（キャッシュを使って高速化）
@st.cache_data(ttl=600)
def load_data():
    # スプレッドシートの全データを読み込む
    df = conn.read()
    return df

try:
    # データ読み込み実行
    df = load_data()

    # データが空でないか確認
    if df is not None and not df.empty:
        st.success("✅ データ取得成功！")
        
        # データの表示
        st.subheader("現在のデータ一覧")
        st.dataframe(df)

        # ここに集計ロジックなどを追加できます
        # 例: st.bar_chart(df, x='店舗名', y='売上')
        
    else:
        st.warning("データが見つかりませんでした。スプレッドシートにデータがあるか確認してください。")

except Exception as e:
    st.error("エラーが発生しました。")
    st.error(f"詳細: {e}")
    st.info("ヒント: Secretsの設定（URL）や、スプレッドシートの共有設定（リンクを知っている全員）を確認してください。")
