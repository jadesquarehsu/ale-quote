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

# --- 4. 主畫面顯示 ---
# --- 4. 主畫面佈局與購物車 ---
st.title("🛡️ ALÉ 代理商專業報價系統")

# 初始化購物車（如果還沒建立過）
if 'cart' not in st.session_state:
    st.session_state.cart = []

# 建立左右兩欄：左邊產品列表，右邊報價清單
col_main, col_cart = st.columns([2, 1])

with col_main:
    st.subheader(f"📦 產品搜尋結果 ({len(df)} 筆)")
    if df.empty:
        st.info("查無符合條件的產品，請調整左側篩選條件。")
    else:
        # 使用迴圈產生每一列產品，並附上加入按鈕
        for _, row in df.head(50).iterrows():
            # 建立摺疊區塊方便瀏覽
            with st.expander(f"➕ {row['Item_No']} - {row['Description_CH']}"):
                st.write(f"**性別：** {row['Gender']} | **備註：** {row['NOTE']}")
                
                # 顯示三個關鍵階層的報價
                m_col1, m_col2, m_col3 = st.columns(3)
                m_col1.metric("10-15pcs", f"${row['10-15PCS']:,}")
                m_col2.metric("16-29pcs", f"${row['16-29PCS']:,}")
                m_col3.metric("30-59pcs", f"${row['30-59PCS']:,}")
                
                # 獨立的加入按鈕，點擊後會存入 session_state.cart
                if st.button("加入報價單", key=f"btn_{row['Item_No']}"):
                    st.session_state.cart.append(row.to_dict())
                    st.toast(f"✅ {row['Item_No']} 已加入")

with col_cart:
    st.subheader("🛒 報價清單預覽")
    if st.session_state.cart:
        cart_df = pd.DataFrame(st.session_state.cart)
        # 只顯示關鍵欄位讓清單簡潔
        st.dataframe(cart_df[['Item_No', '10-15PCS', '16-29PCS', '30-59PCS']], use_container_width=True)
        
        # 提供清空按鈕
        if st.button("🗑️ 清空清單"):
            st.session_state.cart = []
            st.rerun()
    else:
        st.info("尚未選取產品，請從左側列表點擊「加入報價單」。")
