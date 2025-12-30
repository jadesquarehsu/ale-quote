import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF

# --- 填入你的 Google Sheet ID ---
# 請將下方的 ID 換成你自己的試算表 ID
SHEET_ID = "1LNaFoDOAr08LGxQ8cCRSSff7U7OU5ABH" 
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"

# 設定網頁
st.set_page_config(page_title="ALÉ 報價系統 (Google 版)", layout="wide")

# 運費代碼
FREIGHT_MAP = {'A': 45, 'B': 63, 'C': 103, 'D': 13, 'E': 22}

# 計算邏輯
def calc_price(row, src_col, design, service, margin, rate):
    try:
        p_price = float(row[src_col])
        if pd.isna(p_price) or p_price <= 0: return np.nan
        f_code = str(row['freight']).strip().upper() if 'freight' in row else 'A'
        ship = FREIGHT_MAP.get(f_code, 45)
        duty = 0.125 if (pd.notna(row['DYED']) and str(row['DYED']).strip()!="") else 0.105
        cost = (p_price * rate) * (1 + 0.05 + duty) + ship
        return round((cost + design + service) / (1 - margin))
    except: return np.nan

# 讀取 Google Sheet 資料 (加上快取，每小時重新抓取一次)
@st.cache_data(ttl=3600)
def load_data_from_google():
    try:
        return pd.read_excel(SHEET_URL)
    except Exception as e:
        st.error(f"連線 Google Sheets 失敗: {e}")
        return None

df_raw = load_data_from_google()

if df_raw is not None:
    # --- 側邊欄：利潤調整 (應您的需求加入) ---
    st.sidebar.header("⚙️ 報價參數設定")
    rate = st.sidebar.number_input("匯率", value=35.0, step=0.1)
    
    st.sidebar.markdown("---")
    st.sidebar.header("📈 自定義利潤率 (%)")
    m1 = st.sidebar.slider("10-15pcs 利潤", 10, 60, 40) / 100
    m2 = st.sidebar.slider("16-29pcs 利潤", 10, 60, 35) / 100
    m3 = st.sidebar.slider("30-59pcs 利潤", 10, 60, 30) / 100

    # 搜尋與篩選 (與之前相同)
    # ... [此處省略部分重複的篩選 UI 程式碼]

    # 計算價格 (帶入滑桿的利潤率)
    df = df_raw.copy()
    df['10-15PCS'] = df.apply(lambda r: calc_price(r, '10-59', 300, 100, m1, rate), axis=1)
    df['16-29PCS'] = df.apply(lambda r: calc_price(r, '10-59', 200, 62, m2, rate), axis=1)
    df['30-59PCS'] = df.apply(lambda r: calc_price(r, '10-59', 150, 33, m3, rate), axis=1)
    # ... 其他級距以此類推

    st.success("✅ 資料已同步 Google Sheets 最更新版本")
    # [顯示產品清單與購物車邏輯]
