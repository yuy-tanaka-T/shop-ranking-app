import streamlit as st
import pandas as pd

# ページ設定
st.set_page_config(page_title="店舗成果評価シミュレーター", layout="wide")

st.title("🏆 店舗成果評価シミュレーター")
st.markdown("手元のExcelファイルまたはCSVファイルをアップロードしてください。")

# --- ファイルアップロード機能 ---
uploaded_file = st.file_uploader("ここにファイルをドラッグ＆ドロップ", type=["xlsx", "xls", "csv"])

if uploaded_file is not None:
    try:
        # ファイル名で判断して、正しい「道具」を使う
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith('.xlsx'):
            # 新しいExcel形式 (.xlsx) は openpyxl を使う
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        else:
            # 古いExcel形式 (.xls) は xlrd を使う、または自動判定
            df = pd.read_excel(uploaded_file)
            
        st.success("✅ ファイル読み込み成功！")
        
        # --- データ表示エリア ---
        st.subheader("📊 データ一覧")
        st.dataframe(df)

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
else:
    st.info("👆 上のボックスからデータをアップロードすると、分析結果が表示されます。")
