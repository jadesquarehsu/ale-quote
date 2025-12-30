import streamlit as st
import pandas as pd
import numpy as np
import urllib.parse

# --- 1. [絕對核心] 設定必須放第一行 ---
st.set_page_config(page_title="ALÉ 專業報價系統", layout="wide")

# ==========================================
# 🔐 安全登入檢查 (新增區塊)
# ==========================================
# 請在這裡設定您的密碼
LOGIN_PASSWORD = "8017"

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

def check_password():
    if st.session_state.password_input == LOGIN_PASSWORD:
        st.session_state.logged_in = True
    else:
        st.error("❌ 密碼錯誤，請重新輸入")

if not st.session_state.logged_in:
    st.markdown("## 🔒 系統鎖定中")
    st.text_input("請輸入內部存取密碼：", type="password", key="password_input", on_change=check_password)
    st.stop()  # 密碼不對就停止執行下面的程式，什麼都看不到

# ==========================================
# 🔓 登入成功後才會執行以下內容
# ==========================================

# --- 2. Google Sheet 設定 ---
# 請確認 ID 是否正確
SHEET_ID = "1gS_uG7FLrYl94y_--X8rO-WB910d65bSjB-H_V8o4b0" 
SHEET_NAME = "Sheet1" 

try:
    encoded_sheet_name = urllib.parse.quote(SHEET_NAME)
    SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={encoded_sheet_name}"
except:
    SHEET_URL = ""

# --- 3. 讀取與計算 ---
@st.cache_data(ttl=300)
def load_data():
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

try:
    df_raw = load_data()
    df_raw.columns = df_raw.columns.str.strip()
except Exception as e:
    st.error("❌ 無法讀取資料，請檢查 Google Sheet 權限。")
    st.stop()

# --- 4. 側邊欄設定 ---
st.sidebar.success("🔓 已登入")
st.sidebar.header("⚙️ 報價參數設定")
rate = st.sidebar.number_input("當前匯率", value=35.0, step=0.1)

st.sidebar.markdown("---")
# 這裡稍微隱藏一下利潤率，把它收進一個折疊選單裡，避免太顯眼
with st.sidebar.expander("📈 進階利潤設定 (點擊展開)"):
    m1 = st.slider("10-15pcs 利潤", 10, 60, 40) / 100
    m2 = st.slider("16-29pcs 利潤", 10, 60, 35) / 100
    m3 = st.slider("30-59pcs 利潤", 10, 60, 30) / 100

st.sidebar.markdown("---")
line_opt = ["全部"] + sorted(df_raw['Line_code'].dropna().unique().tolist())
cate_opt = ["全部"] + sorted(df_raw['Category'].dropna().unique().tolist())
sel_line = st.sidebar.selectbox("系列", line_opt)
sel_cate = st.sidebar.selectbox("類型", cate_opt)
search_kw = st.sidebar.text_input("搜尋關鍵字 (貨號/品名)")

# 計算與篩選
df = df_raw.copy()
df['10-15PCS'] = df.apply(lambda r: calc_price(r, '10-59', 300, 100, m1, rate), axis=1)
df['16-29PCS'] = df.apply(lambda r: calc_price(r, '10-59', 200, 62, m2, rate), axis=1)
df['30-59PCS'] = df.apply(lambda r: calc_price(r, '10-59', 150, 33, m3, rate), axis=1)

if sel_line != "全部": df = df[df['Line_code'] == sel_line]
if sel_cate != "全部": df = df[df['Category'] == sel_cate]
if search_kw: 
    df = df[
        df['Description_CH'].str.contains(search_kw, na=False, case=False) | 
        df['Item_No'].astype(str).str.contains(search_kw, na=False)
    ]

# --- 5. 主畫面與購物車 ---
st.title("🛡️ ALÉ 代理商專業報價系統")

if 'cart' not in st.session_state:
    st.session_state.cart = []

col_main, col_cart = st.columns([2, 1])

with col_main:
    st.subheader(f"📦 產品搜尋結果 ({len(df)} 筆)")
    if df.empty:
        st.info("查無符合條件的產品。")
    else:
        for _, row in df.head(50).iterrows():
            with st.expander(f"➕ {row['Item_No']} - {row['Description_CH']}"):
                st.write(f"**備註：** {row['NOTE']}")
                c1, c2, c3 = st.columns(3)
                c1.metric("10-15pcs", f"${row['10-15PCS']:,}")
                c2.metric("16-29pcs", f"${row['16-29PCS']:,}")
                c3.metric("30-59pcs", f"${row['30-59PCS']:,}")
                
                if st.button("加入報價單", key=f"add_{row['Item_No']}"):
                    st.session_state.cart.append(row.to_dict())
                    st.toast(f"✅ 已加入 {row['Item_No']}")

with col_cart:
    st.subheader("🛒 報價清單")
    if st.session_state.cart:
        cart_df = pd.DataFrame(st.session_state.cart)
        st.dataframe(cart_df[['Item_No', '10-15PCS', '16-29PCS']], use_container_width=True)
        if st.button("🗑️ 清空全部"):
            st.session_state.cart = []
            st.rerun()
    else:
        st.info("尚未選取產品")
