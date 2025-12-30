import streamlit as st
import pandas as pd
import numpy as np
import urllib.parse

# --- [關鍵] 這行必須是程式碼中第一個出現的 st 指令 ---
st.set_page_config(page_title="ALÉ 專業報價系統", layout="wide")

# --- 1. 設定 Google Sheet ID (請務必檢查此處的 ID 是否正確) ---
SHEET_ID = "1LNaFoDOAr08LGxQ8cCRSSff7U7OU5ABH" 
SHEET_NAME = "Sheet1" 

# 安全處理網址編碼，避免 ascii 錯誤
try:
    encoded_sheet_name = urllib.parse.quote(SHEET_NAME)
    SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={encoded_sheet_name}"
except Exception as e:
    st.error(f"網址轉換出錯: {e}")

# --- 2. 讀取與計算邏輯 ---
@st.cache_data(ttl=300)
def load_data():
    # 強制指定 utf-8 並使用 csv 格式讀取，這最穩定
    return pd.read_csv(SHEET_URL, encoding='utf-8')

FREIGHT_MAP = {'A': 45, 'B': 63, 'C': 103, 'D': 13, 'E': 22}

def calc_price(row, src_col, design, service, margin, rate):
    try:
        p_price = float(row[src_col])
        if pd.isna(p_price) or p_price <= 0: return np.nan
        f_code = str(row['freight']).strip().upper() if 'freight' in row and pd.notna(row['freight']) else 'A'
        ship = FREIGHT_MAP.get(f_code, 45)
        duty = 0.125 if (pd.notna(row['DYED']) and str(row['DYED']).strip()!="") else 0.105
        cost = (p_price * rate) * (1 + 0.05 + duty) + ship
        return round((cost + design + service) / (1 - margin))
    except: return np.nan

# --- 3. 執行資料載入 ---
try:
    df_raw = load_data()
    # 確保欄位名稱沒有空格
    df_raw.columns = df_raw.columns.str.strip()
except Exception as e:
    st.error(f"❌ 無法讀取試算表。請確認 ID 正確且已開啟「知道連結的人皆可檢視」。")
    st.info(f"技術錯誤訊息: {e}")
    st.stop()

# --- 4. 介面與顯示 ---
st.sidebar.header("⚙️ 報價參數設定")
rate = st.sidebar.number_input("當前匯率", value=35.0, step=0.1)

st.sidebar.markdown("---")
st.sidebar.header("📈 自定義利潤率 (%)")
m1 = st.sidebar.slider("10-15pcs 利潤", 10, 60, 40) / 100
m2 = st.sidebar.slider("16-29pcs 利潤", 10, 60, 35) / 100
m3 = st.sidebar.slider("30-59pcs 利潤", 10, 60, 30) / 100

# 篩選選單
st.sidebar.markdown("---")
line_opt = ["全部"] + sorted(df_raw['Line_code'].dropna().unique().tolist())
cate_opt = ["全部"] + sorted(df_raw['Category'].dropna().unique().tolist())
sel_line = st.sidebar.selectbox("系列", line_opt)
sel_cate = st.sidebar.selectbox("類型", cate_opt)
search_kw = st.sidebar.text_input("搜尋關鍵字")

# 計算與過濾
df = df_raw.copy()
df['10-15PCS'] = df.apply(lambda r: calc_price(r, '10-59', 300, 100, m1, rate), axis=1)
df['16-29PCS'] = df.apply(lambda r: calc_price(r, '10-59', 200, 62, m2, rate), axis=1)
df['30-59PCS'] = df.apply(lambda r: calc_price(r, '10-59', 150, 33, m3, rate), axis=1)

if sel_line != "全部": df = df[df['Line_code'] == sel_line]
if sel_cate != "全部": df = df[df['Category'] == sel_cate]
if search_kw: df = df[df['Description_CH'].str.contains(search_kw, na=False, case=False)]

st.title("🛡️ ALÉ 代理商專業報價系統")
st.dataframe(df[['Item_No', 'Description_CH', '10-15PCS', '16-29PCS', '30-59PCS']].head(50))
