import streamlit as st
import pandas as pd
import numpy as np
import os
from fpdf import FPDF
from datetime import datetime

# --- 設定網頁標題與風格 ---
st.set_page_config(page_title="ALÉ 專業報價系統", layout="wide")

# 運費代碼換算
FREIGHT_MAP = {'A': 45, 'B': 63, 'C': 103, 'D': 13, 'E': 22}

# --- 核心計算邏輯 ---
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

# --- 讀取資料 ---
@st.cache_data # 效能優化：這會讓網頁讀取更快
def load_data():
    if os.path.exists('data_ale.xlsx'):
        return pd.read_excel('data_ale.xlsx')
    return None

df_raw = load_data()

if df_raw is None:
    st.error("❌ 找不到 data_ale.xlsx，請確認檔案已上傳。")
else:
    # --- 側邊欄設定 ---
    st.sidebar.header("📊 全域參數設定")
    rate = st.sidebar.number_input("當前匯率", value=35.0, step=0.1)
    
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 篩選條件")
    line_opt = ["全部"] + sorted(df_raw['Line_code'].dropna().unique().tolist())
    cate_opt = ["全部"] + sorted(df_raw['Category'].dropna().unique().tolist())
    gend_opt = ["全部"] + sorted(df_raw['Gender'].dropna().unique().tolist())
    
    sel_line = st.sidebar.selectbox("選擇系列", line_opt)
    sel_cate = st.sidebar.selectbox("選擇類型", cate_opt)
    sel_gend = st.sidebar.selectbox("選擇性別", gend_opt)
    search_kw = st.sidebar.text_input("產品名稱關鍵字搜尋")

    # --- 計算報價 ---
    df = df_raw.copy()
    df['10-15PCS'] = df.apply(lambda r: calc_price(r, '10-59', 300, 100, 0.40, rate), axis=1)
    df['16-29PCS'] = df.apply(lambda r: calc_price(r, '10-59', 200, 62, 0.35, rate), axis=1)
    df['30-59PCS'] = df.apply(lambda r: calc_price(r, '10-59', 150, 33, 0.30, rate), axis=1)
    df['60-99PCS'] = df.apply(lambda r: calc_price(r, '60-99', 100, 33, 0.30, rate), axis=1)
    df['100-199PCS'] = df.apply(lambda r: calc_price(r, '100-199', 60, 30, 0.30, rate), axis=1)

    # --- 執行篩選 ---
    if sel_line != "全部": df = df[df['Line_code'] == sel_line]
    if sel_cate != "全部": df = df[df['Category'] == sel_cate]
    if sel_gend != "全部": df = df[df['Gender'] == sel_gend]
    if search_kw: df = df[df['Description_CH'].str.contains(search_kw, na=False, case=False)]

    # --- 主介面顯示 ---
    st.title("🛡️ ALÉ 代理商專業報價系統")
    
    # 購物車初始化
    if 'cart' not in st.session_state: st.session_state.cart = []

    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📦 產品搜尋結果")
        display_cols = ['Item_No', 'Description_CH', '10-15PCS', '16-29PCS', '30-59PCS', '60-99PCS', '100-199PCS']
        
        # 顯示搜尋結果並提供加入按鈕
        for _, row in df.head(20).iterrows():
            with st.expander(f"➕ {row['Item_No']} - {row['Description_CH']}"):
                st.write(f"性別: {row['Gender']} | 備註: {row['NOTE']}")
                c_btn1, c_btn2, c_btn3, c_btn4, c_btn5 = st.columns(5)
                c_btn1.metric("10-15pcs", f"${row['10-15PCS']:,}")
                c_btn2.metric("16-29pcs", f"${row['16-29PCS']:,}")
                c_btn3.metric("30-59pcs", f"${row['30-59PCS']:,}")
                if st.button(f"加入報價清單", key=row['Item_No']):
                    st.session_state.cart.append(row.to_dict())
                    st.toast(f"✅ {row['Item_No']} 已加入")

    with col2:
        st.subheader("🛒 報價清單預覽")
        if st.session_state.cart:
            cart_df = pd.DataFrame(st.session_state.cart)
            st.dataframe(cart_df[['Item_No', '10-15PCS', '16-29PCS']])
            if st.button("🗑️ 清空清單"):
                st.session_state.cart = []
                st.rerun()
            
            # 這裡可以加入導出 PDF 的邏輯 (為了簡化，先以網頁顯示為主)
        else:
            st.info("尚未選取產品")