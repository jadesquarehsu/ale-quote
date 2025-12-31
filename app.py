import streamlit as st
import pandas as pd
import numpy as np
from urllib.parse import quote
import os

# --- 1. 網頁基本設定 ---
st.set_page_config(page_title="ALÉ 專業報價系統", layout="wide")

# ==========================================
# 🔐 安全密碼鎖
# ==========================================
PASSWORD = "8017"

input_pass = st.sidebar.text_input("🔒 請輸入通關密碼", type="password")

if input_pass != PASSWORD:
    st.sidebar.warning("❌ 未輸入或密碼錯誤")
    st.markdown("## 🔒 系統已鎖定")
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
        # 讀取 CSV
        df = pd.read_csv(SHEET_URL, encoding='utf-8')
        # 強制把 Item_No 轉成字串
        if 'Item_No' in df.columns:
            df['Item_No'] = df['Item_No'].astype(str).str.strip()
        return df
    except:
        return None

# --- 4. 計算邏輯 ---
FREIGHT_MAP = {'A': 45, 'B': 63, 'C': 103, 'D': 13, 'E': 22}

def calc_price(row, src_col, design, service, margin, rate):
    try:
        p_price = float(row[src_col])
        if pd.isna(p_price) or p_price <= 0: return 0.0 # 改回傳 0.0 避免 NaN 導致報錯
        
        f_code = str(row['freight']).strip().upper() if 'freight' in row and pd.notna(row['freight']) else 'A'
        ship = FREIGHT_MAP.get(f_code, 45)
        
        duty = 0.125 if (pd.notna(row['DYED']) and str(row['DYED']).strip()!="") else 0.105
        
        cost = (p_price * rate) * (1 + 0.05 + duty) + ship
        return round((cost + design + service) / (1 - margin))
    except:
        return 0.0 # 出錯回傳 0

# 回呼函數：確保按鈕點擊有效
def add_to_cart_callback(item_dict):
    st.session_state.cart.append(item_dict)
    st.toast(f"✅ 已加入 {item_dict.get('Item_No', '產品')}")

# 載入資料
df_raw = load_data()

if df_raw is None:
    st.error("❌ 無法讀取資料，請檢查 Google Sheet 權限。")
    st.stop()

df_raw.columns = df_raw.columns.str.strip()

# --- 6. 參數設定面板 ---
st.sidebar.success("✅ 已解鎖")
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

# --- 7. 執行計算與過濾 ---
df = df_raw.copy()

df['10-15PCS'] = df.apply(lambda r: calc_price(r, '10-59', 300, 100, m1, rate), axis=1)
df['16-29PCS'] = df.apply(lambda r: calc_price(r, '10-59', 200, 62, m2, rate), axis=1)
df['30-59PCS'] = df.apply(lambda r: calc_price(r, '10-59', 150, 33, m3, rate), axis=1)

if sel_line != "全部": df = df[df['Line_code'] == sel_line]
if sel_cate != "全部": df = df[df['Category'] == sel_cate]
if sel_gend != "全部": df = df[df['Gender'] == sel_gend]
if search_kw: 
    df = df[
        df['Description_CH'].str.contains(search_kw, na=False, case=False) | 
        df['Item_No'].str.contains(search_kw, na=False)
    ]

# --- 8. 主畫面顯示 ---
st.title("🛡️ ALÉ 代理商專業報價系統")

if 'cart' not in st.session_state:
    st.session_state.cart = []

col_main, col_cart = st.columns([2, 1])

# === 左側：搜尋結果 ===
with col_main:
    st.subheader(f"📦 搜尋結果 ({len(df)} 筆)")
    if df.empty:
        st.info("查無產品")
    else:
        for _, row in df.head(50).iterrows():
            gender_label = f"({row['Gender']})" if 'Gender' in row and pd.notna(row['Gender']) else ""
            with st.expander(f"➕ {row['Item_No']} {gender_label} - {row['Description_CH']}"):
                
                # 顯示圖片
                item_no_str = str(row['Item_No']).strip()
                img_path_png = f"images/{item_no_str}.png"
                img_path_jpg = f"images/{item_no_str}.jpg"
                
                if os.path.exists(img_path_png):
                    st.image(img_path_png, width=300)
                elif os.path.exists(img_path_jpg):
                    st.image(img_path_jpg, width=300)
                
                # 顯示資訊
                note = row['NOTE'] if pd.notna(row['NOTE']) else "無"
                st.write(f"**備註：** {note}")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("10-15pcs", f"${row['10-15PCS']:,}")
                c2.metric("16-29pcs", f"${row['16-29PCS']:,}")
                c3.metric("30-59pcs", f"${row['30-59PCS']:,}")
                
                # 加入按鈕
                st.button(
                    "加入報價單", 
                    key=f"btn_{row['Item_No']}",
                    on_click=add_to_cart_callback,
                    args=(row.to_dict(),)
                )

# === 右側：報價清單 (終極防錯版) ===
with col_cart:
    st.subheader(f"🛒 報價清單 ({len(st.session_state.cart)})")
    
    if st.session_state.cart:
        if st.button("🗑️ 清空全部"):
            st.session_state.cart = []
            st.rerun()
        
        st.divider()

        # 這裡加了 try-except 保護機制
        for i, item in enumerate(st.session_state.cart):
            try:
                # 1. 準備資料 (防呆)
                i_no = str(item.get('Item_No', '未知型號')).strip()
                
                # 2. 處理價格 (確保一定是數字，不是 None 或 NaN)
                def safe_price(val):
                    try:
                        return float(val) if pd.notna(val) else 0.0
                    except:
                        return 0.0
                
                p1 = safe_price(item.get('10-15PCS', 0))
                p2 = safe_price(item.get('16-29PCS', 0))
                
                # 3. 顯示介面
                c_img, c_text = st.columns([1, 2])
                
                with c_img:
                    path_png = f"images/{i_no}.png"
                    path_jpg = f"images/{i_no}.jpg"
                    if os.path.exists(path_png):
                        st.image(path_png, use_container_width=True)
                    elif os.path.exists(path_jpg):
                        st.image(path_jpg, use_container_width=True)
                    else:
                        st.write("📷") 
                
                with c_text:
                    st.markdown(f"**{i_no}**")
                    # 使用安全的 f-string 格式化
                    st.write(f"10-15pcs: **${p1:,.0f}**")
                    st.caption(f"16-29pcs: ${p2:,.0f}")
                
                st.divider()
            
            except Exception as e:
                # 如果這筆資料真的壞了，印出紅色錯誤訊息，而不是空白
                st.error(f"顯示錯誤: {e}")

    else:
        st.info("尚未選取產品")
