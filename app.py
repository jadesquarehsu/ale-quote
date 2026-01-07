import streamlit as st
import pandas as pd
import numpy as np
from urllib.parse import quote
import os
import io
from PIL import Image
from datetime import datetime, timedelta

# --- 1. 網頁基本設定 ---
st.set_page_config(page_title="ALÉ 專業報價系統", page_icon="🚴", layout="wide")

# ==========================================
# 🔐 安全密碼鎖
# ==========================================
PASSWORD = "8017"

input_pass = st.sidebar.text_input("🔒 請輸入通關密碼", type="password")

if input_pass != PASSWORD:
    st.sidebar.warning("❌ 未輸入或密碼錯誤")
    st.markdown("## 🔒 系統已鎖定")
    st.info("⚠️ 請在左側輸入密碼以存取報價系統。")
    st.stop() 

# ==========================================
# 🔓 驗證通過區
# ==========================================

# --- 2. Google Sheet 設定 ---
SHEET_ID = "1LNaFoDOAr08LGxQ8cCRSSff7U7OU5ABH" 
SHEET_NAME = "Sheet1" 

try:
    encoded_sheet_name = quote(SHEET_NAME)
    SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={encoded_sheet_name}"
except:
    SHEET_URL = ""

# --- 3. 讀取資料 ---
@st.cache_data(ttl=300)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL, encoding='utf-8')
        if 'Item_No' in df.columns:
            df['Item_No'] = df['Item_No'].astype(str).str.strip()
        
        for col in ['pic code_1', 'pic code_2']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
            else:
                df[col] = "" 
                
        return df
    except:
        return None

# --- 4. 計算邏輯 ---
FREIGHT_MAP = {'A': 45, 'B': 63, 'C': 103, 'D': 13, 'E': 22}

def calc_price(row, src_col, design, service, margin, rate):
    try:
        p_price = float(row[src_col])
        if pd.isna(p_price) or p_price <= 0: return 0.0
        
        f_code = str(row['freight']).strip().upper() if 'freight' in row and pd.notna(row['freight']) else 'A'
        ship = FREIGHT_MAP.get(f_code, 45)
        
        duty = 0.125 if (pd.notna(row['DYED']) and str(row['DYED']).strip()!="") else 0.105
        
        cost = (p_price * rate) * (1 + 0.05 + duty) + ship
        return round((cost + design + service) / (1 - margin))
    except:
        return 0.0

# 找圖功能的強力邏輯
def find_image_robust(filename):
    if not filename or str(filename).lower() == "nan" or str(filename).strip() == "":
        return None
    
    clean_name = str(filename).strip()
    base_name = clean_name
    if "." in clean_name:
        base_name = clean_name.rsplit('.', 1)[0]
    
    candidates = [
        clean_name,
        f"{clean_name}.png", f"{clean_name}.PNG",
        f"{clean_name}.jpg", f"{clean_name}.JPG",
        f"{base_name}.png", f"{base_name}.PNG",
        f"{base_name}.jpg", f"{base_name}.JPG"
    ]
    
    for c in candidates:
        path = f"images/{c}"
        if os.path.exists(path):
            return path
            
    return None

# 回呼函數
def add_to_cart_callback(item_dict):
    st.session_state.cart.append(item_dict)
    st.toast(f"✅ 已加入 {item_dict.get('Item_No', '產品')}")

# 載入資料
df_raw = load_data()

if df_raw is None:
    st.error("❌ 無法讀取資料，請檢查 Google Sheet 權限。")
    st.stop()

df_raw.columns = df_raw.columns.str.strip()

# --- 5. 參數設定 (左側選單) ---
st.sidebar.success("✅ 已解鎖")
st.sidebar.markdown("---")

# 客戶資訊輸入區
st.sidebar.header("📝 客戶資訊 (填寫後會印在報價單)")
client_team = st.sidebar.text_input("隊名")
client_contact = st.sidebar.text_input("聯絡人")
client_phone = st.sidebar.text_input("電話")
client_address = st.sidebar.text_input("地址")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ 參數設定")
rate = st.sidebar.number_input("當前匯率", value=35.0, step=0.1)

with st.sidebar.expander("📈 進階利潤率設定 (點擊展開)"):
    m1 = st.slider("10-15pcs (%)", 10, 60, 40) / 100
    m2 = st.slider("16-29pcs (%)", 10, 60, 35) / 100
    m3 = st.slider("30-59pcs (%)", 10, 60, 30) / 100

st.sidebar.markdown("---")
line_opt = ["全部"] + sorted(df_raw['Line_code'].dropna().unique().tolist()) if 'Line_code' in df_raw.columns else ["全部"]
cate_opt = ["全部"] + sorted(df_raw['Category'].dropna().unique().tolist()) if 'Category' in df_raw.columns else ["全部"]
gend_opt = ["全部"] + sorted(df_raw['Gender'].dropna().unique().tolist()) if 'Gender' in df_raw.columns else ["全部"]

sel_line = st.sidebar.selectbox("系列篩選", line_opt)
sel_cate = st.sidebar.selectbox("類型篩選", cate_opt)
sel_gend = st.sidebar.selectbox("性別篩選", gend_opt)
search_kw = st.sidebar.text_input("搜尋關鍵字")

# --- 6. 執行計算與篩選 ---
df = df_raw.copy()

df['10-15PCS'] = df.apply(lambda r: calc_price(r
