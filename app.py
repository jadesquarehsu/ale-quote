import streamlit as st
import pandas as pd
import numpy as np
import os

# --- 1. 設定 Google Sheet ID ---
# 請將這裡換成您 Google 試算表網址中的那串 ID
SHEET_ID = "1LNaFoDOAr08LGxQ8cCRSSff7U7OU5ABH" 
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"

# 網頁基本設定
st.set_page_config(page_title="ALÉ 專業報價系統", layout="wide")

# 運費代碼換算
FREIGHT_MAP = {'A': 45, 'B': 63, 'C': 103, 'D': 13, 'E': 22}

# 核心計算邏輯
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

# 讀取資料並加上快取
@st.cache_data(ttl=300) # 每 5 分鐘自動刷新一次
def load_data():
    return pd.read_excel(SHEET_URL)

try:
    df_raw = load_data()
    st.sidebar.success("✅ 資料已同步 Google Sheets")
except Exception as e:
    st.error(f"❌ 無法讀取 Google 試算表，請確認 ID 正確且已開啟「知道連結的任何人皆可檢視」。錯誤資訊: {e}")
    st.stop()

# --- 2. 介面設定 ---
st.sidebar.header("⚙️ 報價參數設定")
rate = st.sidebar.number_input("當前匯率", value=35.0, step=0.1)

st.sidebar.markdown("---")
st.sidebar.header("📈 自定義利潤率 (%)")
m1 = st.sidebar.slider("10-15pcs 利潤", 10, 60, 40) / 100
m2 = st.sidebar.slider("16-29pcs 利潤", 10, 60, 35) / 100
m3 = st.sidebar.slider("30-59pcs 利潤", 10, 60, 30) / 100

# 篩選選單
st.sidebar.markdown("---")
st.sidebar.header("🔍 產品搜尋")
line_opt = ["全部"] + sorted(df_raw['Line_code'].dropna().unique().tolist())
cate_opt = ["全部"] + sorted(df_raw['Category'].dropna().unique().tolist())
gend_opt = ["全部"] + sorted(df_raw['Gender'].dropna().unique().tolist())

sel_line = st.sidebar.selectbox("系列", line_opt)
sel_cate = st.sidebar.selectbox("類型", cate_opt)
sel_gend = st.sidebar.selectbox("性別", gend_opt)
search_kw = st.sidebar.text_input("搜尋產品名稱或 Item No")

# --- 3. 計算與過濾 ---
df = df_raw.copy()
# 執行計算 (帶入滑動條的利潤率)
df['10-15PCS'] = df.apply(lambda r: calc_price(r, '10-59', 300, 100, m1, rate), axis=1)
df['16-29PCS'] = df.apply(lambda r: calc_price(r, '10-59', 200, 62, m2, rate), axis=1)
df['30-59PCS'] = df.apply(lambda r: calc_price(r, '10-59', 150, 33, m3, rate), axis=1)

# 過濾邏輯
if sel_line != "全部": df = df[df['Line_code'] == sel_line]
if sel_cate != "全部": df = df[df['Category'] == sel_cate]
if sel_gend != "全部": df = df[df['Gender'] == sel_gend]
if search_kw:
    df = df[
        df['Description_CH'].str.contains(search_kw, na=False, case=False) | 
        df['Item_No'].astype(str).str.contains(search_kw, na=False)
    ]

# --- 4. 主畫面顯示 ---
st.title("🛡️ ALÉ 代理商專業報價系統")

# 初始化購物車
if 'cart' not in st.session_state: st.session_state.cart = []

col_main, col_cart = st.columns([2, 1])

with col_main:
    st.subheader(f"📦 產品列表 ({len(df)} 筆)")
    if df.empty:
        st.info("查無符合條件的產品。")
    else:
        for _, row in df.head(50).iterrows():
            with st.expander(f"➕ {row['Item_No']} - {row['Description_CH']}"):
                c1, c2, c3 = st.columns(3)
                c1.metric("10-15pcs", f"${row['10-15PCS']:,}")
                c2.metric("16-29pcs", f"${row['16-29PCS']:,}")
                c3.metric("30-59pcs", f"${row['30-59PCS']:,}")
                if st.button("加入報價清單", key=f"add_{row['Item_No']}"):
                    st.session_state.cart.append(row.to_dict())
                    st.toast(f"✅ {row['Item_No']} 已加入")

with col_cart:
    st.subheader("🛒 報價清單預覽")
    if st.session_state.cart:
        cart_df = pd.DataFrame(st.session_state.cart)
        st.table(cart_df[['Item_No', '10-15PCS', '16-29PCS', '30-59PCS']])
        if st.button("🗑️ 清空清單"):
            st.session_state.cart = []
            st.rerun()
    else:
        st.write("尚未選取任何產品")
